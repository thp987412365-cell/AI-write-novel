"""AI 剧情大纲生成路由：SSE 流式生成剧情大纲。

POST /api/llm/generate-plot-outline
请求: { novel_id }
响应: text/event-stream
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import AsyncGenerator
from uuid import uuid4

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from application.services.novel.plot_outline_service import generate_plot_outline
from application.db.repositories.outline_repository import outline_repo
from application.db.repositories.novel_repository import novel_repo
from application.db.repositories.knowledge_repository import novel_knowledge_link_repo

router = APIRouter(prefix="/api/llm", tags=["llm"])
logger = logging.getLogger(__name__)


def _sse_event(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


class GeneratePlotOutlineRequest(BaseModel):
    novel_id: str = Field(..., min_length=1, description="小说 ID")
    use_knowledge: bool = Field(default=False, description="是否结合知识库内容进行大纲规划")
    temperature: float | None = Field(default=None, ge=0, le=2)
    top_p: float | None = Field(default=None, ge=0, le=1)
    max_tokens: int | None = Field(default=None, gt=0)


def _build_gen_kwargs(req: GeneratePlotOutlineRequest) -> dict:
    kwargs: dict = {}
    for key in ("temperature", "top_p", "max_tokens"):
        val = getattr(req, key)
        if val is not None:
            kwargs[key] = val
    return kwargs


@router.post("/generate-plot-outline")
async def generate_plot_outline_endpoint(req: GeneratePlotOutlineRequest):
    """AI 生成剧情大纲（SSE 流式）。"""

    async def event_stream() -> AsyncGenerator[str, None]:
        request_id = uuid4().hex[:8]
        gen_kwargs = _build_gen_kwargs(req)

        logger.info(
            "[generate_plot_outline] request_id=%s novel_id=%s started",
            request_id, req.novel_id,
        )

        # 验证小说存在
        try:
            await novel_repo.get_novel_by_id(req.novel_id)
        except Exception as e:
            yield _sse_event("step", {"step": "outline", "status": "error", "error": f"小说不存在: {e}"})
            yield _sse_event("done", {"success": False})
            return

        # 推送 running
        yield _sse_event("step", {"step": "outline", "status": "running"})
        step_start = time.perf_counter()

        # 获取知识库上下文（如果需要）
        knowledge_docs = []
        if req.use_knowledge:
            try:
                knowledge_docs = await novel_knowledge_link_repo.get_linked_doc_contents(req.novel_id)
                if knowledge_docs:
                    logger.info(
                        "[generate_plot_outline] request_id=%s knowledge_docs=%d",
                        request_id, len(knowledge_docs),
                    )
            except Exception as e:
                logger.warning("获取知识库文档失败: %s", e)

        try:
            outline_data = await generate_plot_outline(req.novel_id, gen_kwargs, knowledge_docs)

            # 保存到数据库
            await outline_repo.upsert_outline(req.novel_id, outline_data)

            elapsed_ms = int((time.perf_counter() - step_start) * 1000)

            total_points = sum(len(arc.get("plot_points", [])) for arc in outline_data["arcs"])
            logger.info(
                "[generate_plot_outline] request_id=%s done arcs=%d points=%d elapsed_ms=%d",
                request_id, len(outline_data["arcs"]), total_points, elapsed_ms,
            )

            yield _sse_event("step", {
                "step": "outline",
                "status": "done",
                "data": outline_data,
                "arcs_count": len(outline_data["arcs"]),
                "points_count": total_points,
                "elapsed_ms": elapsed_ms,
            })
        except Exception as e:
            logger.exception("[generate_plot_outline] request_id=%s failed", request_id)
            yield _sse_event("step", {"step": "outline", "status": "error", "error": str(e)})
            yield _sse_event("done", {"success": False})
            return

        yield _sse_event("done", {
            "success": True,
            "result": outline_data,
        })

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
