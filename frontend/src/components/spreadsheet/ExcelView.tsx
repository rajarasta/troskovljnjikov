"use client";

import { useMemo, useState, useCallback, useRef } from "react";
import { useBoQStore } from "@/stores/boqStore";
import { useSelectionStore } from "@/stores/selectionStore";
import type { BoQItem } from "@/lib/types";

const MIN_COL_W = 36;

// ── Layout constants ─────────────────────────────────────────────────

const BASE_FONT = 13;
const COL_W_DEFAULT = 100;
const COL_W_DESC = 280;
const COL_W_NARROW = 55; // for unit, qty, price, total, first col
const OVERSCAN = 12;
// Grid line color — matches Excel's #e2e2e2
const GRID = "#d9dce0";
// Header background — light gray like Excel/Sheets
const HDR_BG = "#f3f3f3";
// Selection — blue like Excel
const SEL_BG = "rgba(22, 119, 255, 0.08)";
const SEL_BORDER = "#1677ff";

// ── Header patterns for narrow columns ──
const narrowPat = [
  "r.br", "rb", "rbr", "br.", "br",          // first col / row number
  "jm", "jedinica", "mjera", "unit",          // unit of measure
  "kol", "količina", "qty", "quantity",        // quantity
  "jc", "cijena", "price", "jed",             // unit price
  "uc", "ukupno", "total",                    // total price
];

function detectDefaultWidth(colIdx: number, headerText?: string): number {
  if (colIdx === 0) return COL_W_NARROW; // first column always narrow
  if (!headerText) return colIdx === 1 ? COL_W_DESC : COL_W_DEFAULT;
  const h = headerText.toLowerCase().trim();
  if (narrowPat.some((p) => h.includes(p))) return COL_W_NARROW;
  if (colIdx === 1) return COL_W_DESC;
  return COL_W_DEFAULT;
}

function colLetter(i: number): string {
  if (i < 26) return String.fromCharCode(65 + i);
  return colLetter(Math.floor(i / 26) - 1) + colLetter(i % 26);
}

/** True if the string looks like a number (for right-alignment) */
function isNumeric(s: string): boolean {
  if (!s) return false;
  const cleaned = s.replace(/[\s€$%,]/g, "").replace(",", ".");
  return /^-?\d+([.,]\d+)?$/.test(cleaned);
}

/** Measure actual row heights using a hidden DOM element */
let measureEl: HTMLDivElement | null = null;

function getMeasureEl(): HTMLDivElement {
  if (measureEl) return measureEl;
  measureEl = document.createElement("div");
  measureEl.style.cssText =
    "position:absolute;top:-9999px;left:-9999px;visibility:hidden;white-space:pre-wrap;word-break:break-word;box-sizing:border-box;";
  document.body.appendChild(measureEl);
  return measureEl;
}

function measureRowHeight(
  row: string[],
  baseH: number,
  fontPx: number,
  wrapAll: boolean,
  colCount: number,
  getColW: (i: number) => number,
): number {
  if (!wrapAll) return baseH;
  const el = getMeasureEl();
  const padH = Math.round(fontPx * 0.46);
  const padV = Math.round(fontPx * 0.23);
  el.style.fontSize = `${fontPx}px`;
  el.style.fontFamily = "system-ui, -apple-system, sans-serif";
  el.style.lineHeight = "1.5";
  el.style.padding = `${padV}px ${padH}px`;

  let maxH = baseH;
  for (let c = 0; c < colCount; c++) {
    const text = row[c] ?? "";
    if (!text || text.length * fontPx * 0.6 < getColW(c)) continue;
    el.style.width = `${getColW(c)}px`;
    el.textContent = text;
    const h = el.offsetHeight;
    if (h > maxH) maxH = h;
  }
  return maxH;
}

/** Binary search: find first index where offsets[i] > value */
function upperBound(offsets: number[], value: number): number {
  let lo = 0, hi = offsets.length - 1;
  while (lo < hi) {
    const mid = (lo + hi) >> 1;
    if (offsets[mid] <= value) lo = mid + 1;
    else hi = mid;
  }
  return lo;
}

// ── Price extraction ─────────────────────────────────────────────────

const qtyPat = ["kol", "količina", "qty", "quantity", "kolicina"];
const pricePat = ["cijena", "jc", "jed", "price", "unit price", "jedinična"];
const totalPat = ["ukupno", "total", "uc"];

function extractPriceData(
  rowData: string[],
  headerRow?: string[],
): { quantity: number; unit_price: number } {
  const r = { quantity: 0, unit_price: 0 };
  if (!headerRow?.length) return r;
  for (let i = 0; i < Math.min(headerRow.length, rowData.length); i++) {
    const h = headerRow[i]?.toLowerCase().trim() ?? "";
    const v = rowData[i]?.trim() ?? "";
    if (!v) continue;
    const n = parseFloat(v.replace(/[^\d.,]/g, "").replace(",", "."));
    if (isNaN(n) || n === 0) continue;
    if (r.quantity === 0 && qtyPat.some((p) => h.includes(p))) r.quantity = n;
    if (r.unit_price === 0 && pricePat.some((p) => h.includes(p)) && !totalPat.some((t) => h.includes(t)))
      r.unit_price = n;
  }
  return r;
}

// ── Types ────────────────────────────────────────────────────────────

interface CellCoord { row: number; col: number }

// ── Component ────────────────────────────────────────────────────────

export default function ExcelView({
  wrapAll = false,
  zoom = 100,
  baseFontSize = BASE_FONT,
}: {
  wrapAll?: boolean;
  zoom?: number;
  baseFontSize?: number;
}) {
  const files = useBoQStore((s) => s.files);
  const selectedFileId = useBoQStore((s) => s.selectedFileId);
  const items = useBoQStore((s) => s.items);
  const addSelection = useSelectionStore((s) => s.addSelection);
  const replaceSelection = useSelectionStore((s) => s.replaceSelection);

  const [anchor, setAnchor] = useState<CellCoord | null>(null);
  const [sel, setSel] = useState<{
    startRow: number; endRow: number; startCol: number; endCol: number;
  } | null>(null);
  const isDragging = useRef(false);
  const pipelineSelRef = useRef<string | null>(null);

  const scrollRef = useRef<HTMLDivElement>(null);
  const [scrollTop, setScrollTop] = useState(0);

  // ── Editing state ──
  const [editCell, setEditCell] = useState<CellCoord | null>(null);
  const [editValue, setEditValue] = useState("");
  const [cellEdits, setCellEdits] = useState<Record<string, string>>({});
  const editRef = useRef<HTMLInputElement>(null);

  // ── Column resize state ──
  const [colWidths, setColWidths] = useState<Record<number, number>>({});
  const resizeRef = useRef<{ colIdx: number; startX: number; startW: number } | null>(null);

  // ── Data ──

  const { sheets, headerRows } = useMemo(() => {
    if (!selectedFileId) return { sheets: [], headerRows: null };
    const file = files.find((f) => f.id === selectedFileId);
    if (!file?.raw_preview) return { sheets: [], headerRows: null };
    return {
      sheets: Object.entries(file.raw_preview)
        .filter(([, r]) => r.length > 0)
        .map(([name, rows]) => ({ name, rows })),
      headerRows: file.header_rows,
    };
  }, [files, selectedFileId]);

  const [activeSheet, setActiveSheet] = useState(0);

  const { rows, colCount } = useMemo(() => {
    if (!sheets.length) return { rows: [], colCount: 0 };
    const data = sheets[Math.min(activeSheet, sheets.length - 1)]?.rows ?? [];
    const cc = data.reduce((max, row) => {
      let last = row.length - 1;
      while (last >= 0 && !row[last]) last--;
      return Math.max(max, last + 1);
    }, 0);
    return { rows: data, colCount: cc };
  }, [sheets, activeSheet]);

  const colHeaders = useMemo(() => {
    if (!headerRows || !sheets.length) return null;
    const s = sheets[Math.min(activeSheet, sheets.length - 1)];
    if (!s) return null;
    const idx = headerRows[s.name];
    if (idx == null || idx < 0) return null;
    return s.rows[idx] ?? null;
  }, [headerRows, sheets, activeSheet]);

  const headerRow = useMemo(() => {
    if (!headerRows || !sheets.length) return undefined;
    const s = sheets[Math.min(activeSheet, sheets.length - 1)];
    if (!s) return undefined;
    const idx = headerRows[s.name];
    if (idx == null || idx < 0) return undefined;
    return s.rows[idx];
  }, [headerRows, sheets, activeSheet]);

  // ── Smart default widths based on header detection ──
  const defaultColWidth = useCallback(
    (i: number) => detectDefaultWidth(i, colHeaders?.[i] ?? undefined),
    [colHeaders],
  );

  // ── Derived sizes ──
  const scale = zoom / 100;
  const fontPx = Math.round(baseFontSize * scale);
  const rowH = Math.max(20, Math.round((baseFontSize * 1.85) * scale));
  const hdrFontSize = Math.round((baseFontSize - 2) * scale);
  const cW = useCallback(
    (i: number) => Math.round((colWidths[i] ?? defaultColWidth(i)) * scale),
    [colWidths, scale, defaultColWidth],
  );

  const onResizeStart = useCallback((colIdx: number, e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    const startW = colWidths[colIdx] ?? defaultColWidth(colIdx);
    const startX = e.clientX;
    const zoomScale = zoom / 100;
    resizeRef.current = { colIdx, startX, startW };

    const onMove = (ev: MouseEvent) => {
      const delta = ev.clientX - startX;
      const newW = Math.max(MIN_COL_W, Math.round(startW + delta / zoomScale));
      setColWidths((prev) => ({ ...prev, [colIdx]: newW }));
    };
    const onUp = () => {
      document.removeEventListener("mousemove", onMove);
      document.removeEventListener("mouseup", onUp);
      document.body.style.cursor = "";
      requestAnimationFrame(() => { resizeRef.current = null; });
    };
    document.addEventListener("mousemove", onMove);
    document.addEventListener("mouseup", onUp);
    document.body.style.cursor = "col-resize";
  }, [colWidths, zoom, defaultColWidth]);

  // ── Row heights & cumulative offsets ──

  const { rowHeights, rowOffsets, totalH } = useMemo(() => {
    const getColW = (i: number) => Math.round((colWidths[i] ?? defaultColWidth(i)) * scale);
    const heights = rows.map((row) => measureRowHeight(row, rowH, fontPx, wrapAll, colCount, getColW));
    const offsets = new Array<number>(rows.length);
    let cum = rowH;
    for (let i = 0; i < rows.length; i++) {
      offsets[i] = cum;
      cum += heights[i];
    }
    return { rowHeights: heights, rowOffsets: offsets, totalH: cum };
  }, [rows, rowH, fontPx, wrapAll, colWidths, colCount, defaultColWidth, scale]);

  // ── Virtual scroll ──

  const containerH = scrollRef.current?.clientHeight ?? 600;
  const vStart = Math.max(0, upperBound(rowOffsets, scrollTop) - 1 - OVERSCAN);
  const vEnd = Math.min(rows.length - 1, upperBound(rowOffsets, scrollTop + containerH) + OVERSCAN);

  const onScroll = useCallback(() => {
    if (scrollRef.current) setScrollTop(scrollRef.current.scrollTop);
  }, []);

  // ── Selection ──

  const bounds = useMemo(() => {
    if (!sel) return null;
    return {
      r1: Math.min(sel.startRow, sel.endRow),
      r2: Math.max(sel.startRow, sel.endRow),
      c1: Math.min(sel.startCol, sel.endCol),
      c2: Math.max(sel.startCol, sel.endCol),
    };
  }, [sel]);

  const onCellDown = useCallback((row: number, col: number, e: React.MouseEvent) => {
    if (editCell) return; // don't start drag when editing
    e.preventDefault();
    isDragging.current = true;
    setAnchor({ row, col });
    setSel({ startRow: row, endRow: row, startCol: col, endCol: col });
  }, [editCell]);

  const onCellEnter = useCallback((row: number, col: number) => {
    if (!isDragging.current || !anchor) return;
    setSel({ startRow: anchor.row, endRow: row, startCol: anchor.col, endCol: col });
  }, [anchor]);

  // ── Editing ──

  const startEdit = useCallback((row: number, col: number) => {
    const key = `${row}:${col}`;
    const current = cellEdits[key] ?? rows[row]?.[col] ?? "";
    setEditCell({ row, col });
    setEditValue(current);
    setTimeout(() => editRef.current?.focus(), 0);
  }, [cellEdits, rows]);

  const commitEdit = useCallback(() => {
    if (!editCell) return;
    const key = `${editCell.row}:${editCell.col}`;
    setCellEdits((prev) => ({ ...prev, [key]: editValue }));
    setEditCell(null);
  }, [editCell, editValue]);

  const cancelEdit = useCallback(() => {
    setEditCell(null);
  }, []);

  const getCellValue = useCallback((row: number, col: number): string => {
    const key = `${row}:${col}`;
    return cellEdits[key] ?? rows[row]?.[col] ?? "";
  }, [cellEdits, rows]);

  const onMouseUp = useCallback(() => {
    isDragging.current = false;
    if (!sel || resizeRef.current) return;
    const b = {
      r1: Math.min(sel.startRow, sel.endRow),
      r2: Math.max(sel.startRow, sel.endRow),
      c1: Math.min(sel.startCol, sel.endCol),
      c2: Math.max(sel.startCol, sel.endCol),
    };

    const cellData: Array<{ row: number; col: number; text: string }> = [];
    for (let r = b.r1; r <= b.r2; r++)
      for (let c = b.c1; c <= b.c2; c++) {
        const v = getCellValue(r, c);
        if (v.trim()) cellData.push({ row: r, col: c, text: v.trim() });
      }
    if (!cellData.length) return;

    const itemIdxs: number[] = [];
    for (let r = b.r1; r <= b.r2; r++) {
      const idx = items.findIndex((it) => it.row === r + 1);
      if (idx >= 0) itemIdxs.push(idx);
    }

    if (itemIdxs.length) {
      const s = Math.min(...itemIdxs), e = Math.max(...itemIdxs);
      const id = pipelineSelRef.current
        ? replaceSelection(pipelineSelRef.current, s, e, items.slice(s, e + 1))
        : addSelection(s, e, items.slice(s, e + 1));
      pipelineSelRef.current = id;
    } else {
      const rowMap = new Map<number, { cells: typeof cellData; pd: ReturnType<typeof extractPriceData> }>();
      for (const c of cellData) {
        if (!rowMap.has(c.row)) {
          rowMap.set(c.row, { cells: [c], pd: extractPriceData(rows[c.row] ?? [], headerRow) });
        } else rowMap.get(c.row)!.cells.push(c);
      }
      const synth: BoQItem[] = Array.from(rowMap.entries()).flatMap(([, { cells, pd }]) =>
        cells.map((c) => ({
          id: `xc-${c.row}-${c.col}-${Date.now()}`, file_id: selectedFileId!,
          sheet_name: null, row: c.row, item_number: null, description: c.text,
          full_description: null, parent_item_number: null, unit: null,
          quantity: pd.quantity, unit_price: pd.unit_price,
          total: pd.quantity * pd.unit_price,
          project_name: null, date: null, material_price: null, labor_price: null,
          material_total: null, labor_total: null, notes: null, drawing_path: null,
          llm_response: null, file_name: null,
        })),
      );
      const mn = Math.min(...cellData.map((c) => c.row));
      const mx = Math.max(...cellData.map((c) => c.row));
      const id = pipelineSelRef.current
        ? replaceSelection(pipelineSelRef.current, mn, mx, synth)
        : addSelection(mn, mx, synth);
      pipelineSelRef.current = id;
    }
  }, [sel, rows, items, headerRow, selectedFileId, addSelection, replaceSelection, getCellValue]);

  // ── Total grid width ──
  const totalW = useMemo(() => {
    let w = 0;
    for (let i = 0; i < colCount; i++) w += cW(i);
    return w;
  }, [colCount, cW]);

  // ── Empty state ──

  if (!sheets.length || !colCount) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-3 text-text-muted select-none">
        <p className="text-sm">Učitajte datoteku za pregled Excel-a</p>
      </div>
    );
  }

  // ── Selection overlay pixel coords ──
  let selOverlay: { left: number; top: number; width: number; height: number } | null = null;
  if (bounds) {
    let left = 0;
    for (let c = 0; c < bounds.c1; c++) left += cW(c);
    let width = 0;
    for (let c = bounds.c1; c <= bounds.c2; c++) width += cW(c);
    const top = rowOffsets[bounds.r1] ?? rowH;
    let height = 0;
    for (let r = bounds.r1; r <= bounds.r2; r++) height += rowHeights[r] ?? rowH;
    selOverlay = { left, top, width, height };
  }

  return (
    <div className="h-full flex flex-col select-none" style={{ background: "#fff" }}>
      {/* Virtualized grid area */}
      <div
        ref={scrollRef}
        className="flex-1 overflow-auto relative"
        onScroll={onScroll}
        onMouseUp={onMouseUp}
        style={{ fontSize: fontPx }}
      >
        {/* Content sizer */}
        <div style={{ width: totalW, height: totalH, position: "relative" }}>

          {/* ── Column headers (sticky top) ── */}
          <div
            className="sticky top-0 z-20 flex"
            style={{ height: rowH }}
          >
            {Array.from({ length: colCount }, (_, i) => {
              const w = cW(i);
              const txt = colHeaders?.[i]?.trim() || colLetter(i);
              const isInSel = bounds && i >= bounds.c1 && i <= bounds.c2;
              return (
                <div
                  key={i}
                  className="shrink-0 flex items-center justify-center truncate px-1"
                  style={{
                    width: w, minWidth: w, height: rowH,
                    fontSize: hdrFontSize,
                    fontWeight: 600,
                    color: isInSel ? SEL_BORDER : "#666",
                    background: isInSel ? "#e8f0fe" : HDR_BG,
                    borderRight: `1px solid ${GRID}`,
                    borderBottom: `1px solid ${GRID}`,
                    position: "relative",
                  }}
                  title={txt}
                >
                  {txt}
                  {/* Resize handle */}
                  <div
                    onMouseDown={(e) => onResizeStart(i, e)}
                    style={{
                      position: "absolute",
                      right: -3,
                      top: 0,
                      width: 6,
                      height: "100%",
                      cursor: "col-resize",
                      zIndex: 1,
                    }}
                  />
                </div>
              );
            })}
          </div>

          {/* ── Virtual rows ── */}
          {rows.length > 0 &&
            Array.from({ length: vEnd - vStart + 1 }, (_, i) => {
              const rIdx = vStart + i;
              const row = rows[rIdx];
              if (!row) return null;
              const y = rowOffsets[rIdx] ?? 0;
              const rH = rowHeights[rIdx] ?? rowH;
              return (
                <div
                  key={rIdx}
                  className="absolute left-0 flex"
                  style={{ top: y, height: rH }}
                >
                  {/* Data cells */}
                  {Array.from({ length: colCount }, (_, cIdx) => {
                    const val = getCellValue(rIdx, cIdx);
                    const w = cW(cIdx);
                    const numeric = isNumeric(val);
                    const shouldWrap = wrapAll && !numeric;
                    const isEditing = editCell?.row === rIdx && editCell?.col === cIdx;
                    const padH = Math.round(fontPx * 0.46);

                    if (isEditing) {
                      return (
                        <div
                          key={cIdx}
                          style={{
                            width: w, minWidth: w, height: rH,
                            borderRight: `1px solid ${GRID}`,
                            borderBottom: `1px solid ${GRID}`,
                            padding: 0,
                          }}
                        >
                          <input
                            ref={editRef}
                            value={editValue}
                            onChange={(e) => setEditValue(e.target.value)}
                            onKeyDown={(e) => {
                              if (e.key === "Enter") commitEdit();
                              if (e.key === "Escape") cancelEdit();
                              if (e.key === "Tab") { e.preventDefault(); commitEdit(); }
                            }}
                            onBlur={commitEdit}
                            style={{
                              width: "100%",
                              height: "100%",
                              fontSize: fontPx,
                              fontFamily: "inherit",
                              padding: `0 ${padH}px`,
                              border: `2px solid ${SEL_BORDER}`,
                              outline: "none",
                              boxSizing: "border-box",
                              background: "#fff",
                            }}
                          />
                        </div>
                      );
                    }

                    return (
                      <div
                        key={cIdx}
                        onMouseDown={(e) => onCellDown(rIdx, cIdx, e)}
                        onMouseEnter={() => onCellEnter(rIdx, cIdx)}
                        onDoubleClick={() => startEdit(rIdx, cIdx)}
                        className={shouldWrap ? "whitespace-pre-wrap break-words" : "truncate"}
                        style={{
                          width: w,
                          minWidth: w,
                          height: rH,
                          display: "flex",
                          alignItems: shouldWrap && rH > rowH ? "flex-start" : "center",
                          padding: shouldWrap
                            ? `${Math.round(fontPx * 0.23)}px ${padH}px`
                            : `0 ${padH}px`,
                          overflow: shouldWrap ? "hidden" : undefined,
                          borderRight: `1px solid ${GRID}`,
                          borderBottom: `1px solid ${GRID}`,
                          cursor: "cell",
                          color: val ? "#1e1e2e" : "#ccc",
                          textAlign: numeric ? "right" : "left",
                          justifyContent: numeric ? "flex-end" : "flex-start",
                          fontVariantNumeric: numeric ? "tabular-nums" : undefined,
                          background: "#fff",
                        }}
                        title={val}
                      >
                        {val}
                      </div>
                    );
                  })}
                </div>
              );
            })}

          {/* ── Selection overlay ── */}
          {selOverlay && !editCell && (
            <div
              className="pointer-events-none absolute z-15"
              style={{
                left: selOverlay.left,
                top: selOverlay.top,
                width: selOverlay.width,
                height: selOverlay.height,
                background: SEL_BG,
                border: `2px solid ${SEL_BORDER}`,
                boxSizing: "border-box",
              }}
            >
              <div
                style={{
                  position: "absolute",
                  right: -3,
                  bottom: -3,
                  width: 6,
                  height: 6,
                  background: SEL_BORDER,
                  border: "1px solid #fff",
                }}
              />
            </div>
          )}
        </div>
      </div>

      {/* ── Sheet tabs ── */}
      {sheets.length > 1 && (
        <div
          className="flex items-center gap-0 shrink-0 overflow-x-auto"
          style={{
            background: HDR_BG,
            borderTop: `1px solid ${GRID}`,
            height: 28,
          }}
        >
          {sheets.map((sheet, idx) => (
            <button
              key={sheet.name}
              onClick={() => setActiveSheet(idx)}
              className="whitespace-nowrap transition-colors"
              style={{
                padding: "0 14px",
                height: 28,
                fontSize: 11,
                fontWeight: idx === activeSheet ? 600 : 400,
                color: idx === activeSheet ? "#1e1e2e" : "#888",
                background: idx === activeSheet ? "#fff" : "transparent",
                borderRight: `1px solid ${GRID}`,
                borderBottom: idx === activeSheet ? "2px solid " + SEL_BORDER : "none",
              }}
            >
              {sheet.name}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
