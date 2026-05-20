import logging
from typing import Any, Dict, List

import pymongo.errors

from application.db.base import BaseRepository
from application.db.utils import to_object_id, get_utc_now
from application.db.errors import NotFoundError, DuplicateKeyError

logger = logging.getLogger(__name__)


class RuleRepository(BaseRepository):
    def __init__(self):
        super().__init__("rules")

    async def create_rule(self, data: Dict[str, Any]) -> str:
        if "novel_id" not in data:
            raise ValueError("novel_id is required")
        if "name" not in data or not data["name"]:
            raise ValueError("Rule name cannot be empty")

        data["novel_id"] = to_object_id(data["novel_id"])
        data.setdefault("category", "custom")
        data.setdefault("description", "")
        data.setdefault("principles", [])
        data.setdefault("exceptions", [])
        data.setdefault("limitations", "")
        data.setdefault("related_factions", [])
        data.setdefault("related_characters", [])
        data.setdefault("impact_on_plot", "")
        data.setdefault("sort_order", 0)

        try:
            return await self.insert_one(data)
        except pymongo.errors.DuplicateKeyError:
            raise DuplicateKeyError(f"同一小说下规则 '{data['name']}' 已存在")

    async def get_rules_by_novel(
        self, novel_id: str,
        category: str | None = None
    ) -> List[Dict[str, Any]]:
        obj_id = to_object_id(novel_id)
        query: Dict[str, Any] = {"novel_id": obj_id}
        if category:
            query["category"] = category
        return await self.find_many(query, sort=[("sort_order", 1)])

    async def get_rule_by_id(self, rule_id: str) -> Dict[str, Any]:
        obj_id = to_object_id(rule_id)
        rule = await self.find_one({"_id": obj_id})
        if not rule:
            raise NotFoundError(f"Rule with id {rule_id} not found")
        return rule

    async def update_rule_info(self, rule_id: str, update_data: Dict[str, Any]) -> bool:
        forbidden = {"_id", "novel_id", "created_at", "is_deleted", "deleted_at"}
        filtered = {k: v for k, v in update_data.items() if k not in forbidden}
        if not filtered:
            return False
        obj_id = to_object_id(rule_id)
        return await self.update_one({"_id": obj_id}, filtered)

    async def soft_delete_rule(self, rule_id: str) -> bool:
        obj_id = to_object_id(rule_id)
        await self.get_rule_by_id(rule_id)
        now = get_utc_now()
        result = await self.collection.update_one(
            {"_id": obj_id},
            {"$set": {"is_deleted": True, "deleted_at": now, "updated_at": now}}
        )
        return result.modified_count > 0

    async def restore_rule(self, rule_id: str) -> bool:
        obj_id = to_object_id(rule_id)
        result = await self.collection.update_one(
            {"_id": obj_id, "is_deleted": True},
            {"$set": {"is_deleted": False, "deleted_at": None, "updated_at": get_utc_now()}}
        )
        return result.modified_count > 0


rule_repo = RuleRepository()
