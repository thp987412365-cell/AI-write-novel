import logging
from typing import Any, Dict, List

from application.db.repositories.location_repository import location_repo
from application.db.repositories.novel_repository import novel_repo

logger = logging.getLogger(__name__)


class LocationService:

    @staticmethod
    async def create_location(data: Dict[str, Any]) -> str:
        novel_id = data.get("novel_id")
        if not novel_id:
            raise ValueError("novel_id is required")
        await novel_repo.get_novel_by_id(novel_id)
        return await location_repo.create_location(data)

    @staticmethod
    async def get_locations_by_novel(
        novel_id: str,
        loc_type: str | None = None,
        parent_id: str | None = None
    ) -> List[Dict[str, Any]]:
        return await location_repo.get_locations_by_novel(novel_id, loc_type, parent_id)

    @staticmethod
    async def get_location_by_id(location_id: str) -> Dict[str, Any]:
        return await location_repo.get_location_by_id(location_id)

    @staticmethod
    async def update_location_info(location_id: str, update_data: Dict[str, Any]) -> bool:
        return await location_repo.update_location_info(location_id, update_data)

    @staticmethod
    async def soft_delete_location(location_id: str) -> bool:
        return await location_repo.soft_delete_location(location_id)

    @staticmethod
    async def restore_location(location_id: str) -> bool:
        return await location_repo.restore_location(location_id)
