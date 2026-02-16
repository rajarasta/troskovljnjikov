"use client";

import { useCallback, useMemo, forwardRef } from "react";
import { Pencil } from "lucide-react";
import { useBoQStore } from "@/stores/boqStore";
import type { BoQItem } from "@/lib/types";

// ── Helpers ──────────────────────────────────────────────────────────

function formatNumber(value: number): string {
  return value.toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

function buildParentSet(items: BoQItem[]): Set<string> {
  const parents = new Set<string>();
  for (const item of items) {
    if (item.parent_item_number) {
      parents.add(item.parent_item_number);
    }
  }
  return parents;
}

// ── Column config (matches SpreadsheetView exactly) ──────────────────

const COLUMNS = [
  { key: "item_number", label: "#", width: "60px", align: "left" as const },
  { key: "description", label: "Description", width: undefined, align: "left" as const },
  { key: "quantity", label: "Qty", width: "80px", align: "right" as const },
  { key: "unit", label: "Unit", width: "60px", align: "left" as const },
  { key: "unit_price", label: "Unit Price", width: "100px", align: "right" as const },
  { key: "total", label: "Total", width: "100px", align: "right" as const },
] as const;

// ── Editable cell ────────────────────────────────────────────────────

function EditableCell({
  value,
  itemId,
  field,
}: {
  value: number;
  itemId: string;
  field: "quantity" | "unit_price";
}) {
  const updateWorkingItem = useBoQStore((s) => s.updateWorkingItem);

  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const parsed = parseFloat(e.target.value);
      updateWorkingItem(itemId, { [field]: isNaN(parsed) ? 0 : parsed });
    },
    [itemId, field, updateWorkingItem],
  );

  return (
    <input
      type="number"
      step="any"
      value={value}
      onChange={handleChange}
      className="
        w-full bg-transparent font-mono text-xs text-right text-text-primary
        outline-none border border-transparent rounded px-1 py-0.5
        hover:border-border-default focus:border-accent-purple focus:ring-1 focus:ring-accent-purple/30
        transition-all duration-150
        [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none
      "
    />
  );
}

// ── Component ────────────────────────────────────────────────────────

const EditableSheet = forwardRef<HTMLDivElement>(function EditableSheet(_props, ref) {
  const workingItems = useBoQStore((s) => s.workingItems);
  const items = useBoQStore((s) => s.items);
  const selectedRow = useBoQStore((s) => s.selectedRow);
  const selectRow = useBoQStore((s) => s.selectRow);

  const parentSet = useMemo(() => buildParentSet(workingItems), [workingItems]);

  const handleRowClick = useCallback(
    (item: BoQItem) => {
      if (selectedRow?.id === item.id) {
        selectRow(null);
      } else {
        selectRow(item);
      }
    },
    [selectedRow, selectRow],
  );

  // ── Empty state ──────────────────────────────────────────────────

  if (workingItems.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-3 text-text-muted select-none">
        <Pencil className="w-10 h-10 opacity-40" />
        <p className="text-sm">Upload a file to view its contents</p>
      </div>
    );
  }

  // ── Table ────────────────────────────────────────────────────────

  return (
    <div ref={ref} className="h-full overflow-auto">
      <table className="w-full text-xs border-collapse">
        <colgroup>
          {COLUMNS.map((col) => (
            <col
              key={col.key}
              style={col.width ? { width: col.width, minWidth: col.width } : undefined}
              className={col.width ? undefined : "w-full"}
            />
          ))}
        </colgroup>

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

        <tbody>
          {workingItems.map((wItem, index) => {
            const originalItem = items[index];
            const isSelected = selectedRow?.id === wItem.id;
            const isParent =
              wItem.parent_item_number === null && wItem.item_number != null && parentSet.has(wItem.item_number);
            const isEvenRow = index % 2 === 0;

            // Detect if price was changed from original
            const priceChanged = originalItem && wItem.unit_price !== originalItem.unit_price;
            const totalChanged = originalItem && wItem.total !== originalItem.total;

            return (
              <tr
                key={wItem.id}
                data-row-index={index}
                onClick={() => handleRowClick(wItem)}
                className={`
                  cursor-pointer transition-colors duration-100 border-b border-border-default/30
                  ${
                    isSelected
                      ? "bg-accent-purple/10 border-l-2 border-l-accent-purple"
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
                  {wItem.item_number}
                </td>

                {/* Description */}
                <td
                  className={`px-3 py-1.5 whitespace-pre-wrap break-words ${
                    isSelected ? "text-accent-purple" : "text-text-primary"
                  }`}
                >
                  {wItem.description}
                </td>

                {/* Qty (editable) */}
                <td className="px-1 py-0.5" onClick={(e) => e.stopPropagation()}>
                  <EditableCell value={wItem.quantity} itemId={wItem.id} field="quantity" />
                </td>

                {/* Unit */}
                <td className="px-3 py-1.5 text-text-muted whitespace-nowrap">
                  {wItem.unit}
                </td>

                {/* Unit Price (editable) */}
                <td
                  className="px-1 py-0.5"
                  onClick={(e) => e.stopPropagation()}
                >
                  <EditableCell value={wItem.unit_price} itemId={wItem.id} field="unit_price" />
                  {priceChanged && (
                    <div className="text-[9px] text-accent-purple font-mono text-right px-1 -mt-0.5">
                      was {originalItem.unit_price.toFixed(2)}
                    </div>
                  )}
                </td>

                {/* Total (auto-calculated) */}
                <td
                  className={`px-3 py-1.5 text-right font-mono whitespace-nowrap ${
                    totalChanged ? "text-accent-purple" : isSelected ? "text-accent-purple" : ""
                  }`}
                >
                  {formatNumber(wItem.total)}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
});

export default EditableSheet;
