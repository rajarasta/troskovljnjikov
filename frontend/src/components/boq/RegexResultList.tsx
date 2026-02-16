"use client";

import { useMemo } from "react";
import { Search } from "lucide-react";
import { useSelectionStore } from "@/stores/selectionStore";
import { useMatchStore } from "@/stores/matchStore";
import ColumnHeader from "@/components/layout/ColumnHeader";
import RegexResultCard from "./RegexResultCard";

function formatNumber(value: number): string {
  return value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

export default function RegexResultList() {
  const selections = useSelectionStore((s) => s.selections);
  const activeSelectionId = useSelectionStore((s) => s.activeSelectionId);
  const { matches, stats, isSearching } = useMatchStore();

  const activeSelection = useMemo(
    () => selections.find((s) => s.id === activeSelectionId),
    [selections, activeSelectionId],
  );

  const sourceDescription = activeSelection
    ? activeSelection.items.map((i) => i.description).join(" ")
    : "";

  return (
    <div className="glass-panel flex flex-col min-h-0">
      <ColumnHeader
        title="Match Results"
        accent="purple"
        badge={matches.length > 0 ? `${matches.length}` : undefined}
      />

      {/* Stats header */}
      {stats && matches.length > 0 && (
        <div className="px-3 py-1.5 border-b border-border-default/50 flex items-center gap-3 text-[10px] text-text-muted">
          <span>AVG: <span className="text-text-primary font-mono">{formatNumber(stats.avgPrice)}</span></span>
          <span>MIN: <span className="text-text-primary font-mono">{formatNumber(stats.minPrice)}</span></span>
          <span>MAX: <span className="text-text-primary font-mono">{formatNumber(stats.maxPrice)}</span></span>
        </div>
      )}

      <div className="flex-1 overflow-y-auto p-2 space-y-2">
        {isSearching ? (
          <div className="flex items-center justify-center h-full gap-2 text-text-secondary text-xs">
            <Search className="w-4 h-4 animate-pulse text-accent-purple" />
            Searching...
          </div>
        ) : matches.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full gap-2 text-text-muted select-none">
            <Search className="w-8 h-8 opacity-40" />
            <p className="text-xs text-center">
              Select rows in Current BOQ to see matches
            </p>
          </div>
        ) : (
          matches.map((match) => (
            <RegexResultCard
              key={match.item.id}
              match={match}
              sourceDescription={sourceDescription}
            />
          ))
        )}
      </div>
    </div>
  );
}
