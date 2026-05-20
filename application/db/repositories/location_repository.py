import logging
from typing import Any, Dict, List

import pymongo.errors

from application.db.base import BaseRepository
from application.db.utils import to_object_id, get_utc_now
from application.db.errors import NotFoundError, DuplicateKeyError

logger = logging.getLogger(__name__)


class LocationRepository(BaseRepository):
    def __init__(self):
        super().__init__("locations")

    async def create_location(self, data: Dict[str, Any]) -> str:
        if "novel_id" not in data:
            raise ValueError("novel_id is required")
        if "name" not in data or not data["name"]:
            raise ValueError("Location name cannot be empty")

        data["novel_id"] = to_object_id(data["novel_id"])
        if data.get("parent_location_id"):
            data["parent_location_id"] = to_object_id(data["parent_location_id"])

        data.setdefault("type", "city")
        data.setdefault("description", "")
        data.setdefault("climate", "")
        data.setdefault("culture", "")
        data.setdefault("history", "")
        data.setdefault("significance", "")
        data.setdefault("controlled_by_faction_ids", [])
        data.setdefault("notable_features", [])
        data.setdefault("tags", [])
        data.setdefault("sort_order", 0)

        try:
            return await self.insert_one(data)
        except pymongo.errors.DuplicateKeyError:
            raise DuplicateKeyError(f"同一小说下地点 '{data['name']}' 已存在")

    async def get_locations_by_novel(
        self, novel_id: str,
        loc_type: str | None = None,
        parent_id: str | None = None
    ) -> List[Dict[str, Any]]:
        obj_id = to_object_id(novel_id)
        query: Dict[str, Any] = {"novel_id": obj_id}
        if loc_type:
            query["type"] = loc_type
        if parent_id:
            query["parent_location_id"] = to_object_id(parent_id)
        return await self.find_many(query, sort=[("sort_order", 1)])

    async def get_location_by_id(self, location_id: str) -> Dict[str, Any]:
        obj_id = to_object_id(location_id)
        loc = await self.find_one({"_id": obj_id})
        if not loc:
            raise NotFoundError(f"Location with id {location_id} not found")
        return loc

    async def update_location_info(self, location_id: str, update_data: Dict[str, Any]) -> bool:
        forbidden = {"_id", "novel_id", "created_at", "is_deleted", "deleted_at"}
        filtered = {k: v for k, v in update_data.items() if k not in forbidden}
        if not filtered:
            return False
        if "parent_location_id" in filtered and filtered["parent_location_id"]:
            filtered["parent_location_id"] = to_object_id(filtered["parent_location_id"])
        obj_id = to_object_id(location_id)
        return await self.update_one({"_id": obj_id}, filtered)

    async def soft_delete_location(self, location_id: str) -> bool:
        obj_id = to_object_id(location_id)
        await self.get_location_by_id(location_id)
        now = get_utc_now()
        result = await self.collection.update_one(
            {"_id": obj_id},
            {"$set": {"is_deleted": True, "deleted_at": now, "updated_at": now}}
        )
        return result.modified_count > 0

    async def restore_location(self, location_id: str) -> bool:
        obj_id = to_object_id(location_id)
        result = await self.collection.update_one(
            {"_id": obj_id, "is_deleted": True},
            {"$set": {"is_deleted": False, "deleted_at": None, "updated_at": get_utc_now()}}
        )
        return result.modified_count > 0


location_repo = LocationRepository()
