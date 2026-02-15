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
  getPanelBySelection: (selectionId: string) => ChatPanel | undefined;
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
    set((s) => ({
      panels: s.panels.map((p) =>
        p.id === panelId ? { ...p, messages: [...p.messages, message] } : p,
      ),
    }));
  },

  setAnalyzing: (panelId, analyzing) => {
    set((s) => ({
      panels: s.panels.map((p) =>
        p.id === panelId ? { ...p, isAnalyzing: analyzing } : p,
      ),
    }));
  },

  setSending: (panelId, sending) => {
    set((s) => ({
      panels: s.panels.map((p) =>
        p.id === panelId ? { ...p, isSending: sending } : p,
      ),
    }));
  },

  setError: (panelId, error) => {
    set((s) => ({
      panels: s.panels.map((p) =>
        p.id === panelId ? { ...p, error } : p,
      ),
    }));
  },

  getPanelBySelection: (selectionId) => {
    return get().panels.find((p) => p.selectionId === selectionId);
  },
}));
