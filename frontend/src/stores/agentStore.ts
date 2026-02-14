import { create } from 'zustand';
import type { HistoricMatchEvent, LineSuggestion } from '../api/types';

interface AgentStore {
  isProcessing: boolean;
  currentUnitId: string | null;
  reasoning: string;
  historicMatches: HistoricMatchEvent[];
  suggestions: Map<string, LineSuggestion>;

  startProcessing: (unitId: string) => void;
  appendReasoning: (text: string) => void;
  addHistoricMatch: (match: HistoricMatchEvent) => void;
  addSuggestion: (suggestion: LineSuggestion) => void;
  finishProcessing: () => void;
  reset: () => void;
}

export const useAgentStore = create<AgentStore>((set) => ({
  isProcessing: false,
  currentUnitId: null,
  reasoning: '',
  historicMatches: [],
  suggestions: new Map(),

  startProcessing: (unitId) =>
    set({
      isProcessing: true,
      currentUnitId: unitId,
      reasoning: '',
      historicMatches: [],
      suggestions: new Map(),
    }),

  appendReasoning: (text) =>
    set((state) => ({ reasoning: state.reasoning + text })),

  addHistoricMatch: (match) =>
    set((state) => ({ historicMatches: [...state.historicMatches, match] })),

  addSuggestion: (suggestion) =>
    set((state) => {
      const newMap = new Map(state.suggestions);
      newMap.set(suggestion.item_number, suggestion);
      return { suggestions: newMap };
    }),

  finishProcessing: () => set({ isProcessing: false }),

  reset: () =>
    set({
      isProcessing: false,
      currentUnitId: null,
      reasoning: '',
      historicMatches: [],
      suggestions: new Map(),
    }),
}));
