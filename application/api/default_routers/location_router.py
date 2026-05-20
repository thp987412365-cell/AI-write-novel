from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional

from application.services.novel.location_service import LocationService
from application.db.errors import NotFoundError, InvalidIdError, DuplicateKeyError

router = APIRouter(prefix="/api/locations", tags=["locations"])


class CreateLocationRequest(BaseModel):
    novel_id: str
    name: str
    type: Optional[str] = None
    parent_location_id: Optional[str] = None
    description: Optional[str] = None
    climate: Optional[str] = None
    culture: Optional[str] = None
    history: Optional[str] = None
    significance: Optional[str] = None
    controlled_by_faction_ids: Optional[List[str]] = None
    notable_features: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    sort_order: Optional[int] = None


class UpdateLocationRequest(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    parent_location_id: Optional[str] = None
    description: Optional[str] = None
    climate: Optional[str] = None
    culture: Optional[str] = None
    history: Optional[str] = None
    significance: Optional[str] = None
    controlled_by_faction_ids: Optional[List[str]] = None
    notable_features: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    sort_order: Optional[int] = None


def _serialize_location(loc: dict) -> dict:
    if "_id" in loc:
        loc["_id"] = str(loc["_id"])
    if "novel_id" in loc:
        loc["novel_id"] = str(loc["novel_id"])
    if "parent_location_id" in loc and loc["parent_location_id"]:
        loc["parent_location_id"] = str(loc["parent_location_id"])
    return loc


@router.post("/create")
async def create_location(req: CreateLocationRequest):
    data = req.model_dump(exclude_unset=True)
    try:
        loc_id = await LocationService.create_location(data)
        return {"id": loc_id, "message": "Location created"}
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except DuplicateKeyError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except (ValueError, InvalidIdError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/novel/{novel_id}")
async def get_locations_by_novel(
    novel_id: str,
    type: Optional[str] = Query(None),
    parent_id: Optional[str] = Query(None)
):
    try:
        locations = await LocationService.get_locations_by_novel(novel_id, type, parent_id)
        for loc in locations:
            _serialize_location(loc)
        return {"data": locations}
    except InvalidIdError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{location_id}")
async def get_location(location_id: str):
    try:
        loc = await LocationService.get_location_by_id(location_id)
        return _serialize_location(loc)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except InvalidIdError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{location_id}")
async def update_location(location_id: str, req: UpdateLocationRequest):
    try:
        success = await LocationService.update_location_info(location_id, req.model_dump(exclude_unset=True))
        return {"success": success}
    except (ValueError, InvalidIdError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{location_id}")
async def soft_delete_location(location_id: str):
    try:
        success = await LocationService.soft_delete_location(location_id)
        return {"success": success}
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except InvalidIdError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{location_id}/restore")
async def restore_location(location_id: str):
    try:
        success = await LocationService.restore_location(location_id)
        return {"success": success}
    except InvalidIdError as e:
        raise HTTPException(status_code=400, detail=str(e))
