"""知识库仓储：管理 knowledge_docs 和 novel_knowledge_links 集合。

文档以 Markdown 格式手动录入，不再基于文件上传。
"""

from typing import Any

from application.db.base import BaseRepository
from application.db.utils import to_object_id


class KnowledgeDocRepository(BaseRepository):
    """知识文档仓储（全局知识库）。"""

    def __init__(self):
        super().__init__("knowledge_docs")

    async def get_all_docs(
        self,
        keyword: str | None = None,
        sort_by: str = "updated_at",
    ) -> list[dict]:
        """获取所有知识文档列表（不含正文内容，仅元信息+摘要）。

        Args:
            keyword: 按标题模糊搜索。
            sort_by: 排序字段。

        Returns:
            list[dict]: 文档元信息列表。
        """
        query: dict[str, Any] = {}
        if keyword:
            query["title"] = {"$regex": keyword, "$options": "i"}

        projection = {"content": 0}  # 不返回正文
        cursor = self.collection.find(query, projection)
        direction = -1 if sort_by == "updated_at" else 1
        cursor = cursor.sort(sort_by, direction)
        docs = await cursor.to_list(length=None)
        return docs

    async def get_doc_by_id(self, doc_id: str) -> dict | None:
        """获取单个文档的完整内容。"""
        from bson import ObjectId
        return await self.find_one({"_id": ObjectId(doc_id)})

    async def create_doc(self, data: dict) -> str:
        """创建知识文档记录。

        Args:
            data: 包含 title, content 等字段。content 为 Markdown 格式文本。

        Returns:
            str: 新文档的 _id。
        """
        return await self.insert_one(data)

    async def update_doc(self, doc_id: str, data: dict) -> bool:
        """更新文档（标题、内容等）。"""
        from bson import ObjectId
        return await self.update_one({"_id": ObjectId(doc_id)}, data)

    async def delete_doc(self, doc_id: str) -> bool:
        """软删除知识文档。"""
        from bson import ObjectId
        return await self.soft_delete_one({"_id": ObjectId(doc_id)})


class NovelKnowledgeLinkRepository(BaseRepository):
    """小说-知识文档关联仓储。"""

    def __init__(self):
        super().__init__("novel_knowledge_links")

    async def get_linked_docs(self, novel_id: str) -> list[dict]:
        """获取小说已关联的知识文档列表（含文档元信息）。

        Returns:
            list[dict]: 每个元素包含 doc_id, title, word_count, linked_at。
        """
        obj_id = to_object_id(novel_id)
        links = await self.find_many({"novel_id": obj_id}, sort=[("created_at", -1)])

        if not links:
            return []

        from bson import ObjectId
        doc_ids = [ObjectId(link["doc_id"]) for link in links]
        docs_cursor = get_database()["knowledge_docs"].find(
            {"_id": {"$in": doc_ids}, "is_deleted": False},
            {"content": 0},
        )
        docs = await docs_cursor.to_list(length=None)
        doc_map = {str(d["_id"]): d for d in docs}

        result = []
        for link in links:
            doc = doc_map.get(link.get("doc_id", ""))
            if doc:
                result.append({
                    "link_id": str(link["_id"]),
                    "doc_id": str(doc["_id"]),
                    "title": doc.get("title", ""),
                    "word_count": doc.get("word_count", 0),
                    "linked_at": str(link.get("created_at", "")),
                })
        return result

    async def link_docs(self, novel_id: str, doc_ids: list[str]) -> int:
        """将知识文档关联到小说（已存在的跳过）。

        Returns:
            int: 实际新增的关联数。
        """
        obj_id = to_object_id(novel_id)
        count = 0
        for doc_id in doc_ids:
            existing = await self.find_one({"novel_id": obj_id, "doc_id": doc_id})
            if existing:
                continue
            await self.insert_one({"novel_id": obj_id, "doc_id": doc_id})
            count += 1
        return count

    async def unlink_doc(self, novel_id: str, doc_id: str) -> bool:
        """取消小说与知识文档的关联。"""
        obj_id = to_object_id(novel_id)
        return await self.hard_delete_one({"novel_id": obj_id, "doc_id": doc_id})

    async def get_linked_doc_contents(self, novel_id: str) -> list[dict]:
        """获取小说关联的知识文档完整内容（供 AI 上下文使用）。

        Returns:
            list[dict]: 每个元素包含 title, content。
        """
        obj_id = to_object_id(novel_id)
        links = await self.find_many({"novel_id": obj_id})

        if not links:
            return []

        from bson import ObjectId
        doc_ids = [ObjectId(link["doc_id"]) for link in links]
        docs_cursor = get_database()["knowledge_docs"].find(
            {"_id": {"$in": doc_ids}, "is_deleted": False},
            {"title": 1, "content": 1, "content_summary": 1},
        )
        docs = await docs_cursor.to_list(length=None)
        return [
            {
                "title": d.get("title", ""),
                "content": d.get("content", ""),
            }
            for d in docs
        ]


def get_database():
    """惰性导入，避免循环依赖。"""
    from application.db.mongo import get_database as _get_db
    return _get_db()


knowledge_doc_repo = KnowledgeDocRepository()
novel_knowledge_link_repo = NovelKnowledgeLinkRepository()
