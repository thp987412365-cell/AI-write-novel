"""实体生成服务：角色、势力、地点、物品、规则、角色关系 (Step 5-10)。"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any

import yaml

from application.llm.config import get_provider_config
from application.services.llm.workflow_service import get_llm_service_for_step, resolve_provider_for_step
from application.services.llm.format_review_service import validate_and_fix_format
from pydantic_definitions.entity_generation_pydantic import (
    CharacterGenerationResult,
    FactionGenerationResult,
    LocationGenerationResult,
    ItemGenerationResult,
    RuleGenerationResult,
    RelationGenerationResult,
)

PROMPT_PATH = Path(__file__).resolve().parents[3] / "prompt_definitions" / "prompt_default.yaml"
WORKFLOW_NAME = "generate_entities"
logger = logging.getLogger(__name__)


def _load_prompts() -> dict:
    with PROMPT_PATH.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _check_json_schema_support(step_name: str) -> bool:
    provider = resolve_provider_for_step(WORKFLOW_NAME, step_name)
    if not provider:
        return False
    return get_provider_config(provider).supports_json_schema


async def generate_characters(
    plot: str,
    genre: str,
    tone: str,
    worldview: str,
    core_seed: str,
    gen_kwargs: dict | None = None,
) -> list[dict]:
    gen_kwargs = gen_kwargs or {}
    prompts = _load_prompts().get("generate_entities", {})
    step_name = "character_generation"

    provider = resolve_provider_for_step(WORKFLOW_NAME, step_name) or ""
    use_schema = _check_json_schema_support(step_name)
    logger.info("[generate_entities] characters running provider=%s json_schema=%s", provider, use_schema)

    svc = get_llm_service_for_step(WORKFLOW_NAME, step_name)
    suffix = "characters_prompt_with_schema_suffix" if use_schema else "characters_prompt_without_schema_suffix"
    prompt = (
        prompts["characters_prompt_base"].format(
            plot=plot,
            genre=genre,
            tone=tone,
            worldview=worldview,
            core_seed=core_seed,
        )
        + "\n"
        + prompts[suffix]
    )

    if use_schema:
        result: CharacterGenerationResult = await svc.generate_structured(prompt, CharacterGenerationResult, **gen_kwargs)
    else:
        raw = await svc.generate_text(prompt, **gen_kwargs)
        result = await validate_and_fix_format(raw, CharacterGenerationResult, "characters")

    return [c.model_dump() for c in result.characters]


async def generate_factions(
    plot: str,
    genre: str,
    tone: str,
    worldview: str,
    core_seed: str,
    character_names: str,
    gen_kwargs: dict | None = None,
) -> list[dict]:
    gen_kwargs = gen_kwargs or {}
    prompts = _load_prompts().get("generate_entities", {})
    step_name = "faction_generation"

    provider = resolve_provider_for_step(WORKFLOW_NAME, step_name) or ""
    use_schema = _check_json_schema_support(step_name)
    logger.info("[generate_entities] factions running provider=%s json_schema=%s", provider, use_schema)

    svc = get_llm_service_for_step(WORKFLOW_NAME, step_name)
    suffix = "factions_prompt_with_schema_suffix" if use_schema else "factions_prompt_without_schema_suffix"
    prompt = (
        prompts["factions_prompt_base"].format(
            plot=plot,
            genre=genre,
            tone=tone,
            worldview=worldview,
            core_seed=core_seed,
            character_names=character_names,
        )
        + "\n"
        + prompts[suffix]
    )

    if use_schema:
        result: FactionGenerationResult = await svc.generate_structured(prompt, FactionGenerationResult, **gen_kwargs)
    else:
        raw = await svc.generate_text(prompt, **gen_kwargs)
        result = await validate_and_fix_format(raw, FactionGenerationResult, "factions")

    return [f.model_dump() for f in result.factions]


async def generate_locations(
    plot: str,
    genre: str,
    tone: str,
    worldview: str,
    gen_kwargs: dict | None = None,
) -> list[dict]:
    gen_kwargs = gen_kwargs or {}
    prompts = _load_prompts().get("generate_entities", {})
    step_name = "location_generation"

    provider = resolve_provider_for_step(WORKFLOW_NAME, step_name) or ""
    use_schema = _check_json_schema_support(step_name)
    logger.info("[generate_entities] locations running provider=%s json_schema=%s", provider, use_schema)

    svc = get_llm_service_for_step(WORKFLOW_NAME, step_name)
    suffix = "locations_prompt_with_schema_suffix" if use_schema else "locations_prompt_without_schema_suffix"
    prompt = (
        prompts["locations_prompt_base"].format(
            plot=plot,
            genre=genre,
            tone=tone,
            worldview=worldview,
        )
        + "\n"
        + prompts[suffix]
    )

    if use_schema:
        result: LocationGenerationResult = await svc.generate_structured(prompt, LocationGenerationResult, **gen_kwargs)
    else:
        raw = await svc.generate_text(prompt, **gen_kwargs)
        result = await validate_and_fix_format(raw, LocationGenerationResult, "locations")

    return [loc.model_dump() for loc in result.locations]


async def generate_items(
    plot: str,
    genre: str,
    worldview: str,
    character_names: str,
    gen_kwargs: dict | None = None,
) -> list[dict]:
    gen_kwargs = gen_kwargs or {}
    prompts = _load_prompts().get("generate_entities", {})
    step_name = "item_generation"

    provider = resolve_provider_for_step(WORKFLOW_NAME, step_name) or ""
    use_schema = _check_json_schema_support(step_name)
    logger.info("[generate_entities] items running provider=%s json_schema=%s", provider, use_schema)

    svc = get_llm_service_for_step(WORKFLOW_NAME, step_name)
    suffix = "items_prompt_with_schema_suffix" if use_schema else "items_prompt_without_schema_suffix"
    prompt = (
        prompts["items_prompt_base"].format(
            plot=plot,
            genre=genre,
            worldview=worldview,
            character_names=character_names,
        )
        + "\n"
        + prompts[suffix]
    )

    if use_schema:
        result: ItemGenerationResult = await svc.generate_structured(prompt, ItemGenerationResult, **gen_kwargs)
    else:
        raw = await svc.generate_text(prompt, **gen_kwargs)
        result = await validate_and_fix_format(raw, ItemGenerationResult, "items")

    return [it.model_dump() for it in result.items]


async def generate_rules(
    plot: str,
    genre: str,
    tone: str,
    worldview: str,
    core_seed: str,
    gen_kwargs: dict | None = None,
) -> list[dict]:
    gen_kwargs = gen_kwargs or {}
    prompts = _load_prompts().get("generate_entities", {})
    step_name = "rule_generation"

    provider = resolve_provider_for_step(WORKFLOW_NAME, step_name) or ""
    use_schema = _check_json_schema_support(step_name)
    logger.info("[generate_entities] rules running provider=%s json_schema=%s", provider, use_schema)

    svc = get_llm_service_for_step(WORKFLOW_NAME, step_name)
    suffix = "rules_prompt_with_schema_suffix" if use_schema else "rules_prompt_without_schema_suffix"
    prompt = (
        prompts["rules_prompt_base"].format(
            plot=plot,
            genre=genre,
            tone=tone,
            worldview=worldview,
            core_seed=core_seed,
        )
        + "\n"
        + prompts[suffix]
    )

    if use_schema:
        result: RuleGenerationResult = await svc.generate_structured(prompt, RuleGenerationResult, **gen_kwargs)
    else:
        raw = await svc.generate_text(prompt, **gen_kwargs)
        result = await validate_and_fix_format(raw, RuleGenerationResult, "rules")

    return [r.model_dump() for r in result.rules]


async def generate_relationships(
    plot: str,
    core_seed: str,
    character_names: str,
    gen_kwargs: dict | None = None,
) -> list[dict]:
    gen_kwargs = gen_kwargs or {}
    prompts = _load_prompts().get("generate_entities", {})
    step_name = "relationship_generation"

    provider = resolve_provider_for_step(WORKFLOW_NAME, step_name) or ""
    use_schema = _check_json_schema_support(step_name)
    logger.info("[generate_entities] relationships running provider=%s json_schema=%s", provider, use_schema)

    svc = get_llm_service_for_step(WORKFLOW_NAME, step_name)
    suffix = "relationships_prompt_with_schema_suffix" if use_schema else "relationships_prompt_without_schema_suffix"
    prompt = (
        prompts["relationships_prompt_base"].format(
            plot=plot,
            core_seed=core_seed,
            character_names=character_names,
        )
        + "\n"
        + prompts[suffix]
    )

    if use_schema:
        result: RelationGenerationResult = await svc.generate_structured(prompt, RelationGenerationResult, **gen_kwargs)
    else:
        raw = await svc.generate_text(prompt, **gen_kwargs)
        result = await validate_and_fix_format(raw, RelationGenerationResult, "relationships")

    return [r.model_dump() for r in result.relationships]
