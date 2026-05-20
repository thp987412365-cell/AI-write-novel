from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Optional

from application.services.novel.chapter_service import ChapterService
from application.db.errors import NotFoundError, InvalidIdError, DuplicateKeyError

router = APIRouter(prefix="/api/chapters", tags=["chapters"])


class CreateChapterRequest(BaseModel):
    novel_id: str
    title: str
    volume_id: Optional[str] = None
    chapter_index: Optional[int] = None
    content: Optional[str] = None
    summary: Optional[str] = None


class UpdateChapterRequest(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    word_count: Optional[int] = None
    status: Optional[str] = None
    summary: Optional[str] = None
    key_events: Optional[List[str]] = None
    appeared_characters: Optional[List[str]] = None
    appeared_locations: Optional[List[str]] = None
    volume_id: Optional[str] = None
    sort_order: Optional[int] = None
    chapter_index: Optional[int] = None


class BatchUpdateSortOrderRequest(BaseModel):
    novel_id: str
    sort_map: Dict[str, int]


def _serialize_chapter(chapter: dict) -> dict:
    if "_id" in chapter:
        chapter["_id"] = str(chapter["_id"])
    if "novel_id" in chapter:
        chapter["novel_id"] = str(chapter["novel_id"])
    if "volume_id" in chapter and chapter["volume_id"]:
        chapter["volume_id"] = str(chapter["volume_id"])
    return chapter


@router.post("/create")
async def create_chapter(req: CreateChapterRequest):
    data = req.model_dump(exclude_unset=True)
    try:
        chapter_id = await ChapterService.create_chapter(data)
        return {"id": chapter_id, "message": "Chapter created"}
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except DuplicateKeyError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except (ValueError, InvalidIdError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/novel/{novel_id}")
async def get_chapters_by_novel(novel_id: str):
    try:
        chapters = await ChapterService.get_chapters_by_novel(novel_id)
        for ch in chapters:
            _serialize_chapter(ch)
        return {"data": chapters}
    except InvalidIdError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/volume/{novel_id}/{volume_id}")
async def get_chapters_by_volume(novel_id: str, volume_id: str):
    try:
        chapters = await ChapterService.get_chapters_by_volume(novel_id, volume_id)
        for ch in chapters:
            _serialize_chapter(ch)
        return {"data": chapters}
    except InvalidIdError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{chapter_id}")
async def get_chapter(chapter_id: str):
    try:
        chapter = await ChapterService.get_chapter_by_id(chapter_id)
        return _serialize_chapter(chapter)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except InvalidIdError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{chapter_id}")
async def update_chapter(chapter_id: str, req: UpdateChapterRequest):
    try:
        success = await ChapterService.update_chapter_info(chapter_id, req.model_dump(exclude_unset=True))
        return {"success": success}
    except DuplicateKeyError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except (ValueError, InvalidIdError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/batch-order")
async def batch_update_sort_order(req: BatchUpdateSortOrderRequest):
    try:
        count = await ChapterService.batch_update_sort_order(req.novel_id, req.sort_map)
        return {"success": True, "updated": count}
    except InvalidIdError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{chapter_id}")
async def soft_delete_chapter(chapter_id: str):
    try:
        success = await ChapterService.soft_delete_chapter(chapter_id)
        return {"success": success}
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except InvalidIdError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{chapter_id}/restore")
async def restore_chapter(chapter_id: str):
    try:
        success = await ChapterService.restore_chapter(chapter_id)
        return {"success": success}
    except InvalidIdError as e:
        raise HTTPException(status_code=400, detail=str(e))
