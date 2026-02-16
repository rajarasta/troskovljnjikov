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
};
