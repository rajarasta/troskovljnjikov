// ── File & Item Models ──────────────────────────────────────────────

export interface BoQFile {
  id: string;
  file_name: string;
  file_type: string;
  project_name: string | null;
  item_count: number;
  sheet_count: number;
  raw_preview: Record<string, string[][]> | null;
  header_rows: Record<string, number> | null;
  indexed_at: string;
}

export interface BoQItem {
  id: string;
  file_id: string;
  sheet_name: string | null;
  row: number;
  item_number: string | null;
  description: string;
  full_description: string | null;
  parent_item_number: string | null;
  unit: string | null;
  quantity: number;
  unit_price: number;
  total: number;
  project_name: string | null;
  date: string | null;
  material_price: number | null;
  labor_price: number | null;
  material_total: number | null;
  labor_total: number | null;
  notes: string | null;
  drawing_path: string | null;
  llm_response: string | null;
  file_name: string | null;
}

// ── Match Models ────────────────────────────────────────────────────

export interface QuantityComparison {
  hasData: boolean;
  ratio?: number;
  percentDiff?: number;
  label: string;
  color: string;
}

export interface MatchResult {
  item: BoQItem;
  similarity: number;
  quantity_comparison: QuantityComparison | null;
}

export interface MatchStats {
  count: number;
  avgPrice: number;
  minPrice: number;
  maxPrice: number;
  priceRange: number;
  statusCounts: Record<string, number>;
}

export interface MatchGroup {
  sub_item: BoQItem;
  matches: MatchResult[];
  stats: MatchStats;
}

export interface MatchResponse {
  matches: MatchResult[];
  stats: MatchStats;
  groups?: MatchGroup[] | null;
  is_composite?: boolean;
  parent_description?: string | null;
}

// ── Pipeline & Agent Models ─────────────────────────────────────────

export type PipelineStage =
  | "upload"
  | "parse"
  | "index"
  | "match"
  | "suggest"
  | "review";

export interface AgentEvent {
  type: string;
  agent_id?: string;
  agent_type?: string;
  target_item_id?: string;
  payload: Record<string, unknown>;
  timestamp: string;
}

// ── Chat Models ─────────────────────────────────────────────────────

export interface ChatMessage {
  id: string;
  item_id: string;
  role: "user" | "assistant" | "system";
  content: string;
  created_at: string;
  image_url?: string;
}

// ── Selection Models ────────────────────────────────────────────────

export interface SelectionMatchRequest {
  descriptions: string[];
  quantities: number[];
  threshold?: number;
  max_results?: number;
}

export interface SelectionAnalysisRequest {
  item_descriptions: string[];
  match_context: MatchResult[];
}

// ── Autopilot Models ──────────────────────────────────────────────

export type ConfidenceTier = "high" | "medium" | "low";

export type AutopilotStatus = "idle" | "summarizing" | "matching" | "pricing" | "done" | "error";

export interface PriceSuggestion {
  suggested_price: number;
  confidence: number;
  based_on: number;
}

export interface AutopilotMatchResult {
  id: string;
  similarity: number;
  metadata: Record<string, unknown>;
}

// ── Preset Models ──────────────────────────────────────────────────

export interface Preset {
  id: string;
  name: string;
  description: string;
  groups: string[];
  is_default: boolean;
}
