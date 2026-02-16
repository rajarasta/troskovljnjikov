import { useEffect, useRef } from "react";
import { useSelectionStore } from "@/stores/selectionStore";
import { useChatPanelStore } from "@/stores/chatPanelStore";
import { useMatchStore } from "@/stores/matchStore";
import { analyzeSelection } from "@/lib/api";
import type { ChatMessage } from "@/lib/types";

/**
 * Type guard for ChatMessage
 */
function isValidChatMessage(obj: any): obj is ChatMessage {
  return (
    obj &&
    typeof obj === 'object' &&
    typeof obj.id === 'string' &&
    typeof obj.item_id === 'string' &&
    typeof obj.role === 'string' &&
    typeof obj.content === 'string' &&
    typeof obj.created_at === 'string'
  );
}

/**
 * Watches selection store. When a new selection is created:
 * 1. Triggers match lookup (deterministic pipeline -> column 2)
 * 2. Creates a chat panel and requests LLM analysis -> column 1
 */
export function useSelectionPipeline() {
  const selections = useSelectionStore((s) => s.selections);
  const startLookup = useMatchStore((s) => s.startLookup);
  const { createPanel, addMessage, setAnalyzing, removePanel, panelExists } = useChatPanelStore();
  const processedIds = useRef(new Set<string>());
  const abortControllers = useRef(new Map<string, AbortController>());

  useEffect(() => {
    // Process new selections
    for (const selection of selections) {
      if (processedIds.current.has(selection.id)) continue;
      processedIds.current.add(selection.id);

      const descriptions = selection.items.map((i) => i.description);
      const label =
        selection.startIndex === selection.endIndex
          ? `Row ${selection.items[0]?.item_number ?? selection.startIndex}`
          : `Rows ${selection.items[0]?.item_number ?? selection.startIndex}\u2013${selection.items[selection.items.length - 1]?.item_number ?? selection.endIndex}`;

      // 1. Trigger deterministic match lookup
      const combinedDesc = descriptions.join("\n");
      const qty = selection.items[0]?.quantity ?? 0;
      startLookup(combinedDesc, qty);

      // 2. Create chat panel + request LLM analysis
      const panelId = createPanel(selection.id, label);
      setAnalyzing(panelId, true);

      // Create abort controller for this request
      const controller = new AbortController();
      abortControllers.current.set(selection.id, controller);

      analyzeSelection(selection.id, descriptions, combinedDesc, controller.signal)
        .then((response) => {
          // Check if panel still exists before updating
          if (panelExists(panelId)) {
            // Validate response before adding
            if (!isValidChatMessage(response)) {
              console.error('[useSelectionPipeline] Invalid chat message response:', response);
              const errorMsg: ChatMessage = {
                id: `err-${Date.now()}`,
                item_id: selection.id,
                role: "system",
                content: "Analysis returned invalid data format",
                created_at: new Date().toISOString(),
              };
              addMessage(panelId, errorMsg);
              setAnalyzing(panelId, false);
              return;
            }
            addMessage(panelId, response);
            setAnalyzing(panelId, false);
          }
        })
        .catch((err) => {
          // Ignore abort errors (expected when cleaning up)
          if (err.name === 'AbortError') {
            return;
          }
          // Check if panel still exists before adding error message
          if (panelExists(panelId)) {
            const errorMsg: ChatMessage = {
              id: `err-${Date.now()}`,
              item_id: selection.id,
              role: "system",
              content: `Analysis failed: ${err instanceof Error ? err.message : "Unknown error"}`,
              created_at: new Date().toISOString(),
            };
            addMessage(panelId, errorMsg);
            setAnalyzing(panelId, false);
          }
        })
        .finally(() => {
          // Clean up abort controller
          abortControllers.current.delete(selection.id);
        });
    }

    // Clean up removed selections
    const currentIds = new Set(selections.map((s) => s.id));
    for (const id of processedIds.current) {
      if (!currentIds.has(id)) {
        // Abort in-flight API request
        const controller = abortControllers.current.get(id);
        if (controller) {
          controller.abort();
          abortControllers.current.delete(id);
        }
        // Remove associated chat panel
        const panel = useChatPanelStore.getState().getPanelBySelection(id);
        if (panel) {
          removePanel(panel.id);
        }
        // Clean up tracking
        processedIds.current.delete(id);
      }
    }
  }, [selections, startLookup, createPanel, addMessage, setAnalyzing, removePanel, panelExists]);
}
