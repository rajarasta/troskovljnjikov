import { create } from "zustand";
import type { BoQFile, BoQItem } from "@/lib/types";
import * as api from "@/lib/api";

interface BoQState {
  // ── State ───────────────────────────────────────────────────────
  selectedFileId: string | null;
  selectedRow: BoQItem | null;
  files: BoQFile[];
  items: BoQItem[];
  workingItems: BoQItem[];
  isLoading: boolean;
  error: string | null;

  // ── Actions ─────────────────────────────────────────────────────
  uploadFile: (file: File) => Promise<void>;
  loadFiles: () => Promise<void>;
  loadItems: (fileId: string) => Promise<void>;
  selectRow: (row: BoQItem | null) => void;
  deleteFile: (fileId: string) => Promise<void>;
  updateWorkingItem: (itemId: string, updates: Partial<Pick<BoQItem, "quantity" | "unit_price" | "total">>) => void;
}

export const useBoQStore = create<BoQState>((set, get) => ({
  selectedFileId: null,
  selectedRow: null,
  files: [],
  items: [],
  workingItems: [],
  isLoading: false,
  error: null,

  uploadFile: async (file: File) => {
    set({ isLoading: true, error: null });
    try {
      const { fileId } = await api.uploadFile(file);
      // Reload full file list to get properly shaped FileInfo objects
      const files = await api.fetchFiles();
      set({ files, selectedFileId: fileId, isLoading: false });
      await get().loadItems(fileId);
    } catch (err) {
      set({
        isLoading: false,
        error: err instanceof Error ? err.message : "Upload failed",
      });
    }
  },

  loadFiles: async () => {
    set({ isLoading: true, error: null });
    try {
      const files = await api.fetchFiles();
      set({ files, isLoading: false });
    } catch (err) {
      set({
        isLoading: false,
        error: err instanceof Error ? err.message : "Failed to load files",
      });
    }
  },

  loadItems: async (fileId: string) => {
    set({ isLoading: true, error: null, selectedFileId: fileId });
    try {
      const items = await api.fetchFileItems(fileId);
      // Deep copy for working items so edits don't mutate originals
      const workingItems = items.map((item) => ({ ...item }));
      set({ items, workingItems, isLoading: false });
    } catch (err) {
      set({
        isLoading: false,
        error: err instanceof Error ? err.message : "Failed to load items",
      });
    }
  },

  selectRow: (row: BoQItem | null) => {
    set({ selectedRow: row });
  },

  deleteFile: async (fileId: string) => {
    set({ isLoading: true, error: null });
    try {
      await api.deleteFile(fileId);
      set((state) => ({
        files: state.files.filter((f) => f.id !== fileId),
        selectedFileId:
          state.selectedFileId === fileId ? null : state.selectedFileId,
        items: state.selectedFileId === fileId ? [] : state.items,
        workingItems: state.selectedFileId === fileId ? [] : state.workingItems,
        selectedRow:
          state.selectedFileId === fileId ? null : state.selectedRow,
        isLoading: false,
      }));
    } catch (err) {
      set({
        isLoading: false,
        error: err instanceof Error ? err.message : "Failed to delete file",
      });
    }
  },

  updateWorkingItem: (itemId: string, updates: Partial<Pick<BoQItem, "quantity" | "unit_price" | "total">>) => {
    set((state) => ({
      workingItems: state.workingItems.map((item) => {
        if (item.id !== itemId) return item;
        const updated = { ...item, ...updates };
        // Auto-recalculate total when quantity or unit_price changes
        if ("quantity" in updates || "unit_price" in updates) {
          updated.total = updated.quantity * updated.unit_price;
        }
        return updated;
      }),
    }));
  },
}));
