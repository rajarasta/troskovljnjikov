"use client";

import { useMemo, useCallback, forwardRef } from "react";
import { FileSpreadsheet } from "lucide-react";
import { useBoQStore } from "@/stores/boqStore";
import { useSelectionStore } from "@/stores/selectionStore";
import { useClipboardStore } from "@/stores/clipboardStore";
import { useAutopilotStore } from "@/stores/autopilotStore";
import { BOQ_COLUMNS, formatNumber } from "@/lib/boqTableConfig";
import { EditableDescriptionCell } from "./EditableDescriptionCell";
import { EditableCell } from "./EditableCell";
import type { SelectionColor } from "@/stores/selectionStore";
import type { BoQItem, ConfidenceTier } from "@/lib/types";

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

// ── Confidence badge ──────────────────────────────────────────────────

const CONFIDENCE_DOT_CLASSES: Record<ConfidenceTier, string> = {
  high: "bg-status-success",
  medium: "bg-status-warning",
  low: "bg-status-danger",
};

const CONFIDENCE_LABELS: Record<ConfidenceTier, string> = {
  high: "High confidence match",
  medium: "Needs review",
  low: "No good match",
};

// ── Component ────────────────────────────────────────────────────────

const SpreadsheetView = forwardRef<HTMLDivElement>(function SpreadsheetView(_props, ref) {
  const items = useBoQStore((s) => s.items);
  const workingItems = useBoQStore((s) => s.workingItems);
  const selectedFileId = useBoQStore((s) => s.selectedFileId);
  const confidences = useAutopilotStore((s) => selectedFileId ? s.confidences[selectedFileId] : undefined);

  const selections = useSelectionStore((s) => s.selections);
  const activeSelectionId = useSelectionStore((s) => s.activeSelectionId);
  const addSelection = useSelectionStore((s) => s.addSelection);
  const setActive = useSelectionStore((s) => s.setActive);
  const setDragAnchor = useSelectionStore((s) => s.setDragAnchor);
  const dragAnchorIndex = useSelectionStore((s) => s.dragAnchorIndex);

  const pickedValue = useClipboardStore((s) => s.pickedValue);
  const clearPicked = useClipboardStore((s) => s.clearPicked);
  const updateWorkingItem = useBoQStore((s) => s.updateWorkingItem);

  const parentSet = useMemo(() => buildParentSet(items), [items]);

  // Use workingItems for display (editable copy), fall back to items
  const displayItems = workingItems.length > 0 ? workingItems : items;

  // Build a lookup map: row index -> { color, isActive } for highlighting.
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
        const start = Math.min(dragAnchorIndex, index);
        const end = Math.max(dragAnchorIndex, index);
        addSelection(start, end, items.slice(start, end + 1));
        setDragAnchor(null);
      } else {
        setDragAnchor(index);
      }
    },
    [dragAnchorIndex, addSelection, items, setDragAnchor],
  );

  const handleMouseUp = useCallback(
    (index: number) => {
      if (dragAnchorIndex !== null && dragAnchorIndex !== index) {
        const start = Math.min(dragAnchorIndex, index);
        const end = Math.max(dragAnchorIndex, index);
        addSelection(start, end, items.slice(start, end + 1));
        setDragAnchor(null);
      }
      if (dragAnchorIndex !== null && dragAnchorIndex === index) {
        addSelection(index, index, items.slice(index, index + 1));
        setDragAnchor(null);
      }
    },
    [dragAnchorIndex, addSelection, items, setDragAnchor],
  );

  const handleSelectionClick = useCallback(
    (index: number) => {
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
          {BOQ_COLUMNS.map((col) => (
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
            {BOQ_COLUMNS.map((col) => (
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
          {displayItems.map((item, index) => {
            const originalItem = items[index];
            const highlight = selectionHighlightMap.get(index);
            const isParent =
              item.parent_item_number === null && item.item_number != null && parentSet.has(item.item_number);
            const isEvenRow = index % 2 === 0;

            // Detect edits
            const priceChanged = originalItem && item.unit_price !== originalItem.unit_price;
            const totalChanged = originalItem && item.total !== originalItem.total;

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
                data-row-index={index}
                onMouseDown={(e) => handleMouseDown(index, e)}
                onMouseUp={() => handleMouseUp(index)}
                onClick={() => handleSelectionClick(index)}
                className={`
                  cursor-pointer transition-colors duration-100 border-b border-border-default/30
                  ${rowClasses}
                  ${!highlight ? "hover:bg-bg-hover" : ""}
                `}
              >
                {/* # + confidence dot */}
                <td className="px-3 py-1.5 font-mono text-text-muted whitespace-nowrap align-top">
                  <span className="inline-flex items-center gap-1.5">
                    {confidences?.[item.id] && (
                      <span
                        className={`inline-block w-1.5 h-1.5 rounded-full shrink-0 ${CONFIDENCE_DOT_CLASSES[confidences[item.id]]}`}
                        title={CONFIDENCE_LABELS[confidences[item.id]]}
                      />
                    )}
                    {item.item_number}
                  </span>
                </td>

                {/* Description — editable with inline autocomplete */}
                <td
                  className="px-3 py-1.5 align-top"
                  onClick={(e) => e.stopPropagation()}
                >
                  <EditableDescriptionCell
                    value={item.description}
                    itemId={item.id}
                    textColor={textColor || undefined}
                    context={displayItems
                      .slice(Math.max(0, index - 2), index + 3)
                      .filter((i) => i.id !== item.id)
                      .map((i) => ({ item_number: i.item_number, description: i.description }))}
                    onCommit={(id, newDesc) => updateWorkingItem(id, { description: newDesc })}
                  />
                </td>

                {/* Unit */}
                <td className="px-3 py-1.5 text-text-muted whitespace-nowrap align-top">
                  {item.unit}
                </td>

                {/* Qty (editable / paste target) */}
                <td
                  className={`px-1 py-0.5 align-top ${
                    pickedValue?.field === "quantity" ? "cursor-copy" : ""
                  }`}
                  onClick={(e) => {
                    if (pickedValue?.field === "quantity") {
                      e.stopPropagation();
                      const val = typeof pickedValue.value === "number"
                        ? pickedValue.value
                        : parseFloat(String(pickedValue.value)) || 0;
                      updateWorkingItem(item.id, { quantity: val });
                      clearPicked();
                    } else {
                      e.stopPropagation();
                    }
                  }}
                >
                  <EditableCell value={item.quantity} itemId={item.id} field="quantity" />
                </td>

                {/* Unit Price (editable / paste target) */}
                <td
                  className={`px-1 py-0.5 align-top ${
                    pickedValue?.field === "unit_price" ? "cursor-copy" : ""
                  }`}
                  onClick={(e) => {
                    if (pickedValue?.field === "unit_price") {
                      e.stopPropagation();
                      const val = typeof pickedValue.value === "number"
                        ? pickedValue.value
                        : parseFloat(String(pickedValue.value)) || 0;
                      updateWorkingItem(item.id, { unit_price: val });
                      clearPicked();
                    } else {
                      e.stopPropagation();
                    }
                  }}
                >
                  <EditableCell value={item.unit_price} itemId={item.id} field="unit_price" />
                  {priceChanged && originalItem && (
                    <div className="text-[9px] text-accent-purple font-mono text-right px-1 -mt-0.5">
                      was {originalItem.unit_price.toFixed(2)}
                    </div>
                  )}
                </td>

                {/* Total (auto-calculated) */}
                <td
                  className={`px-3 py-1.5 text-right font-mono whitespace-nowrap align-top ${
                    totalChanged ? "text-accent-purple" : textColor
                  }`}
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
