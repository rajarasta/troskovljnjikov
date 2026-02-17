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
  item_type?: string | null;
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
  llm_confidence: number | null;
  llm_reasoning: string | null;
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

// ── Web Price Search Models ────────────────────────────────────────

export type SearchStatus = "idle" | "searching" | "done" | "error";

export interface WebQuote {
  // Core pricing fields
  vendor: string;
  url: string;
  product_name: string;
  unit_price: number;
  currency: string;
  unit: string;
  pack_size: number | null;
  pack_unit: string | null;
  vat_included: boolean;
  confidence: number;

  // Images
  image_url: string;
  image_urls: string[];

  // Stock & Availability
  availability: string;
  stock_status: string;
  stock_quantity: number | null;
  lead_time_days: number | null;

  // Reviews & Ratings
  rating: number | null;
  review_count: number | null;

  // Shipping
  shipping_cost: number | null;
  free_shipping_threshold: number | null;
  shipping_policy: string;

  // Product Details
  brand: string;
  sku: string;
  ean: string;
  specifications: Record<string, string>;

  // Volume/Bulk Pricing
  volume_prices: Array<{ min_qty?: number; price?: number }>;

  // Metadata
  evidence: Record<string, string>;
  scraped_at: string;
  source_method: string;
}

export interface ComputedTotal {
  quantity: number;
  unit_price_ex_vat: number;
  subtotal_ex_vat: number;
  vat: number;
  shipping_estimate: number;
  total: number;
  currency: string;
  notes: string[];
}

export interface SearchResultData {
  quotes: WebQuote[];
  best_quote: WebQuote | null;
  computed: ComputedTotal | null;
  reasoning: string;
  search_log: string[];
}

// ── Preset Models ──────────────────────────────────────────────────

export interface Preset {
  id: string;
  name: string;
  description: string;
  groups: string[];
  is_default: boolean;
}
