import { create } from 'zustand';
import type { ParsedBoQ, LogicalUnit, OutputLineState } from '../api/types';

interface BoQStore {
  parsedBoQ: ParsedBoQ | null;
  currentUnitIndex: number;
  outputData: Map<string, OutputLineState[]>;

  setParsedBoQ: (boq: ParsedBoQ) => void;
  setCurrentUnit: (index: number) => void;
  currentUnit: () => LogicalUnit | null;
  initOutputForUnit: (unit: LogicalUnit) => void;
  updateOutputLine: (unitId: string, itemNumber: string, updates: Partial<OutputLineState>) => void;
}

export const useBoQStore = create<BoQStore>((set, get) => ({
  parsedBoQ: null,
  currentUnitIndex: 0,
  outputData: new Map(),

  setParsedBoQ: (boq) =>
    set({ parsedBoQ: boq, currentUnitIndex: 0, outputData: new Map() }),

  setCurrentUnit: (index) => set({ currentUnitIndex: index }),

  currentUnit: () => {
    const { parsedBoQ, currentUnitIndex } = get();
    if (!parsedBoQ || currentUnitIndex >= parsedBoQ.units.length) return null;
    return parsedBoQ.units[currentUnitIndex];
  },

  initOutputForUnit: (unit) => {
    const outputData = new Map(get().outputData);
    if (!outputData.has(unit.id)) {
      outputData.set(
        unit.id,
        unit.priced_lines.map((pl) => ({
          original: pl,
          suggestedPrice: null,
          confidence: null,
          agentReasoning: '',
          userAccepted: null,
          userEditedPrice: null,
        }))
      );
      set({ outputData });
    }
  },

  updateOutputLine: (unitId, itemNumber, updates) => {
    const outputData = new Map(get().outputData);
    const lines = outputData.get(unitId);
    if (lines) {
      const idx = lines.findIndex((l) => l.original.item_number === itemNumber);
      if (idx >= 0) {
        lines[idx] = { ...lines[idx], ...updates };
        outputData.set(unitId, [...lines]);
        set({ outputData });
      }
    }
  },
}));
