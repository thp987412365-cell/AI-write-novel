"""知识库 RESTful CRUD 路由：手动创建、编辑、查看、删除 Markdown 文档。

POST   /api/knowledge/docs        — 新建文档（title + markdown content）
GET    /api/knowledge/docs        — 获取文档列表
GET    /api/knowledge/docs/{id}   — 获取文档详情（含正文）
PUT    /api/knowledge/docs/{id}   — 更新文档（标题 + 内容）
DELETE /api/knowledge/docs/{id}   — 删除文档
"""

import logging
import re

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from application.db.repositories.knowledge_repository import knowledge_doc_repo

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])
logger = logging.getLogger(__name__)


def _strip_markdown(text: str) -> str:
    """去除 Markdown 标记，提取纯文本用于字数统计和摘要。"""
    # 移除代码块
    text = re.sub(r"```[\s\S]*?```", "", text)
    # 移除行内代码
    text = re.sub(r"`[^`]*`", "", text)
    # 移除标题标记
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    # 移除粗体/斜体
    text = re.sub(r"\*{1,3}([^*]+)\*{1,3}", r"\1", text)
    # 移除链接 [text](url)
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    # 移除图片 ![alt](url)
    text = re.sub(r"!\[([^\]]*)\]\([^)]*\)", r"\1", text)
    # 移除列表标记
    text = re.sub(r"^[\s]*[-*+]\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^[\s]*\d+\.\s+", "", text, flags=re.MULTILINE)
    # 移除引用标记
    text = re.sub(r"^>\s+", "", text, flags=re.MULTILINE)
    # 移除水平线
    text = re.sub(r"^[-*_]{3,}\s*$", "", text, flags=re.MULTILINE)
    return text


def _count_words(text: str) -> int:
    """统计文本字数（去除空白和 Markdown 标记后）。"""
    plain = _strip_markdown(text)
    return len(plain.replace("\n", "").replace(" ", ""))


def _make_summary(text: str, max_chars: int = 500) -> str:
    """生成文本摘要（去除 Markdown 后截取前 N 个字符）。"""
    plain = _strip_markdown(text)
    if len(plain) <= max_chars:
        return plain
    return plain[:max_chars] + "……"


def _serialize_doc(doc: dict) -> dict:
    """将文档字典中的 ObjectId 转为字符串。"""
    if doc is None:
        return None
    from bson import ObjectId

    def _convert(val):
        if isinstance(val, ObjectId):
            return str(val)
        if isinstance(val, dict):
            return {k: _convert(v) for k, v in val.items()}
        if isinstance(val, list):
            return [_convert(v) for v in val]
        return val

    return _convert(doc)


class CreateDocRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=100, description="文档标题")
    content: str = Field(..., min_length=1, description="Markdown 格式的文档内容")


class UpdateDocRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=100, description="文档标题")
    content: str | None = Field(default=None, min_length=1, description="Markdown 格式的文档内容")


@router.post("/docs")
async def create_knowledge_doc(body: CreateDocRequest):
    """创建知识文档（Markdown 手动录入）。

    标题和内容均由用户手动输入，内容格式为 Markdown。
    """
    # 检查同名文档是否已存在
    existing = await knowledge_doc_repo.find_one({"title": body.title})
    if existing:
        raise HTTPException(status_code=409, detail=f"文档「{body.title}」已存在")

    word_count = _count_words(body.content)
    doc_data = {
        "title": body.title,
        "content": body.content,
        "content_summary": _make_summary(body.content, 500),
        "word_count": word_count,
        "format": "markdown",
    }

    doc_id = await knowledge_doc_repo.create_doc(doc_data)
    logger.info(
        "[knowledge] created doc_id=%s title=%s words=%d",
        doc_id, body.title, word_count,
    )

    return {
        "doc_id": doc_id,
        "title": body.title,
        "word_count": word_count,
        "summary": _make_summary(body.content, 200),
    }


@router.get("/docs")
async def list_knowledge_docs(
    keyword: str | None = Query(default=None, description="按标题搜索"),
):
    """获取全局知识库文档列表（不含正文）。"""
    docs = await knowledge_doc_repo.get_all_docs(keyword=keyword)
    return {"data": [_serialize_doc(d) for d in docs]}


@router.get("/docs/{doc_id}")
async def get_knowledge_doc(doc_id: str):
    """获取单个知识文档的详情（含 Markdown 正文）。"""
    doc = await knowledge_doc_repo.get_doc_by_id(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")
    return {"data": _serialize_doc(doc)}


@router.put("/docs/{doc_id}")
async def update_knowledge_doc(doc_id: str, body: UpdateDocRequest):
    """更新知识文档的标题和/或内容。"""
    doc = await knowledge_doc_repo.get_doc_by_id(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")

    update_data = {}
    if body.title is not None:
        update_data["title"] = body.title
    if body.content is not None:
        update_data["content"] = body.content
        update_data["content_summary"] = _make_summary(body.content, 500)
        update_data["word_count"] = _count_words(body.content)

    if not update_data:
        raise HTTPException(status_code=400, detail="没有需要更新的字段")

    updated = await knowledge_doc_repo.update_doc(doc_id, update_data)
    return {"success": updated}


@router.delete("/docs/{doc_id}")
async def delete_knowledge_doc(doc_id: str):
    """删除知识文档（软删除）。"""
    doc = await knowledge_doc_repo.get_doc_by_id(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")

    await knowledge_doc_repo.delete_doc(doc_id)
    return {"success": True, "message": "删除成功"}
