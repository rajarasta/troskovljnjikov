"use client";

import { useEffect, useState } from "react";
import { wsClient } from "@/lib/ws";
import { useAgentStore } from "@/stores/agentStore";
import { usePipelineStore } from "@/stores/pipelineStore";
import type { AgentEvent, PipelineStage } from "@/lib/types";

const PIPELINE_STAGES: PipelineStage[] = [
  "upload",
  "parse",
  "index",
  "match",
  "suggest",
  "review",
];

export function useWebSocket() {
  const [isConnected, setIsConnected] = useState(false);
  const addEvent = useAgentStore((s) => s.addEvent);
  const setStage = usePipelineStore((s) => s.setStage);
  const resetPipeline = usePipelineStore((s) => s.reset);

  useEffect(() => {
    wsClient.connect();

    // Poll connection status
    const statusInterval = setInterval(() => {
      setIsConnected(wsClient.isConnected);
    }, 1000);

    const handleMessage = (event: AgentEvent) => {
      // Dispatch to agent store
      addEvent(event);

      // Dispatch pipeline-related events
      if (event.type === "pipeline_stage") {
        const stage = event.payload?.stage as PipelineStage | undefined;
        const progress = (event.payload?.progress as number) ?? 0;
        if (stage && PIPELINE_STAGES.includes(stage)) {
          setStage(stage, progress);
        }
      }

      if (event.type === "pipeline_complete" || event.type === "pipeline_error") {
        resetPipeline();
      }
    };

    wsClient.onMessage(handleMessage);

    return () => {
      clearInterval(statusInterval);
      wsClient.offMessage(handleMessage);
      wsClient.disconnect();
    };
  }, [addEvent, setStage, resetPipeline]);

  return { isConnected };
}
