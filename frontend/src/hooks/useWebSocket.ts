"use client";

import { useEffect, useState } from "react";
import { wsClient } from "@/lib/ws";
import { useAgentStore } from "@/stores/agentStore";
import type { AgentEvent } from "@/lib/types";

import { pipelineHandlers } from "./wsHandlers/pipelineHandlers";
import { autopilotHandlers } from "./wsHandlers/autopilotHandlers";
import { chatHandlers } from "./wsHandlers/chatHandlers";
import { agentHandlers } from "./wsHandlers/agentHandlers";
import { searchHandlers } from "./wsHandlers/searchHandlers";

const handlers: Record<string, (event: AgentEvent) => void> = {
  ...pipelineHandlers,
  ...autopilotHandlers,
  ...chatHandlers,
  ...agentHandlers,
  ...searchHandlers,
};

// Only track actual agent lifecycle events in the Agent Activity panel.
// Other WS events (match results, price suggestions, summary tokens, etc.)
// are handled by their specific handlers but don't need to clutter the panel.
const AGENT_EVENT_PREFIXES = ["agent:", "pipeline:", "pricing:"];

export function useWebSocket() {
  const [isConnected, setIsConnected] = useState(false);
  const addEvent = useAgentStore((s) => s.addEvent);

  useEffect(() => {
    wsClient.connect();

    const statusInterval = setInterval(() => {
      setIsConnected(wsClient.isConnected);
    }, 1000);

    const handleMessage = (event: AgentEvent) => {
      // Only add to Agent Activity panel if it's an actual agent/pipeline event
      if (AGENT_EVENT_PREFIXES.some((p) => event.type.startsWith(p))) {
        addEvent(event);
      }
      handlers[event.type]?.(event);
    };

    wsClient.onMessage(handleMessage);

    return () => {
      clearInterval(statusInterval);
      wsClient.offMessage(handleMessage);
      wsClient.disconnect();
    };
  }, [addEvent]);

  return { isConnected };
}
