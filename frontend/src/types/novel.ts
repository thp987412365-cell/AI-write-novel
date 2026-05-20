export interface NovelSummary {
  _id: string;
  title: string;
  subtitle?: string;
  genre: string;
  tags: string[];
  cover_image?: string;
  status: string;
  stats: {
    chapter_count: number;
    total_word_count: number;
  };
  created_at: string;
  updated_at: string;
}

export interface NovelDetail extends NovelSummary {
  introduction?: string;
  summary?: string;
  core_seed?: string;
  worldview?: string;
  writing_style?: string;
  narrative_pov?: string;
  era_background?: string;
  plot?: string;
  tone?: string;
  target_audience?: string;
  core_idea?: string;
  number_of_chapters?: number;
  words_per_chapter?: number;
}

export interface CreateNovelRequest {
  title: string;
  subtitle?: string;
  genre?: string;
  tags?: string[];
  introduction?: string;
  summary?: string;
  core_seed?: string;
  worldview?: string;
  writing_style?: string;
  narrative_pov?: string;
  era_background?: string;
  cover_image?: string;
  plot?: string;
  tone?: string;
  target_audience?: string;
  core_idea?: string;
  number_of_chapters?: number;
  words_per_chapter?: number;
  characters?: GeneratedCharacter[];
  factions?: GeneratedFaction[];
  locations?: GeneratedLocation[];
  items?: GeneratedItem[];
  rules?: GeneratedRule[];
  relationships?: GeneratedRelation[];
}

export interface AICreateRequest {
  user_idea: string;
  number_of_chapters?: number;
  words_per_chapter?: number;
  // 可选生成参数
  temperature?: number | null;
  top_p?: number | null;
  max_tokens?: number | null;
  presence_penalty?: number | null;
  frequency_penalty?: number | null;
  system_prompt?: string | null;
}

export interface AICreateStepResult {
  step: string;
  data: Record<string, unknown>;
}

export interface AICreateResponse {
  expand_idea?: {
    plot: string;
  };
  extract_idea: {
    plot?: string;
    genre: string;
    tone: string;
    target_audience: string;
    core_idea: string;
  };
  core_seed: {
    core_seed: string;
  };
  novel_meta: {
    title: string;
    subtitle: string;
    introduction: string;
    summary: string;
    worldview: string;
    writing_style: string;
    narrative_pov: string;
    era_background: string;
    tags: string[];
  };
  characters?: GeneratedCharacter[];
  factions?: GeneratedFaction[];
  locations?: GeneratedLocation[];
  items?: GeneratedItem[];
  rules?: GeneratedRule[];
  relationships?: GeneratedRelation[];
}

export interface GeneratedCharacter {
  name: string;
  role: string;
  gender: string;
  age: string;
  appearance: string;
  personality: string;
  background: string;
  abilities: string[];
  goals: string;
  secrets: string;
}

export interface GeneratedFaction {
  name: string;
  faction_type: string;
  level_type: string;
  positioning: string;
  public_stance: string;
  core_goal: string;
  hidden_goal: string;
  resources_and_advantages: string[];
  organization_style: string;
  core_values: string[];
  conflict_with_mainline: string;
}

export interface GeneratedLocation {
  name: string;
  type: string;
  description: string;
  climate: string;
  culture: string;
  history: string;
  significance: string;
  notable_features: string[];
}

export interface GeneratedItem {
  name: string;
  type: string;
  rarity: string;
  description: string;
  abilities: string[];
  origin: string;
  limitations: string;
  significance: string;
}

export interface GeneratedRule {
  name: string;
  category: string;
  description: string;
  principles: string[];
  exceptions: string[];
  limitations: string;
  impact_on_plot: string;
}

export interface GeneratedRelation {
  source_name: string;
  target_name: string;
  relation_type: string;
  description: string;
}

/** AI 创建草稿，用于 sessionStorage 传递到 Writing 创建态 */
export interface WritingDraft extends CreateNovelRequest {
  _fromAI?: boolean;
}

/** Writing 侧栏导航项 */
export type WritingSidebarItem =
  | "novel-info"
  | "chapter-editor"
  | "plot-outline"
  | "knowledge-base"
  | "character-cards"
  | "location-cards"
  | "faction-cards"
  | "item-cards"
  | "rule-cards"
  | "relationship-map";

/** 章节 */
export interface Chapter {
  _id: string;
  novel_id: string;
  volume_id?: string;
  chapter_index: number;
  title: string;
  content: string;
  word_count: number;
  status: string;
  summary: string;
  key_events: string[];
  sort_order: number;
}

/** 角色 */
export interface Character {
  _id: string;
  novel_id: string;
  char_id: string;
  name: string;
  aliases: string[];
  role: string;
  gender: string;
  age: string;
  appearance: string;
  personality: string;
  background: string;
  abilities: string[];
  goals: string;
  secrets: string;
  relationships: CharacterRelation[];
  faction_id?: string;
  status: string;
  avatar_url: string;
  tags: string[];
  sort_order: number;
}

export interface CharacterRelation {
  target_id: string;
  relation_type: string;
  description: string;
}

export interface CharacterGraph {
  nodes: CharacterGraphNode[];
  edges: CharacterGraphEdge[];
}

export interface CharacterGraphNode {
  id: string;
  char_id: string;
  name: string;
  role: string;
  faction_id?: string;
  status: string;
}

export interface CharacterGraphEdge {
  source: string;
  target: string;
  relation_type: string;
  description: string;
}

/** 地点 */
export interface Location {
  _id: string;
  novel_id: string;
  name: string;
  type: string;
  parent_location_id?: string;
  description: string;
  climate: string;
  culture: string;
  history: string;
  significance: string;
  controlled_by_faction_ids: string[];
  notable_features: string[];
  tags: string[];
  sort_order: number;
}

/** 势力 */
export interface Faction {
  _id: string;
  novel_id: string;
  faction_id: string;
  name: string;
  alias: string[];
  faction_type: string;
  level_type: string;
  parent_faction_id?: string;
  positioning: string;
  public_stance: string;
  core_goal: string;
  hidden_goal: string;
  resources_and_advantages: string[];
  organization_style: string;
  core_values: string[];
  conflict_with_mainline: string;
  is_public: boolean;
  influence_scope: string;
  active_status: string;
  tags: string[];
  sort_order: number;
}

/** 物品 */
export interface Item {
  _id: string;
  novel_id: string;
  name: string;
  type: string;
  rarity: string;
  description: string;
  abilities: string[];
  origin: string;
  current_owner_character_id?: string;
  history: string;
  limitations: string;
  significance: string;
  tags: string[];
  sort_order: number;
}

/** 剧情大纲 */
export interface PlotOutline {
  _id: string;
  novel_id: string;
  arcs: StoryArc[];
  created_at?: string;
  updated_at?: string;
}

export interface StoryArc {
  title: string;
  summary: string;
  plot_points: PlotPoint[];
}

export interface PlotPoint {
  title: string;
  description: string;
  status: "pending" | "in_progress" | "completed";
  target_chapters: number;
  key_characters: string[];
  key_locations: string[];
  chapter_ids: string[];
  point_index?: number;
}

/** 规则 */
export interface Rule {
  _id: string;
  novel_id: string;
  name: string;
  category: string;
  description: string;
  principles: string[];
  exceptions: string[];
  limitations: string;
  related_factions: string[];
  related_characters: string[];
  impact_on_plot: string;
  sort_order: number;
}

/** 知识库文档（Markdown 手动录入） */
export interface KnowledgeDoc {
  _id: string;
  title: string;
  word_count: number;
  content_summary: string;
  content?: string;
  format: string;
  created_at: string;
  updated_at: string;
}

/** 小说关联的知识文档 */
export interface NovelKnowledgeLink {
  link_id: string;
  doc_id: string;
  title: string;
  word_count: number;
  linked_at: string;
}
