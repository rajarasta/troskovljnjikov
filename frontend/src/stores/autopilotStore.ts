import { create } from "zustand";
import type {
  AutopilotMatchResult,
  AutopilotStatus,
  ConfidenceTier,
  PriceSuggestion,
} from "@/lib/types";

interface AutopilotState {
  // Per-file processing state
  status: Record<string, AutopilotStatus>;
  progress: Record<string, { current: number; total: number }>;

  // Cached results (populated from WS events)
  matchCache: Record<string, Record<string, AutopilotMatchResult[]>>;
  priceCache: Record<string, Record<string, PriceSuggestion>>;
  confidences: Record<string, Record<string, ConfidenceTier>>;

  // Summary streaming
  summaryTokens: Record<string, string>;
  summaryDone: Record<string, boolean>;

  // Completion stats
  completionStats: Record<string, {
    total_items: number;
    matched_items: number;
    priced_items: number;
    high_confidence: number;
    medium_confidence: number;
    low_confidence: number;
  }>;

  // Errors
  errors: Record<string, string>;

  // Actions
  appendSummaryToken: (fileId: string, token: string, done: boolean) => void;
  setProgress: (fileId: string, current: number, total: number) => void;
  setStatus: (fileId: string, status: AutopilotStatus) => void;
  addMatchResult: (fileId: string, itemId: string, confidence: ConfidenceTier) => void;
  addPriceSuggestion: (fileId: string, itemId: string, suggestion: PriceSuggestion) => void;
  setComplete: (fileId: string, stats: AutopilotState["completionStats"][string]) => void;
  setError: (fileId: string, error: string) => void;

  // Getters
  getCachedMatches: (fileId: string, itemId: string) => AutopilotMatchResult[] | null;
  getCachedPrice: (fileId: string, itemId: string) => PriceSuggestion | null;
  getConfidence: (fileId: string, itemId: string) => ConfidenceTier | null;
}

export const useAutopilotStore = create<AutopilotState>((set, get) => ({
  status: {},
  progress: {},
  errors: {},
  matchCache: {},
  priceCache: {},
  confidences: {},
  summaryTokens: {},
  summaryDone: {},
  completionStats: {},

  appendSummaryToken: (fileId, token, done) => {
    set((s) => ({
      summaryTokens: {
        ...s.summaryTokens,
        [fileId]: (s.summaryTokens[fileId] || "") + token,
      },
      summaryDone: { ...s.summaryDone, [fileId]: done },
      status: { ...s.status, [fileId]: done ? s.status[fileId] : "summarizing" },
    }));
  },

  setProgress: (fileId, current, total) => {
    set((s) => ({
      progress: { ...s.progress, [fileId]: { current, total } },
    }));
  },

  setStatus: (fileId, status) => {
    set((s) => ({
      status: { ...s.status, [fileId]: status },
    }));
  },

  addMatchResult: (fileId, itemId, confidence) => {
    set((s) => ({
      confidences: {
        ...s.confidences,
        [fileId]: { ...(s.confidences[fileId] || {}), [itemId]: confidence },
      },
    }));
  },

  addPriceSuggestion: (fileId, itemId, suggestion) => {
    set((s) => ({
      priceCache: {
        ...s.priceCache,
        [fileId]: { ...(s.priceCache[fileId] || {}), [itemId]: suggestion },
      },
    }));
  },

  setComplete: (fileId, stats) => {
    set((s) => ({
      status: { ...s.status, [fileId]: "done" },
      completionStats: { ...s.completionStats, [fileId]: stats },
    }));
  },

  setError: (fileId, error) => {
    set((s) => ({
      status: { ...s.status, [fileId]: "error" },
      errors: { ...s.errors, [fileId]: error },
    }));
  },

  getCachedMatches: (fileId, itemId) => {
    return get().matchCache[fileId]?.[itemId] ?? null;
  },

  getCachedPrice: (fileId, itemId) => {
    return get().priceCache[fileId]?.[itemId] ?? null;
  },

  getConfidence: (fileId, itemId) => {
    return get().confidences[fileId]?.[itemId] ?? null;
  },
}));
