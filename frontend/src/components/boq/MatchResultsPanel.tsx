"use client";

import { useState } from "react";
import { Search, WrapText } from "lucide-react";
import { useSelectionStore } from "@/stores/selectionStore";
import { useMatchStore } from "@/stores/matchStore";
import { formatNumber } from "@/lib/boqTableConfig";
import ColumnHeader from "@/components/layout/ColumnHeader";
import MatchResultsTable from "./MatchResultsTable";


export default function MatchResultsPanel() {
  const activeSelectionId = useSelectionStore((s) => s.activeSelectionId);
  const selections = useSelectionStore((s) => s.selections);
  const resultsBySelection = useMatchStore((s) => s.resultsBySelection);
  const [wrapText, setWrapText] = useState(true);

  const activeSelection = activeSelectionId
    ? selections.find((s) => s.id === activeSelectionId)
    : undefined;

  const activeResult = activeSelectionId
    ? resultsBySelection[activeSelectionId]
    : undefined;

  const matches = activeResult?.matches ?? [];
  const stats = activeResult?.stats ?? null;
  const isSearching = activeResult?.isSearching ?? false;
  const groups = activeResult?.groups ?? null;
  const isComposite = activeResult?.isComposite ?? false;
  const parentDescription = activeResult?.parentDescription ?? null;

  const totalMatchCount = isComposite && groups
    ? groups.reduce((sum, g) => sum + g.matches.length, 0)
    : matches.length;
  const hasResults = totalMatchCount > 0;

  const hasSelection = activeSelection && activeSelection.items.length > 0;

  return (
    <div className="flex flex-col gap-2 h-full min-h-0">
      {/* Panel 1: Selection preview */}
      {hasSelection && (
        <div className="glass-panel flex flex-col min-h-0 shrink-0 max-h-[50%] overflow-hidden">
          <ColumnHeader
            title="Odabir"
            accent="cyan"
            badge={`${activeSelection.items.length}`}
          />
          <div className="flex-1 overflow-y-auto min-h-0 px-2.5 py-1.5">
            {activeSelection.items.map((item) => {
              const desc = item.description?.trim();
              if (!desc) return null;
              const hasQty = item.quantity != null && item.quantity > 0;
              const hasPrice = item.unit_price != null && item.unit_price > 0;
              return (
                <div key={item.id} className="flex items-baseline gap-1.5 text-[11px] leading-snug py-0.5">
                  {item.item_number && (
                    <span className="font-mono text-text-muted shrink-0">{item.item_number}</span>
                  )}
                  <span className="text-text-primary truncate">{desc}</span>
                  {(hasQty || item.unit || hasPrice) && (
                    <span className="text-text-muted shrink-0 ml-auto font-mono">
                      {hasQty ? formatNumber(item.quantity) : ""}
                      {item.unit ? ` ${item.unit}` : ""}
                      {hasPrice ? ` @ ${formatNumber(item.unit_price)}` : ""}
                    </span>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Panel 2: Match results */}
      <div className="glass-panel flex flex-col min-h-0 flex-1 overflow-hidden">
        <ColumnHeader
          title="Match Results"
          accent="purple"
          badge={hasResults ? `${totalMatchCount}` : undefined}
          actions={
            <button
              onClick={() => setWrapText((w) => !w)}
              title={wrapText ? "Compact (no wrap)" : "Wrap text"}
              className={`p-1 rounded transition-colors ${
                wrapText
                  ? "bg-accent-purple/15 text-accent-purple"
                  : "text-text-muted hover:text-text-secondary"
              }`}
            >
              <WrapText className="w-3.5 h-3.5" />
            </button>
          }
        />

        {/* Stats header */}
        {stats && hasResults && (
          <div className="shrink-0 px-3 py-1.5 border-b border-border-default/50 flex items-center gap-3 text-[10px] text-text-muted">
            <span>AVG: <span className="text-text-primary font-mono">{formatNumber(stats.avgPrice ?? 0)}</span></span>
            <span>MIN: <span className="text-text-primary font-mono">{formatNumber(stats.minPrice ?? 0)}</span></span>
            <span>MAX: <span className="text-text-primary font-mono">{formatNumber(stats.maxPrice ?? 0)}</span></span>
          </div>
        )}

        <div className="flex-1 overflow-y-auto min-h-0">
          {isSearching ? (
            <div className="flex items-center justify-center h-full gap-2 text-text-secondary text-xs">
              <Search className="w-4 h-4 animate-pulse text-accent-purple" />
              Searching...
            </div>
          ) : !hasResults ? (
            <div className="flex flex-col items-center justify-center h-full gap-2 text-text-muted select-none">
              <Search className="w-8 h-8 opacity-40" />
              <p className="text-xs text-center">
                Select rows in Current BOQ to see matches
              </p>
            </div>
          ) : (
            <MatchResultsTable
              matches={matches}
              wrapText={wrapText}
              groups={groups}
              isComposite={isComposite}
              parentDescription={parentDescription}
              refQty={activeSelection?.items[0]?.quantity ?? null}
              refPrice={activeSelection?.items[0]?.unit_price ?? null}
            />
          )}
        </div>
      </div>
    </div>
  );
}
