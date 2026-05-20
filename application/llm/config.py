"""LLM 服务商配置模型与配置读取工具。"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from application.config import get_config_value

# 支持的客户端类别
LLMProviderType = Literal["openai", "gemini", "claude"]


class LLMProviderConfig(BaseModel):
    """单个 LLM 服务商的接入配置。

    type 字段决定使用哪种客户端类别（openai / gemini / claude），
    配置的 key 作为用户自定义别名，同一 type 可定义多个不同别名的配置。

    超时配置拆分为连接超时和读取超时：
    - connect_timeout_seconds: 建立 TCP/TLS 连接的超时（默认 10 秒）
    - read_timeout_seconds: 等待模型生成响应的超时（默认 300 秒）
    """

    type: LLMProviderType = Field(default="openai", description="客户端类别: openai / gemini / claude")
    base_url: str = Field(default="", description="服务商 API 基地址")
    api_key: str = Field(default="", description="API Key")
    default_model: str = Field(default="", description="默认模型名称")
    enabled: bool = Field(default=False, description="是否启用")
    connect_timeout_seconds: int = Field(default=10, description="连接超时（秒）")
    read_timeout_seconds: int = Field(default=300, description="读取/生成超时（秒）")
    max_retries: int = Field(default=2, description="最大重试次数")
    max_concurrency: int = Field(default=5, description="最大并发数")
    use_system_proxy: bool = Field(default=False, description="是否允许 SDK 读取系统代理配置")
    supports_streaming: bool = Field(default=True, description="是否支持流式输出")
    supports_json_schema: bool = Field(default=False, description="是否支持 JSON Schema 输出")
    supports_function_calling: bool = Field(default=False, description="是否支持 function calling")

    # 生成参数默认值（请求未指定时使用，请求级别优先）
    temperature: float | None = Field(default=None, ge=0, le=2, description="默认采样温度")
    top_p: float | None = Field(default=None, ge=0, le=1, description="默认核采样概率")
    max_tokens: int | None = Field(default=None, gt=0, description="默认最大生成 token 数")
    system_prompt: str | None = Field(default=None, description="默认系统提示词")
    presence_penalty: float | None = Field(default=None, ge=-2, le=2, description="默认存在惩罚")
    frequency_penalty: float | None = Field(default=None, ge=-2, le=2, description="默认频率惩罚")

    @model_validator(mode="before")
    @classmethod
    def _migrate_timeout_fields(cls, data: Any) -> Any:
        """兼容旧版 timeout_seconds 字段：将其迁移到 connect_timeout_seconds 和 read_timeout_seconds。"""
        if isinstance(data, dict) and "timeout_seconds" in data:
            old = data.pop("timeout_seconds")
            if "connect_timeout_seconds" not in data:
                data["connect_timeout_seconds"] = min(old, 10)
            if "read_timeout_seconds" not in data:
                # 若旧值 ≤120 秒，升级到新的默认 300 秒（小说生成等场景需要更长超时）
                data["read_timeout_seconds"] = old if old > 120 else 300
        return data


class LLMConfig(BaseModel):
    """LLM 总体配置，包含默认服务商与所有服务商列表。"""

    default_provider: str = Field(default="openai_gpt4o_mini", description="默认服务商别名")
    format_review_provider: str = Field(default="", description="格式审校服务商别名，需支持 json_schema")
    providers: dict[str, LLMProviderConfig] = Field(default_factory=dict, description="服务商配置映射（key 为别名）")


def get_llm_config() -> LLMConfig:
    """从应用配置中读取并解析 LLM 配置段。"""
    raw = get_config_value("llm", {})
    return LLMConfig.model_validate(raw)


def get_provider_config(provider_name: str | None = None) -> LLMProviderConfig:
    """获取指定别名的服务商配置，未指定时返回默认服务商。"""
    llm_cfg = get_llm_config()
    name = provider_name or llm_cfg.default_provider
    if name not in llm_cfg.providers:
        raise ValueError(f"未找到 LLM 服务商配置: {name}")
    return llm_cfg.providers[name]
