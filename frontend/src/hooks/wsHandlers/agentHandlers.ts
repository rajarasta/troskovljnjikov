import { useLlmSettingsStore } from "@/stores/llmSettingsStore";
import type { AgentEvent } from "@/lib/types";

export const agentHandlers: Record<string, (event: AgentEvent) => void> = {
  "agent:run_start": (event) => {
    const agentId = event.payload?.agent_id as string | undefined;
    if (agentId) {
      useLlmSettingsStore.getState().setAgentActive(agentId);
    }
  },
  "agent:run_end": (event) => {
    const agentId = event.payload?.agent_id as string | undefined;
    if (agentId) {
      useLlmSettingsStore.getState().setAgentInactive(agentId);
    }
  },
  // Lookup agent lifecycle events
  "agent:spawn": (event) => {
    const agent = event.payload?.agent as string | undefined;
    if (agent === "lookup") {
      // Lookup agent spawned - system is resolving a synthetic cell ID
      const itemId = event.payload?.item_id as string | undefined;
      console.debug(`[Lookup Agent] Spawned for item: ${itemId}`);
    }
  },
  "agent:result": (event) => {
    const agent = event.payload?.agent as string | undefined;
    if (agent === "lookup") {
      // Lookup agent completed successfully
      const itemId = event.payload?.item_id as string | undefined;
      const resolved = event.payload?.resolved as boolean | undefined;
      const description = event.payload?.description as string | undefined;
      console.debug(`[Lookup Agent] Resolved: ${itemId} -> ${description}`);
    }
  },
  "agent:error": (event) => {
    const agent = event.payload?.agent as string | undefined;
    if (agent === "lookup") {
      // Lookup agent failed
      const itemId = event.payload?.item_id as string | undefined;
      const error = event.payload?.error as string | undefined;
      console.error(`[Lookup Agent] Error for ${itemId}: ${error}`);
    }
  },
};
