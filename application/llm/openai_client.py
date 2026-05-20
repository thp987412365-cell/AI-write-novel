"""OpenAI 兼容客户端实现，支持 OpenAI / DeepSeek / OpenRouter 等兼容平台。"""

from __future__ import annotations

import json
import re
import time
from typing import Any, AsyncGenerator

import httpx
import openai
from openai import AsyncOpenAI
from pydantic import BaseModel

from application.llm.base_client import BaseLLMClient
from application.llm.config import LLMProviderConfig
from application.llm.exceptions import (
    LLMAuthError,
    LLMError,
    LLMRateLimitError,
    LLMResponseError,
    LLMSchemaError,
    LLMTimeoutError,
)
from application.llm.logger import log_llm_error, log_llm_request, log_llm_response
from application.llm.models import LLMRequest, LLMResponse, TokenUsage


class OpenAICompatibleClient(BaseLLMClient):
    """基于 Chat Completions API 的 OpenAI 兼容客户端。

    兼容所有支持 /v1/chat/completions 端点的服务商，
    结构化输出通过 beta.chat.completions.parse() 实现。
    """

    def __init__(self, config: LLMProviderConfig, provider_name: str = "openai") -> None:
        super().__init__(config, provider_name)
        # 使用分层超时：连接 10s，读取 300s（适配小说生成等长时间任务）
        timeout = httpx.Timeout(
            connect=float(config.connect_timeout_seconds),
            read=float(config.read_timeout_seconds),
            write=float(config.read_timeout_seconds),
            pool=float(config.connect_timeout_seconds),
        )
        self._http_client = openai.DefaultAsyncHttpxClient(
            trust_env=config.use_system_proxy,
            timeout=timeout,
        )
        self._client = AsyncOpenAI(
            base_url=config.base_url,
            api_key=config.api_key,
            timeout=timeout,
            max_retries=config.max_retries,
            http_client=self._http_client,
        )

    def _build_params(self, request: LLMRequest) -> dict[str, Any]:
        """根据请求构建 Chat Completions API 调用参数。"""
        params: dict[str, Any] = {
            "model": self._resolve_model(request),
            "messages": self._build_messages(request),
        }
        if request.temperature is not None:
            params["temperature"] = request.temperature
        if request.top_p is not None:
            params["top_p"] = request.top_p
        if request.max_tokens is not None:
            params["max_tokens"] = request.max_tokens
        if request.presence_penalty is not None:
            params["presence_penalty"] = request.presence_penalty
        if request.frequency_penalty is not None:
            params["frequency_penalty"] = request.frequency_penalty
        if request.stop is not None:
            params["stop"] = request.stop
        return params

    def _map_error(self, exc: Exception, model: str = "") -> LLMError:
        """将 OpenAI SDK 异常映射为自定义异常。"""
        kwargs = {"provider": self.provider_name, "model": model}
        if isinstance(exc, openai.AuthenticationError):
            return LLMAuthError(str(exc), **kwargs)
        if isinstance(exc, openai.RateLimitError):
            return LLMRateLimitError(str(exc), **kwargs)
        if isinstance(exc, openai.APITimeoutError):
            return LLMTimeoutError(str(exc), **kwargs)
        if isinstance(exc, openai.APIError):
            return LLMResponseError(str(exc), **kwargs)
        return LLMError(str(exc), **kwargs)

    @staticmethod
    def _should_fallback_prompted_schema(exc: Exception) -> bool:
        """判断当前异常是否适合降级为提示词约束的 JSON 输出。"""
        message = str(exc).lower()
        return "response_format" in message and (
            "unavailable" in message or "unsupported" in message or "invalid" in message
        )

    @staticmethod
    def _extract_json_candidate(text: str) -> str:
        """从模型文本响应中提取最可能的 JSON 片段。"""
        stripped = text.strip()

        fence_match = re.search(r"```(?:json)?\s*(.*?)\s*```", stripped, flags=re.DOTALL | re.IGNORECASE)
        if fence_match:
            return fence_match.group(1).strip()

        decoder = json.JSONDecoder()
        for idx, char in enumerate(stripped):
            if char not in "[{":
                continue
            try:
                _, end = decoder.raw_decode(stripped[idx:])
                return stripped[idx:idx + end]
            except json.JSONDecodeError:
                continue
        return stripped

    @staticmethod
    def _build_prompted_schema_instruction(request: LLMRequest, schema: type[BaseModel]) -> str:
        """将原始对话包装为严格 JSON 输出提示词。"""
        schema_json = json.dumps(schema.model_json_schema(), ensure_ascii=False, indent=2)
        message_lines: list[str] = []
        if request.system_prompt:
            message_lines.append(f"[system]\n{request.system_prompt}")
        for msg in request.messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            message_lines.append(f"[{role}]\n{content}")
        conversation = "\n\n".join(message_lines)
        return (
            "请基于以下对话内容完成任务，并严格输出合法 JSON。\n"
            "不要输出解释、不要输出 Markdown、不要使用代码块，只输出 JSON 本体。\n\n"
            f"目标 JSON Schema:\n{schema_json}\n\n"
            f"原始对话:\n{conversation}"
        )

    async def _schema_generate_via_prompt(
        self,
        request: LLMRequest,
        schema: type[BaseModel],
        *,
        model: str,
        start: float,
    ) -> LLMResponse:
        """当原生 response_format 不可用时，降级为提示词约束的 JSON 输出。"""
        fallback_request = request.model_copy(
            update={
                "messages": [
                    {
                        "role": "user",
                        "content": self._build_prompted_schema_instruction(request, schema),
                    }
                ],
                "system_prompt": "",
            }
        )
        resp = await self._client.chat.completions.create(**self._build_params(fallback_request))
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        choice = resp.choices[0] if resp.choices else None
        raw_content = (choice.message.content or "") if choice else ""
        json_text = self._extract_json_candidate(raw_content)

        try:
            parsed_obj = schema.model_validate_json(json_text)
        except Exception as exc:
            error = LLMSchemaError(
                f"结构化输出降级后仍未返回有效 JSON: {exc}",
                provider=self.provider_name,
                model=model,
            )
            log_llm_error(error, provider=self.provider_name, model=model)
            raise error from exc

        result = LLMResponse(
            content=parsed_obj.model_dump_json(),
            raw_response=resp.model_dump(warnings=False) if hasattr(resp, "model_dump") else None,
            usage=self._extract_usage(resp.usage),
            model=resp.model or model,
            provider=self.provider_name,
            duration_ms=elapsed_ms,
            finish_reason=(choice.finish_reason or "") if choice else "",
            success=True,
        )
        result = self._finalize_response(result)
        log_llm_response(result)
        return result

    @staticmethod
    def _extract_usage(usage: Any) -> TokenUsage:
        """从响应中提取 Token 用量。"""
        if usage is None:
            return TokenUsage()
        return TokenUsage(
            input_tokens=getattr(usage, "prompt_tokens", 0) or 0,
            output_tokens=getattr(usage, "completion_tokens", 0) or 0,
            total_tokens=getattr(usage, "total_tokens", 0) or 0,
        )

    async def text_generate(self, request: LLMRequest) -> LLMResponse:
        """调用 Chat Completions API 进行普通文本生成。"""
        request = self._apply_defaults(request)
        model = self._resolve_model(request)
        log_llm_request(request, self.provider_name)
        start = time.perf_counter()

        try:
            resp = await self._client.chat.completions.create(**self._build_params(request))
        except Exception as exc:
            mapped = self._map_error(exc, model)
            log_llm_error(mapped, provider=self.provider_name, model=model)
            raise mapped from exc

        elapsed_ms = int((time.perf_counter() - start) * 1000)
        choice = resp.choices[0] if resp.choices else None
        result = LLMResponse(
            content=(choice.message.content or "") if choice else "",
            raw_response=resp.model_dump(warnings=False) if hasattr(resp, "model_dump") else None,
            usage=self._extract_usage(resp.usage),
            model=resp.model or model,
            provider=self.provider_name,
            duration_ms=elapsed_ms,
            finish_reason=(choice.finish_reason or "") if choice else "",
            success=True,
        )
        result = self._finalize_response(result)
        log_llm_response(result)
        return result

    async def schema_generate(self, request: LLMRequest, schema: type[BaseModel]) -> LLMResponse:
        """通过 beta.chat.completions.parse() 进行结构化 JSON 输出。

        将 Pydantic Schema 作为 response_format 传入，SDK 自动处理
        JSON Schema 注入与响应解析，返回的 content 为序列化后的 JSON 字符串。
        """
        request = self._apply_defaults(request)
        model = self._resolve_model(request)
        log_llm_request(request, self.provider_name)
        start = time.perf_counter()

        try:
            params = self._build_params(request)
            resp = await self._client.beta.chat.completions.parse(
                **params,
                response_format=schema,
            )
        except Exception as exc:
            if self._should_fallback_prompted_schema(exc):
                return await self._schema_generate_via_prompt(request, schema, model=model, start=start)
            mapped = self._map_error(exc, model)
            log_llm_error(mapped, provider=self.provider_name, model=model)
            raise mapped from exc

        elapsed_ms = int((time.perf_counter() - start) * 1000)
        choice = resp.choices[0] if resp.choices else None

        # 提取解析后的结构化对象
        parsed_obj = choice.message.parsed if choice else None
        if parsed_obj is None:
            refusal = getattr(choice.message, "refusal", None) if choice else None
            err_msg = refusal or "模型未返回有效的结构化输出"
            error = LLMSchemaError(err_msg, provider=self.provider_name, model=model)
            log_llm_error(error, provider=self.provider_name, model=model)
            raise error

        result = LLMResponse(
            content=parsed_obj.model_dump_json(),
            raw_response=resp.model_dump(warnings=False) if hasattr(resp, "model_dump") else None,
            usage=self._extract_usage(resp.usage),
            model=resp.model or model,
            provider=self.provider_name,
            duration_ms=elapsed_ms,
            finish_reason=(choice.finish_reason or "") if choice else "",
            success=True,
        )
        result = self._finalize_response(result)
        log_llm_response(result)
        return result

    async def stream_text(self, request: LLMRequest) -> AsyncGenerator[str, None]:
        """流式调用 Chat Completions API，逐块 yield 生成文本。"""
        request = self._apply_defaults(request)
        model = self._resolve_model(request)
        log_llm_request(request, self.provider_name)

        try:
            params = self._build_params(request)
            params["stream"] = True
            stream = await self._client.chat.completions.create(**params)

            async def raw_chunks() -> AsyncGenerator[str, None]:
                async for chunk in stream:
                    if chunk.choices and chunk.choices[0].delta.content:
                        yield chunk.choices[0].delta.content

            async for clean_chunk in self._sanitize_stream_chunks(raw_chunks()):
                yield clean_chunk
        except Exception as exc:
            mapped = self._map_error(exc, model)
            log_llm_error(mapped, provider=self.provider_name, model=model)
            raise mapped from exc
