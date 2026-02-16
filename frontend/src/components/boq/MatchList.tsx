"use client";

import { motion, AnimatePresence } from "framer-motion";
import { Loader2, Search, TrendingUp } from "lucide-react";
import { useMatchStore } from "@/stores/matchStore";
import { MatchCard } from "./MatchCard";
import type { MatchStats } from "@/lib/types";

// ── Stats Header ────────────────────────────────────────────────────

function StatsHeader({ stats }: { stats: MatchStats }) {
  const { minPrice, maxPrice, avgPrice, count, priceRange } = stats;

  // Position of average within min-max range (clamped 0-100)
  const avgPosition =
    priceRange > 0
      ? Math.min(100, Math.max(0, ((avgPrice - minPrice) / priceRange) * 100))
      : 50;

  return (
    <div className="px-3 py-2.5 border-b border-border-default space-y-2">
      {/* Top row: count + price summary */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1.5">
          <TrendingUp className="w-3 h-3 text-accent-cyan" />
          <span className="text-[10px] text-text-muted uppercase tracking-wider font-semibold">
            {count} matches
          </span>
        </div>
        <span className="text-[10px] text-text-muted font-mono">
          avg {avgPrice.toFixed(2)}
        </span>
      </div>

      {/* Price range visualization */}
      <div className="relative">
        {/* Min/max labels */}
        <div className="flex justify-between text-[9px] text-text-muted font-mono mb-1">
          <span>{minPrice.toFixed(2)}</span>
          <span>{maxPrice.toFixed(2)}</span>
        </div>

        {/* Track */}
        <div className="relative h-1.5 rounded-full bg-bg-tertiary overflow-hidden">
          {/* Full range fill */}
          <div className="absolute inset-0 bg-gradient-to-r from-accent-purple/40 to-accent-cyan/40 rounded-full" />
        </div>

        {/* Average marker */}
        <div
          className="absolute bottom-0 w-px h-3 bg-accent-cyan"
          style={{ left: `${avgPosition}%` }}
        >
          <div className="absolute -top-3.5 left-1/2 -translate-x-1/2 text-[8px] text-accent-cyan font-mono whitespace-nowrap">
            avg
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Main Component ──────────────────────────────────────────────────

export function MatchList() {
  const { matches, stats, isSearching } = useMatchStore();

  return (
    <div className="flex flex-col min-h-0 h-full">
      {/* Loading state */}
      <AnimatePresence mode="wait">
        {isSearching && (
          <motion.div
            key="loading"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="flex items-center gap-2 px-3 py-4 text-sm text-text-secondary"
          >
            <Loader2 className="w-4 h-4 animate-spin text-accent-purple" />
            <span className="text-xs">Searching matches...</span>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Empty state */}
      {!isSearching && matches.length === 0 && (
        <div className="flex flex-col items-center justify-center flex-1 gap-2 px-4 py-8">
          <Search className="w-5 h-5 text-text-muted/50" />
          <p className="text-xs text-text-muted text-center leading-relaxed">
            Select a row to find matching items across projects
          </p>
        </div>
      )}

      {/* Stats header */}
      {!isSearching && stats && matches.length > 0 && (
        <StatsHeader stats={stats} />
      )}

      {/* Scrollable results list */}
      {!isSearching && matches.length > 0 && (
        <div className="flex-1 overflow-y-auto">
          <div className="flex flex-col py-1">
            {matches.map((match, i) => (
              <MatchCard
                key={`${match.item.id}-${i}`}
                match={match}
                index={i}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
