"""剧情大纲服务：生成大纲、管理节点状态、构建剧情上下文。"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

from application.llm.config import get_provider_config
from application.services.llm.workflow_service import get_llm_service_for_step, resolve_provider_for_step
from application.services.llm.format_review_service import validate_and_fix_format
from application.db.repositories.novel_repository import novel_repo
from application.db.repositories.character_repository import character_repo
from application.db.repositories.location_repository import location_repo
from application.db.repositories.outline_repository import outline_repo
from pydantic_definitions.plot_outline_pydantic import PlotOutlineResult

PROMPT_PATH = Path(__file__).resolve().parents[3] / "prompt_definitions" / "prompt_default.yaml"
WORKFLOW_NAME = "generate_plot_outline"
logger = logging.getLogger(__name__)


def _load_prompts() -> dict:
    with PROMPT_PATH.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _check_json_schema_support(step_name: str) -> bool:
    provider = resolve_provider_for_step(WORKFLOW_NAME, step_name)
    if not provider:
        return False
    return get_provider_config(provider).supports_json_schema


def _build_knowledge_context(docs: list[dict]) -> str:
    """将知识库文档内容格式化为 prompt 上下文。

    Args:
        docs: 文档列表，每个包含 title, content 字段。

    Returns:
        str: 格式化的知识库上下文。
    """
    if not docs:
        return ""

    lines = [
        "【参考知识库】以下内容来自用户的知识库素材，请参考这些素材的世界观、设定、剧情风格来规划大纲：",
        "",
    ]
    for doc in docs:
        title = doc.get("title", "未知文档")
        content = doc.get("content", "")
        if len(content) > 2000:
            content = content[:2000] + "\n……（内容过长已截断）"
        lines.append(f"--- 素材「{title}」---")
        lines.append(content)
        lines.append("")

    lines.append("请结合以上知识库素材进行大纲规划，但不必完全照搬，保持创作独立性。")
    return "\n".join(lines)


async def generate_plot_outline(
    novel_id: str,
    gen_kwargs: dict | None = None,
    knowledge_docs: list[dict] | None = None,
) -> dict:
    """为指定小说生成剧情大纲。

    Args:
        novel_id: 小说 ID。
        gen_kwargs: LLM 生成参数。
        knowledge_docs: 关联的知识库文档内容列表（可选）。

    Returns:
        dict: 包含 arcs 的完整大纲数据。
    """
    gen_kwargs = gen_kwargs or {}
    prompts = _load_prompts().get("generate_plot_outline", {})
    step_name = "outline_generation"

    # 收集上下文
    novel = await novel_repo.get_novel_by_id(novel_id)
    characters = await character_repo.get_characters_by_novel(novel_id)
    locations = await location_repo.find_many(
        {"novel_id": novel.get("_id")},
        limit=100,
    )

    char_list = "\n".join(
        f"- {c.get('name', '')}（{c.get('role', '')}）：{c.get('personality', '')[:60]}"
        for c in characters
    )
    loc_list = "\n".join(
        f"- {l.get('name', '')}（{l.get('type', '')}）：{l.get('description', '')[:60]}"
        for l in locations
    )

    total_chapters = novel.get("number_of_chapters", 100)

    provider = resolve_provider_for_step(WORKFLOW_NAME, step_name) or ""
    use_schema = _check_json_schema_support(step_name)
    svc = get_llm_service_for_step(WORKFLOW_NAME, step_name)

    suffix = (
        "outline_generation_prompt_with_schema_suffix"
        if use_schema
        else "outline_generation_prompt_without_schema_suffix"
    )

    base_prompt = prompts["outline_generation_prompt_base"].format(
        plot=novel.get("plot", novel.get("summary", "")),
        genre=novel.get("genre", ""),
        worldview=novel.get("worldview", ""),
        core_seed=novel.get("core_seed", ""),
        total_chapters=total_chapters,
        character_list=char_list,
        location_list=loc_list,
    )

    # 注入知识库上下文
    if knowledge_docs:
        knowledge_context = _build_knowledge_context(knowledge_docs)
        if knowledge_context:
            base_prompt = base_prompt + "\n\n" + knowledge_context

    full_prompt = base_prompt + "\n" + prompts[suffix]

    logger.info(
        "[generate_plot_outline] novel_id=%s provider=%s json_schema=%s prompt_len=%d",
        novel_id, provider, use_schema, len(full_prompt),
    )

    if use_schema:
        result: PlotOutlineResult = await svc.generate_structured(
            full_prompt, PlotOutlineResult, **gen_kwargs
        )
    else:
        raw = await svc.generate_text(full_prompt, **gen_kwargs)
        result = await validate_and_fix_format(raw, PlotOutlineResult, "plot_outline")

    # 构建完整的大纲数据（含状态初始化）
    arcs_data = []
    for ai, arc in enumerate(result.arcs):
        points_data = []
        for pi, point in enumerate(arc.plot_points):
            points_data.append({
                "point_index": pi + 1,
                "title": point.title,
                "description": point.description,
                "target_chapters": point.target_chapters,
                "key_characters": point.key_characters,
                "key_locations": point.key_locations,
                "status": "pending",
                "chapter_ids": [],
            })
        arcs_data.append({
            "arc_index": ai + 1,
            "title": arc.title,
            "summary": arc.summary,
            "plot_points": points_data,
        })

    return {"arcs": arcs_data}


def format_plot_point_context(point: dict | None) -> str:
    """将当前剧情节点格式化为 LLM prompt 文本。

    Args:
        point: get_current_plot_point 返回的字典，或 None。

    Returns:
        str: 格式化的剧情节点上下文文本。
    """
    if not point:
        return "（暂无剧情大纲指引，请基于小说整体设定自由发挥本章。）"

    lines = [
        "【当前剧情任务 —— 本章需要推进的剧情】",
        f"所属篇章: {point.get('arc_title', '')}",
        f"剧情节点: 「{point.get('point_title', '')}」（本节点第 {point.get('chapter_count', 0) + 1}/{point.get('target_chapters', 1)} 章）",
        f"剧情要求: {point.get('description', '')}",
    ]

    key_chars = point.get("key_characters", [])
    if key_chars:
        lines.append(f"涉及角色: {', '.join(key_chars)}")

    key_locs = point.get("key_locations", [])
    if key_locs:
        lines.append(f"涉及地点: {', '.join(key_locs)}")

    lines.append("请围绕以上剧情目标写作本章，确保本章推进该节点的剧情。")
    return "\n".join(lines)
