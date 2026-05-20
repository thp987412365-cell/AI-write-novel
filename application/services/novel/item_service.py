import logging
from typing import Any, Dict, List

from application.db.repositories.item_repository import item_repo
from application.db.repositories.novel_repository import novel_repo

logger = logging.getLogger(__name__)


class ItemService:

    @staticmethod
    async def create_item(data: Dict[str, Any]) -> str:
        novel_id = data.get("novel_id")
        if not novel_id:
            raise ValueError("novel_id is required")
        await novel_repo.get_novel_by_id(novel_id)
        return await item_repo.create_item(data)

    @staticmethod
    async def get_items_by_novel(
        novel_id: str,
        item_type: str | None = None,
        rarity: str | None = None
    ) -> List[Dict[str, Any]]:
        return await item_repo.get_items_by_novel(novel_id, item_type, rarity)

    @staticmethod
    async def get_item_by_id(item_id: str) -> Dict[str, Any]:
        return await item_repo.get_item_by_id(item_id)

    @staticmethod
    async def update_item_info(item_id: str, update_data: Dict[str, Any]) -> bool:
        return await item_repo.update_item_info(item_id, update_data)

    @staticmethod
    async def soft_delete_item(item_id: str) -> bool:
        return await item_repo.soft_delete_item(item_id)

    @staticmethod
    async def restore_item(item_id: str) -> bool:
        return await item_repo.restore_item(item_id)
