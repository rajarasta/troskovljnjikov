import { create } from 'zustand';

interface UIStore {
  scrollLocked: boolean;
  toggleScrollLock: () => void;
}

export const useUIStore = create<UIStore>((set) => ({
  scrollLocked: true,
  toggleScrollLock: () => set((state) => ({ scrollLocked: !state.scrollLocked })),
}));
