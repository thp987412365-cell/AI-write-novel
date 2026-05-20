"""剧情大纲相关的 Pydantic Schema 定义。

用于 generate_plot_outline 工作流中 LLM 结构化输出的校验。
"""

from pydantic import BaseModel, Field, ConfigDict


class PlotPointSchema(BaseModel):
    """单个剧情节点。"""
    model_config = ConfigDict(extra="forbid")

    title: str = Field(..., min_length=1, max_length=40, description="节点标题，如「意外觉醒」")
    description: str = Field(..., min_length=30, max_length=500, description="该节点的详细剧情描述")
    target_chapters: int = Field(..., ge=1, le=20, description="预计需要的章节数（3-5章）")
    key_characters: list[str] = Field(
        default_factory=list,
        description="涉及的角色名称列表（必须是已有角色）"
    )
    key_locations: list[str] = Field(
        default_factory=list,
        description="涉及的地点名称列表（必须是已有地点）"
    )


class StoryArcSchema(BaseModel):
    """一个剧情弧（大篇章）。"""
    model_config = ConfigDict(extra="forbid")

    title: str = Field(..., min_length=1, max_length=40, description="篇章标题，如「第一卷·觉醒之路」")
    summary: str = Field(..., min_length=20, max_length=300, description="该篇章的概要描述")
    plot_points: list[PlotPointSchema] = Field(..., min_length=2, max_length=20, description="该篇章下的剧情节点列表")


class PlotOutlineResult(BaseModel):
    """AI 生成的剧情大纲结果。"""
    model_config = ConfigDict(extra="forbid")

    arcs: list[StoryArcSchema] = Field(..., min_length=1, max_length=10, description="剧情弧列表")
