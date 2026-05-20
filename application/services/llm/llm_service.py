"""LLM 高层服务封装，提供简洁的文本/结构化/流式生成接口。"""

from __future__ import annotations

import asyncio
import json
import logging
import random
from typing import Any, AsyncGenerator

from pydantic import BaseModel

from application.llm.exceptions import LLMTimeoutError, LLMRateLimitError
from application.llm.factory import create_llm_client
from application.llm.models import LLMRequest, LLMResponse
from application.db.mongo import get_database
from application.db.utils import get_utc_now

logger = logging.getLogger(__name__)


async def _retry_with_backoff(
    coro_factory,
    *,
    max_retries: int = 3,
    base_delay: float = 2.0,
    max_delay: float = 60.0,
) -> Any:
    """带指数退避的重试执行器，仅对超时和限流错误重试。

    每次重试前等待 base_delay * 2^attempt + jitter 秒，
    最大等待不超过 max_delay 秒。
    """
    last_exc: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            return await coro_factory()
        except (LLMTimeoutError, LLMRateLimitError) as exc:
            last_exc = exc
            if attempt >= max_retries:
                break
            delay = min(base_delay * (2 ** attempt) + random.uniform(0, 1), max_delay)
            logger.warning(
                "LLM 调用失败 (%s)，第 %d/%d 次重试，%.1f 秒后重试...",
                type(exc).__name__, attempt + 1, max_retries, delay,
            )
            await asyncio.sleep(delay)
    raise last_exc  # type: ignore[misc]


async def _persist_llm_call(request: LLMRequest, response: LLMResponse) -> None:
    """将 LLM 调用记录持久化到数据库。"""
    try:
        db = get_database()
        doc = {
            "provider": response.provider or "",
            "model": response.model or "",
            "system_prompt": request.system_prompt,
            "messages": [
                {"role": m["role"], "content": m["content"]}
                for m in request.messages
            ],
            "temperature": request.temperature,
            "top_p": request.top_p,
            "max_tokens": request.max_tokens,
            "response_content": response.content,
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
            "total_tokens": response.usage.total_tokens,
            "duration_ms": response.duration_ms,
            "finish_reason": response.finish_reason,
            "success": response.success,
            "error": response.error,
            "metadata": request.metadata,
            "created_at": get_utc_now(),
        }
        await db["llm_call_logs"].insert_one(doc)
    except Exception:
        logger.exception(
            "持久化 LLM 调用日志失败 provider=%s model=%s success=%s error=%s",
            response.provider, response.model, response.success, response.error,
        )


class LLMService:
    """面向业务层的 LLM 能力封装。

    将底层客户端的请求构造、日志记录等细节隐藏，
    对外暴露 generate_text / generate_structured / stream_text 三个简洁方法。
    """

    def __init__(self, provider_name: str | None = None) -> None:
        self._client = create_llm_client(provider_name)

    def _make_request(
        self,
        prompt: str,
        system_prompt: str = "",
        **kwargs: Any,
    ) -> LLMRequest:
        """将简单参数组装为 LLMRequest。"""
        messages = [{"role": "user", "content": prompt}]
        return LLMRequest(
            messages=messages,
            system_prompt=system_prompt,
            **kwargs,
        )

    async def generate_text(
        self,
        prompt: str,
        system_prompt: str = "",
        **kwargs: Any,
    ) -> str:
        """普通文本生成，返回纯文本内容。超时/限流时自动指数退避重试。"""
        request = self._make_request(prompt, system_prompt, **kwargs)
        try:
            response: LLMResponse = await _retry_with_backoff(
                lambda: self._client.text_generate(request),
                max_retries=self._client.config.max_retries,
            )
        except Exception as exc:
            error_response = LLMResponse(
                provider=self._client.provider_name,
                success=False,
                error=str(exc),
            )
            await _persist_llm_call(request, error_response)
            raise
        await _persist_llm_call(request, response)
        return response.content

    async def generate_structured(
        self,
        prompt: str,
        schema: type[BaseModel],
        system_prompt: str = "",
        **kwargs: Any,
    ) -> BaseModel:
        """结构化生成，返回解析后的 Pydantic 模型实例。超时/限流时自动指数退避重试。"""
        request = self._make_request(prompt, system_prompt, **kwargs)
        try:
            response: LLMResponse = await _retry_with_backoff(
                lambda: self._client.schema_generate(request, schema),
                max_retries=self._client.config.max_retries,
            )
        except Exception as exc:
            error_response = LLMResponse(
                provider=self._client.provider_name,
                success=False,
                error=str(exc),
            )
            await _persist_llm_call(request, error_response)
            raise
        await _persist_llm_call(request, response)
        return schema.model_validate(json.loads(response.content))

    async def stream_text(
        self,
        prompt: str,
        system_prompt: str = "",
        **kwargs: Any,
    ) -> AsyncGenerator[str, None]:
        """流式文本生成，逐块 yield 文本片段。"""
        request = self._make_request(prompt, system_prompt, **kwargs)
        async for chunk in self._client.stream_text(request):
            yield chunk
