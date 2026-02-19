import { create } from "zustand";
import type { BoQItem } from "@/lib/types";

const SELECTION_COLORS = [
  "cyan",
  "purple",
  "amber",
  "emerald",
  "rose",
  "sky",
] as const;

export type SelectionColor = (typeof SELECTION_COLORS)[number];

export interface BoQSelection {
  id: string;
  startIndex: number;
  endIndex: number;
  items: BoQItem[];
  color: SelectionColor;
}

interface SelectionState {
  // ── State ───────────────────────────────────────────────────────
  selections: BoQSelection[];
  activeSelectionId: string | null;
  dragAnchorIndex: number | null;

  // ── Actions ─────────────────────────────────────────────────────
  addSelection: (startIndex: number, endIndex: number, items: BoQItem[]) => string;
  replaceSelection: (oldId: string, startIndex: number, endIndex: number, items: BoQItem[]) => string;
  removeSelection: (id: string) => void;
  setActive: (id: string | null) => void;
  clearAll: () => void;
  setDragAnchor: (index: number | null) => void;
}

let selectionCounter = 0;

export const useSelectionStore = create<SelectionState>((set, get) => ({
  selections: [],
  activeSelectionId: null,
  dragAnchorIndex: null,

  addSelection: (startIndex, endIndex, items) => {
    const id = `sel-${++selectionCounter}-${Date.now()}`;
    const colorIndex = get().selections.length % SELECTION_COLORS.length;
    const color = SELECTION_COLORS[colorIndex];
    const selection: BoQSelection = {
      id,
      startIndex: Math.min(startIndex, endIndex),
      endIndex: Math.max(startIndex, endIndex),
      items,
      color,
    };
    console.log("📊 SelectionStore.addSelection:", { id, itemCount: items.length, items: items.map(i => ({ id: i.id, description: i.description })) });
    set((s) => ({
      selections: [...s.selections, selection],
      activeSelectionId: id,
    }));
    return id;
  },

  replaceSelection: (oldId, startIndex, endIndex, items) => {
    const id = `sel-${++selectionCounter}-${Date.now()}`;
    const oldSelection = get().selections.find((s) => s.id === oldId);
    const color = oldSelection?.color ?? SELECTION_COLORS[get().selections.length % SELECTION_COLORS.length];
    const selection: BoQSelection = {
      id,
      startIndex: Math.min(startIndex, endIndex),
      endIndex: Math.max(startIndex, endIndex),
      items,
      color,
    };
    set((s) => ({
      selections: [...s.selections.filter((sel) => sel.id !== oldId), selection],
      activeSelectionId: id,
    }));
    return id;
  },

  removeSelection: (id) => {
    set((s) => ({
      selections: s.selections.filter((sel) => sel.id !== id),
      activeSelectionId: s.activeSelectionId === id ? null : s.activeSelectionId,
    }));
  },

  setActive: (id) => set({ activeSelectionId: id }),
  clearAll: () => set({ selections: [], activeSelectionId: null }),
  setDragAnchor: (index) => set({ dragAnchorIndex: index }),
}));
