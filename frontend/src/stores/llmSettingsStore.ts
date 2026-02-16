import { create } from "zustand";
import type { AgentSettings, AllAgentSettings } from "@/lib/api/llmSettings";
import { fetchLlmSettings, updateLlmSettings, resetLlmSettings } from "@/lib/api/llmSettings";

interface LlmSettingsState {
  agents: AllAgentSettings;
  activeAgentIds: Set<string>;
  isLoaded: boolean;
  isLoading: boolean;

  fetchAll: () => Promise<void>;
  updateAgent: (agentId: string, updates: {
    temperature?: number;
    knowledge_prompt?: string;
    instruction_prompt?: string;
    enabled?: boolean;
  }) => Promise<void>;
  resetAgent: (agentId: string) => Promise<void>;
  setAgentActive: (agentId: string) => void;
  setAgentInactive: (agentId: string) => void;
}

export const useLlmSettingsStore = create<LlmSettingsState>((set, get) => ({
  agents: {},
  activeAgentIds: new Set(),
  isLoaded: false,
  isLoading: false,

  fetchAll: async () => {
    if (get().isLoading) return;
    set({ isLoading: true });
    try {
      const agents = await fetchLlmSettings();
      set({ agents, isLoaded: true, isLoading: false });
    } catch (err) {
      console.error("[llmSettingsStore] Failed to fetch settings:", err);
      set({ isLoading: false });
    }
  },

  updateAgent: async (agentId, updates) => {
    try {
      const updated = await updateLlmSettings(agentId, updates);
      set((s) => ({
        agents: { ...s.agents, [agentId]: updated },
      }));
    } catch (err) {
      console.error("[llmSettingsStore] Failed to update agent:", agentId, err);
    }
  },

  resetAgent: async (agentId) => {
    try {
      const reset = await resetLlmSettings(agentId);
      set((s) => ({
        agents: { ...s.agents, [agentId]: reset },
      }));
    } catch (err) {
      console.error("[llmSettingsStore] Failed to reset agent:", agentId, err);
    }
  },

  setAgentActive: (agentId) => {
    set((s) => {
      const next = new Set(s.activeAgentIds);
      next.add(agentId);
      return { activeAgentIds: next };
    });
  },

  setAgentInactive: (agentId) => {
    set((s) => {
      const next = new Set(s.activeAgentIds);
      next.delete(agentId);
      return { activeAgentIds: next };
    });
  },
}));
