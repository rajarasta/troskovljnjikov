import { create } from "zustand";

interface FilePreviewState {
  previewFileId: string | null;
  previewFileName: string | null;
  setPreviewFile: (fileId: string, fileName: string) => void;
  closePreview: () => void;
}

export const useFilePreviewStore = create<FilePreviewState>((set) => ({
  previewFileId: null,
  previewFileName: null,

  setPreviewFile: (fileId, fileName) =>
    set({ previewFileId: fileId, previewFileName: fileName }),

  closePreview: () =>
    set({ previewFileId: null, previewFileName: null }),
}));
