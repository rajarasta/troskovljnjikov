// Shared column definitions and style helpers for BoQ tables.
// Used by both MatchResultsTable and SpreadsheetView to ensure visual consistency.

import { usePresetStore } from "@/stores/presetStore";

export const BOQ_COLUMNS = [
  { key: "item_number", label: "#", width: "60px", align: "left" as const },
  { key: "description", label: "Stavka", width: undefined, align: "left" as const },
  { key: "unit", label: "Jed.", width: "60px", align: "left" as const },
  { key: "quantity", label: "Količina", width: "80px", align: "right" as const },
  { key: "unit_price", label: "Jed. cijena", width: "100px", align: "right" as const },
  { key: "total", label: "Ukupno", width: "100px", align: "right" as const },
] as const;

export type ColumnKey = (typeof BOQ_COLUMNS)[number]["key"];

export function getRowClasses(index: number, isHighlighted: boolean): string {
  if (isHighlighted) return "";
  const isEven = index % 2 === 0;
  return isEven ? "bg-transparent" : "bg-bg-secondary/30";
}

export function getCellClasses(key: ColumnKey): string {
  if (key === "description") {
    return "px-3 py-1.5 whitespace-pre-wrap break-words text-text-primary align-top";
  }
  if (key === "item_number") {
    return "px-3 py-1.5 font-mono text-text-muted whitespace-nowrap align-top";
  }
  if (key === "unit") {
    return "px-3 py-1.5 text-text-muted whitespace-nowrap align-top";
  }
  // Numeric: quantity, unit_price, total
  return "px-3 py-1.5 text-right font-mono text-text-primary whitespace-nowrap align-top";
}

export function formatNumber(value: number): string {
  return value.toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

// ── Full canonical column set & visibility filter ────────────────────

export interface BoQColumn {
  key: string;
  label: string;
  width: string | undefined;
  align: "left" | "right" | "center";
}

const ALL_BOQ_COLUMNS: BoQColumn[] = [
  { key: "item_number",      label: "#",               width: "60px",    align: "left" },
  { key: "description",      label: "Opis stavke",     width: undefined, align: "left" },
  { key: "unit",             label: "Jed.",            width: "60px",    align: "left" },
  { key: "quantity",         label: "Koli\u010dina",        width: "80px",    align: "right" },
  { key: "unit_price",       label: "Jed. cijena",     width: "100px",   align: "right" },
  { key: "total",            label: "Ukupno",          width: "100px",   align: "right" },
  { key: "material_price",   label: "Cijena mat.",     width: "100px",   align: "right" },
  { key: "labor_price",      label: "Cijena rada",     width: "100px",   align: "right" },
  { key: "material_total",   label: "Uk. materijal",   width: "100px",   align: "right" },
  { key: "labor_total",      label: "Uk. rad",         width: "100px",   align: "right" },
  { key: "notes",            label: "Bilje\u0161ke",        width: "150px",   align: "left" },
  { key: "drawing",          label: "Crte\u017e",           width: "80px",    align: "center" },
  { key: "llm_response",     label: "LLM",             width: "150px",   align: "left" },
  { key: "status",           label: "Status",          width: "90px",    align: "center" },
  { key: "updated_at",       label: "Datum",           width: "90px",    align: "center" },
  { key: "full_description", label: "Puni opis",       width: "200px",   align: "left" },
  { key: "parent_item_number", label: "Nadre\u0111ena",     width: "80px",    align: "left" },
  { key: "item_type",        label: "Tip",             width: "80px",    align: "center" },
];

export { ALL_BOQ_COLUMNS };

export function getVisibleColumns(): BoQColumn[] {
  const activeKeys = usePresetStore.getState().getActiveColumns();
  return ALL_BOQ_COLUMNS.filter((c) => activeKeys.includes(c.key));
}
