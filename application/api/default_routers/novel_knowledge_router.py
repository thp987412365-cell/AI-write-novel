"""小说知识关联路由：管理小说与知识文档的关联。

GET    /api/novels/{novel_id}/knowledge          — 获取已关联的知识文档
POST   /api/novels/{novel_id}/knowledge/link     — 关联知识文档到小说
DELETE /api/novels/{novel_id}/knowledge/{doc_id} — 取消关联
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from application.db.repositories.knowledge_repository import (
    knowledge_doc_repo,
    novel_knowledge_link_repo,
)
from application.db.repositories.novel_repository import novel_repo

router = APIRouter(prefix="/api/novels", tags=["novel-knowledge"])


class LinkDocsRequest(BaseModel):
    doc_ids: list[str] = Field(..., min_length=1, max_length=50, description="要关联的知识文档 ID 列表")


@router.get("/{novel_id}/knowledge")
async def get_novel_knowledge(novel_id: str):
    """获取小说已关联的知识文档列表。"""
    await novel_repo.get_novel_by_id(novel_id)  # 校验存在
    docs = await novel_knowledge_link_repo.get_linked_docs(novel_id)
    return {"data": docs}


@router.post("/{novel_id}/knowledge/link")
async def link_knowledge_to_novel(novel_id: str, body: LinkDocsRequest):
    """将知识文档关联到小说。

    只能从全局知识库中勾选已存在的文档。
    """
    await novel_repo.get_novel_by_id(novel_id)

    # 验证所有 doc_id 存在
    for doc_id in body.doc_ids:
        doc = await knowledge_doc_repo.get_doc_by_id(doc_id)
        if not doc:
            raise HTTPException(status_code=404, detail=f"知识文档 {doc_id} 不存在")

    count = await novel_knowledge_link_repo.link_docs(novel_id, body.doc_ids)
    return {"success": True, "linked_count": count, "message": f"成功关联 {count} 个文档"}


@router.delete("/{novel_id}/knowledge/{doc_id}")
async def unlink_knowledge_from_novel(novel_id: str, doc_id: str):
    """取消小说与知识文档的关联。"""
    await novel_repo.get_novel_by_id(novel_id)
    doc = await knowledge_doc_repo.get_doc_by_id(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="知识文档不存在")

    success = await novel_knowledge_link_repo.unlink_doc(novel_id, doc_id)
    if not success:
        raise HTTPException(status_code=404, detail="关联不存在")

    return {"success": True, "message": "取消关联成功"}
