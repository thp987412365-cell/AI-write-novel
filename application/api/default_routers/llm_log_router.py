"""AI 大模型调用日志路由：查询和清理 LLM 调用历史记录。

GET  /api/llm-logs        — 分页查询调用日志列表
GET  /api/llm-logs/{id}   — 获取单条日志详情
DELETE /api/llm-logs       — 清空全部日志
"""

import logging

from fastapi import APIRouter, HTTPException, Query

from application.db.mongo import get_database
from application.db.utils import to_object_id

router = APIRouter(prefix="/api/llm-logs", tags=["llm-logs"])
logger = logging.getLogger(__name__)


def _serialize_log(doc: dict) -> dict:
    doc["_id"] = str(doc["_id"])
    if "created_at" in doc and hasattr(doc["created_at"], "isoformat"):
        doc["created_at"] = doc["created_at"].isoformat()
    return doc


@router.get("")
async def list_llm_logs(
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=20, ge=1, le=100, description="每页条数"),
    provider: str = Query(default="", description="按 provider 筛选"),
    success: bool | None = Query(default=None, description="按成功/失败筛选"),
):
    """分页查询 LLM 调用日志列表，按时间倒序排列。"""
    db = get_database()
    coll = db["llm_call_logs"]

    query: dict = {}
    if provider:
        query["provider"] = provider
    if success is not None:
        query["success"] = success

    total = await coll.count_documents(query)
    skip = (page - 1) * page_size

    cursor = coll.find(query).sort("created_at", -1).skip(skip).limit(page_size)
    items = await cursor.to_list(length=page_size)

    return {
        "data": [_serialize_log(item) for item in items],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, (total + page_size - 1) // page_size) if total else 1,
    }


@router.get("/{log_id}")
async def get_llm_log(log_id: str):
    """获取单条 LLM 调用日志详情。"""
    db = get_database()
    coll = db["llm_call_logs"]

    try:
        obj_id = to_object_id(log_id)
    except Exception:
        raise HTTPException(status_code=400, detail="无效的日志 ID")

    doc = await coll.find_one({"_id": obj_id})
    if not doc:
        raise HTTPException(status_code=404, detail="日志不存在")

    return {"data": _serialize_log(doc)}


@router.delete("")
async def clear_llm_logs():
    """清空全部 LLM 调用日志。"""
    db = get_database()
    coll = db["llm_call_logs"]
    result = await coll.delete_many({})
    logger.info("清空 LLM 调用日志，共删除 %d 条记录", result.deleted_count)
    return {"message": f"已清空 {result.deleted_count} 条日志记录"}
