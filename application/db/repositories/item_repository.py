import logging
from typing import Any, Dict, List

import pymongo.errors

from application.db.base import BaseRepository
from application.db.utils import to_object_id, get_utc_now
from application.db.errors import NotFoundError, DuplicateKeyError

logger = logging.getLogger(__name__)


class ItemRepository(BaseRepository):
    def __init__(self):
        super().__init__("items")

    async def create_item(self, data: Dict[str, Any]) -> str:
        if "novel_id" not in data:
            raise ValueError("novel_id is required")
        if "name" not in data or not data["name"]:
            raise ValueError("Item name cannot be empty")

        data["novel_id"] = to_object_id(data["novel_id"])
        if data.get("current_owner_character_id"):
            data["current_owner_character_id"] = to_object_id(data["current_owner_character_id"])

        data.setdefault("type", "artifact")
        data.setdefault("rarity", "common")
        data.setdefault("description", "")
        data.setdefault("abilities", [])
        data.setdefault("origin", "")
        data.setdefault("history", "")
        data.setdefault("limitations", "")
        data.setdefault("significance", "")
        data.setdefault("tags", [])
        data.setdefault("sort_order", 0)

        try:
            return await self.insert_one(data)
        except pymongo.errors.DuplicateKeyError:
            raise DuplicateKeyError(f"同一小说下物品 '{data['name']}' 已存在")

    async def get_items_by_novel(
        self, novel_id: str,
        item_type: str | None = None,
        rarity: str | None = None
    ) -> List[Dict[str, Any]]:
        obj_id = to_object_id(novel_id)
        query: Dict[str, Any] = {"novel_id": obj_id}
        if item_type:
            query["type"] = item_type
        if rarity:
            query["rarity"] = rarity
        return await self.find_many(query, sort=[("sort_order", 1)])

    async def get_item_by_id(self, item_id: str) -> Dict[str, Any]:
        obj_id = to_object_id(item_id)
        item = await self.find_one({"_id": obj_id})
        if not item:
            raise NotFoundError(f"Item with id {item_id} not found")
        return item

    async def update_item_info(self, item_id: str, update_data: Dict[str, Any]) -> bool:
        forbidden = {"_id", "novel_id", "created_at", "is_deleted", "deleted_at"}
        filtered = {k: v for k, v in update_data.items() if k not in forbidden}
        if not filtered:
            return False
        if "current_owner_character_id" in filtered and filtered["current_owner_character_id"]:
            filtered["current_owner_character_id"] = to_object_id(filtered["current_owner_character_id"])
        obj_id = to_object_id(item_id)
        return await self.update_one({"_id": obj_id}, filtered)

    async def soft_delete_item(self, item_id: str) -> bool:
        obj_id = to_object_id(item_id)
        await self.get_item_by_id(item_id)
        now = get_utc_now()
        result = await self.collection.update_one(
            {"_id": obj_id},
            {"$set": {"is_deleted": True, "deleted_at": now, "updated_at": now}}
        )
        return result.modified_count > 0

    async def restore_item(self, item_id: str) -> bool:
        obj_id = to_object_id(item_id)
        result = await self.collection.update_one(
            {"_id": obj_id, "is_deleted": True},
            {"$set": {"is_deleted": False, "deleted_at": None, "updated_at": get_utc_now()}}
        )
        return result.modified_count > 0


item_repo = ItemRepository()
