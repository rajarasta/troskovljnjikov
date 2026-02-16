import { create } from "zustand";
import type { MatchResult, MatchStats } from "@/lib/types";
import * as api from "@/lib/api";

interface MatchState {
  // ── State ───────────────────────────────────────────────────────
  matches: MatchResult[];
  stats: MatchStats | null;
  isSearching: boolean;
  error: string | null;

  // ── Actions ─────────────────────────────────────────────────────
  startLookup: (description: string, quantity?: number) => Promise<void>;
  clearMatches: () => void;
}

export const useMatchStore = create<MatchState>((set) => ({
  matches: [],
  stats: null,
  isSearching: false,
  error: null,

  startLookup: async (description: string, quantity?: number) => {
    set({ isSearching: true, error: null });
    try {
      const response = await api.matchItems(description, quantity);
      set({
        matches: response.matches,
        stats: response.stats,
        isSearching: false,
      });
    } catch (err) {
      set({
        isSearching: false,
        error: err instanceof Error ? err.message : "Match lookup failed",
      });
    }
  },

  clearMatches: () => {
    set({ matches: [], stats: null, error: null });
  },
}));
