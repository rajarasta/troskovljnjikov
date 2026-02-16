import { useAutopilotStore } from "@/stores/autopilotStore";
import { useChatPanelStore } from "@/stores/chatPanelStore";
import type { AgentEvent } from "@/lib/types";

export const autopilotHandlers: Record<string, (event: AgentEvent) => void> = {
  "autopilot:summary_token": (event) => {
    const payload = event.payload ?? {};
    const fileId = payload.file_id as string;
    const token = payload.token as string;
    const done = payload.done as boolean;
    useAutopilotStore.getState().appendSummaryToken(fileId, token, done);

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
  },

  "autopilot:match_progress": (event) => {
    const payload = event.payload ?? {};
    const autopilot = useAutopilotStore.getState();
    autopilot.setProgress(
      payload.file_id as string,
      payload.current as number,
      payload.total as number,
    );
    autopilot.setStatus(payload.file_id as string, "matching");
  },

  "autopilot:match_result": (event) => {
    const payload = event.payload ?? {};
    useAutopilotStore.getState().addMatchResult(
      payload.file_id as string,
      payload.item_id as string,
      payload.confidence as "high" | "medium" | "low",
    );
  },

  "autopilot:price_suggested": (event) => {
    const payload = event.payload ?? {};
    const autopilot = useAutopilotStore.getState();
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
  },

  "autopilot:complete": (event) => {
    const payload = event.payload ?? {};
    useAutopilotStore.getState().setComplete(payload.file_id as string, {
      total_items: payload.total_items as number,
      matched_items: payload.matched_items as number,
      priced_items: payload.priced_items as number,
      high_confidence: payload.high_confidence as number,
      medium_confidence: payload.medium_confidence as number,
      low_confidence: payload.low_confidence as number,
    });
  },

  "autopilot:error": (event) => {
    const payload = event.payload ?? {};
    useAutopilotStore.getState().setError(
      payload.file_id as string,
      payload.error as string,
    );
  },
};
