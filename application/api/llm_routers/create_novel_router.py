"""AI 创建小说路由：通过 4 步 LLM 管道从用户创意生成完整小说设定（SSE 流式状态推送）。"""

from __future__ import annotations

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
from application.services.llm.entity_generation_service import (
    generate_characters,
    generate_factions,
    generate_locations,
    generate_items,
    generate_rules,
    generate_relationships,
)
from pydantic_definitions.novel_pydantic import (
    ExpandIdeaSchema,
    ExtractIdeaSchema,
    CoreSeedSchema,
    NovelMetaSchema,
)

router = APIRouter(prefix="/api/llm", tags=["llm"])

PROMPT_PATH = Path(__file__).resolve().parents[3] / "prompt_definitions" / "prompt_default.yaml"
WORKFLOW_NAME = "create_novel_by_ai"
logger = logging.getLogger(__name__)


def _load_prompts() -> dict:
    """读取 prompt 定义文件。"""
    with PROMPT_PATH.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _check_json_schema_support(step_name: str) -> bool:
    """检查指定步骤对应的 Provider 是否支持 JSON Schema 输出。"""
    provider = resolve_provider_for_step(WORKFLOW_NAME, step_name)
    if not provider:
        return False
    return get_provider_config(provider).supports_json_schema


def _sse_event(event: str, data: dict) -> str:
    """格式化一条 SSE 事件。"""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _log_workflow_event(request_id: str, step: str, status: str, **details: object) -> None:
    logger.info(
        "[create_novel_by_ai] request_id=%s step=%s status=%s details=%s",
        request_id,
        step,
        status,
        details or {},
    )


class AICreateNovelRequest(BaseModel):
    user_idea: str
    number_of_chapters: int = 100
    words_per_chapter: int = 3000
    # 可选生成参数，前端传入时覆盖 provider 级别默认值
    temperature: float | None = Field(default=None, ge=0, le=2)
    top_p: float | None = Field(default=None, ge=0, le=1)
    max_tokens: int | None = Field(default=None, gt=0)
    presence_penalty: float | None = Field(default=None, ge=-2, le=2)
    frequency_penalty: float | None = Field(default=None, ge=-2, le=2)
    system_prompt: str | None = Field(default=None)


def _build_gen_kwargs(req: AICreateNovelRequest) -> dict:
    """从请求中提取非空的生成参数，用于传入 LLMService。"""
    kwargs: dict = {}
    for key in ("temperature", "top_p", "max_tokens", "presence_penalty", "frequency_penalty", "system_prompt"):
        val = getattr(req, key)
        if val is not None:
            kwargs[key] = val
    return kwargs


@router.post("/create-novel-by-ai")
async def create_novel_by_ai(req: AICreateNovelRequest):
    """4 步 LLM 管道（SSE 流式）：expand_idea → extract_idea → core_seed → novel_meta。"""

    async def event_stream() -> AsyncGenerator[str, None]:
        request_id = uuid4().hex[:8]
        workflow_start = time.perf_counter()
        prompts = _load_prompts().get("create_novel_by_ai", {})
        gen_kwargs = _build_gen_kwargs(req)
        _log_workflow_event(
            request_id,
            "workflow",
            "started",
            idea_chars=len(req.user_idea),
            number_of_chapters=req.number_of_chapters,
            words_per_chapter=req.words_per_chapter,
            overrides=sorted(gen_kwargs.keys()),
        )

        # Step 1: Expand Idea to Full Novel Story
        yield _sse_event("step", {"step": "expand_idea", "status": "running"})
        step_started_at = time.perf_counter()
        provider0 = resolve_provider_for_step(WORKFLOW_NAME, "expand_idea_to_full_novel_story") or ""
        use_schema0 = _check_json_schema_support("expand_idea_to_full_novel_story")
        _log_workflow_event(
            request_id,
            "expand_idea",
            "running",
            provider=provider0 or "unresolved",
            json_schema=use_schema0,
        )
        try:
            svc0 = get_llm_service_for_step(WORKFLOW_NAME, "expand_idea_to_full_novel_story")
            suffix0 = "expand_idea_to_full_novel_story_prompt_with_schema_suffix" if use_schema0 else "expand_idea_to_full_novel_story_prompt_without_schema_suffix"
            prompt0 = (
                prompts["expand_idea_to_full_novel_story_prompt_base"].format(
                    user_idea=req.user_idea,
                )
                + "\n"
                + prompts[suffix0]
            )
            if use_schema0:
                expanded: ExpandIdeaSchema = await svc0.generate_structured(prompt0, ExpandIdeaSchema, **gen_kwargs)
            else:
                raw0 = await svc0.generate_text(prompt0, **gen_kwargs)
                raw0 = raw0.strip()
                if len(raw0) < 200:
                    raise ValueError(f"LLM 返回的剧情文本过短（{len(raw0)}字），可能生成失败")
                expanded = ExpandIdeaSchema(plot=raw0)
            _log_workflow_event(
                request_id,
                "expand_idea",
                "done",
                provider=provider0 or "unresolved",
                elapsed_ms=int((time.perf_counter() - step_started_at) * 1000),
            )
            yield _sse_event("step", {"step": "expand_idea", "status": "done", "data": expanded.model_dump()})
        except Exception as e:
            logger.exception(
                "[create_novel_by_ai] request_id=%s step=%s failed provider=%s",
                request_id,
                "expand_idea",
                provider0 or "unresolved",
            )
            yield _sse_event("step", {"step": "expand_idea", "status": "error", "error": str(e)})
            yield _sse_event("done", {"success": False})
            return

        # Step 2: Extract Idea
        yield _sse_event("step", {"step": "extract_idea", "status": "running"})
        step_started_at = time.perf_counter()
        provider1 = resolve_provider_for_step(WORKFLOW_NAME, "extract_idea") or ""
        use_schema1 = _check_json_schema_support("extract_idea")
        _log_workflow_event(
            request_id,
            "extract_idea",
            "running",
            provider=provider1 or "unresolved",
            json_schema=use_schema1,
        )
        try:
            svc1 = get_llm_service_for_step(WORKFLOW_NAME, "extract_idea")
            suffix1 = "extract_idea_prompt_with_schema_suffix" if use_schema1 else "extract_idea_prompt_without_schema_suffix"
            prompt1 = (
                prompts["extract_idea_prompt_base"].format(
                    plot=expanded.plot,
                )
                + "\n"
                + prompts[suffix1]
            )
            if use_schema1:
                idea: ExtractIdeaSchema = await svc1.generate_structured(prompt1, ExtractIdeaSchema, **gen_kwargs)
            else:
                raw1 = await svc1.generate_text(prompt1, **gen_kwargs)
                idea = await validate_and_fix_format(raw1, ExtractIdeaSchema, "extract_idea")
            _log_workflow_event(
                request_id,
                "extract_idea",
                "done",
                provider=provider1 or "unresolved",
                elapsed_ms=int((time.perf_counter() - step_started_at) * 1000),
            )
            yield _sse_event("step", {"step": "extract_idea", "status": "done", "data": idea.model_dump()})
        except Exception as e:
            logger.exception(
                "[create_novel_by_ai] request_id=%s step=%s failed provider=%s",
                request_id,
                "extract_idea",
                provider1 or "unresolved",
            )
            yield _sse_event("step", {"step": "extract_idea", "status": "error", "error": str(e)})
            yield _sse_event("done", {"success": False})
            return

        # Step 3: Core Seed
        yield _sse_event("step", {"step": "core_seed", "status": "running"})
        step_started_at = time.perf_counter()
        provider2 = resolve_provider_for_step(WORKFLOW_NAME, "core_seed") or ""
        use_schema2 = _check_json_schema_support("core_seed")
        _log_workflow_event(
            request_id,
            "core_seed",
            "running",
            provider=provider2 or "unresolved",
            json_schema=use_schema2,
        )
        try:
            svc2 = get_llm_service_for_step(WORKFLOW_NAME, "core_seed")
            suffix2 = "core_seed_prompt_with_schema_suffix" if use_schema2 else "core_seed_prompt_without_schema_suffix"
            prompt2 = (
                prompts["core_seed_prompt_base"].format(
                    plot=expanded.plot,
                    genre=idea.genre,
                    tone=idea.tone,
                    target_audience=idea.target_audience,
                    core_idea=idea.core_idea,
                    number_of_chapters=req.number_of_chapters,
                    words_per_chapter=req.words_per_chapter,
                )
                + "\n"
                + prompts[suffix2]
            )
            if use_schema2:
                seed: CoreSeedSchema = await svc2.generate_structured(prompt2, CoreSeedSchema, **gen_kwargs)
            else:
                raw2 = await svc2.generate_text(prompt2, **gen_kwargs)
                seed = await validate_and_fix_format(raw2, CoreSeedSchema, "core_seed")
            _log_workflow_event(
                request_id,
                "core_seed",
                "done",
                provider=provider2 or "unresolved",
                elapsed_ms=int((time.perf_counter() - step_started_at) * 1000),
            )
            yield _sse_event("step", {"step": "core_seed", "status": "done", "data": seed.model_dump()})
        except Exception as e:
            logger.exception(
                "[create_novel_by_ai] request_id=%s step=%s failed provider=%s",
                request_id,
                "core_seed",
                provider2 or "unresolved",
            )
            yield _sse_event("step", {"step": "core_seed", "status": "error", "error": str(e)})
            yield _sse_event("done", {"success": False})
            return

        # Step 4: Novel Meta
        yield _sse_event("step", {"step": "novel_meta", "status": "running"})
        step_started_at = time.perf_counter()
        provider3 = resolve_provider_for_step(WORKFLOW_NAME, "novel_meta") or ""
        use_schema3 = _check_json_schema_support("novel_meta")
        _log_workflow_event(
            request_id,
            "novel_meta",
            "running",
            provider=provider3 or "unresolved",
            json_schema=use_schema3,
        )
        try:
            svc3 = get_llm_service_for_step(WORKFLOW_NAME, "novel_meta")
            suffix3 = "novel_meta_prompt_with_schema_suffix" if use_schema3 else "novel_meta_prompt_without_schema_suffix"
            prompt3 = (
                prompts["novel_meta_prompt_base"].format(
                    plot=expanded.plot,
                    genre=idea.genre,
                    tone=idea.tone,
                    target_audience=idea.target_audience,
                    core_idea=idea.core_idea,
                    number_of_chapters=req.number_of_chapters,
                    words_per_chapter=req.words_per_chapter,
                    core_seed=seed.core_seed,
                )
                + "\n"
                + prompts[suffix3]
            )
            if use_schema3:
                meta: NovelMetaSchema = await svc3.generate_structured(prompt3, NovelMetaSchema, **gen_kwargs)
            else:
                raw3 = await svc3.generate_text(prompt3, **gen_kwargs)
                meta = await validate_and_fix_format(raw3, NovelMetaSchema, "novel_meta")
            _log_workflow_event(
                request_id,
                "novel_meta",
                "done",
                provider=provider3 or "unresolved",
                elapsed_ms=int((time.perf_counter() - step_started_at) * 1000),
            )
            yield _sse_event("step", {"step": "novel_meta", "status": "done", "data": meta.model_dump()})
        except Exception as e:
            logger.exception(
                "[create_novel_by_ai] request_id=%s step=%s failed provider=%s",
                request_id,
                "novel_meta",
                provider3 or "unresolved",
            )
            yield _sse_event("step", {"step": "novel_meta", "status": "error", "error": str(e)})
            yield _sse_event("done", {"success": False})
            return

        # Step 5: Characters
        character_names_str = ""
        characters: list[dict] = []
        yield _sse_event("step", {"step": "characters", "status": "running"})
        step_started_at = time.perf_counter()
        _log_workflow_event(request_id, "characters", "running")
        try:
            characters = await generate_characters(
                plot=expanded.plot,
                genre=idea.genre,
                tone=idea.tone,
                worldview=meta.worldview,
                core_seed=seed.core_seed,
                gen_kwargs=gen_kwargs,
            )
            character_names_str = "\n".join(
                f"- {c.get('name', '')}（{c.get('role', '')}）" for c in characters
            )
            _log_workflow_event(request_id, "characters", "done",
                count=len(characters),
                elapsed_ms=int((time.perf_counter() - step_started_at) * 1000))
            yield _sse_event("step", {"step": "characters", "status": "done",
                "data": characters, "count": len(characters)})
        except Exception as e:
            logger.exception("[create_novel_by_ai] request_id=%s step=%s failed", request_id, "characters")
            yield _sse_event("step", {"step": "characters", "status": "error", "error": str(e)})
            yield _sse_event("done", {"success": False})
            return

        # Step 6: Factions
        factions: list[dict] = []
        yield _sse_event("step", {"step": "factions", "status": "running"})
        step_started_at = time.perf_counter()
        _log_workflow_event(request_id, "factions", "running")
        try:
            factions = await generate_factions(
                plot=expanded.plot,
                genre=idea.genre,
                tone=idea.tone,
                worldview=meta.worldview,
                core_seed=seed.core_seed,
                character_names=character_names_str,
                gen_kwargs=gen_kwargs,
            )
            _log_workflow_event(request_id, "factions", "done",
                count=len(factions),
                elapsed_ms=int((time.perf_counter() - step_started_at) * 1000))
            yield _sse_event("step", {"step": "factions", "status": "done",
                "data": factions, "count": len(factions)})
        except Exception as e:
            logger.exception("[create_novel_by_ai] request_id=%s step=%s failed", request_id, "factions")
            yield _sse_event("step", {"step": "factions", "status": "error", "error": str(e)})
            yield _sse_event("done", {"success": False})
            return

        # Step 7: Locations
        locations: list[dict] = []
        yield _sse_event("step", {"step": "locations", "status": "running"})
        step_started_at = time.perf_counter()
        _log_workflow_event(request_id, "locations", "running")
        try:
            locations = await generate_locations(
                plot=expanded.plot,
                genre=idea.genre,
                tone=idea.tone,
                worldview=meta.worldview,
                gen_kwargs=gen_kwargs,
            )
            _log_workflow_event(request_id, "locations", "done",
                count=len(locations),
                elapsed_ms=int((time.perf_counter() - step_started_at) * 1000))
            yield _sse_event("step", {"step": "locations", "status": "done",
                "data": locations, "count": len(locations)})
        except Exception as e:
            logger.exception("[create_novel_by_ai] request_id=%s step=%s failed", request_id, "locations")
            yield _sse_event("step", {"step": "locations", "status": "error", "error": str(e)})
            yield _sse_event("done", {"success": False})
            return

        # Step 8: Items
        items: list[dict] = []
        yield _sse_event("step", {"step": "items", "status": "running"})
        step_started_at = time.perf_counter()
        _log_workflow_event(request_id, "items", "running")
        try:
            items = await generate_items(
                plot=expanded.plot,
                genre=idea.genre,
                worldview=meta.worldview,
                character_names=character_names_str,
                gen_kwargs=gen_kwargs,
            )
            _log_workflow_event(request_id, "items", "done",
                count=len(items),
                elapsed_ms=int((time.perf_counter() - step_started_at) * 1000))
            yield _sse_event("step", {"step": "items", "status": "done",
                "data": items, "count": len(items)})
        except Exception as e:
            logger.exception("[create_novel_by_ai] request_id=%s step=%s failed", request_id, "items")
            yield _sse_event("step", {"step": "items", "status": "error", "error": str(e)})
            yield _sse_event("done", {"success": False})
            return

        # Step 9: Rules
        rules: list[dict] = []
        yield _sse_event("step", {"step": "rules", "status": "running"})
        step_started_at = time.perf_counter()
        _log_workflow_event(request_id, "rules", "running")
        try:
            rules = await generate_rules(
                plot=expanded.plot,
                genre=idea.genre,
                tone=idea.tone,
                worldview=meta.worldview,
                core_seed=seed.core_seed,
                gen_kwargs=gen_kwargs,
            )
            _log_workflow_event(request_id, "rules", "done",
                count=len(rules),
                elapsed_ms=int((time.perf_counter() - step_started_at) * 1000))
            yield _sse_event("step", {"step": "rules", "status": "done",
                "data": rules, "count": len(rules)})
        except Exception as e:
            logger.exception("[create_novel_by_ai] request_id=%s step=%s failed", request_id, "rules")
            yield _sse_event("step", {"step": "rules", "status": "error", "error": str(e)})
            yield _sse_event("done", {"success": False})
            return

        # Step 10: Relationships
        relationships: list[dict] = []
        if characters:
            yield _sse_event("step", {"step": "relationships", "status": "running"})
            step_started_at = time.perf_counter()
            _log_workflow_event(request_id, "relationships", "running")
            try:
                relationships = await generate_relationships(
                    plot=expanded.plot,
                    core_seed=seed.core_seed,
                    character_names=character_names_str,
                    gen_kwargs=gen_kwargs,
                )
                _log_workflow_event(request_id, "relationships", "done",
                    count=len(relationships),
                    elapsed_ms=int((time.perf_counter() - step_started_at) * 1000))
                yield _sse_event("step", {"step": "relationships", "status": "done",
                    "data": relationships, "count": len(relationships)})
            except Exception as e:
                logger.exception("[create_novel_by_ai] request_id=%s step=%s failed", request_id, "relationships")
                yield _sse_event("step", {"step": "relationships", "status": "error", "error": str(e)})
                yield _sse_event("done", {"success": False})
                return
        else:
            _log_workflow_event(request_id, "relationships", "skipped", reason="no characters")
            yield _sse_event("step", {"step": "relationships", "status": "done",
                "data": [], "count": 0})

        # Step 11: Generate Plot Outline (基于完整的剧情和角色列表)
        plot_outline: list[dict] = []
        yield _sse_event("step", {"step": "plot_outline", "status": "running"})
        step_started_at = time.perf_counter()
        _log_workflow_event(request_id, "plot_outline", "running")
        try:
            # 构建大纲生成的上下文
            char_list = "\n".join(
                f"- {c.get('name', '')}（{c.get('role', '')}）" for c in characters
            )
            loc_list = "\n".join(
                f"- {l.get('name', '')}（{l.get('type', '')}）" for l in locations
            )

            prompts_all = _load_prompts()
            outline_prompts = prompts_all.get("generate_plot_outline", {})
            svc_outline = get_llm_service_for_step("generate_plot_outline", "outline_generation")
            provider_o = resolve_provider_for_step("generate_plot_outline", "outline_generation")
            use_schema_o = get_provider_config(provider_o).supports_json_schema if provider_o else False
            suffix_o = "outline_generation_prompt_with_schema_suffix" if use_schema_o else "outline_generation_prompt_without_schema_suffix"

            prompt_o = (
                outline_prompts["outline_generation_prompt_base"].format(
                    plot=expanded.plot,
                    genre=idea.genre,
                    worldview=meta.worldview,
                    core_seed=seed.core_seed,
                    total_chapters=req.number_of_chapters,
                    character_list=char_list,
                    location_list=loc_list,
                )
                + "\n"
                + outline_prompts[suffix_o]
            )

            from pydantic_definitions.plot_outline_pydantic import PlotOutlineResult

            if use_schema_o:
                outline_result: PlotOutlineResult = await svc_outline.generate_structured(
                    prompt_o, PlotOutlineResult, **gen_kwargs
                )
            else:
                raw_o = await svc_outline.generate_text(prompt_o, **gen_kwargs)
                outline_result = await validate_and_fix_format(raw_o, PlotOutlineResult, "plot_outline")

            plot_outline = [arc.model_dump() for arc in outline_result.arcs]
            total_points = sum(len(arc.plot_points) for arc in outline_result.arcs)
            _log_workflow_event(request_id, "plot_outline", "done",
                arcs=len(plot_outline), points=total_points,
                elapsed_ms=int((time.perf_counter() - step_started_at) * 1000))
            yield _sse_event("step", {"step": "plot_outline", "status": "done",
                "data": plot_outline, "arcs_count": len(plot_outline), "points_count": total_points})
        except Exception as e:
            logger.exception("[create_novel_by_ai] request_id=%s step=%s failed", request_id, "plot_outline")
            # 大纲生成失败不中断整个流程，降级处理
            _log_workflow_event(request_id, "plot_outline", "failed", error=str(e))
            yield _sse_event("step", {"step": "plot_outline", "status": "error",
                "error": f"大纲生成失败（不影响其他数据）: {e}", "data": []})

        # All steps completed
        _log_workflow_event(
            request_id,
            "workflow",
            "done",
            total_elapsed_ms=int((time.perf_counter() - workflow_start) * 1000),
        )
        yield _sse_event("done", {
            "success": True,
            "result": {
                "expand_idea": expanded.model_dump(),
                "extract_idea": idea.model_dump(),
                "core_seed": seed.model_dump(),
                "novel_meta": meta.model_dump(),
                "characters": characters,
                "factions": factions,
                "locations": locations,
                "items": items,
                "rules": rules,
                "relationships": relationships,
                "plot_outline": plot_outline,
            },
        })

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
