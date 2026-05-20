"""剧情大纲 RESTful CRUD 路由。

提供大纲的查询、节点更新等接口。
"""

from fastapi import APIRouter
from pydantic import BaseModel, Field

from application.db.repositories.outline_repository import outline_repo
from application.db.repositories.novel_repository import novel_repo

router = APIRouter(prefix="/api/outlines", tags=["outlines"])


class UpdatePlotPointRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=40)
    description: str | None = Field(default=None, min_length=1, max_length=500)
    target_chapters: int | None = Field(default=None, ge=1, le=20)
    key_characters: list[str] | None = None
    key_locations: list[str] | None = None


def _serialize(obj: dict) -> dict:
    """将 ObjectId 转为字符串（递归处理嵌套结构）。"""
    from bson import ObjectId

    def _convert(val):
        if isinstance(val, ObjectId):
            return str(val)
        if isinstance(val, dict):
            return {k: _convert(v) for k, v in val.items()}
        if isinstance(val, list):
            return [_convert(v) for v in val]
        return val

    return _convert(obj)


@router.get("/novel/{novel_id}")
async def get_outline(novel_id: str):
    """获取小说的剧情大纲。"""
    await novel_repo.get_novel_by_id(novel_id)  # 校验存在
    outline = await outline_repo.get_outline_by_novel(novel_id)
    if not outline:
        return {"data": None}
    return {"data": _serialize(outline)}


@router.put("/novel/{novel_id}/point")
async def update_plot_point(
    novel_id: str,
    arc_index: int,
    point_index: int,
    body: UpdatePlotPointRequest,
):
    """更新某个剧情节点的内容。"""
    await novel_repo.get_novel_by_id(novel_id)

    outline = await outline_repo.get_outline_by_novel(novel_id)
    if not outline:
        return {"error": "大纲不存在，请先生成剧情大纲"}

    arcs = outline.get("arcs", [])
    if arc_index < 0 or arc_index >= len(arcs):
        return {"error": f"arc_index {arc_index} 越界"}

    points = arcs[arc_index].get("plot_points", [])
    if point_index < 0 or point_index >= len(points):
        return {"error": f"point_index {point_index} 越界"}

    # 只更新非 None 的字段
    update_fields = {}
    for field in ("title", "description", "target_chapters", "key_characters", "key_locations"):
        val = getattr(body, field, None)
        if val is not None:
            update_fields[field] = val

    if not update_fields:
        return {"error": "没有需要更新的字段"}

    # 构建 update 文档
    update_doc = {}
    for field_name, field_value in update_fields.items():
        update_doc[f"arcs.{arc_index}.plot_points.{point_index}.{field_name}"] = field_value

    from application.db.utils import to_object_id
    obj_id = to_object_id(novel_id)
    from application.db import mongo
    db = mongo.get_database()
    collection = db["plot_outlines"]

    result = await collection.update_one(
        {"novel_id": obj_id},
        {"$set": update_doc},
    )

    if result.modified_count > 0:
        return {"success": True, "message": "更新成功"}
    return {"success": True, "message": "没有变化"}


@router.get("/novel/{novel_id}/current-point")
async def get_current_plot_point(novel_id: str):
    """获取当前正在进行中的剧情节点（供章节生成使用）。"""
    await novel_repo.get_novel_by_id(novel_id)
    point = await outline_repo.get_current_plot_point(novel_id)
    return {"data": point}
