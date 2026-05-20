from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Dict, List, Optional

from application.services.novel.character_service import CharacterService
from application.db.errors import NotFoundError, InvalidIdError, DuplicateKeyError

router = APIRouter(prefix="/api/characters", tags=["characters"])


class CreateCharacterRequest(BaseModel):
    novel_id: str
    name: str
    aliases: Optional[List[str]] = None
    role: Optional[str] = None
    gender: Optional[str] = None
    age: Optional[str] = None
    appearance: Optional[str] = None
    personality: Optional[str] = None
    background: Optional[str] = None
    abilities: Optional[List[str]] = None
    goals: Optional[str] = None
    secrets: Optional[str] = None
    relationships: Optional[List[Dict]] = None
    faction_id: Optional[str] = None
    first_appearance_chapter_index: Optional[int] = None
    status: Optional[str] = None
    avatar_url: Optional[str] = None
    tags: Optional[List[str]] = None
    sort_order: Optional[int] = None


class UpdateCharacterRequest(BaseModel):
    name: Optional[str] = None
    aliases: Optional[List[str]] = None
    role: Optional[str] = None
    gender: Optional[str] = None
    age: Optional[str] = None
    appearance: Optional[str] = None
    personality: Optional[str] = None
    background: Optional[str] = None
    abilities: Optional[List[str]] = None
    goals: Optional[str] = None
    secrets: Optional[str] = None
    relationships: Optional[List[Dict]] = None
    faction_id: Optional[str] = None
    first_appearance_chapter_index: Optional[int] = None
    status: Optional[str] = None
    avatar_url: Optional[str] = None
    tags: Optional[List[str]] = None
    sort_order: Optional[int] = None


class BatchUpdateSortOrderRequest(BaseModel):
    novel_id: str
    sort_map: Dict[str, int]


def _serialize_character(ch: dict) -> dict:
    if "_id" in ch:
        ch["_id"] = str(ch["_id"])
    if "novel_id" in ch:
        ch["novel_id"] = str(ch["novel_id"])
    return ch


@router.post("/create")
async def create_character(req: CreateCharacterRequest):
    data = req.model_dump(exclude_unset=True)
    try:
        char_id = await CharacterService.create_character(data)
        return {"id": char_id, "char_id": data.get("char_id"), "message": "Character created"}
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except DuplicateKeyError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except (ValueError, InvalidIdError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/novel/{novel_id}")
async def get_characters_by_novel(
    novel_id: str,
    role: Optional[str] = Query(None),
    faction_id: Optional[str] = Query(None)
):
    try:
        characters = await CharacterService.get_characters_by_novel(novel_id, role, faction_id)
        for ch in characters:
            _serialize_character(ch)
        return {"data": characters}
    except InvalidIdError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/novel/{novel_id}/graph")
async def get_characters_graph(novel_id: str):
    try:
        graph = await CharacterService.get_characters_graph(novel_id)
        return graph
    except InvalidIdError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{character_id}")
async def get_character(character_id: str):
    try:
        character = await CharacterService.get_character_by_id(character_id)
        return _serialize_character(character)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except InvalidIdError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{character_id}")
async def update_character(character_id: str, req: UpdateCharacterRequest):
    try:
        success = await CharacterService.update_character_info(character_id, req.model_dump(exclude_unset=True))
        return {"success": success}
    except (ValueError, InvalidIdError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/batch-order")
async def batch_update_sort_order(req: BatchUpdateSortOrderRequest):
    try:
        count = await CharacterService.batch_update_sort_order(req.novel_id, req.sort_map)
        return {"success": True, "updated": count}
    except InvalidIdError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{character_id}")
async def soft_delete_character(character_id: str):
    try:
        success = await CharacterService.soft_delete_character(character_id)
        return {"success": success}
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except InvalidIdError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{character_id}/restore")
async def restore_character(character_id: str):
    try:
        success = await CharacterService.restore_character(character_id)
        return {"success": success}
    except InvalidIdError as e:
        raise HTTPException(status_code=400, detail=str(e))
