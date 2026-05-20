"""章节 AI 续写相关的 Pydantic Schema 定义。

用于 generate_chapters 工作流中 LLM 结构化输出的校验。
"""

from pydantic import BaseModel, Field, ConfigDict


class NewCharacterInfo(BaseModel):
    """章节正文中新出现的角色信息。"""
    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1, max_length=30, description="角色姓名")
    role: str = Field(default="supporting", description="角色定位: protagonist / antagonist / supporting")
    gender: str = Field(default="", max_length=10)
    age: str = Field(default="", max_length=30)
    appearance: str = Field(default="", max_length=200, description="外貌特征")
    personality: str = Field(default="", max_length=300, description="性格描述")
    background: str = Field(default="", max_length=500, description="背景故事")
    abilities: list[str] = Field(default_factory=list, description="能力列表")
    goals: str = Field(default="", max_length=300, description="目标与动机")
    secrets: str = Field(default="", max_length=300, description="不为人知的秘密")


class NewLocationInfo(BaseModel):
    """章节正文中新出现的地点信息。"""
    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1, max_length=30, description="地点名称")
    type: str = Field(default="city", description="地点类型")
    description: str = Field(default="", max_length=300, description="地点描述")
    climate: str = Field(default="", max_length=100)
    culture: str = Field(default="", max_length=200)
    history: str = Field(default="", max_length=300)
    significance: str = Field(default="", max_length=200)
    notable_features: list[str] = Field(default_factory=list)


class NewFactionInfo(BaseModel):
    """章节正文中新出现的势力信息。"""
    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1, max_length=30, description="势力名称")
    faction_type: str = Field(default="organization", description="势力类型")
    level_type: str = Field(default="minor", description="势力级别: core / major / minor")
    positioning: str = Field(default="", max_length=200)
    public_stance: str = Field(default="", max_length=100)
    core_goal: str = Field(default="", max_length=200)
    hidden_goal: str = Field(default="", max_length=200)
    resources_and_advantages: list[str] = Field(default_factory=list)
    organization_style: str = Field(default="", max_length=100)
    core_values: list[str] = Field(default_factory=list)
    conflict_with_mainline: str = Field(default="", max_length=200)


class NewItemInfo(BaseModel):
    """章节正文中新出现的物品信息。"""
    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1, max_length=30, description="物品名称")
    type: str = Field(default="artifact")
    rarity: str = Field(default="common")
    description: str = Field(default="", max_length=200)
    abilities: list[str] = Field(default_factory=list)
    origin: str = Field(default="", max_length=200)
    limitations: str = Field(default="", max_length=150)
    significance: str = Field(default="", max_length=200)


class NewRuleInfo(BaseModel):
    """章节正文中新出现的规则信息。"""
    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1, max_length=30, description="规则名称")
    category: str = Field(default="custom")
    description: str = Field(default="", max_length=300)
    principles: list[str] = Field(default_factory=list)
    exceptions: list[str] = Field(default_factory=list)
    limitations: str = Field(default="", max_length=150)
    impact_on_plot: str = Field(default="", max_length=200)


class NewRelationInfo(BaseModel):
    """章节正文中新出现的角色关系。"""
    model_config = ConfigDict(extra="forbid")

    source_name: str = Field(..., min_length=1, max_length=30, description="关系源角色名（必须是已有或本章新增的角色）")
    target_name: str = Field(..., min_length=1, max_length=30, description="关系目标角色名")
    relation_type: str = Field(default="关联", description="关系类型: 敌对/盟友/亲属/师徒/情感/朋友/从属")
    description: str = Field(default="", max_length=100)


class NewEntities(BaseModel):
    """章节正文中出现的所有新实体汇总。"""
    model_config = ConfigDict(extra="forbid")

    characters: list[NewCharacterInfo] = Field(default_factory=list)
    locations: list[NewLocationInfo] = Field(default_factory=list)
    factions: list[NewFactionInfo] = Field(default_factory=list)
    items: list[NewItemInfo] = Field(default_factory=list)
    rules: list[NewRuleInfo] = Field(default_factory=list)
    relationships: list[NewRelationInfo] = Field(default_factory=list)


class ChapterWriteResult(BaseModel):
    """单章 AI 续写的结构化输出。"""
    model_config = ConfigDict(extra="forbid")

    title: str = Field(..., min_length=1, max_length=80, description="章节标题")
    content: str = Field(..., min_length=100, description="章节正文，目标 5000-8000 字")
    summary: str = Field(..., min_length=10, max_length=500, description="章节摘要，100-200字")
    key_events: list[str] = Field(default_factory=list, description="本章关键事件列表，3-5条")
    appeared_characters: list[str] = Field(
        default_factory=list,
        description="本章出场的已有角色名称列表（必须是设定中已存在的角色名）"
    )
    appeared_locations: list[str] = Field(
        default_factory=list,
        description="本章出现的地点名称列表"
    )
    new_entities: NewEntities = Field(
        default_factory=NewEntities,
        description="本章中新出现的实体（角色/地点/势力/物品/规则/关系），仅填写设定中不存在的"
    )
