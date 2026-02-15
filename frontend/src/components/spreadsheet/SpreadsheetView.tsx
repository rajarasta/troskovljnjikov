"use client";

import { useMemo, useCallback, forwardRef } from "react";
import { FileSpreadsheet } from "lucide-react";
import { useBoQStore } from "@/stores/boqStore";
import { useSelectionStore } from "@/stores/selectionStore";
import type { SelectionColor } from "@/stores/selectionStore";
import type { BoQItem } from "@/lib/types";

// ── Helpers ──────────────────────────────────────────────────────────

function formatNumber(value: number): string {
  return value.toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

/** Set of item_numbers that have at least one child referencing them */
function buildParentSet(items: BoQItem[]): Set<string> {
  const parents = new Set<string>();
  for (const item of items) {
    if (item.parent_item_number) {
      parents.add(item.parent_item_number);
    }
  }
  return parents;
}

// ── Selection color style maps ──────────────────────────────────────
// Tailwind requires full class names at build time, so we map each
// SelectionColor to its concrete active/inactive class strings.

const ACTIVE_ROW_CLASSES: Record<SelectionColor, string> = {
  cyan: "bg-accent-cyan/15 border-l-2 border-l-accent-cyan",
  purple: "bg-accent-purple/15 border-l-2 border-l-accent-purple",
  amber: "bg-accent-amber/15 border-l-2 border-l-accent-amber",
  emerald: "bg-accent-emerald/15 border-l-2 border-l-accent-emerald",
  rose: "bg-accent-rose/15 border-l-2 border-l-accent-rose",
  sky: "bg-accent-sky/15 border-l-2 border-l-accent-sky",
};

const INACTIVE_ROW_CLASSES: Record<SelectionColor, string> = {
  cyan: "bg-accent-cyan/5",
  purple: "bg-accent-purple/5",
  amber: "bg-accent-amber/5",
  emerald: "bg-accent-emerald/5",
  rose: "bg-accent-rose/5",
  sky: "bg-accent-sky/5",
};

const ACTIVE_TEXT_CLASSES: Record<SelectionColor, string> = {
  cyan: "text-accent-cyan",
  purple: "text-accent-purple",
  amber: "text-accent-amber",
  emerald: "text-accent-emerald",
  rose: "text-accent-rose",
  sky: "text-accent-sky",
};

// ── Column config ────────────────────────────────────────────────────

const COLUMNS = [
  { key: "item_number", label: "#", width: "60px", align: "left" as const },
  { key: "description", label: "Description", width: undefined, align: "left" as const },
  { key: "quantity", label: "Qty", width: "80px", align: "right" as const },
  { key: "unit", label: "Unit", width: "60px", align: "left" as const },
  { key: "unit_price", label: "Unit Price", width: "100px", align: "right" as const },
  { key: "total", label: "Total", width: "100px", align: "right" as const },
] as const;

// ── Component ────────────────────────────────────────────────────────

const SpreadsheetView = forwardRef<HTMLDivElement>(function SpreadsheetView(_props, ref) {
  const items = useBoQStore((s) => s.items);

  const selections = useSelectionStore((s) => s.selections);
  const activeSelectionId = useSelectionStore((s) => s.activeSelectionId);
  const addSelection = useSelectionStore((s) => s.addSelection);
  const setActive = useSelectionStore((s) => s.setActive);
  const setDragAnchor = useSelectionStore((s) => s.setDragAnchor);
  const dragAnchorIndex = useSelectionStore((s) => s.dragAnchorIndex);

  const parentSet = useMemo(() => buildParentSet(items), [items]);

  // Build a lookup map: row index -> { color, isActive } for highlighting.
  // Later selections paint over earlier ones for overlapping rows.
  const selectionHighlightMap = useMemo(() => {
    const map = new Map<number, { color: SelectionColor; isActive: boolean }>();
    for (const sel of selections) {
      const isActive = sel.id === activeSelectionId;
      for (let i = sel.startIndex; i <= sel.endIndex; i++) {
        map.set(i, { color: sel.color, isActive });
      }
    }
    return map;
  }, [selections, activeSelectionId]);

  // ── Mouse handlers for multi-area selection ──────────────────────

  const handleMouseDown = useCallback(
    (index: number, e: React.MouseEvent) => {
      if (e.shiftKey && dragAnchorIndex !== null) {
        // Shift+click: create range from anchor to this row
        const start = Math.min(dragAnchorIndex, index);
        const end = Math.max(dragAnchorIndex, index);
        addSelection(start, end, items.slice(start, end + 1));
        setDragAnchor(null);
      } else {
        // Normal click: set anchor for potential drag
        setDragAnchor(index);
      }
    },
    [dragAnchorIndex, addSelection, items, setDragAnchor],
  );

  const handleMouseUp = useCallback(
    (index: number) => {
      if (dragAnchorIndex !== null && dragAnchorIndex !== index) {
        // Drag completed: create selection from anchor to this row
        const start = Math.min(dragAnchorIndex, index);
        const end = Math.max(dragAnchorIndex, index);
        addSelection(start, end, items.slice(start, end + 1));
        setDragAnchor(null);
      }
      // If anchor === index, this is a single-row click.
      // We create a single-row selection on click release.
      if (dragAnchorIndex !== null && dragAnchorIndex === index) {
        addSelection(index, index, items.slice(index, index + 1));
        setDragAnchor(null);
      }
    },
    [dragAnchorIndex, addSelection, items, setDragAnchor],
  );

  const handleSelectionClick = useCallback(
    (index: number) => {
      // If the clicked row belongs to an existing selection, make it active
      for (const sel of selections) {
        if (index >= sel.startIndex && index <= sel.endIndex) {
          setActive(sel.id);
          return;
        }
      }
    },
    [selections, setActive],
  );

  // ── Empty state ──────────────────────────────────────────────────

  if (items.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-3 text-text-muted select-none">
        <FileSpreadsheet className="w-10 h-10 opacity-40" />
        <p className="text-sm">Upload a file to view its contents</p>
      </div>
    );
  }

  // ── Table ────────────────────────────────────────────────────────

  return (
    <div ref={ref} className="h-full overflow-auto select-none">
      <table className="w-full text-xs border-collapse">
        {/* Column sizing via colgroup */}
        <colgroup>
          {COLUMNS.map((col) => (
            <col
              key={col.key}
              style={col.width ? { width: col.width, minWidth: col.width } : undefined}
              className={col.width ? undefined : "w-full"}
            />
          ))}
        </colgroup>

        {/* ── Sticky header ──────────────────────────────────────── */}
        <thead className="sticky top-0 z-10 bg-bg-secondary">
          <tr className="border-b border-border-default">
            {COLUMNS.map((col) => (
              <th
                key={col.key}
                className={`
                  px-3 py-2 font-semibold text-[10px] uppercase tracking-wider text-text-muted
                  ${col.align === "right" ? "text-right" : "text-left"}
                `}
              >
                {col.label}
              </th>
            ))}
          </tr>
        </thead>

        {/* ── Body ───────────────────────────────────────────────── */}
        <tbody>
          {items.map((item, index) => {
            const highlight = selectionHighlightMap.get(index);
            const isParent =
              item.parent_item_number === null && item.item_number != null && parentSet.has(item.item_number);
            const isEvenRow = index % 2 === 0;

            // Determine row classes based on selection state
            let rowClasses: string;
            if (highlight) {
              rowClasses = highlight.isActive
                ? ACTIVE_ROW_CLASSES[highlight.color]
                : INACTIVE_ROW_CLASSES[highlight.color];
            } else if (isParent) {
              rowClasses = "bg-bg-tertiary font-bold";
            } else {
              rowClasses = isEvenRow ? "bg-transparent" : "bg-bg-secondary/30";
            }

            const textColor = highlight?.isActive ? ACTIVE_TEXT_CLASSES[highlight.color] : "";

            return (
              <tr
                key={item.id}
                onMouseDown={(e) => handleMouseDown(index, e)}
                onMouseUp={() => handleMouseUp(index)}
                onClick={() => handleSelectionClick(index)}
                className={`
                  cursor-pointer transition-colors duration-100 border-b border-border-default/30
                  ${rowClasses}
                  ${!highlight ? "hover:bg-bg-hover" : ""}
                `}
              >
                {/* # */}
                <td className="px-3 py-1.5 font-mono text-text-muted whitespace-nowrap">
                  {item.item_number}
                </td>

                {/* Description */}
                <td
                  className={`px-3 py-1.5 whitespace-pre-wrap break-words ${
                    textColor || "text-text-primary"
                  }`}
                >
                  {item.description}
                </td>

                {/* Qty */}
                <td className="px-3 py-1.5 text-right font-mono whitespace-nowrap">
                  {item.quantity}
                </td>

                {/* Unit */}
                <td className="px-3 py-1.5 text-text-muted whitespace-nowrap">
                  {item.unit}
                </td>

                {/* Unit Price */}
                <td className="px-3 py-1.5 text-right font-mono whitespace-nowrap">
                  {formatNumber(item.unit_price)}
                </td>

                {/* Total */}
                <td
                  className={`px-3 py-1.5 text-right font-mono whitespace-nowrap ${textColor}`}
                >
                  {formatNumber(item.total)}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
});

export default SpreadsheetView;
