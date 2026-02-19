"use client";

import { useEffect, useState } from "react";
import { wsClient } from "@/lib/ws";
import { useAgentStore } from "@/stores/agentStore";
import { useAutopilotStore } from "@/stores/autopilotStore";
import { useChatPanelStore } from "@/stores/chatPanelStore";
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

      // ── Autopilot events ────────────────────────────────────────
      const autopilot = useAutopilotStore.getState();
      const payload = event.payload ?? {};

      if (event.type === "autopilot:summary_token") {
        const fileId = payload.file_id as string;
        const token = payload.token as string;
        const done = payload.done as boolean;
        autopilot.appendSummaryToken(fileId, token, done);

        // Stream tokens into the chat panel for this file
        if (done) {
          const store = useChatPanelStore.getState();
          const panel = store.getPanelBySelection(`file:${fileId}`);
          if (panel) {
            const fullText = useAutopilotStore.getState().summaryTokens[fileId] || "";
            store.addMessage(panel.id, {
              id: `summary-${fileId}-${Date.now()}`,
              item_id: `file:${fileId}`,
              role: "assistant",
              content: fullText,
              created_at: new Date().toISOString(),
            });
            store.setAnalyzing(panel.id, false);
          }
        }
      }

      if (event.type === "autopilot:match_progress") {
        autopilot.setProgress(
          payload.file_id as string,
          payload.current as number,
          payload.total as number,
        );
        autopilot.setStatus(payload.file_id as string, "matching");
      }

      if (event.type === "autopilot:match_result") {
        autopilot.addMatchResult(
          payload.file_id as string,
          payload.item_id as string,
          payload.match_count as number,
          payload.top_similarity as number,
          payload.confidence as "high" | "medium" | "low",
        );
      }

      if (event.type === "autopilot:price_suggested") {
        autopilot.addPriceSuggestion(
          payload.file_id as string,
          payload.item_id as string,
          {
            suggested_price: payload.suggested_price as number,
            confidence: payload.confidence as number,
            based_on: payload.based_on as number,
          },
        );
        autopilot.setStatus(payload.file_id as string, "pricing");
      }

      if (event.type === "autopilot:complete") {
        autopilot.setComplete(payload.file_id as string, {
          total_items: payload.total_items as number,
          matched_items: payload.matched_items as number,
          priced_items: payload.priced_items as number,
          high_confidence: payload.high_confidence as number,
          medium_confidence: payload.medium_confidence as number,
          low_confidence: payload.low_confidence as number,
        });
      }

      if (event.type === "autopilot:error") {
        autopilot.setError(payload.file_id as string, payload.error as string);
      }

      // ── Chat streaming events ───────────────────────────────────
      if (event.type === "chat:token") {
        const chatStore = useChatPanelStore.getState();
        const itemId = payload.item_id as string;
        const token = payload.token as string;
        // Find the panel for this item and update the last assistant message
        const panel = chatStore.getPanelBySelection(itemId);
        if (panel) {
          const lastMsg = panel.messages[panel.messages.length - 1];
          if (lastMsg && lastMsg.role === "assistant" && lastMsg.id.startsWith("streaming-")) {
            // Update existing streaming message
            const updatedMessages = [...panel.messages];
            updatedMessages[updatedMessages.length - 1] = {
              ...lastMsg,
              content: lastMsg.content + token,
            };
            // Direct state update for streaming performance
            useChatPanelStore.setState((s) => ({
              panels: s.panels.map((p) =>
                p.id === panel.id ? { ...p, messages: updatedMessages } : p,
              ),
            }));
          }
        }
      }

      if (event.type === "chat:complete") {
        const chatStore = useChatPanelStore.getState();
        const itemId = payload.item_id as string;
        const panel = chatStore.getPanelBySelection(itemId);
        if (panel) {
          chatStore.setSending(panel.id, false);
        }
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
