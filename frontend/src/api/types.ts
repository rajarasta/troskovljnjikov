export interface PricedLine {
  item_number: string;
  description: string;
  unit: string;
  quantity: number;
  unit_price: number | null;
  total: number | null;
  excel_row: number;
}

export interface LogicalUnit {
  id: string;
  item_number: string;
  title: string;
  description: string;
  priced_lines: PricedLine[];
  parent_section: string;
  parent_chapter: string;
  excel_start_row: number;
  excel_end_row: number;
}

export interface ParsedBoQ {
  filename: string;
  format_detected: string;
  sheet_name: string;
  chapter_title: string;
  units: LogicalUnit[];
  metadata: Record<string, unknown>;
}

export interface HistoricPricedLine {
  item_number: string;
  description: string;
  unit_of_measure: string;
  unit_price: number | null;
  quantity: number;
}

export interface HistoricMatchEvent {
  unit_id: number;
  title: string;
  project_name: string;
  item_number: string;
  priced_lines: HistoricPricedLine[];
}

export interface LineSuggestion {
  item_number: string;
  suggested_price: number;
  confidence: number;
  reasoning: string;
}

export interface OutputLineState {
  original: PricedLine;
  suggestedPrice: number | null;
  confidence: number | null;
  agentReasoning: string;
  userAccepted: boolean | null;
  userEditedPrice: number | null;
}
