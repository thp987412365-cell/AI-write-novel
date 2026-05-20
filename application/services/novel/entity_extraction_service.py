"""实体提取服务：从 LLM 生成的章节输出中提取新实体并自动创建。

负责：
1. 解析章节生成结果中的 new_entities 字段
2. 与已有实体进行名称相似度比对，避免重复创建
3. 自动调用对应的 repository 创建新实体
4. 更新角色关系（将新关系写入对应角色的 relationships 字段）
5. 更新章节的 appeared_characters / appeared_locations 字段（关联已有角色ID）
"""

from __future__ import annotations

import logging
from typing import Any

from application.db.repositories.character_repository import character_repo
from application.db.repositories.location_repository import location_repo
from application.db.repositories.faction_repository import faction_repo
from application.db.repositories.item_repository import item_repo
from application.db.repositories.rule_repository import rule_repo
from application.db.utils import to_object_id, to_str_id

logger = logging.getLogger(__name__)


def _name_similarity(name1: str, name2: str) -> float:
    """计算两个名称的相似度（简单版）。

    规则：
    1. 完全相等 → 1.0
    2. 一个包含另一个 → 0.8
    3. 共享字符比例 → 0~1
    """
    n1 = name1.strip().lower()
    n2 = name2.strip().lower()
    if n1 == n2:
        return 1.0
    if n1 in n2 or n2 in n1:
        return 0.8
    # 共享字符比例
    common = len(set(n1) & set(n2))
    total = len(set(n1) | set(n2))
    return common / total if total > 0 else 0.0


def _is_duplicate_name(new_name: str, existing_names: list[str], threshold: float = 0.6) -> bool:
    """判断新名称是否与已有名称重复。"""
    for existing in existing_names:
        if _name_similarity(new_name, existing) >= threshold:
            return True
    return False


def _map_to_existing_id(
    name: str,
    existing_data: list[dict],
    threshold: float = 0.6,
) -> str | None:
    """将名称映射到已有实体的 _id。

    优先精确匹配，其次相似度匹配。
    """
    # 精确匹配
    for item in existing_data:
        if item.get('name', '').strip().lower() == name.strip().lower():
            return str(item.get('_id', ''))
    # 相似度匹配
    for item in existing_data:
        if _name_similarity(name, item.get('name', '')) >= threshold:
            return str(item.get('_id', ''))
    return None


async def extract_and_create_entities(
    novel_id: str,
    chapter_index: int,
    new_entities: dict,
    all_characters: list[dict],
    all_locations: list[dict],
    all_factions: list[dict],
    all_items: list[dict],
    all_rules: list[dict],
) -> dict[str, int]:
    """从章节生成结果中提取新实体并自动创建。

    Args:
        novel_id: 小说 ID。
        chapter_index: 当前章节序号。
        new_entities: 章节生成结果中的 new_entities 字典。
        all_characters: 已有角色列表（用于去重）。
        all_locations: 已有地点列表。
        all_factions: 已有势力列表。
        all_items: 已有物品列表。
        all_rules: 已有规则列表。

    Returns:
        dict: 各类型新创建实体的数量统计。
    """
    stats: dict[str, int] = {
        "characters": 0,
        "locations": 0,
        "factions": 0,
        "items": 0,
        "rules": 0,
        "relationships": 0,
    }

    existing_char_names = [c.get('name', '') for c in all_characters]
    existing_loc_names = [l.get('name', '') for l in all_locations]
    existing_fac_names = [f.get('name', '') for f in all_factions]
    existing_item_names = [it.get('name', '') for it in all_items]
    existing_rule_names = [r.get('name', '') for r in all_rules]

    novel_obj_id = to_object_id(novel_id)

    # 用于关系映射的 [name -> _id] 字典（包含已有和新创建的）
    char_name_to_id: dict[str, str] = {}
    for c in all_characters:
        char_name_to_id[c.get('name', '')] = str(c.get('_id', ''))

    # === 创建新角色 ===
    new_characters = new_entities.get('characters', []) or []
    for nc in new_characters:
        name = nc.get('name', '').strip()
        if not name:
            continue
        if _is_duplicate_name(name, existing_char_names):
            logger.debug("跳过重复角色: %s", name)
            # 仍然加入映射，方便后续关系查找
            existing_id = _map_to_existing_id(name, all_characters)
            if existing_id and name not in char_name_to_id:
                char_name_to_id[name] = existing_id
            continue

        try:
            char_data = {
                "novel_id": novel_obj_id,
                "name": name,
                "role": nc.get('role', 'supporting'),
                "gender": nc.get('gender', ''),
                "age": nc.get('age', ''),
                "appearance": nc.get('appearance', ''),
                "personality": nc.get('personality', ''),
                "background": nc.get('background', ''),
                "abilities": nc.get('abilities', []),
                "goals": nc.get('goals', ''),
                "secrets": nc.get('secrets', ''),
                "first_appearance_chapter_index": chapter_index,
            }
            char_id = await character_repo.create_character(char_data)
            char_name_to_id[name] = str(char_id)
            stats["characters"] += 1
            logger.info("创建新角色: %s (chapter %d)", name, chapter_index)
        except Exception as e:
            logger.error("创建角色 %s 失败: %s", name, e)

    # === 创建新地点 ===
    new_locations = new_entities.get('locations', []) or []
    for nl in new_locations:
        name = nl.get('name', '').strip()
        if not name or _is_duplicate_name(name, existing_loc_names):
            continue
        try:
            loc_data = {
                "novel_id": novel_obj_id,
                "name": name,
                "type": nl.get('type', 'city'),
                "description": nl.get('description', ''),
                "climate": nl.get('climate', ''),
                "culture": nl.get('culture', ''),
                "history": nl.get('history', ''),
                "significance": nl.get('significance', ''),
                "notable_features": nl.get('notable_features', []),
            }
            await location_repo.create_location(loc_data)
            stats["locations"] += 1
            logger.info("创建新地点: %s", name)
        except Exception as e:
            logger.error("创建地点 %s 失败: %s", name, e)

    # === 创建新势力 ===
    new_factions = new_entities.get('factions', []) or []
    for nf in new_factions:
        name = nf.get('name', '').strip()
        if not name or _is_duplicate_name(name, existing_fac_names):
            continue
        try:
            fac_data = {
                "novel_id": novel_obj_id,
                "name": name,
                "faction_type": nf.get('faction_type', 'organization'),
                "level_type": nf.get('level_type', 'minor'),
                "positioning": nf.get('positioning', ''),
                "public_stance": nf.get('public_stance', ''),
                "core_goal": nf.get('core_goal', ''),
                "hidden_goal": nf.get('hidden_goal', ''),
                "resources_and_advantages": nf.get('resources_and_advantages', []),
                "organization_style": nf.get('organization_style', ''),
                "core_values": nf.get('core_values', []),
                "conflict_with_mainline": nf.get('conflict_with_mainline', ''),
                "first_appearance_chapter_id": str(chapter_index),
            }
            await faction_repo.create_faction(fac_data)
            stats["factions"] += 1
            logger.info("创建新势力: %s", name)
        except Exception as e:
            logger.error("创建势力 %s 失败: %s", name, e)

    # === 创建新物品 ===
    new_items = new_entities.get('items', []) or []
    for ni in new_items:
        name = ni.get('name', '').strip()
        if not name or _is_duplicate_name(name, existing_item_names):
            continue
        try:
            item_data = {
                "novel_id": novel_obj_id,
                "name": name,
                "type": ni.get('type', 'artifact'),
                "rarity": ni.get('rarity', 'common'),
                "description": ni.get('description', ''),
                "abilities": ni.get('abilities', []),
                "origin": ni.get('origin', ''),
                "limitations": ni.get('limitations', ''),
                "significance": ni.get('significance', ''),
            }
            await item_repo.create_item(item_data)
            stats["items"] += 1
            logger.info("创建新物品: %s", name)
        except Exception as e:
            logger.error("创建物品 %s 失败: %s", name, e)

    # === 创建新规则 ===
    new_rules = new_entities.get('rules', []) or []
    for nr in new_rules:
        name = nr.get('name', '').strip()
        if not name or _is_duplicate_name(name, existing_rule_names):
            continue
        try:
            rule_data = {
                "novel_id": novel_obj_id,
                "name": name,
                "category": nr.get('category', 'custom'),
                "description": nr.get('description', ''),
                "principles": nr.get('principles', []),
                "exceptions": nr.get('exceptions', []),
                "limitations": nr.get('limitations', ''),
                "impact_on_plot": nr.get('impact_on_plot', ''),
            }
            await rule_repo.create_rule(rule_data)
            stats["rules"] += 1
            logger.info("创建新规则: %s", name)
        except Exception as e:
            logger.error("创建规则 %s 失败: %s", name, e)

    # === 更新角色关系 ===
    new_relationships = new_entities.get('relationships', []) or []
    # 合并已有和新创建的角色名到 char_name_to_id
    for c in all_characters:
        cname = c.get('name', '')
        if cname and cname not in char_name_to_id:
            char_name_to_id[cname] = str(c.get('_id', ''))

    for nr in new_relationships:
        source_name = nr.get('source_name', '').strip()
        target_name = nr.get('target_name', '').strip()
        if not source_name or not target_name:
            continue

        source_id = char_name_to_id.get(source_name) or _map_to_existing_id(source_name, all_characters)
        target_id = char_name_to_id.get(target_name) or _map_to_existing_id(target_name, all_characters)

        if not source_id or not target_id:
            logger.debug("关系映射失败: %s -> %s (source_id=%s, target_id=%s)",
                         source_name, target_name, source_id, target_id)
            continue

        try:
            source_char = await character_repo.get_character_by_id(source_id)
            existing_rels = source_char.get('relationships', []) or []

            # 检查是否已存在相同的关系
            already_exists = any(
                r.get('target_id') == target_id
                for r in existing_rels
            )
            if already_exists:
                continue

            existing_rels.append({
                "target_id": target_id,
                "relation_type": nr.get('relation_type', '关联'),
                "description": nr.get('description', ''),
            })
            await character_repo.update_character_info(source_id, {"relationships": existing_rels})
            stats["relationships"] += 1
            logger.info("更新角色关系: %s -> %s (%s)", source_name, target_name, nr.get('relation_type', ''))
        except Exception as e:
            logger.error("更新关系失败 %s -> %s: %s", source_name, target_name, e)

    return stats


def resolve_appeared_refs(
    appeared_char_names: list[str],
    appeared_loc_names: list[str],
    all_characters: list[dict],
    all_locations: list[dict],
) -> tuple[list[str], list[str]]:
    """将章节中出现的角色名/地点名解析为对应的实体 _id 列表。

    用于填充 Chapter 的 appeared_characters / appeared_locations 字段。

    Returns:
        (character_ids, location_ids): 解析后的 ID 列表。
    """
    char_ids: list[str] = []
    for name in appeared_char_names:
        mapped = _map_to_existing_id(name, all_characters, threshold=0.7)
        if mapped:
            char_ids.append(mapped)

    loc_ids: list[str] = []
    for name in appeared_loc_names:
        mapped = _map_to_existing_id(name, all_locations, threshold=0.7)
        if mapped:
            loc_ids.append(mapped)

    return char_ids, loc_ids
