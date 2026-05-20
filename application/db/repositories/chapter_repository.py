import logging
from typing import Any, Dict, List

import pymongo.errors

from application.db.base import BaseRepository
from application.db.utils import to_object_id, get_utc_now
from application.db.errors import NotFoundError, DuplicateKeyError

logger = logging.getLogger(__name__)


class ChapterRepository(BaseRepository):
    def __init__(self):
        super().__init__("chapters")

    async def _get_next_chapter_index(self, novel_id) -> int:
        obj_id = to_object_id(novel_id)
        cursor = self.collection.find(
            {"novel_id": obj_id, "is_deleted": False},
            projection={"chapter_index": 1}
        ).sort("chapter_index", -1).limit(1)
        docs = await cursor.to_list(length=1)
        if docs:
            return docs[0].get("chapter_index", 0) + 1
        return 1

    async def create_chapter(self, data: Dict[str, Any]) -> str:
        if "novel_id" not in data:
            raise ValueError("novel_id is required")
        if "title" not in data or not data["title"]:
            raise ValueError("Chapter title cannot be empty")

        data["novel_id"] = to_object_id(data["novel_id"])
        if data.get("volume_id"):
            data["volume_id"] = to_object_id(data["volume_id"])

        if not data.get("chapter_index"):
            data["chapter_index"] = await self._get_next_chapter_index(data["novel_id"])

        data.setdefault("content", "")
        data.setdefault("word_count", 0)
        data.setdefault("status", "draft")
        data.setdefault("summary", "")
        data.setdefault("key_events", [])
        data.setdefault("appeared_characters", [])
        data.setdefault("appeared_locations", [])
        data.setdefault("sort_order", data.get("chapter_index", 0))

        try:
            return await self.insert_one(data)
        except pymongo.errors.DuplicateKeyError:
            raise DuplicateKeyError(
                f"同一小说下 chapter_index={data['chapter_index']} 已存在"
            )

    async def get_chapters_by_novel(self, novel_id: str) -> List[Dict[str, Any]]:
        obj_id = to_object_id(novel_id)
        return await self.find_many(
            {"novel_id": obj_id},
            sort=[("sort_order", 1)]
        )

    async def get_chapters_by_volume(self, novel_id: str, volume_id: str) -> List[Dict[str, Any]]:
        obj_id = to_object_id(novel_id)
        vol_id = to_object_id(volume_id)
        return await self.find_many(
            {"novel_id": obj_id, "volume_id": vol_id},
            sort=[("sort_order", 1)]
        )

    async def get_chapter_by_id(self, chapter_id: str) -> Dict[str, Any]:
        obj_id = to_object_id(chapter_id)
        chapter = await self.find_one({"_id": obj_id})
        if not chapter:
            raise NotFoundError(f"Chapter with id {chapter_id} not found")
        return chapter

    async def update_chapter_info(self, chapter_id: str, update_data: Dict[str, Any]) -> bool:
        allowed_fields = {"title", "content", "word_count", "status", "summary",
                          "key_events", "appeared_characters", "appeared_locations",
                          "volume_id", "sort_order", "chapter_index"}
        filtered = {k: v for k, v in update_data.items() if k in allowed_fields}
        if not filtered:
            return False
        if "volume_id" in filtered and filtered["volume_id"]:
            filtered["volume_id"] = to_object_id(filtered["volume_id"])
        obj_id = to_object_id(chapter_id)
        try:
            return await self.update_one({"_id": obj_id}, filtered)
        except pymongo.errors.DuplicateKeyError:
            raise DuplicateKeyError("chapter_index 冲突")

    async def batch_update_sort_order(self, novel_id: str, sort_map: Dict[str, int]) -> int:
        obj_id = to_object_id(novel_id)
        count = 0
        for chapter_id_str, order in sort_map.items():
            chapter_obj_id = to_object_id(chapter_id_str)
            result = await self.update_one(
                {"_id": chapter_obj_id, "novel_id": obj_id},
                {"sort_order": order},
                include_deleted=True
            )
            if result:
                count += 1
        return count

    async def soft_delete_chapter(self, chapter_id: str) -> bool:
        obj_id = to_object_id(chapter_id)
        await self.get_chapter_by_id(chapter_id)
        now = get_utc_now()
        result = await self.collection.update_one(
            {"_id": obj_id},
            {"$set": {"is_deleted": True, "deleted_at": now, "updated_at": now}}
        )
        return result.modified_count > 0

    async def restore_chapter(self, chapter_id: str) -> bool:
        obj_id = to_object_id(chapter_id)
        result = await self.collection.update_one(
            {"_id": obj_id, "is_deleted": True},
            {"$set": {"is_deleted": False, "deleted_at": None, "updated_at": get_utc_now()}}
        )
        return result.modified_count > 0


chapter_repo = ChapterRepository()
