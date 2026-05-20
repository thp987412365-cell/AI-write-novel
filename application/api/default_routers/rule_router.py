from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional

from application.services.novel.rule_service import RuleService
from application.db.errors import NotFoundError, InvalidIdError, DuplicateKeyError

router = APIRouter(prefix="/api/rules", tags=["rules"])


class CreateRuleRequest(BaseModel):
    novel_id: str
    name: str
    category: Optional[str] = None
    description: Optional[str] = None
    principles: Optional[List[str]] = None
    exceptions: Optional[List[str]] = None
    limitations: Optional[str] = None
    related_factions: Optional[List[str]] = None
    related_characters: Optional[List[str]] = None
    impact_on_plot: Optional[str] = None
    sort_order: Optional[int] = None


class UpdateRuleRequest(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    principles: Optional[List[str]] = None
    exceptions: Optional[List[str]] = None
    limitations: Optional[str] = None
    related_factions: Optional[List[str]] = None
    related_characters: Optional[List[str]] = None
    impact_on_plot: Optional[str] = None
    sort_order: Optional[int] = None


def _serialize_rule(rule: dict) -> dict:
    if "_id" in rule:
        rule["_id"] = str(rule["_id"])
    if "novel_id" in rule:
        rule["novel_id"] = str(rule["novel_id"])
    return rule


@router.post("/create")
async def create_rule(req: CreateRuleRequest):
    data = req.model_dump(exclude_unset=True)
    try:
        rule_id = await RuleService.create_rule(data)
        return {"id": rule_id, "message": "Rule created"}
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except DuplicateKeyError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except (ValueError, InvalidIdError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/novel/{novel_id}")
async def get_rules_by_novel(
    novel_id: str,
    category: Optional[str] = Query(None)
):
    try:
        rules = await RuleService.get_rules_by_novel(novel_id, category)
        for rule in rules:
            _serialize_rule(rule)
        return {"data": rules}
    except InvalidIdError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{rule_id}")
async def get_rule(rule_id: str):
    try:
        rule = await RuleService.get_rule_by_id(rule_id)
        return _serialize_rule(rule)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except InvalidIdError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{rule_id}")
async def update_rule(rule_id: str, req: UpdateRuleRequest):
    try:
        success = await RuleService.update_rule_info(rule_id, req.model_dump(exclude_unset=True))
        return {"success": success}
    except (ValueError, InvalidIdError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{rule_id}")
async def soft_delete_rule(rule_id: str):
    try:
        success = await RuleService.soft_delete_rule(rule_id)
        return {"success": success}
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except InvalidIdError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{rule_id}/restore")
async def restore_rule(rule_id: str):
    try:
        success = await RuleService.restore_rule(rule_id)
        return {"success": success}
    except InvalidIdError as e:
        raise HTTPException(status_code=400, detail=str(e))
