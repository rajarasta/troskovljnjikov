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

export function useWebSocket() {
  const [isConnected, setIsConnected] = useState(false);
  const addEvent = useAgentStore((s) => s.addEvent);

  useEffect(() => {
    wsClient.connect();

    const statusInterval = setInterval(() => {
      setIsConnected(wsClient.isConnected);
    }, 1000);

    const handleMessage = (event: AgentEvent) => {
      addEvent(event);
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
