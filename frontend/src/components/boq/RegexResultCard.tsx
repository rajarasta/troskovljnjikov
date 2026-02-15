"use client";

import { useMemo } from "react";
import { ArrowRight } from "lucide-react";
import { useBoQStore } from "@/stores/boqStore";
import type { MatchResult } from "@/lib/types";
import { QuantityGauge } from "./QuantityGauge";

interface RegexResultCardProps {
  match: MatchResult;
  sourceDescription: string;
}

/** Highlight words in `text` that differ from `reference` */
function highlightDiffs(text: string, reference: string): React.ReactNode[] {
  const textWords = text.split(/\s+/);
  const refWords = new Set(reference.toLowerCase().split(/\s+/));
  return textWords.map((word, i) => {
    const isDiff = !refWords.has(word.toLowerCase());
    return (
      <span key={i}>
        {i > 0 && " "}
        <span className={isDiff ? "bg-accent-amber/20 text-accent-amber rounded px-0.5" : ""}>
          {word}
        </span>
      </span>
    );
  });
}

function formatNumber(value: number): string {
  return value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

export default function RegexResultCard({ match, sourceDescription }: RegexResultCardProps) {
  const updateWorkingItem = useBoQStore((s) => s.updateWorkingItem);

  const highlighted = useMemo(
    () => highlightDiffs(match.item.description, sourceDescription),
    [match.item.description, sourceDescription],
  );

  const handleApply = () => {
    updateWorkingItem(match.item.id, { unit_price: match.item.unit_price });
  };

  return (
    <div className="glass-panel p-2 rounded-lg border border-border-default/50 text-xs space-y-1.5">
      {/* Description with diffs */}
      <p className="text-text-primary leading-relaxed whitespace-pre-wrap">
        {highlighted}
      </p>

      {/* Metadata row */}
      <div className="flex items-center gap-2 text-text-muted">
        <span className="font-mono">{match.item.unit}</span>
        <span className="font-mono">{match.item.quantity}</span>
        <span className="flex-1" />
        <span className="font-mono font-semibold text-text-primary">
          {formatNumber(match.item.unit_price)}
        </span>
        <span className="font-mono">
          {formatNumber(match.item.total)}
        </span>
      </div>

      {/* Source + actions */}
      <div className="flex items-center gap-2">
        {match.item.project_name && (
          <span className="text-[10px] text-text-muted truncate">
            {match.item.project_name}
          </span>
        )}
        {match.item.date && (
          <span className="text-[10px] text-text-muted">{match.item.date}</span>
        )}
        {match.quantity_comparison && (
          <QuantityGauge comparison={match.quantity_comparison} />
        )}
        <span className="flex-1" />
        <button
          onClick={handleApply}
          className="flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-medium
                     bg-accent-cyan/10 text-accent-cyan border border-accent-cyan/20
                     hover:bg-accent-cyan/20 transition-colors"
        >
          APPLY <ArrowRight className="w-2.5 h-2.5" />
        </button>
      </div>

      {/* Similarity badge */}
      <div className="flex items-center gap-1">
        <div
          className="h-1 rounded-full bg-accent-cyan/30"
          style={{ width: `${match.similarity * 100}%` }}
        />
        <span className="text-[9px] text-text-muted font-mono">
          {(match.similarity * 100).toFixed(0)}%
        </span>
      </div>
    </div>
  );
}
