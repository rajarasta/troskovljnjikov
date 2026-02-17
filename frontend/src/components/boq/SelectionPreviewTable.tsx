"use client";

import { formatNumber } from "@/lib/boqTableConfig";
import type { BoQItem } from "@/lib/types";
import type { SelectionColor } from "@/stores/selectionStore";

interface SelectionPreviewTableProps {
  items: BoQItem[];
  color: SelectionColor;
}

const BORDER_CLASSES: Record<SelectionColor, string> = {
  cyan: "border-l-2 border-l-accent-cyan",
  purple: "border-l-2 border-l-accent-purple",
  amber: "border-l-2 border-l-accent-amber",
  emerald: "border-l-2 border-l-accent-emerald",
  rose: "border-l-2 border-l-accent-rose",
  sky: "border-l-2 border-l-accent-sky",
};

export default function SelectionPreviewTable({ items, color }: SelectionPreviewTableProps) {
  if (items.length === 0) return null;

  return (
    <table className={`w-full text-[10px] border-collapse ${BORDER_CLASSES[color]}`}>
      <thead>
        <tr className="bg-bg-secondary/60">
          <th className="px-1.5 py-1 text-left font-semibold text-text-muted w-[40px]">#</th>
          <th className="px-1.5 py-1 text-left font-semibold text-text-muted">Opis</th>
          <th className="px-1.5 py-1 text-left font-semibold text-text-muted w-[30px]">JM</th>
          <th className="px-1.5 py-1 text-right font-semibold text-text-muted w-[50px]">Kol.</th>
          <th className="px-1.5 py-1 text-right font-semibold text-text-muted w-[60px]">JC</th>
          <th className="px-1.5 py-1 text-right font-semibold text-text-muted w-[60px]">Ukupno</th>
        </tr>
      </thead>
      <tbody>
        {items.map((item) => {
          const isHeader = item.item_type === "section_header";
          if (isHeader) {
            return (
              <tr key={item.id} className="bg-accent-cyan/10">
                <td className="px-1.5 py-1 font-mono text-text-muted">{item.item_number ?? ""}</td>
                <td colSpan={5} className="px-1.5 py-1 font-semibold text-text-primary">
                  {item.description}
                </td>
              </tr>
            );
          }
          return (
            <tr key={item.id} className="border-t border-border-default/30 hover:bg-bg-hover/30">
              <td className="px-1.5 py-1 font-mono text-text-muted align-top whitespace-nowrap">{item.item_number ?? ""}</td>
              <td className="px-1.5 py-1 text-text-primary whitespace-pre-wrap break-words">{item.full_description || item.description}</td>
              <td className="px-1.5 py-1 text-text-muted align-top whitespace-nowrap">{item.unit ?? ""}</td>
              <td className="px-1.5 py-1 text-right font-mono text-text-primary align-top whitespace-nowrap">{formatNumber(item.quantity)}</td>
              <td className="px-1.5 py-1 text-right font-mono text-text-primary align-top whitespace-nowrap">{item.unit_price ? formatNumber(item.unit_price) : ""}</td>
              <td className="px-1.5 py-1 text-right font-mono text-text-primary align-top whitespace-nowrap">{item.total ? formatNumber(item.total) : ""}</td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}
