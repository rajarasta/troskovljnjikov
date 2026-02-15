// ── File & Item Models ──────────────────────────────────────────────

export interface BoQFile {
  id: string;
  file_name: string;
  file_type: string;
  project_name: string | null;
  item_count: number;
  sheet_count: number;
  raw_preview: Record<string, string[][]> | null;
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

export interface MatchResponse {
  matches: MatchResult[];
  stats: MatchStats;
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
}
