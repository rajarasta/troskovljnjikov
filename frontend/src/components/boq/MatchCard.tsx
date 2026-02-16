"use client";

import { useCallback } from "react";
import { motion } from "framer-motion";
import { Check } from "lucide-react";
import { useBoQStore } from "@/stores/boqStore";
import type { MatchResult } from "@/lib/types";

interface MatchCardProps {
  match: MatchResult;
  index: number;
  onClick?: () => void;
}

function getSimilarityColor(similarity: number): {
  bg: string;
  text: string;
  border: string;
} {
  if (similarity > 0.8) {
    return {
      bg: "bg-status-success/15",
      text: "text-status-success",
      border: "border-status-success/30",
    };
  }
  if (similarity > 0.5) {
    return {
      bg: "bg-status-warning/15",
      text: "text-status-warning",
      border: "border-status-warning/30",
    };
  }
  return {
    bg: "bg-status-danger/15",
    text: "text-status-danger",
    border: "border-status-danger/30",
  };
}

export function MatchCard({ match, index, onClick }: MatchCardProps) {
  const { item, similarity, quantity_comparison } = match;
  const pct = (similarity * 100).toFixed(0);
  const colors = getSimilarityColor(similarity);

  const selectedRow = useBoQStore((s) => s.selectedRow);
  const updateWorkingItem = useBoQStore((s) => s.updateWorkingItem);

  const handleApply = useCallback(
    (e: React.MouseEvent) => {
      e.stopPropagation();
      if (!selectedRow) return;
      updateWorkingItem(selectedRow.id, { unit_price: item.unit_price });
    },
    [selectedRow, updateWorkingItem, item.unit_price],
  );

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2, delay: index * 0.05 }}
      onClick={onClick}
      className="group flex flex-col gap-1.5 px-2.5 py-2 rounded cursor-pointer
                 transition-colors duration-150 hover:bg-bg-hover/60 hover:backdrop-blur-sm
                 border border-transparent hover:border-border-default"
    >
      {/* Top row: similarity + price + apply */}
      <div className="flex items-center gap-2">
        {/* Similarity badge */}
        <span
          className={`shrink-0 inline-flex items-center justify-center w-10 h-5
                       rounded text-[10px] font-semibold font-mono border
                       ${colors.bg} ${colors.text} ${colors.border}`}
        >
          {pct}%
        </span>

        {/* Project name */}
        <span className="text-[10px] text-accent-purple bg-accent-purple/10 px-1.5 py-0 rounded">
          {item.project_name}
        </span>

        <div className="flex-1" />

        {/* Price + unit */}
        <span className="text-xs font-mono text-text-primary">
          {item.unit_price.toFixed(2)}
        </span>
        <span className="text-[10px] text-text-muted">{item.unit}</span>

        {/* Apply button */}
        {selectedRow && (
          <button
            onClick={handleApply}
            className="shrink-0 flex items-center gap-0.5 px-1.5 py-0.5 rounded text-[10px]
                       text-accent-purple border border-accent-purple/30
                       hover:bg-accent-purple/10 hover:border-accent-purple/60
                       transition-all duration-150 opacity-0 group-hover:opacity-100"
            title="Apply this price to working copy"
          >
            <Check className="w-3 h-3" />
            Apply
          </button>
        )}
      </div>

      {/* Description */}
      <p className="text-xs text-text-primary leading-tight whitespace-pre-wrap break-words">
        {item.description}
      </p>

      {/* Quantity comparison */}
      {quantity_comparison?.hasData && (
        <div className="flex items-center gap-1 text-[10px]">
          <span
            className="w-1.5 h-1.5 rounded-full shrink-0"
            style={{ backgroundColor: quantity_comparison.color }}
          />
          <span className="text-text-muted">{quantity_comparison.label}</span>
        </div>
      )}
    </motion.div>
  );
}
