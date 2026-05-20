"""AI 章节续写路由：SSE 流式生成章节内容。

POST /api/llm/generate-chapters
请求: { novel_id, num_chapters }
响应: text/event-stream

每次调用在已有章节末尾追加指定数量的章节。
每章完成后自动提取并创建新实体。
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
import yaml
from pathlib import Path
from typing import AsyncGenerator
from uuid import uuid4

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from application.llm.config import get_provider_config
from application.services.llm.workflow_service import get_llm_service_for_step, resolve_provider_for_step
from application.services.llm.format_review_service import validate_and_fix_format
from application.services.novel.context_builder_service import build_chapter_context
from application.services.novel.entity_extraction_service import (
    extract_and_create_entities,
    resolve_appeared_refs,
)
from application.services.novel.plot_outline_service import format_plot_point_context
from application.db.repositories.chapter_repository import chapter_repo
from application.db.repositories.novel_repository import novel_repo
from application.db.repositories.outline_repository import outline_repo
from application.db.repositories.knowledge_repository import novel_knowledge_link_repo
from pydantic_definitions.chapter_generation_pydantic import ChapterWriteResult

router = APIRouter(prefix="/api/llm", tags=["llm"])

PROMPT_PATH = Path(__file__).resolve().parents[3] / "prompt_definitions" / "prompt_default.yaml"
WORKFLOW_NAME = "generate_chapters"
logger = logging.getLogger(__name__)


def _load_prompts() -> dict:
    with PROMPT_PATH.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _check_json_schema_support(step_name: str) -> bool:
    provider = resolve_provider_for_step(WORKFLOW_NAME, step_name)
    if not provider:
        return False
    return get_provider_config(provider).supports_json_schema


def _sse_event(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


class GenerateChaptersRequest(BaseModel):
    novel_id: str = Field(..., min_length=1, description="小说 ID")
    num_chapters: int = Field(..., gt=0, le=50, description="本次生成的章节数量（1-50）")
    use_knowledge: bool = Field(default=False, description="是否结合知识库内容进行创作")
    temperature: float | None = Field(default=None, ge=0, le=2)
    top_p: float | None = Field(default=None, ge=0, le=1)
    max_tokens: int | None = Field(default=None, gt=0)
    presence_penalty: float | None = Field(default=None, ge=-2, le=2)
    frequency_penalty: float | None = Field(default=None, ge=-2, le=2)
    system_prompt: str | None = Field(default=None)


def _build_gen_kwargs(req: GenerateChaptersRequest) -> dict:
    kwargs: dict = {}
    for key in ("temperature", "top_p", "max_tokens", "presence_penalty", "frequency_penalty", "system_prompt"):
        val = getattr(req, key)
        if val is not None:
            kwargs[key] = val
    return kwargs


def _build_knowledge_context(novel_id: str, linked_docs: list[dict]) -> str:
    """构建知识库上下文字符串，注入到 prompt 中。

    Args:
        linked_docs: novel_knowledge_link_repo.get_linked_doc_contents 的返回结果。

    Returns:
        str: 格式化的知识库上下文。
    """
    if not linked_docs:
        return ""

    lines = [
        "【参考知识库】以下内容来自你的知识库，请在创作本章时参考这些素材的风格、设定和内容：",
        "",
    ]
    for doc in linked_docs:
        title = doc.get("title", "未知文档")
        content = doc.get("content", "")
        # 限制每个文档最多 3000 字，避免 prompt 过长
        if len(content) > 3000:
            content = content[:3000] + "\n……（内容过长已截断）"
        lines.append(f"--- 文档「{title}」---")
        lines.append(content)
        lines.append("")

    lines.append("请合理借鉴以上知识库内容进行创作，但不要直接照搬原文。")
    return "\n".join(lines)


async def _generate_single_chapter(
    novel_id: str,
    chapter_index: int,
    context: dict,
    prompts: dict,
    gen_kwargs: dict,
    request_id: str,
    use_knowledge: bool = False,
) -> dict:
    """生成单个章节的完整流程（构建 prompt → 调用 LLM → 保存 → 提取实体）。

    Returns:
        dict: 包含 chapter、new_entities 等信息的字典。
    """
    step_name = "write_chapter"
    provider = resolve_provider_for_step(WORKFLOW_NAME, step_name) or ""
    use_schema = _check_json_schema_support(step_name)

    svc = get_llm_service_for_step(WORKFLOW_NAME, step_name)
    suffix = (
        "write_chapter_prompt_with_schema_suffix"
        if use_schema
        else "write_chapter_prompt_without_schema_suffix"
    )

    # 获取当前剧情节点上下文
    plot_point = await outline_repo.get_current_plot_point(novel_id)
    plot_point_context = format_plot_point_context(plot_point)

    # 构建知识库上下文
    knowledge_context = ""
    if use_knowledge:
        linked_docs = await novel_knowledge_link_repo.get_linked_doc_contents(novel_id)
        knowledge_context = _build_knowledge_context(novel_id, linked_docs)
        if knowledge_context:
            logger.info(
                "[generate_chapters] request_id=%s chapter=%d knowledge_docs=%d",
                request_id, chapter_index, len(linked_docs),
            )

    # 构建 prompt
    base_prompt = prompts["write_chapter_prompt_base"].format(
        chapter_index=chapter_index,
        novel_title=context["novel_title"],
        genre=context["genre"],
        tone=context["tone"],
        worldview=context["worldview"],
        writing_style=context["writing_style"],
        narrative_pov=context["narrative_pov"],
        era_background=context["era_background"],
        novel_summary=context["novel_summary"],
        entity_context=context["entity_context"],
        recent_context=context["recent_context"],
    )
    # 注入剧情节点任务
    base_prompt = base_prompt + "\n\n" + plot_point_context
    # 注入知识库上下文
    if knowledge_context:
        base_prompt = base_prompt + "\n\n" + knowledge_context
    full_prompt = base_prompt + "\n" + prompts[suffix]

    logger.info(
        "[generate_chapters] request_id=%s chapter=%d running provider=%s json_schema=%s prompt_len=%d",
        request_id, chapter_index, provider, use_schema, len(full_prompt),
    )

    # 调用 LLM
    if use_schema:
        result: ChapterWriteResult = await svc.generate_structured(
            full_prompt, ChapterWriteResult, **gen_kwargs
        )
    else:
        raw = await svc.generate_text(full_prompt, **gen_kwargs)
        result = await validate_and_fix_format(raw, ChapterWriteResult, "chapter_write")

    content = result.content
    word_count = len(content.replace("\n", "").replace(" ", ""))

    # 保存章节
    chapter_data = {
        "novel_id": novel_id,
        "title": result.title,
        "chapter_index": chapter_index,
        "content": content,
        "word_count": word_count,
        "status": "draft",
        "summary": result.summary,
        "key_events": result.key_events,
    }
    chapter_id = await chapter_repo.create_chapter(chapter_data)

    # 立即更新小说统计（逐章增量，中断不丢失）
    try:
        await novel_repo.increment_novel_stats(novel_id, {
            "current_chapter_count": 1,
            "current_word_count": word_count,
        })
    except Exception as e:
        logger.error("更新小说统计失败 chapter=%d: %s", chapter_index, e)

    # 提取并创建新实体
    new_entities_dict = result.new_entities.model_dump() if result.new_entities else {}
    raw_data = context.get("raw", {})
    all_characters = raw_data.get("characters", [])
    all_locations = raw_data.get("locations", [])
    all_factions = raw_data.get("factions", [])
    all_items = raw_data.get("items", [])
    all_rules = raw_data.get("rules", [])

    entity_stats = await extract_and_create_entities(
        novel_id=novel_id,
        chapter_index=chapter_index,
        new_entities=new_entities_dict,
        all_characters=all_characters,
        all_locations=all_locations,
        all_factions=all_factions,
        all_items=all_items,
        all_rules=all_rules,
    )

    # 更新章节的 appeared_characters / appeared_locations
    appeared_char_ids, appeared_loc_ids = resolve_appeared_refs(
        result.appeared_characters,
        result.appeared_locations,
        all_characters,
        all_locations,
    )
    if appeared_char_ids or appeared_loc_ids:
        try:
            await chapter_repo.update_chapter_info(
                chapter_id,
                {
                    "appeared_characters": appeared_char_ids,
                    "appeared_locations": appeared_loc_ids,
                },
            )
        except Exception as e:
            logger.error("更新章节出场信息失败 chapter=%s: %s", chapter_id, e)

    # 推进剧情大纲节点
    if plot_point:
        try:
            await outline_repo.advance_plot_point(
                novel_id=novel_id,
                arc_index=plot_point["arc_index"],
                point_index=plot_point["point_index"],
                chapter_id=chapter_id,
            )
        except Exception as e:
            logger.error("推进大纲节点失败 chapter=%s: %s", chapter_id, e)

    return {
        "chapter_id": chapter_id,
        "chapter_index": chapter_index,
        "title": result.title,
        "word_count": word_count,
        "new_entities": entity_stats,
    }


@router.post("/generate-chapters")
async def generate_chapters(req: GenerateChaptersRequest):
    """AI 续写章节（SSE 流式）。"""

    async def event_stream() -> AsyncGenerator[str, None]:
        request_id = uuid4().hex[:8]
        workflow_start = time.perf_counter()
        prompts = _load_prompts().get("generate_chapters", {})
        gen_kwargs = _build_gen_kwargs(req)

        logger.info(
            "[generate_chapters] request_id=%s novel_id=%s num_chapters=%d started",
            request_id, req.novel_id, req.num_chapters,
        )

        # 验证小说存在
        try:
            await novel_repo.get_novel_by_id(req.novel_id)
        except Exception as e:
            yield _sse_event("step", {"step": "workflow", "status": "error", "error": f"小说不存在: {e}"})
            yield _sse_event("done", {"success": False})
            return

        # 确定起始章节序号
        try:
            chapters = await chapter_repo.get_chapters_by_novel(req.novel_id)
            start_index = len(chapters) + 1
        except Exception:
            start_index = 1

        logger.info(
            "[generate_chapters] request_id=%s start_index=%d total=%d existing=%d",
            request_id, start_index, req.num_chapters, start_index - 1,
        )

        # 断点续传：如果已有存量章节，告知前端
        if start_index > 1:
            yield _sse_event("step", {
                "step": "workflow",
                "status": "resume",
                "existing_chapters": start_index - 1,
                "start_index": start_index,
            })

        total_new_entities: dict[str, int] = {
            "characters": 0,
            "locations": 0,
            "factions": 0,
            "items": 0,
            "rules": 0,
        }
        generated_chapters: list[dict] = []

        for i in range(req.num_chapters):
            chapter_index = start_index + i

            # 推送进度：running
            yield _sse_event("step", {
                "step": "writing",
                "status": "running",
                "current": i + 1,
                "total": req.num_chapters,
                "chapter_index": chapter_index,
            })

            step_start = time.perf_counter()

            try:
                # 每章单独构建上下文（因为上一章可能新增了实体）
                context = await build_chapter_context(req.novel_id)

                result = await _generate_single_chapter(
                    novel_id=req.novel_id,
                    chapter_index=chapter_index,
                    context=context,
                    prompts=prompts,
                    gen_kwargs=gen_kwargs,
                    request_id=request_id,
                    use_knowledge=req.use_knowledge,
                )

                elapsed_ms = int((time.perf_counter() - step_start) * 1000)
                logger.info(
                    "[generate_chapters] request_id=%s chapter=%d/%d done title=%s words=%d elapsed_ms=%d new_entities=%s",
                    request_id, i + 1, req.num_chapters, result["title"],
                    result["word_count"], elapsed_ms, result["new_entities"],
                )

                # 累计新实体统计
                for k in total_new_entities:
                    total_new_entities[k] += result["new_entities"].get(k, 0)

                generated_chapters.append({
                    "chapter_id": result["chapter_id"],
                    "chapter_index": result["chapter_index"],
                    "title": result["title"],
                    "word_count": result["word_count"],
                })

                # 推送进度：done
                yield _sse_event("step", {
                    "step": "writing",
                    "status": "done",
                    "current": i + 1,
                    "total": req.num_chapters,
                    "chapter_index": chapter_index,
                    "chapter_id": result["chapter_id"],
                    "title": result["title"],
                    "word_count": result["word_count"],
                    "new_entities": result["new_entities"],
                    "elapsed_ms": elapsed_ms,
                })

                # 章节间短暂冷却（避免 LLM 调用过于密集）
                if i < req.num_chapters - 1:
                    await _async_sleep(1)

            except Exception as e:
                logger.exception(
                    "[generate_chapters] request_id=%s chapter=%d failed",
                    request_id, chapter_index,
                )
                yield _sse_event("step", {
                    "step": "writing",
                    "status": "error",
                    "current": i + 1,
                    "total": req.num_chapters,
                    "chapter_index": chapter_index,
                    "error": str(e),
                })
                # 不中断，继续生成后续章节

        total_elapsed_ms = int((time.perf_counter() - workflow_start) * 1000)
        logger.info(
            "[generate_chapters] request_id=%s done chapters=%d total_entities=%s elapsed_ms=%d",
            request_id, len(generated_chapters), total_new_entities, total_elapsed_ms,
        )

        yield _sse_event("done", {
            "success": True,
            "chapters_generated": len(generated_chapters),
            "chapters": generated_chapters,
            "total_new_entities": total_new_entities,
            "elapsed_ms": total_elapsed_ms,
        })

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


async def _async_sleep(seconds: float) -> None:
    """异步 sleep 辅助函数。"""
    await asyncio.sleep(seconds)
