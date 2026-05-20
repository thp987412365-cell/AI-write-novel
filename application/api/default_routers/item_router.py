from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional

from application.services.novel.item_service import ItemService
from application.db.errors import NotFoundError, InvalidIdError, DuplicateKeyError

router = APIRouter(prefix="/api/items", tags=["items"])


class CreateItemRequest(BaseModel):
    novel_id: str
    name: str
    type: Optional[str] = None
    rarity: Optional[str] = None
    description: Optional[str] = None
    abilities: Optional[List[str]] = None
    origin: Optional[str] = None
    current_owner_character_id: Optional[str] = None
    history: Optional[str] = None
    limitations: Optional[str] = None
    significance: Optional[str] = None
    tags: Optional[List[str]] = None
    sort_order: Optional[int] = None


class UpdateItemRequest(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    rarity: Optional[str] = None
    description: Optional[str] = None
    abilities: Optional[List[str]] = None
    origin: Optional[str] = None
    current_owner_character_id: Optional[str] = None
    history: Optional[str] = None
    limitations: Optional[str] = None
    significance: Optional[str] = None
    tags: Optional[List[str]] = None
    sort_order: Optional[int] = None


def _serialize_item(item: dict) -> dict:
    if "_id" in item:
        item["_id"] = str(item["_id"])
    if "novel_id" in item:
        item["novel_id"] = str(item["novel_id"])
    if "current_owner_character_id" in item and item["current_owner_character_id"]:
        item["current_owner_character_id"] = str(item["current_owner_character_id"])
    return item


@router.post("/create")
async def create_item(req: CreateItemRequest):
    data = req.model_dump(exclude_unset=True)
    try:
        item_id = await ItemService.create_item(data)
        return {"id": item_id, "message": "Item created"}
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except DuplicateKeyError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except (ValueError, InvalidIdError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/novel/{novel_id}")
async def get_items_by_novel(
    novel_id: str,
    type: Optional[str] = Query(None),
    rarity: Optional[str] = Query(None)
):
    try:
        items = await ItemService.get_items_by_novel(novel_id, type, rarity)
        for item in items:
            _serialize_item(item)
        return {"data": items}
    except InvalidIdError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{item_id}")
async def get_item(item_id: str):
    try:
        item = await ItemService.get_item_by_id(item_id)
        return _serialize_item(item)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except InvalidIdError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{item_id}")
async def update_item(item_id: str, req: UpdateItemRequest):
    try:
        success = await ItemService.update_item_info(item_id, req.model_dump(exclude_unset=True))
        return {"success": success}
    except (ValueError, InvalidIdError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{item_id}")
async def soft_delete_item(item_id: str):
    try:
        success = await ItemService.soft_delete_item(item_id)
        return {"success": success}
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except InvalidIdError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{item_id}/restore")
async def restore_item(item_id: str):
    try:
        success = await ItemService.restore_item(item_id)
        return {"success": success}
    except InvalidIdError as e:
        raise HTTPException(status_code=400, detail=str(e))
