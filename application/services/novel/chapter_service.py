import logging
from typing import Any, Dict, List

from application.db.repositories.chapter_repository import chapter_repo
from application.db.repositories.novel_repository import novel_repo

logger = logging.getLogger(__name__)


class ChapterService:

    @staticmethod
    async def create_chapter(data: Dict[str, Any]) -> str:
        novel_id = data.get("novel_id")
        if not novel_id:
            raise ValueError("novel_id is required")
        await novel_repo.get_novel_by_id(novel_id)
        return await chapter_repo.create_chapter(data)

    @staticmethod
    async def get_chapters_by_novel(novel_id: str) -> List[Dict[str, Any]]:
        return await chapter_repo.get_chapters_by_novel(novel_id)

    @staticmethod
    async def get_chapters_by_volume(novel_id: str, volume_id: str) -> List[Dict[str, Any]]:
        return await chapter_repo.get_chapters_by_volume(novel_id, volume_id)

    @staticmethod
    async def get_chapter_by_id(chapter_id: str) -> Dict[str, Any]:
        return await chapter_repo.get_chapter_by_id(chapter_id)

    @staticmethod
    async def update_chapter_info(chapter_id: str, update_data: Dict[str, Any]) -> bool:
        return await chapter_repo.update_chapter_info(chapter_id, update_data)

    @staticmethod
    async def batch_update_sort_order(novel_id: str, sort_map: Dict[str, int]) -> int:
        return await chapter_repo.batch_update_sort_order(novel_id, sort_map)

    @staticmethod
    async def soft_delete_chapter(chapter_id: str) -> bool:
        return await chapter_repo.soft_delete_chapter(chapter_id)

    @staticmethod
    async def restore_chapter(chapter_id: str) -> bool:
        return await chapter_repo.restore_chapter(chapter_id)
