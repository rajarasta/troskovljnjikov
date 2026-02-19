import { create } from "zustand";
import type { MatchResult, MatchStats, MatchGroup } from "@/lib/types";
import * as api from "@/lib/api";

/** Per-selection match results */
export interface SelectionMatchState {
  matches: MatchResult[];
  stats: MatchStats | null;
  isSearching: boolean;
  error: string | null;
  groups: MatchGroup[] | null;
  isComposite: boolean;
  parentDescription: string | null;
}

interface MatchState {
  // ── State ───────────────────────────────────────────────────────
  /** Match results keyed by selection ID */
  resultsBySelection: Record<string, SelectionMatchState>;

  // ── Actions ─────────────────────────────────────────────────────
  startLookup: (
    selectionId: string,
    description: string,
    quantity?: number,
    fileId?: string,
    startRow?: number,
    endRow?: number,
  ) => Promise<void>;
  /** Populate results from autopilot cache without API call */
  setCachedResults: (selectionId: string, matches: MatchResult[], stats?: MatchStats | null) => void;
  clearSelection: (selectionId: string) => void;
  clearAll: () => void;
}

const emptyResult: SelectionMatchState = {
  matches: [],
  stats: null,
  isSearching: false,
  error: null,
  groups: null,
  isComposite: false,
  parentDescription: null,
};

export const useMatchStore = create<MatchState>((set, get) => ({
  resultsBySelection: {},

  startLookup: async (
    selectionId: string,
    description: string,
    quantity?: number,
    fileId?: string,
    startRow?: number,
    endRow?: number,
  ) => {
    // Mark this selection as searching
    set((s) => ({
      resultsBySelection: {
        ...s.resultsBySelection,
        [selectionId]: {
          ...(s.resultsBySelection[selectionId] ?? emptyResult),
          isSearching: true,
          error: null,
        },
      },
    }));

    try {
      const response = await api.matchItems(
        description, quantity, undefined, fileId, startRow, endRow,
      );
      // Only update if selection still exists (wasn't removed while searching)
      const current = get().resultsBySelection[selectionId];
      if (current) {
        set((s) => ({
          resultsBySelection: {
            ...s.resultsBySelection,
            [selectionId]: {
              matches: response.matches,
              stats: response.stats,
              isSearching: false,
              error: null,
              groups: response.groups ?? null,
              isComposite: response.is_composite ?? false,
              parentDescription: response.parent_description ?? null,
            },
          },
        }));
      }
    } catch (err) {
      const current = get().resultsBySelection[selectionId];
      if (current) {
        set((s) => ({
          resultsBySelection: {
            ...s.resultsBySelection,
            [selectionId]: {
              ...(s.resultsBySelection[selectionId] ?? emptyResult),
              isSearching: false,
              error: err instanceof Error ? err.message : "Match lookup failed",
            },
          },
        }));
      }
    }
  },

  setCachedResults: (selectionId, matches, stats) => {
    const prices = matches
      .map((m) => m.item.unit_price)
      .filter((p) => p > 0);
    const computedStats: MatchStats = stats ?? {
      count: prices.length,
      avgPrice: prices.length ? prices.reduce((a, b) => a + b, 0) / prices.length : 0,
      minPrice: prices.length ? Math.min(...prices) : 0,
      maxPrice: prices.length ? Math.max(...prices) : 0,
      priceRange: prices.length ? Math.max(...prices) - Math.min(...prices) : 0,
      statusCounts: {},
    };
    set((s) => ({
      resultsBySelection: {
        ...s.resultsBySelection,
        [selectionId]: {
          matches,
          stats: computedStats,
          isSearching: false,
          error: null,
          groups: null,
          isComposite: false,
          parentDescription: null,
        },
      },
    }));
  },

  clearSelection: (selectionId: string) => {
    set((s) => {
      const { [selectionId]: _, ...rest } = s.resultsBySelection;
      return { resultsBySelection: rest };
    });
  },

  clearAll: () => {
    set({ resultsBySelection: {} });
  },
}));
