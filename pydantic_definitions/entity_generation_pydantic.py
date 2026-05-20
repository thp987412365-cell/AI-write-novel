from pydantic import BaseModel, Field, ConfigDict


class GeneratedCharacter(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1, max_length=30)
    role: str = Field(default="supporting")
    gender: str = Field(default="", max_length=10)
    age: str = Field(default="", max_length=30)
    appearance: str = Field(default="", max_length=200)
    personality: str = Field(default="", max_length=300)
    background: str = Field(default="", max_length=500)
    abilities: list[str] = Field(default_factory=list)
    goals: str = Field(default="", max_length=300)
    secrets: str = Field(default="", max_length=300)


class CharacterGenerationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    characters: list[GeneratedCharacter] = Field(..., min_length=1, max_length=8)


class GeneratedFaction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1, max_length=30)
    faction_type: str = Field(default="organization")
    level_type: str = Field(default="major")
    positioning: str = Field(default="", max_length=200)
    public_stance: str = Field(default="", max_length=100)
    core_goal: str = Field(default="", max_length=200)
    hidden_goal: str = Field(default="", max_length=200)
    resources_and_advantages: list[str] = Field(default_factory=list)
    organization_style: str = Field(default="", max_length=100)
    core_values: list[str] = Field(default_factory=list)
    conflict_with_mainline: str = Field(default="", max_length=200)


class FactionGenerationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    factions: list[GeneratedFaction] = Field(..., min_length=1, max_length=5)


class GeneratedLocation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1, max_length=30)
    type: str = Field(default="city")
    description: str = Field(default="", max_length=300)
    climate: str = Field(default="", max_length=100)
    culture: str = Field(default="", max_length=200)
    history: str = Field(default="", max_length=300)
    significance: str = Field(default="", max_length=200)
    notable_features: list[str] = Field(default_factory=list)


class LocationGenerationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    locations: list[GeneratedLocation] = Field(..., min_length=1, max_length=5)


class GeneratedItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1, max_length=30)
    type: str = Field(default="artifact")
    rarity: str = Field(default="common")
    description: str = Field(default="", max_length=200)
    abilities: list[str] = Field(default_factory=list)
    origin: str = Field(default="", max_length=200)
    limitations: str = Field(default="", max_length=150)
    significance: str = Field(default="", max_length=200)


class ItemGenerationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[GeneratedItem] = Field(..., min_length=1, max_length=5)


class GeneratedRule(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1, max_length=30)
    category: str = Field(default="custom")
    description: str = Field(default="", max_length=300)
    principles: list[str] = Field(default_factory=list)
    exceptions: list[str] = Field(default_factory=list)
    limitations: str = Field(default="", max_length=150)
    impact_on_plot: str = Field(default="", max_length=200)


class RuleGenerationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rules: list[GeneratedRule] = Field(..., min_length=1, max_length=5)


class GeneratedRelation(BaseModel):
    source_name: str = Field(..., min_length=1, max_length=30)
    target_name: str = Field(..., min_length=1, max_length=30)
    relation_type: str = Field(default="关联")
    description: str = Field(default="", max_length=100)


class RelationGenerationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    relationships: list[GeneratedRelation] = Field(..., min_length=1, max_length=20)
