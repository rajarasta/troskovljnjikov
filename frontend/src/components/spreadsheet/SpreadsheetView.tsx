"use client";

import { useMemo, useCallback, forwardRef } from "react";
import { FileSpreadsheet } from "lucide-react";
import { useBoQStore } from "@/stores/boqStore";
import { useMatchStore } from "@/stores/matchStore";
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
  const selectedRow = useBoQStore((s) => s.selectedRow);
  const selectRow = useBoQStore((s) => s.selectRow);
  const startLookup = useMatchStore((s) => s.startLookup);
  const clearMatches = useMatchStore((s) => s.clearMatches);

  const parentSet = useMemo(() => buildParentSet(items), [items]);

  const handleRowClick = useCallback(
    (item: BoQItem) => {
      if (selectedRow?.id === item.id) {
        // Deselect on second click
        selectRow(null);
        clearMatches();
      } else {
        selectRow(item);
        startLookup(item.description, item.quantity);
      }
    },
    [selectedRow, selectRow, startLookup, clearMatches],
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
    <div ref={ref} className="h-full overflow-auto">
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
            const isSelected = selectedRow?.id === item.id;
            const isParent =
              item.parent_item_number === null && item.item_number != null && parentSet.has(item.item_number);
            const isEvenRow = index % 2 === 0;

            return (
              <tr
                key={item.id}
                onClick={() => handleRowClick(item)}
                className={`
                  cursor-pointer transition-colors duration-100 border-b border-border-default/30
                  ${
                    isSelected
                      ? "bg-accent-cyan/10 border-l-2 border-l-accent-cyan"
                      : isParent
                        ? "bg-bg-tertiary font-bold"
                        : isEvenRow
                          ? "bg-transparent"
                          : "bg-bg-secondary/30"
                  }
                  ${!isSelected ? "hover:bg-bg-hover" : ""}
                `}
              >
                {/* # */}
                <td className="px-3 py-1.5 font-mono text-text-muted whitespace-nowrap">
                  {item.item_number}
                </td>

                {/* Description */}
                <td
                  className={`px-3 py-1.5 whitespace-pre-wrap break-words ${
                    isSelected ? "text-accent-cyan" : "text-text-primary"
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
                  className={`px-3 py-1.5 text-right font-mono whitespace-nowrap ${
                    isSelected ? "text-accent-cyan" : ""
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
