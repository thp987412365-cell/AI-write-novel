import logging
from typing import Any, Dict, List

from application.db.repositories.character_repository import character_repo
from application.db.repositories.novel_repository import novel_repo

logger = logging.getLogger(__name__)


class CharacterService:

    @staticmethod
    async def create_character(data: Dict[str, Any]) -> str:
        novel_id = data.get("novel_id")
        if not novel_id:
            raise ValueError("novel_id is required")
        await novel_repo.get_novel_by_id(novel_id)
        return await character_repo.create_character(data)

    @staticmethod
    async def get_characters_by_novel(
        novel_id: str,
        role: str | None = None,
        faction_id: str | None = None
    ) -> List[Dict[str, Any]]:
        return await character_repo.get_characters_by_novel(novel_id, role, faction_id)

    @staticmethod
    async def get_character_by_id(character_id: str) -> Dict[str, Any]:
        return await character_repo.get_character_by_id(character_id)

    @staticmethod
    async def update_character_info(character_id: str, update_data: Dict[str, Any]) -> bool:
        return await character_repo.update_character_info(character_id, update_data)

    @staticmethod
    async def batch_update_sort_order(novel_id: str, sort_map: Dict[str, int]) -> int:
        return await character_repo.batch_update_sort_order(novel_id, sort_map)

    @staticmethod
    async def soft_delete_character(character_id: str) -> bool:
        return await character_repo.soft_delete_character(character_id)

    @staticmethod
    async def restore_character(character_id: str) -> bool:
        return await character_repo.restore_character(character_id)

    @staticmethod
    async def get_characters_graph(novel_id: str) -> Dict[str, Any]:
        return await character_repo.get_characters_graph(novel_id)
