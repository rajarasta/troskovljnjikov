import { create } from "zustand";
import type { ChatMessage } from "@/lib/types";

export interface ChatPanel {
  id: string;
  selectionId: string;
  label: string;
  messages: ChatMessage[];
  isAnalyzing: boolean;
  isSending: boolean;
  error: string | null;
}

interface ChatPanelState {
  panels: ChatPanel[];
  activePanelId: string | null;

  createPanel: (selectionId: string, label: string) => string;
  removePanel: (panelId: string) => void;
  setActive: (panelId: string | null) => void;
  addMessage: (panelId: string, message: ChatMessage) => void;
  setAnalyzing: (panelId: string, analyzing: boolean) => void;
  setSending: (panelId: string, sending: boolean) => void;
  setError: (panelId: string, error: string | null) => void;
  clearAll: () => void;
  getPanelBySelection: (selectionId: string) => ChatPanel | undefined;
  panelExists: (panelId: string) => boolean;
}

let panelCounter = 0;

export const useChatPanelStore = create<ChatPanelState>((set, get) => ({
  panels: [],
  activePanelId: null,

  createPanel: (selectionId, label) => {
    const existing = get().panels.find((p) => p.selectionId === selectionId);
    if (existing) {
      set({ activePanelId: existing.id });
      return existing.id;
    }
    const id = `chat-${++panelCounter}-${Date.now()}`;
    const panel: ChatPanel = {
      id,
      selectionId,
      label,
      messages: [],
      isAnalyzing: false,
      isSending: false,
      error: null,
    };
    set((s) => ({
      panels: [...s.panels, panel],
      activePanelId: id,
    }));
    return id;
  },

  removePanel: (panelId) => {
    set((s) => ({
      panels: s.panels.filter((p) => p.id !== panelId),
      activePanelId: s.activePanelId === panelId ? null : s.activePanelId,
    }));
  },

  setActive: (panelId) => set({ activePanelId: panelId }),

  addMessage: (panelId, message) => {
    if (!get().panels.some((p) => p.id === panelId)) {
      if (process.env.NODE_ENV === 'development') {
        console.warn(`[chatPanelStore] Attempted to add message to non-existent panel: ${panelId}`);
      }
      return;
    }
    set((s) => ({
      panels: s.panels.map((p) =>
        p.id === panelId ? { ...p, messages: [...p.messages, message] } : p,
      ),
    }));
  },

  setAnalyzing: (panelId, analyzing) => {
    if (!get().panels.some((p) => p.id === panelId)) {
      if (process.env.NODE_ENV === 'development') {
        console.warn(`[chatPanelStore] Attempted to set analyzing state on non-existent panel: ${panelId}`);
      }
      return;
    }
    set((s) => ({
      panels: s.panels.map((p) =>
        p.id === panelId ? { ...p, isAnalyzing: analyzing } : p,
      ),
    }));
  },

  setSending: (panelId, sending) => {
    if (!get().panels.some((p) => p.id === panelId)) {
      if (process.env.NODE_ENV === 'development') {
        console.warn(`[chatPanelStore] Attempted to set sending state on non-existent panel: ${panelId}`);
      }
      return;
    }
    set((s) => ({
      panels: s.panels.map((p) =>
        p.id === panelId ? { ...p, isSending: sending } : p,
      ),
    }));
  },

  setError: (panelId, error) => {
    if (!get().panels.some((p) => p.id === panelId)) {
      if (process.env.NODE_ENV === 'development') {
        console.warn(`[chatPanelStore] Attempted to set error on non-existent panel: ${panelId}`);
      }
      return;
    }
    set((s) => ({
      panels: s.panels.map((p) =>
        p.id === panelId ? { ...p, error } : p,
      ),
    }));
  },

  clearAll: () => set({ panels: [], activePanelId: null }),

  getPanelBySelection: (selectionId) => {
    return get().panels.find((p) => p.selectionId === selectionId);
  },

  panelExists: (panelId) => {
    return get().panels.some((p) => p.id === panelId);
  },
}));
