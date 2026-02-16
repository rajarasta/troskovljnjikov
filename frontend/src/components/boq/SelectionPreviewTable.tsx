"use client";

import { formatNumber } from "@/lib/boqTableConfig";
import type { BoQItem } from "@/lib/types";
import type { SelectionColor } from "@/stores/selectionStore";

interface SelectionPreviewTableProps {
  items: BoQItem[];
  color: SelectionColor;
}

// Darker border colors for selection cards
const BORDER_CLASSES: Record<SelectionColor, string> = {
  cyan: "border-l-4 border-l-accent-cyan/80",
  purple: "border-l-4 border-l-accent-purple/80",
  amber: "border-l-4 border-l-accent-amber/80",
  emerald: "border-l-4 border-l-accent-emerald/80",
  rose: "border-l-4 border-l-accent-rose/80",
  sky: "border-l-4 border-l-accent-sky/80",
};

export default function SelectionPreviewTable({ items, color }: SelectionPreviewTableProps) {
  if (items.length === 0) return null;

  return (
    <div className="flex gap-1.5 overflow-x-auto px-2 py-1.5">
      {items.map((item) => (
        <div
          key={item.id}
          className={`
            flex-shrink-0 w-auto min-w-[180px] max-w-[300px]
            bg-bg-secondary/50 rounded-md
            ${BORDER_CLASSES[color]}
            px-1.5 py-1 text-[9px] leading-tight
            hover:bg-bg-hover/50 transition-colors
          `}
        >
          {/* Header: Item Number + Unit */}
          <div className="flex items-center gap-2 mb-0.5 text-[8px]">
            {item.item_number && (
              <span className="font-mono text-text-muted">#{item.item_number}</span>
            )}
            {item.unit && (
              <span className="text-text-secondary font-mono">{item.unit}</span>
            )}
          </div>

          {/* Description */}
          <div className="text-text-primary mb-1 leading-tight">
            {item.description}
          </div>

          {/* Details: All in one line */}
          <div className="flex items-center gap-2 text-[8px] font-mono">
            <span className="text-text-primary">
              {item.quantity ? formatNumber(item.quantity) : "-"}
            </span>
            <span className="text-text-muted">×</span>
            <span className="text-text-primary">
              {item.unit_price ? formatNumber(item.unit_price) : "-"}
            </span>
            <span className="text-text-muted">=</span>
            <span className="text-text-primary font-semibold">
              {formatNumber(item.total)}
            </span>
          </div>
        </div>
      ))}
    </div>
  );
}
