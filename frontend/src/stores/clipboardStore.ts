import { create } from "zustand";

interface PickedValue {
  value: number | string;
  field: string;
  sourceMatchId: string;
}

interface ClipboardState {
  pickedValue: PickedValue | null;
  pickValue: (value: number | string, field: string, sourceMatchId: string) => void;
  clearPicked: () => void;
}

export const useClipboardStore = create<ClipboardState>((set) => ({
  pickedValue: null,
  pickValue: (value, field, sourceMatchId) =>
    set({ pickedValue: { value, field, sourceMatchId } }),
  clearPicked: () => set({ pickedValue: null }),
}));
