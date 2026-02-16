"use client";

import ColumnHeader from "@/components/layout/ColumnHeader";
import { MatchList } from "./MatchList";
import { useMatchStore } from "@/stores/matchStore";

export default function MatchResultsPanel() {
  const { matches } = useMatchStore();

  return (
    <div className="glass-panel flex flex-col min-h-0 h-full">
      <ColumnHeader
        title="Matches"
        accent="purple"
        badge={matches.length > 0 ? `${matches.length}` : undefined}
      />
      <div className="flex-1 min-h-0">
        <MatchList />
      </div>
    </div>
  );
}
