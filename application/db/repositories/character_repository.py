import logging
from typing import Any, Dict, List

import pymongo.errors

from application.db.base import BaseRepository
from application.db.utils import to_object_id, get_utc_now
from application.db.errors import NotFoundError, DuplicateKeyError

logger = logging.getLogger(__name__)


class CharacterRepository(BaseRepository):
    def __init__(self):
        super().__init__("characters")

    async def _get_next_char_id(self, novel_id) -> str:
        obj_id = to_object_id(novel_id)
        cursor = self.collection.find(
            {"novel_id": obj_id},
            projection={"char_id": 1}
        ).sort("char_id", -1).limit(1)
        docs = await cursor.to_list(length=1)
        if docs and docs[0].get("char_id"):
            try:
                num = int(docs[0]["char_id"].split("_")[1])
                return f"char_{num + 1:06d}"
            except (IndexError, ValueError):
                pass
        return "char_000001"

    async def create_character(self, data: Dict[str, Any]) -> str:
        if "novel_id" not in data:
            raise ValueError("novel_id is required")
        if "name" not in data or not data["name"]:
            raise ValueError("Character name cannot be empty")

        data["novel_id"] = to_object_id(data["novel_id"])
        if not data.get("char_id"):
            data["char_id"] = await self._get_next_char_id(data["novel_id"])

        data.setdefault("aliases", [])
        data.setdefault("role", "supporting")
        data.setdefault("gender", "")
        data.setdefault("age", "")
        data.setdefault("appearance", "")
        data.setdefault("personality", "")
        data.setdefault("background", "")
        data.setdefault("abilities", [])
        data.setdefault("goals", "")
        data.setdefault("secrets", "")
        data.setdefault("relationships", [])
        data.setdefault("faction_id", None)
        data.setdefault("first_appearance_chapter_index", None)
        data.setdefault("status", "alive")
        data.setdefault("avatar_url", "")
        data.setdefault("tags", [])
        data.setdefault("sort_order", 0)

        try:
            return await self.insert_one(data)
        except pymongo.errors.DuplicateKeyError:
            raise DuplicateKeyError(
                f"同一小说下角色名 '{data['name']}' 已存在"
            )

    async def get_characters_by_novel(
        self, novel_id: str,
        role: str | None = None,
        faction_id: str | None = None
    ) -> List[Dict[str, Any]]:
        obj_id = to_object_id(novel_id)
        query: Dict[str, Any] = {"novel_id": obj_id}
        if role:
            query["role"] = role
        if faction_id:
            query["faction_id"] = faction_id
        return await self.find_many(query, sort=[("sort_order", 1)])

    async def get_character_by_id(self, character_id: str) -> Dict[str, Any]:
        obj_id = to_object_id(character_id)
        character = await self.find_one({"_id": obj_id})
        if not character:
            raise NotFoundError(f"Character with id {character_id} not found")
        return character

    async def get_character_by_char_id(self, novel_id: str, char_id: str) -> Dict[str, Any]:
        obj_id = to_object_id(novel_id)
        character = await self.find_one({"novel_id": obj_id, "char_id": char_id})
        if not character:
            raise NotFoundError(f"Character with char_id {char_id} not found")
        return character

    async def update_character_info(self, character_id: str, update_data: Dict[str, Any]) -> bool:
        forbidden = {"_id", "novel_id", "char_id", "created_at", "is_deleted", "deleted_at"}
        filtered = {k: v for k, v in update_data.items() if k not in forbidden}
        if not filtered:
            return False
        obj_id = to_object_id(character_id)
        return await self.update_one({"_id": obj_id}, filtered)

    async def batch_update_sort_order(self, novel_id: str, sort_map: Dict[str, int]) -> int:
        obj_id = to_object_id(novel_id)
        count = 0
        for character_id_str, order in sort_map.items():
            char_obj_id = to_object_id(character_id_str)
            result = await self.update_one(
                {"_id": char_obj_id, "novel_id": obj_id},
                {"sort_order": order}
            )
            if result:
                count += 1
        return count

    async def soft_delete_character(self, character_id: str) -> bool:
        obj_id = to_object_id(character_id)
        await self.get_character_by_id(character_id)
        now = get_utc_now()
        result = await self.collection.update_one(
            {"_id": obj_id},
            {"$set": {"is_deleted": True, "deleted_at": now, "updated_at": now}}
        )
        return result.modified_count > 0

    async def restore_character(self, character_id: str) -> bool:
        obj_id = to_object_id(character_id)
        result = await self.collection.update_one(
            {"_id": obj_id, "is_deleted": True},
            {"$set": {"is_deleted": False, "deleted_at": None, "updated_at": get_utc_now()}}
        )
        return result.modified_count > 0

    async def get_characters_graph(self, novel_id: str) -> Dict[str, Any]:
        characters = await self.get_characters_by_novel(novel_id)
        nodes = []
        edges = []
        char_map: Dict[str, str] = {}

        for ch in characters:
            cid = str(ch["_id"])
            name = ch.get("name", "")
            char_map[cid] = name
            char_id = ch.get("char_id", "")
            nodes.append({
                "id": cid,
                "char_id": char_id,
                "name": name,
                "role": ch.get("role", "supporting"),
                "faction_id": ch.get("faction_id"),
                "status": ch.get("status", "alive"),
                "avatar_url": ch.get("avatar_url", ""),
            })

        for ch in characters:
            cid = str(ch["_id"])
            for rel in ch.get("relationships", []):
                edges.append({
                    "source": cid,
                    "target": rel.get("target_id", ""),
                    "relation_type": rel.get("relation_type", "关联"),
                    "description": rel.get("description", ""),
                })

        return {"nodes": nodes, "edges": edges}


character_repo = CharacterRepository()
