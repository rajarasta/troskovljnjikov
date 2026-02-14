import { create } from "zustand";
import type { BoQFile, BoQItem } from "@/lib/types";
import * as api from "@/lib/api";

interface BoQState {
  // ── State ───────────────────────────────────────────────────────
  selectedFileId: string | null;
  selectedRow: BoQItem | null;
  files: BoQFile[];
  items: BoQItem[];
  isLoading: boolean;
  error: string | null;

  // ── Actions ─────────────────────────────────────────────────────
  uploadFile: (file: File) => Promise<void>;
  loadFiles: () => Promise<void>;
  loadItems: (fileId: string) => Promise<void>;
  selectRow: (row: BoQItem | null) => void;
  deleteFile: (fileId: string) => Promise<void>;
}

export const useBoQStore = create<BoQState>((set, get) => ({
  selectedFileId: null,
  selectedRow: null,
  files: [],
  items: [],
  isLoading: false,
  error: null,

  uploadFile: async (file: File) => {
    set({ isLoading: true, error: null });
    try {
      const uploaded = await api.uploadFile(file);
      set((state) => ({
        files: [...state.files, uploaded],
        selectedFileId: uploaded.id,
        isLoading: false,
      }));
      // Auto-load items for the newly uploaded file
      await get().loadItems(uploaded.id);
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
      set({ items, isLoading: false });
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
}));
