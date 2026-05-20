import logging
from typing import Any, Dict, List

from application.db.repositories.rule_repository import rule_repo
from application.db.repositories.novel_repository import novel_repo

logger = logging.getLogger(__name__)


class RuleService:

    @staticmethod
    async def create_rule(data: Dict[str, Any]) -> str:
        novel_id = data.get("novel_id")
        if not novel_id:
            raise ValueError("novel_id is required")
        await novel_repo.get_novel_by_id(novel_id)
        return await rule_repo.create_rule(data)

    @staticmethod
    async def get_rules_by_novel(
        novel_id: str,
        category: str | None = None
    ) -> List[Dict[str, Any]]:
        return await rule_repo.get_rules_by_novel(novel_id, category)

    @staticmethod
    async def get_rule_by_id(rule_id: str) -> Dict[str, Any]:
        return await rule_repo.get_rule_by_id(rule_id)

    @staticmethod
    async def update_rule_info(rule_id: str, update_data: Dict[str, Any]) -> bool:
        return await rule_repo.update_rule_info(rule_id, update_data)

    @staticmethod
    async def soft_delete_rule(rule_id: str) -> bool:
        return await rule_repo.soft_delete_rule(rule_id)

    @staticmethod
    async def restore_rule(rule_id: str) -> bool:
        return await rule_repo.restore_rule(rule_id)
