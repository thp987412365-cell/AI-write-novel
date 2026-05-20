"""上下文构建服务：为章节 AI 续写构建完整的上下文信息。

负责收集小说元信息、所有实体卡片（角色/地点/势力/物品/规则/关系）、
以及最近章节摘要，并格式化为 LLM 可读的文本注入到 prompt 中。

对于实体数量较多的情况，会采用分级显示策略：
- 近期活跃的实体 → 完整卡片
- 其余实体 → 缩略展示（仅名称 + 一句话定位）
"""

from __future__ import annotations

import logging
from typing import Any

from application.db.repositories.novel_repository import novel_repo
from application.db.repositories.character_repository import character_repo
from application.db.repositories.location_repository import location_repo
from application.db.repositories.faction_repository import faction_repo
from application.db.repositories.item_repository import item_repo
from application.db.repositories.rule_repository import rule_repo
from application.db.repositories.chapter_repository import chapter_repo
from application.db.utils import to_object_id

logger = logging.getLogger(__name__)

# 上下文 Token 预算（粗略估算：1 中文字符 ≈ 1 token）
MAX_CONTEXT_CHARS = 30000  # 总上下文上限
RECENT_ACTIVE_LIMIT = 8     # 近期活跃角色/地点完整展示数量上限


async def _fetch_all_characters(novel_id: str) -> list[dict]:
    """获取小说的所有角色。"""
    try:
        return await character_repo.get_characters_by_novel(novel_id)
    except Exception:
        return []


async def _fetch_all_locations(novel_id: str) -> list[dict]:
    """获取小说的所有地点。"""
    try:
        obj_id = to_object_id(novel_id)
        return await location_repo.find_many({"novel_id": obj_id}, limit=200)
    except Exception:
        return []


async def _fetch_all_factions(novel_id: str) -> list[dict]:
    """获取小说的所有势力。"""
    try:
        obj_id = to_object_id(novel_id)
        return await faction_repo.find_many({"novel_id": obj_id}, limit=200)
    except Exception:
        return []


async def _fetch_all_items(novel_id: str) -> list[dict]:
    """获取小说的所有物品。"""
    try:
        obj_id = to_object_id(novel_id)
        return await item_repo.find_many({"novel_id": obj_id}, limit=200)
    except Exception:
        return []


async def _fetch_all_rules(novel_id: str) -> list[dict]:
    """获取小说的所有规则。"""
    try:
        obj_id = to_object_id(novel_id)
        return await rule_repo.find_many({"novel_id": obj_id}, limit=200)
    except Exception:
        return []


async def _fetch_recent_chapters(novel_id: str, limit: int = 3) -> list[dict]:
    """获取最近 N 章的摘要信息。"""
    try:
        chapters = await chapter_repo.get_chapters_by_novel(novel_id)
        # chapters 已经是按 sort_order 排序的，取最后 limit 个
        return chapters[-limit:] if len(chapters) > limit else chapters
    except Exception:
        return []


def _format_characters(
    characters: list[dict],
    active_names: set[str] | None = None,
) -> str:
    """格式化角色卡为文本。

    Args:
        characters: 角色列表。
        active_names: 近期活跃角色的名称集合，这些角色会被完整展示。
    """
    if not characters:
        return "（暂无角色设定）"

    active_names = active_names or set()
    lines: list[str] = []
    for i, c in enumerate(characters):
        name = c.get('name', '未知')
        role = c.get('role', 'supporting')
        if name in active_names:
            # 活跃角色 → 完整展示
            lines.append(f"  [{c.get('char_id', i + 1)}] {name}")
            lines.append(f"      定位: {role}")
            lines.append(f"      性别: {c.get('gender', '')}　年龄: {c.get('age', '')}")
            lines.append(f"      外貌: {c.get('appearance', '')}")
            lines.append(f"      性格: {c.get('personality', '')}")
            lines.append(f"      背景: {c.get('background', '')}")
            lines.append(f"      能力: {', '.join(c.get('abilities', []))}")
            lines.append(f"      目标: {c.get('goals', '')}")
            lines.append(f"      秘密: {c.get('secrets', '')}")
        else:
            # 非活跃角色 → 缩略展示
            lines.append(f"  [{c.get('char_id', i + 1)}] {name} ({role})")
            personality = c.get('personality', '')
            if personality:
                lines.append(f"      简介: {personality[:80]}")

        # 关系
        relationships = c.get('relationships', [])
        if relationships:
            rel_strs = []
            for r in relationships:
                # 尝试从角色列表中找 target 名字
                target_id = r.get('target_id', '')
                target_name = ""
                for oc in characters:
                    if str(oc.get('_id', '')) == str(target_id):
                        target_name = oc.get('name', '')
                        break
                if target_name:
                    rel_strs.append(f"{target_name}({r.get('relation_type', '')})")
                else:
                    rel_strs.append(f"{target_id}({r.get('relation_type', '')})")
            lines.append(f"      关系: {', '.join(rel_strs)}")

        lines.append("")
    return "\n".join(lines)


def _format_locations(locations: list[dict], active_names: set[str] | None = None) -> str:
    """格式化地点卡为文本。"""
    if not locations:
        return "（暂无地点设定）"

    active_names = active_names or set()
    lines: list[str] = []
    for loc in locations:
        name = loc.get('name', '未知')
        lines.append(f"  [{loc.get('type', '')}] {name}")
        if name in active_names:
            lines.append(f"      描述: {loc.get('description', '')}")
            lines.append(f"      气候: {loc.get('climate', '')}")
            lines.append(f"      文化: {loc.get('culture', '')}")
            lines.append(f"      历史: {loc.get('history', '')}")
            lines.append(f"      故事意义: {loc.get('significance', '')}")
        else:
            desc = loc.get('description', '')
            if desc:
                lines.append(f"      简介: {desc[:80]}")
        lines.append("")
    return "\n".join(lines)


def _format_factions(factions: list[dict]) -> str:
    """格式化势力卡为文本（紧凑模式，减少 prompt 消耗）。"""
    if not factions:
        return "（暂无势力设定）"

    lines: list[str] = []
    for f in factions:
        name = f.get('name', '未知')
        ftype = f.get('faction_type', '')
        level = f.get('level_type', '')
        positioning = f.get('positioning', '')
        core_goal = f.get('core_goal', '')
        parts = [name]
        if ftype:
            parts.append(ftype)
        if level:
            parts.append(level)
        lines.append(f"  {' | '.join(parts)}")
        if positioning:
            lines.append(f"      定位: {positioning}")
        if core_goal:
            lines.append(f"      目标: {core_goal}")
        hidden = f.get('hidden_goal', '')
        if hidden and hidden != core_goal:
            lines.append(f"      隐藏目标: {hidden}")
        lines.append("")
    return "\n".join(lines)


def _format_items(items: list[dict]) -> str:
    """格式化物品卡为文本（紧凑模式，减少 prompt 消耗）。"""
    if not items:
        return "（暂无物品设定）"

    lines: list[str] = []
    for it in items:
        name = it.get('name', '未知')
        rarity = it.get('rarity', 'common')
        itype = it.get('type', '')
        desc = it.get('description', '')
        abilities = it.get('abilities', [])
        lines.append(f"  [{rarity}] {name}" + (f" ({itype})" if itype else ""))
        if desc:
            lines.append(f"      {desc[:100]}")
        if abilities:
            lines.append(f"      能力: {', '.join(abilities)}")
        lines.append("")
    return "\n".join(lines)


def _format_rules(rules: list[dict]) -> str:
    """格式化规则卡为文本（紧凑模式，减少 prompt 消耗）。"""
    if not rules:
        return "（暂无规则设定）"

    lines: list[str] = []
    for r in rules:
        name = r.get('name', '未知')
        category = r.get('category', '')
        desc = r.get('description', '')
        lines.append(f"  [{category}] {name}" if category else f"  {name}")
        if desc:
            lines.append(f"      {desc[:120]}")
        impact = r.get('impact_on_plot', '')
        if impact:
            lines.append(f"      剧情影响: {impact}")
        lines.append("")
    return "\n".join(lines)


def _format_recent_chapters(chapters: list[dict]) -> str:
    """格式化最近章节摘要。"""
    if not chapters:
        return "（这是小说的开头章节，没有前情提要。）"

    lines: list[str] = []
    for i, ch in enumerate(chapters):
        idx = ch.get('chapter_index', '?')
        title = ch.get('title', '未命名')
        summary = ch.get('summary', '')
        lines.append(f"  第{idx}章「{title}」")
        if summary:
            lines.append(f"  摘要: {summary}")
        else:
            content = ch.get('content', '')
            if content:
                # 无摘要时取正文前200字作为概要
                lines.append(f"  概要: {content[:200]}...")
        lines.append("")
    return "\n".join(lines)


def _trim_context(text: str, max_chars: int = MAX_CONTEXT_CHARS) -> str:
    """裁剪上下文到指定长度。"""
    if len(text) <= max_chars:
        return text
    # 从末尾开始裁剪（保留前面的设定和后面的前情提要）
    logger.warning("上下文过长 (%d 字符)，已裁剪到 %d 字符", len(text), max_chars)
    return text[:max_chars] + "\n\n...（上下文过长，已截断）"


async def build_chapter_context(novel_id: str) -> dict[str, Any]:
    """构建章节续写的完整上下文。

    Returns:
        dict 包含:
        - novel_title, genre, tone, worldview, writing_style, narrative_pov, era_background, novel_summary
        - entity_context: 格式化的实体文本
        - recent_context: 前情提要文本
    """
    # 1. 加载小说元信息
    novel = await novel_repo.get_novel_by_id(novel_id)

    # 2. 加载所有实体
    characters = await _fetch_all_characters(novel_id)
    locations = await _fetch_all_locations(novel_id)
    factions = await _fetch_all_factions(novel_id)
    items = await _fetch_all_items(novel_id)
    rules = await _fetch_all_rules(novel_id)
    recent_chapters = await _fetch_recent_chapters(novel_id, limit=3)

    # 3. 提取近期活跃的角色和地点名称
    active_char_names: set[str] = set()
    active_loc_names: set[str] = set()
    for ch in recent_chapters:
        for name in ch.get('appeared_characters', []):
            active_char_names.add(name)
        for name in ch.get('appeared_locations', []):
            active_loc_names.add(name)

    # 如果活跃集合太小，至少让前 RECENT_ACTIVE_LIMIT 个角色完整展示
    if len(active_char_names) < 5 and len(characters) > 0:
        for c in characters[:RECENT_ACTIVE_LIMIT]:
            active_char_names.add(c.get('name', ''))

    # 4. 构建实体上下文字段
    char_text = _format_characters(characters, active_char_names)
    loc_text = _format_locations(locations, active_loc_names)
    faction_text = _format_factions(factions)
    item_text = _format_items(items)
    rule_text = _format_rules(rules)

    entity_context = (
        f"【角色卡（共 {len(characters)} 个）】\n{char_text}\n"
        f"【地点卡（共 {len(locations)} 个）】\n{loc_text}\n"
        f"【势力卡（共 {len(factions)} 个）】\n{faction_text}\n"
        f"【物品卡（共 {len(items)} 个）】\n{item_text}\n"
        f"【规则卡（共 {len(rules)} 个）】\n{rule_text}"
    )

    # 5. 构建前情提要
    recent_context = _format_recent_chapters(recent_chapters)

    # 6. 裁剪过长的上下文
    entity_context = _trim_context(entity_context)

    return {
        "novel_title": novel.get("title", ""),
        "genre": novel.get("genre", "unclassified"),
        "tone": novel.get("tone", ""),
        "worldview": novel.get("worldview", ""),
        "writing_style": novel.get("writing_style", ""),
        "narrative_pov": novel.get("narrative_pov", ""),
        "era_background": novel.get("era_background", ""),
        "novel_summary": novel.get("summary", novel.get("introduction", "")),
        "entity_context": entity_context,
        "recent_context": recent_context,
        "raw": {
            "characters": characters,
            "locations": locations,
            "factions": factions,
            "items": items,
            "rules": rules,
        },
    }
