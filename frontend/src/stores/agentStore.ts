import { create } from "zustand";
import type { AgentEvent } from "@/lib/types";

interface AgentState {
  // ── State ───────────────────────────────────────────────────────
  events: AgentEvent[];
  activeAgents: Map<string, AgentEvent>;
  isPanelOpen: boolean;

  // ── Actions ─────────────────────────────────────────────────────
  addEvent: (event: AgentEvent) => void;
  togglePanel: () => void;
  clearEvents: () => void;
}

export const useAgentStore = create<AgentState>((set) => ({
  events: [],
  activeAgents: new Map(),
  isPanelOpen: false,

  addEvent: (event: AgentEvent) => {
    set((state) => {
      const newEvents = [...state.events, event];
      const newActiveAgents = new Map(state.activeAgents);

      if (event.agent_id) {
        if (
          event.type === "agent_complete" ||
          event.type === "agent_error"
        ) {
          newActiveAgents.delete(event.agent_id);
        } else {
          newActiveAgents.set(event.agent_id, event);
        }
      }

      return {
        events: newEvents,
        activeAgents: newActiveAgents,
      };
    });
  },

  togglePanel: () => {
    set((state) => ({ isPanelOpen: !state.isPanelOpen }));
  },

  clearEvents: () => {
    set({ events: [], activeAgents: new Map() });
  },
}));
