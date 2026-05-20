"""格式审校服务：当 LLM 原始响应无法通过 Schema 校验时，调用 Provider 进行修正。"""

from __future__ import annotations

import json
import logging
import re
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from application.llm.config import get_llm_config, get_provider_config
from application.services.llm.llm_service import LLMService

logger = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)

_MD_JSON_RE = re.compile(
    r"```(?:json)?\s*\n(.*?)\n\s*```",
    re.DOTALL,
)

_CANDIDATE_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)


def _repair_json_text(text: str) -> list[str]:
    """尝试修复常见的 LLM JSON 输出格式问题，返回多个候选修复文本。

    常见的 LLM JSON 问题：
    1. 尾部逗号（{...,} 或 [...,]）
    2. 括号不匹配导致截断/多余
    3. 值中包含未转义的换行符

    各策略独立运行，返回所有有效候选（去重）。
    """
    if not text or not text.strip():
        return []
    stripped = text.strip()
    candidates: list[str] = []

    # 策略 A：简单去除尾部逗号
    no_trailing = re.sub(r",\s*([}\]])", r"\1", stripped)
    if no_trailing != stripped:
        candidates.append(no_trailing)

    # 策略 B：基于括号深度匹配提取完整 JSON 对象
    def _balanced_extract(s: str) -> str | None:
        start = s.find("{")
        if start < 0:
            return None
        depth = 0
        in_string = False
        escape_next = False
        for i, ch in enumerate(s[start:], start):
            if escape_next:
                escape_next = False
                continue
            if ch == "\\":
                escape_next = True
                continue
            if ch == '"' and not escape_next:
                in_string = not in_string
                continue
            if in_string:
                continue
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return s[start : i + 1]
        return None

    balanced = _balanced_extract(stripped)
    if balanced and balanced != stripped:
        candidates.append(balanced)

    # 策略 C：去尾部逗号 + 平衡提取
    balanced_no_trail = _balanced_extract(no_trailing)
    if balanced_no_trail and balanced_no_trail != stripped and balanced_no_trail != no_trailing:
        candidates.append(balanced_no_trail)

    # 策略 D：修复值中未转义的换行符（常见于 content 字段）
    # 将 JSON 字符串值内部的真实换行替换为 \n
    try:
        # 简单启发式：在引号之间的换行替换为 \\n
        in_string = False
        escape_next = False
        chars: list[str] = []
        for ch in stripped:
            if escape_next:
                chars.append(ch)
                escape_next = False
                continue
            if ch == "\\":
                chars.append(ch)
                escape_next = True
                continue
            if ch == '"':
                in_string = not in_string
                chars.append(ch)
                continue
            if in_string and ch == "\n":
                chars.append("\\n")
                continue
            if in_string and ch == "\r":
                chars.append("\\r")
                continue
            if in_string and ch == "\t":
                chars.append("\\t")
                continue
            chars.append(ch)
        unescaped = "".join(chars)
        if unescaped != stripped:
            candidates.append(unescaped)
    except Exception:
        pass

    return candidates


def _extract_json_text(raw: str) -> str:
    """从 LLM 原始响应中提取纯 JSON 文本。

    优先级：
    1. 完整匹配 markdown 代码块 ```json ... ```
    2. 查找代码块中的 JSON ``` ... ```
    3. 查找文本中首个完整 JSON 对象 { ... }
    4. 返回原始文本（最后兜底）
    """
    if not raw:
        return ""
    stripped = raw.strip()

    m = _MD_JSON_RE.match(stripped)
    if m:
        return m.group(1).strip()
    m = _MD_JSON_RE.search(stripped)
    if m:
        return m.group(1).strip()

    m = _CANDIDATE_JSON_RE.search(stripped)
    if m:
        candidate = m.group(0).strip()
        if candidate != stripped:
            return candidate

    return stripped


def _resolve_format_review_provider() -> tuple[str, bool]:
    """解析格式审校 Provider，返回 (provider_name, supports_json_schema)。

    优先使用配置的 format_review_provider，否则自动查找已启用的 Provider。
    若找不到支持 json_schema 的 Provider，会回退到任意已启用的 Provider（使用文本生成兜底）。
    """
    llm_cfg = get_llm_config()

    configured = llm_cfg.format_review_provider
    if configured:
        if configured in llm_cfg.providers:
            prov = llm_cfg.providers[configured]
            if prov.enabled:
                return configured, prov.supports_json_schema
        logger.warning(
            "配置的 format_review_provider '%s' 不可用（不存在 / 未启用），尝试自动查找",
            configured,
        )

    for name, cfg in llm_cfg.providers.items():
        if cfg.enabled and cfg.supports_json_schema:
            return name, True

    for name, cfg in llm_cfg.providers.items():
        if cfg.enabled:
            logger.warning("无可用的支持 json_schema 的 Provider，回退到 '%s'（使用文本生成方式）", name)
            return name, False

    raise ValueError("没有任何已启用的 Provider，无法进行格式审校")


def _try_parse_json(raw_text: str, schema: type[T], step_label: str = "") -> T | None:
    """尝试多种方式解析 LLM 原始响应，返回 schema 实例或 None。

    依次尝试：原始文本 → 提取 JSON → 修复 JSON（去尾逗号/平衡括号/转义换行）→ 格式审校。
    """
    candidates: list[str] = []
    stripped = raw_text.strip()
    if stripped:
        candidates.append(stripped)
    extracted = _extract_json_text(raw_text)
    if extracted and extracted != stripped:
        candidates.append(extracted)

    # 对每个候选文本，额外生成修复版本
    for base in list(candidates):
        repaired = _repair_json_text(base)
        for r in repaired:
            if r not in candidates:
                candidates.append(r)

    for text in candidates:
        try:
            return schema.model_validate_json(text)
        except (ValidationError, ValueError):
            pass
        try:
            obj = json.loads(text)
            return schema.model_validate(obj)
        except (json.JSONDecodeError, ValidationError, ValueError):
            pass

    return None


async def validate_and_fix_format(
    raw_text: str,
    schema: type[T],
    step_label: str = "",
) -> T:
    """尝试将原始文本解析为目标 schema；失败时自动调用 Provider 修正。

    Parameters
    ----------
    raw_text : str
        LLM 返回的原始文本。
    schema : type[T]
        目标 Pydantic Schema 类型。
    step_label : str
        步骤标识，用于日志。

    Returns
    -------
    T
        解析或审校后的 Schema 实例。
    """
    result = _try_parse_json(raw_text, schema, step_label)
    if result is not None:
        return result

    logger.warning(
        "%s 响应格式校验失败（尝试了原始文本和去除 markdown 包裹），尝试格式审校: %s",
        step_label or "unknown",
        raw_text[:200],
    )

    reviewer_provider, has_schema_support = _resolve_format_review_provider()
    logger.info(
        "%s 启用格式审校 provider=%s schema=%s json_schema=%s",
        step_label or "unknown",
        reviewer_provider,
        schema.__name__,
        has_schema_support,
    )
    reviewer = LLMService(provider_name=reviewer_provider)
    schema_json = json.dumps(schema.model_json_schema(), ensure_ascii=False, indent=2)
    review_prompt = (
        "以下是另一个 AI 的原始输出，但格式不符合要求。\n"
        "请从中提取有效信息，严格按以下 JSON Schema 输出合法 JSON，不要输出任何额外内容。\n\n"
        f"目标 JSON Schema:\n{schema_json}\n\n"
        f"原始输出:\n{raw_text}"
    )
    if has_schema_support:
        return await reviewer.generate_structured(review_prompt, schema)

    raw = await reviewer.generate_text(review_prompt)
    result = _try_parse_json(raw, schema, step_label)
    if result is not None:
        return result

    raise ValueError(
        f"{step_label or 'unknown'} 格式审校后仍无法解析为 {schema.__name__}，"
        f"响应内容: {raw[:500]}"
    )
