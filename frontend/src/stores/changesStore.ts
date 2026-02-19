import { create } from "zustand";
import { useBoQStore } from "./boqStore";
import type { BoQItem } from "@/lib/types";

export interface BoQChange {
  itemId: string;
  row: number;
  itemNumber: string | null;
  description: string;
  field: "quantity" | "unit_price" | "total" | "description";
  oldValue: number | string;
  newValue: number | string;
}

interface ChangesState {
  changes: BoQChange[];
  recompute: () => void;
  revertChange: (itemId: string, field: BoQChange["field"]) => void;
  revertAll: () => void;
}

function diffItems(originals: BoQItem[], working: BoQItem[]): BoQChange[] {
  const changes: BoQChange[] = [];
  const origMap = new Map(originals.map((i) => [i.id, i]));

  for (const w of working) {
    const o = origMap.get(w.id);
    if (!o) continue;

    // Numeric fields
    for (const field of ["quantity", "unit_price", "total"] as const) {
      if (o[field] !== w[field]) {
        changes.push({
          itemId: w.id,
          row: w.row,
          itemNumber: w.item_number,
          description: w.description,
          field,
          oldValue: o[field],
          newValue: w[field],
        });
      }
    }

    // Description field
    if (o.description !== w.description) {
      changes.push({
        itemId: w.id,
        row: w.row,
        itemNumber: w.item_number,
        description: w.description,
        field: "description",
        oldValue: o.description,
        newValue: w.description,
      });
    }
  }
  return changes;
}

export const useChangesStore = create<ChangesState>((set) => ({
  changes: [],

  recompute: () => {
    const { items, workingItems } = useBoQStore.getState();
    set({ changes: diffItems(items, workingItems) });
  },

  revertChange: (itemId, field) => {
    const { items, updateWorkingItem } = useBoQStore.getState();
    const original = items.find((i) => i.id === itemId);
    if (!original) return;
    updateWorkingItem(itemId, { [field]: original[field] });
    // Recompute after revert
    const { items: freshItems, workingItems } = useBoQStore.getState();
    set({ changes: diffItems(freshItems, workingItems) });
  },

  revertAll: () => {
    const boq = useBoQStore.getState();
    for (const item of boq.items) {
      boq.updateWorkingItem(item.id, {
        quantity: item.quantity,
        unit_price: item.unit_price,
        total: item.total,
        description: item.description,
      });
    }
    set({ changes: [] });
  },
}));
