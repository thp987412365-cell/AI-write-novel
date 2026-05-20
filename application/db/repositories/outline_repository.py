"""剧情大纲仓储：管理 plot_outlines 集合的 CRUD 操作。"""

from typing import Any

from application.db.base import BaseRepository
from application.db.utils import to_object_id
from application.db.errors import NotFoundError


class OutlineRepository(BaseRepository):
    def __init__(self):
        super().__init__("plot_outlines")

    async def get_outline_by_novel(self, novel_id: str) -> dict | None:
        """获取小说的剧情大纲。"""
        obj_id = to_object_id(novel_id)
        return await self.find_one({"novel_id": obj_id})

    async def upsert_outline(self, novel_id: str, data: dict) -> str:
        """创建或覆盖剧情大纲（一个小说只有一份大纲）。

        Args:
            novel_id: 小说 ID。
            data: 包含 arcs 等字段的字典。

        Returns:
            str: 大纲文档的 _id。
        """
        obj_id = to_object_id(novel_id)
        data["novel_id"] = obj_id

        existing = await self.find_one({"novel_id": obj_id})
        if existing:
            existing_doc_id = existing["_id"]
            update_data = {k: v for k, v in data.items() if k != "novel_id"}
            await self.update_one({"_id": existing_doc_id}, update_data)
            return str(existing_doc_id)
        else:
            return await self.insert_one(data)

    async def update_plot_point_status(
        self,
        novel_id: str,
        arc_index: int,
        point_index: int,
        status: str,
        chapter_id: str | None = None,
    ) -> bool:
        """更新某个剧情节点的状态。

        Args:
            novel_id: 小说 ID。
            arc_index: 剧情弧序号（0-based）。
            point_index: 节点序号（0-based）。
            status: 新状态 (pending / in_progress / completed)。
            chapter_id: 关联的章节 ID（可选，追加到 chapter_ids）。

        Returns:
            bool: 是否更新成功。
        """
        obj_id = to_object_id(novel_id)
        set_fields: dict[str, Any] = {
            f"arcs.{arc_index}.plot_points.{point_index}.status": status,
        }
        if chapter_id:
            # 追加 chapter_id 到数组
            await self.collection.update_one(
                {"novel_id": obj_id},
                {"$addToSet": {f"arcs.{arc_index}.plot_points.{point_index}.chapter_ids": chapter_id}},
            )

        result = await self.collection.update_one(
            {"novel_id": obj_id},
            {"$set": set_fields},
        )
        return result.modified_count > 0

    async def get_current_plot_point(self, novel_id: str) -> dict | None:
        """获取当前正在进行中的剧情节点。

        优先返回 status=in_progress 的节点，否则返回第一个 status=pending 的节点。

        Returns:
            dict | None: { arc_index, point_index, arc_title, point_title, description,
                           target_chapters, chapter_count, key_characters, key_locations }
            如果大纲不存在则返回 None。
        """
        outline = await self.get_outline_by_novel(novel_id)
        if not outline or not outline.get("arcs"):
            return None

        arcs = outline["arcs"]
        # 优先找 in_progress
        for ai, arc in enumerate(arcs):
            for pi, point in enumerate(arc.get("plot_points", [])):
                if point.get("status") == "in_progress":
                    return {
                        "arc_index": ai,
                        "point_index": pi,
                        "arc_title": arc.get("title", ""),
                        "point_title": point.get("title", ""),
                        "description": point.get("description", ""),
                        "target_chapters": point.get("target_chapters", 1),
                        "chapter_count": len(point.get("chapter_ids", [])),
                        "key_characters": point.get("key_characters", []),
                        "key_locations": point.get("key_locations", []),
                    }

        # 否则找第一个 pending
        for ai, arc in enumerate(arcs):
            for pi, point in enumerate(arc.get("plot_points", [])):
                if point.get("status") == "pending":
                    # 自动标记为 in_progress
                    await self.update_plot_point_status(novel_id, ai, pi, "in_progress")
                    return {
                        "arc_index": ai,
                        "point_index": pi,
                        "arc_title": arc.get("title", ""),
                        "point_title": point.get("title", ""),
                        "description": point.get("description", ""),
                        "target_chapters": point.get("target_chapters", 1),
                        "chapter_count": 0,
                        "key_characters": point.get("key_characters", []),
                        "key_locations": point.get("key_locations", []),
                    }

        return None  # 所有节点都已完成

    async def advance_plot_point(
        self,
        novel_id: str,
        arc_index: int,
        point_index: int,
        chapter_id: str,
    ) -> bool:
        """章节生成完成后，推进剧情节点状态。

        将 chapter_id 追加到当前节点，如果章节数已满则标记 completed 并激活下一个。

        Returns:
            bool: 是否成功推进。
        """
        outline = await self.get_outline_by_novel(novel_id)
        if not outline:
            return False

        # 追加 chapter_id
        obj_id = to_object_id(novel_id)
        await self.collection.update_one(
            {"novel_id": obj_id},
            {"$addToSet": {f"arcs.{arc_index}.plot_points.{point_index}.chapter_ids": chapter_id}},
        )

        # 检查章节数是否已满
        point = outline["arcs"][arc_index]["plot_points"][point_index]
        current_count = len(point.get("chapter_ids", [])) + 1  # +1 for the one we just added
        target = point.get("target_chapters", 1)

        if current_count >= target:
            # 标记当前节点为 completed
            await self.update_plot_point_status(novel_id, arc_index, point_index, "completed")
            # 激活下一个节点
            await self._activate_next_point(novel_id, arc_index, point_index)

        return True

    async def _activate_next_point(self, novel_id: str, arc_index: int, point_index: int) -> None:
        """激活指定节点之后的下一个节点。"""
        outline = await self.get_outline_by_novel(novel_id)
        if not outline:
            return

        arcs = outline["arcs"]
        # 同一弧内的下一个节点
        points = arcs[arc_index].get("plot_points", [])
        if point_index + 1 < len(points):
            await self.update_plot_point_status(novel_id, arc_index, point_index + 1, "in_progress")
            return

        # 下一个弧的第一个节点
        if arc_index + 1 < len(arcs):
            next_points = arcs[arc_index + 1].get("plot_points", [])
            if next_points:
                await self.update_plot_point_status(novel_id, arc_index + 1, 0, "in_progress")


outline_repo = OutlineRepository()
