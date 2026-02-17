import { create } from "zustand";
import type {
  SearchStatus,
  WebQuote,
  ComputedTotal,
  SearchResultData,
} from "@/lib/types";

interface SearchState {
  // Per-item state
  status: Record<string, SearchStatus>;
  quotes: Record<string, WebQuote[]>;
  bestQuote: Record<string, WebQuote | null>;
  computed: Record<string, ComputedTotal | null>;
  reasoning: Record<string, string>;
  searchLog: Record<string, string[]>;

  // Actions
  setStarted: (itemId: string) => void;
  addQuote: (itemId: string, quote: WebQuote) => void;
  setComplete: (
    itemId: string,
    data: {
      quote_count: number;
      best_quote: WebQuote | null;
      computed: ComputedTotal | null;
      reasoning: string;
      error?: string;
    }
  ) => void;
  setError: (itemId: string, error: string) => void;
  clearItem: (itemId: string) => void;

  // Getters
  getResult: (itemId: string) => SearchResultData | null;
}

export const useSearchStore = create<SearchState>((set, get) => ({
  status: {},
  quotes: {},
  bestQuote: {},
  computed: {},
  reasoning: {},
  searchLog: {},

  setStarted: (itemId) => {
    set((s) => ({
      status: { ...s.status, [itemId]: "searching" },
      quotes: { ...s.quotes, [itemId]: [] },
      bestQuote: { ...s.bestQuote, [itemId]: null },
      computed: { ...s.computed, [itemId]: null },
      reasoning: { ...s.reasoning, [itemId]: "" },
      searchLog: { ...s.searchLog, [itemId]: [] },
    }));
  },

  addQuote: (itemId, quote) => {
    set((s) => ({
      quotes: {
        ...s.quotes,
        [itemId]: [...(s.quotes[itemId] || []), quote],
      },
    }));
  },

  setComplete: (itemId, data) => {
    if (data.error) {
      set((s) => ({
        status: { ...s.status, [itemId]: "error" },
        reasoning: { ...s.reasoning, [itemId]: data.error || "" },
      }));
    } else {
      set((s) => ({
        status: { ...s.status, [itemId]: "done" },
        bestQuote: { ...s.bestQuote, [itemId]: data.best_quote },
        computed: { ...s.computed, [itemId]: data.computed },
        reasoning: { ...s.reasoning, [itemId]: data.reasoning },
      }));
    }
  },

  setError: (itemId, error) => {
    set((s) => ({
      status: { ...s.status, [itemId]: "error" },
      reasoning: { ...s.reasoning, [itemId]: error },
    }));
  },

  clearItem: (itemId) => {
    set((s) => {
      const newStatus = { ...s.status };
      delete newStatus[itemId];
      const newQuotes = { ...s.quotes };
      delete newQuotes[itemId];
      const newBest = { ...s.bestQuote };
      delete newBest[itemId];
      const newComputed = { ...s.computed };
      delete newComputed[itemId];
      const newReasoning = { ...s.reasoning };
      delete newReasoning[itemId];
      return {
        status: newStatus,
        quotes: newQuotes,
        bestQuote: newBest,
        computed: newComputed,
        reasoning: newReasoning,
      };
    });
  },

  getResult: (itemId) => {
    const s = get();
    if (!s.status[itemId] || s.status[itemId] === "idle") return null;
    return {
      quotes: s.quotes[itemId] || [],
      best_quote: s.bestQuote[itemId] || null,
      computed: s.computed[itemId] || null,
      reasoning: s.reasoning[itemId] || "",
      search_log: s.searchLog[itemId] || [],
    };
  },
}));
