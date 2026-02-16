"use client";

import { useMemo, useState, useCallback, useRef } from "react";
import { useBoQStore } from "@/stores/boqStore";
import { useSelectionStore } from "@/stores/selectionStore";
import { useMatchStore } from "@/stores/matchStore";

const ROW_HEIGHT = 28;
const OVERSCAN = 10;

// Column widths: B (description) is wide, others are moderate
const ROW_HDR_W = 44;
const COL_W_DEFAULT = 110;
const COL_W_DESC = 320; // column B (index 1) — usually descriptions

function colWidth(colIndex: number): number {
  return colIndex === 1 ? COL_W_DESC : COL_W_DEFAULT;
}

function colLetter(index: number): string {
  if (index < 26) return String.fromCharCode(65 + index);
  return colLetter(Math.floor(index / 26) - 1) + colLetter(index % 26);
}

interface CellCoord {
  row: number;
  col: number;
}

export default function RawSheetGrid() {
  const files = useBoQStore((s) => s.files);
  const selectedFileId = useBoQStore((s) => s.selectedFileId);
  const addSelection = useSelectionStore((s) => s.addSelection);
  const startLookup = useMatchStore((s) => s.startLookup);
  const items = useBoQStore((s) => s.items);

  // Cell selection state
  const [anchor, setAnchor] = useState<CellCoord | null>(null);
  const [selection, setSelection] = useState<{
    startRow: number;
    endRow: number;
    startCol: number;
    endCol: number;
  } | null>(null);
  const isDragging = useRef(false);

  // Virtual scroll state
  const scrollRef = useRef<HTMLDivElement>(null);
  const [scrollTop, setScrollTop] = useState(0);

  // Get all sheets and active sheet
  const sheets = useMemo(() => {
    if (!selectedFileId) return [];
    const file = files.find((f) => f.id === selectedFileId);
    if (!file?.raw_preview) return [];
    return Object.entries(file.raw_preview)
      .filter(([, rows]) => rows.length > 0)
      .map(([name, rows]) => ({ name, rows }));
  }, [files, selectedFileId]);

  const [activeSheet, setActiveSheet] = useState(0);

  const { rows, colCount } = useMemo(() => {
    if (sheets.length === 0) return { rows: [], colCount: 0 };
    const data = sheets[Math.min(activeSheet, sheets.length - 1)]?.rows ?? [];
    const cc = data.reduce((max, row) => {
      let last = row.length - 1;
      while (last >= 0 && !row[last]) last--;
      return Math.max(max, last + 1);
    }, 0);
    return { rows: data, colCount: cc };
  }, [sheets, activeSheet]);

  // Virtual scroll: compute visible row range
  const containerHeight = scrollRef.current?.clientHeight ?? 600;
  const totalHeight = rows.length * ROW_HEIGHT;
  const startRow = Math.max(0, Math.floor(scrollTop / ROW_HEIGHT) - OVERSCAN);
  const endRow = Math.min(
    rows.length - 1,
    Math.ceil((scrollTop + containerHeight) / ROW_HEIGHT) + OVERSCAN,
  );

  const handleScroll = useCallback(() => {
    if (scrollRef.current) {
      setScrollTop(scrollRef.current.scrollTop);
    }
  }, []);

  // Selection bounds
  const selBounds = useMemo(() => {
    if (!selection) return null;
    return {
      r1: Math.min(selection.startRow, selection.endRow),
      r2: Math.max(selection.startRow, selection.endRow),
      c1: Math.min(selection.startCol, selection.endCol),
      c2: Math.max(selection.startCol, selection.endCol),
    };
  }, [selection]);

  const handleMouseDown = useCallback(
    (row: number, col: number, e: React.MouseEvent) => {
      e.preventDefault();
      isDragging.current = true;
      setAnchor({ row, col });
      setSelection({ startRow: row, endRow: row, startCol: col, endCol: col });
    },
    [],
  );

  const handleMouseEnter = useCallback(
    (row: number, col: number) => {
      if (!isDragging.current || !anchor) return;
      setSelection({
        startRow: anchor.row,
        endRow: row,
        startCol: anchor.col,
        endCol: col,
      });
    },
    [anchor],
  );

  const handleMouseUp = useCallback(() => {
    isDragging.current = false;
    if (!selection || !selBounds) return;

    // Collect selected cell text
    const texts: string[] = [];
    for (let r = selBounds.r1; r <= selBounds.r2; r++) {
      for (let c = selBounds.c1; c <= selBounds.c2; c++) {
        const val = rows[r]?.[c] ?? "";
        if (val.trim()) texts.push(val.trim());
      }
    }

    if (texts.length === 0) return;

    // Try mapping raw row indices to parsed item indices
    const selectedItemIndices: number[] = [];
    for (let r = selBounds.r1; r <= selBounds.r2; r++) {
      const itemIdx = items.findIndex((item) => item.row === r + 1);
      if (itemIdx >= 0) selectedItemIndices.push(itemIdx);
    }

    if (selectedItemIndices.length > 0) {
      // Mapped to parsed items — use full selection pipeline
      const startIdx = Math.min(...selectedItemIndices);
      const endIdx = Math.max(...selectedItemIndices);
      addSelection(startIdx, endIdx, items.slice(startIdx, endIdx + 1));
    } else {
      // No parsed item match — directly search with the cell text
      const searchText = texts.join(" ");
      startLookup(searchText);
    }
  }, [selection, selBounds, rows, items, addSelection, startLookup]);

  if (sheets.length === 0 || colCount === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-3 text-text-muted select-none">
        <p className="text-sm">Re-upload file to view raw sheet data</p>
        <p className="text-xs text-text-muted">
          Files uploaded before this feature need re-uploading
        </p>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col select-none">
      {/* Sheet tabs */}
      {sheets.length > 1 && (
        <div className="flex items-center gap-px px-1 py-1 bg-bg-tertiary border-b border-border-default shrink-0 overflow-x-auto">
          {sheets.map((sheet, idx) => (
            <button
              key={sheet.name}
              onClick={() => setActiveSheet(idx)}
              className={`px-2 py-0.5 text-[10px] font-mono rounded transition-colors whitespace-nowrap ${
                idx === activeSheet
                  ? "bg-accent-cyan/10 text-accent-cyan border border-accent-cyan/20"
                  : "text-text-muted hover:text-text-secondary hover:bg-bg-hover"
              }`}
            >
              {sheet.name}
            </button>
          ))}
        </div>
      )}

      {/* Virtualized grid */}
      <div
        ref={scrollRef}
        className="flex-1 overflow-auto"
        onScroll={handleScroll}
        onMouseUp={handleMouseUp}
      >
        <div style={{ height: totalHeight + ROW_HEIGHT, position: "relative" }}>
          {/* Sticky column header row */}
          <div
            className="sticky top-0 z-20 flex"
            style={{ height: ROW_HEIGHT }}
          >
            <div
              className="shrink-0 sticky left-0 z-30 bg-bg-tertiary border-r border-b border-border-default"
              style={{ width: ROW_HDR_W, minWidth: ROW_HDR_W }}
            />
            {Array.from({ length: colCount }, (_, i) => {
              const w = colWidth(i);
              return (
                <div
                  key={i}
                  className="shrink-0 flex items-center justify-center text-[10px] font-mono font-semibold text-text-secondary bg-bg-tertiary border-r border-b border-border-default"
                  style={{ width: w, minWidth: w, height: ROW_HEIGHT }}
                >
                  {colLetter(i)}
                </div>
              );
            })}
          </div>

          {/* Virtual rows */}
          {rows.length > 0 &&
            Array.from({ length: endRow - startRow + 1 }, (_, i) => {
              const rIdx = startRow + i;
              const row = rows[rIdx];
              if (!row) return null;
              const y = (rIdx + 1) * ROW_HEIGHT; // +1 for header
              const hasContent = row.some((cell) => cell?.trim());

              return (
                <div
                  key={rIdx}
                  className="absolute left-0 flex"
                  style={{
                    top: y,
                    height: ROW_HEIGHT,
                    willChange: "transform",
                  }}
                >
                  {/* Row number header — sticky left */}
                  <div
                    className="shrink-0 sticky left-0 z-10 flex items-center justify-center text-[10px] font-mono text-text-muted bg-bg-tertiary border-r border-b border-border-default/60 font-medium"
                    style={{ width: ROW_HDR_W, minWidth: ROW_HDR_W }}
                  >
                    {rIdx + 1}
                  </div>

                  {/* Data cells */}
                  {Array.from({ length: colCount }, (_, cIdx) => {
                    const val = row[cIdx] ?? "";
                    const w = colWidth(cIdx);
                    const isSelected =
                      selBounds &&
                      rIdx >= selBounds.r1 &&
                      rIdx <= selBounds.r2 &&
                      cIdx >= selBounds.c1 &&
                      cIdx <= selBounds.c2;

                    return (
                      <div
                        key={cIdx}
                        onMouseDown={(e) => handleMouseDown(rIdx, cIdx, e)}
                        onMouseEnter={() => handleMouseEnter(rIdx, cIdx)}
                        className={`shrink-0 flex items-center px-2 text-xs font-mono border-r border-b truncate cursor-cell transition-colors duration-75 ${
                          isSelected
                            ? "bg-accent-purple/12 text-accent-purple border-accent-purple/25 font-medium"
                            : hasContent
                              ? rIdx % 2 === 0
                                ? "text-text-primary border-border-default/50"
                                : "text-text-primary bg-bg-secondary/40 border-border-default/50"
                              : "text-text-muted/40 border-border-default/25"
                        }`}
                        style={{
                          width: w,
                          minWidth: w,
                          height: ROW_HEIGHT,
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
        </div>
      </div>
    </div>
  );
}
