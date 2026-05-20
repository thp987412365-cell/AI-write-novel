from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Optional, Any

from application.db.repositories.novel_repository import novel_repo
from application.db.repositories.character_repository import character_repo
from application.db.repositories.faction_repository import faction_repo
from application.db.repositories.location_repository import location_repo
from application.db.repositories.item_repository import item_repo
from application.db.repositories.rule_repository import rule_repo
from application.services.novel.novel_service import NovelService
from application.db.errors import NotFoundError, InvalidIdError
from application.db.utils import to_object_id
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/novels", tags=["novels"])

class CreateNovelRequest(BaseModel):
    title: str
    subtitle: Optional[str] = None
    genre: Optional[str] = "unclassified"
    tags: Optional[List[str]] = []
    introduction: Optional[str] = None
    summary: Optional[str] = None
    core_seed: Optional[str] = None
    worldview: Optional[str] = None
    writing_style: Optional[str] = None
    narrative_pov: Optional[str] = None
    era_background: Optional[str] = None
    cover_image: Optional[str] = None
    plot: Optional[str] = None
    tone: Optional[str] = None
    target_audience: Optional[str] = None
    core_idea: Optional[str] = None
    number_of_chapters: Optional[int] = None
    words_per_chapter: Optional[int] = None
    characters: Optional[List[Dict[str, Any]]] = None
    factions: Optional[List[Dict[str, Any]]] = None
    locations: Optional[List[Dict[str, Any]]] = None
    items: Optional[List[Dict[str, Any]]] = None
    rules: Optional[List[Dict[str, Any]]] = None
    relationships: Optional[List[Dict[str, Any]]] = None

class UpdateNovelRequest(BaseModel):
    title: Optional[str] = None
    subtitle: Optional[str] = None
    genre: Optional[str] = None
    tags: Optional[List[str]] = None
    introduction: Optional[str] = None
    summary: Optional[str] = None
    core_seed: Optional[str] = None
    worldview: Optional[str] = None
    writing_style: Optional[str] = None
    narrative_pov: Optional[str] = None
    era_background: Optional[str] = None
    cover_image: Optional[str] = None
    plot: Optional[str] = None
    tone: Optional[str] = None
    target_audience: Optional[str] = None
    core_idea: Optional[str] = None
    number_of_chapters: Optional[int] = None
    words_per_chapter: Optional[int] = None

class StatusUpdate(BaseModel):
    status: str

@router.post("/create")
async def create_novel(req: CreateNovelRequest):
    """创建一个新的小说项目，同时批量创建关联实体。"""
    data = req.model_dump(exclude_unset=True)

    characters_data = data.pop("characters", None) or []
    factions_data = data.pop("factions", None) or []
    locations_data = data.pop("locations", None) or []
    items_data = data.pop("items", None) or []
    rules_data = data.pop("rules", None) or []
    relationships_data = data.pop("relationships", None) or []

    try:
        novel_id = await novel_repo.create_novel(data)

        stats: dict[str, int] = {"characters": 0, "factions": 0, "locations": 0, "items": 0, "rules": 0, "relationships": 0}

        for ch in characters_data:
            ch["novel_id"] = novel_id
            await character_repo.create_character(ch)
            stats["characters"] += 1

        for fac in factions_data:
            fac["novel_id"] = novel_id
            if not fac.get("faction_id"):
                fac["faction_id"] = await faction_repo._get_next_faction_id(novel_id)
            if "faction_id" in fac:
                await faction_repo.create_faction(fac)
                stats["factions"] += 1

        for loc in locations_data:
            loc["novel_id"] = novel_id
            await location_repo.create_location(loc)
            stats["locations"] += 1

        for it in items_data:
            it["novel_id"] = novel_id
            await item_repo.create_item(it)
            stats["items"] += 1

        for rule in rules_data:
            rule["novel_id"] = novel_id
            await rule_repo.create_rule(rule)
            stats["rules"] += 1

        if relationships_data:
            all_chars = await character_repo.get_characters_by_novel(novel_id)
            name_to_id: dict[str, str] = {c.get("name", ""): str(c["_id"]) for c in all_chars}
            for rel in relationships_data:
                source_name = rel.get("source_name", "")
                target_name = rel.get("target_name", "")
                if source_name and target_name:
                    source_id = name_to_id.get(source_name)
                    target_id = name_to_id.get(target_name)
                    if source_id and target_id:
                        rel_entry = {
                            "target_id": target_id,
                            "relation_type": rel.get("relation_type", "关联"),
                            "description": rel.get("description", ""),
                        }
                        await character_repo.collection.update_one(
                            {"_id": to_object_id(source_id)},
                            {"$push": {"relationships": rel_entry}}
                        )
                        stats["relationships"] += 1

        return {"id": novel_id, "message": "Novel created", "stats": stats}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/list")
async def get_all_novels():
    """获取所有小说的列表，仅包含基础信息。"""
    novels = await novel_repo.get_all_novels()
    for novel in novels:
        if "_id" in novel:
            novel["_id"] = str(novel["_id"])
        novel["stats"] = {
            "chapter_count": novel.get("current_chapter_count", 0),
            "total_word_count": novel.get("current_word_count", 0)
        }
    return {"data": novels}

@router.get("/deleted/list")
async def get_deleted_novels():
    """获取所有已软删除的小说列表（回收站）。"""
    novels = await novel_repo.get_deleted_novels()
    for novel in novels:
        if "_id" in novel:
            novel["_id"] = str(novel["_id"])
        novel["stats"] = {
            "chapter_count": novel.get("current_chapter_count", 0),
            "total_word_count": novel.get("current_word_count", 0)
        }
    return {"data": novels}

@router.get("/{novel_id}")
async def get_novel(novel_id: str):
    """根据ID获取指定小说的详细信息。"""
    try:
        novel = await novel_repo.get_novel_by_id(novel_id)
        novel["_id"] = str(novel["_id"])
        novel["stats"] = {
            "chapter_count": novel.get("current_chapter_count", 0),
            "total_word_count": novel.get("current_word_count", 0)
        }
        return novel
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except InvalidIdError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/{novel_id}")
async def update_novel(novel_id: str, req: UpdateNovelRequest):
    """更新指定小说的基础信息（如标题、简介等）。"""
    try:
        success = await novel_repo.update_novel_info(novel_id, req.model_dump(exclude_unset=True))
        return {"success": success}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.patch("/{novel_id}/status")
async def update_status(novel_id: str, req: StatusUpdate):
    """更新指定小说的状态（例如从草稿变为连载中）。"""
    try:
        success = await novel_repo.update_novel_status(novel_id, req.status)
        return {"success": success}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{novel_id}")
async def soft_delete(novel_id: str):
    """软删除指定的小说及将其放入回收站。"""
    try:
        success = await novel_repo.soft_delete_novel(novel_id)
        return {"success": success}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{novel_id}/restore")
async def restore_novel(novel_id: str):
    """从回收站中恢复（取消软删除）指定的小说。"""
    try:
        success = await novel_repo.restore_novel(novel_id)
        return {"success": success}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{novel_id}/hard")
async def hard_delete(novel_id: str):
    """彻底（物理）删除指定的小说及其所有关联数据，不可恢复。"""
    try:
        stats = await NovelService.hard_delete_novel(novel_id)
        return {"message": "Hard deleted successfully", "stats": stats}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
