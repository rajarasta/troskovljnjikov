import { useEffect, useRef } from "react";
import { useSelectionStore } from "@/stores/selectionStore";
import { useChatPanelStore } from "@/stores/chatPanelStore";
import { useMatchStore } from "@/stores/matchStore";
import { useAutopilotStore } from "@/stores/autopilotStore";
import { analyzeSelection, fetchCachedMatches } from "@/lib/api";
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
 *
 * Store actions are accessed via getState() inside the effect so the
 * only reactive dependency is `selections`. This prevents the effect
 * from re-firing when chat panels or match results update, which was
 * causing panels to be spuriously cleaned up and recreated.
 */
export function useSelectionPipeline() {
  const selections = useSelectionStore((s) => s.selections);
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

      // 1. Match lookup — check autopilot cache first for single-item selections
      const combinedDesc = selection.items.length === 1
        ? (selection.items[0].full_description || selection.items[0].description)
        : selection.items
            .filter((i) => i.item_type !== "section_header")
            .map((i) => i.full_description || i.description)
            .join(" | ");
      const qty = selection.items[0]?.quantity ?? 0;
      const fileId = selection.items[0]?.file_id || undefined;
      const startRow = Math.min(...selection.items.map((i) => i.row));
      const endRow = Math.max(...selection.items.map((i) => i.row));
      const firstItem = selection.items[0];
      const autopilotConfidence = fileId && firstItem
        ? useAutopilotStore.getState().getConfidence(fileId, firstItem.id)
        : null;

      if (autopilotConfidence && fileId && firstItem && selection.items.length === 1) {
        // Use cached matches from autopilot (resolved via backend endpoint, no ChromaDB query)
        fetchCachedMatches(fileId, firstItem.id, qty)
          .then((response) => {
            useMatchStore.getState().setCachedResults(selection.id, response.matches, response.stats);
          })
          .catch(() => {
            // Fall back to regular search if cache fetch fails
            useMatchStore.getState().startLookup(
              selection.id, combinedDesc, qty, fileId, startRow, endRow,
            );
          });
      } else {
        // No cache hit or multi-item selection — standard search
        useMatchStore.getState().startLookup(
          selection.id, combinedDesc, qty, fileId, startRow, endRow,
        );
      }

      // 2. Create chat panel + request LLM analysis
      const chatStore = useChatPanelStore.getState();
      const panelId = chatStore.createPanel(selection.id, label);
      chatStore.setAnalyzing(panelId, true);

      // Create abort controller for this request
      const controller = new AbortController();
      abortControllers.current.set(selection.id, controller);

      analyzeSelection(selection.id, descriptions, combinedDesc, controller.signal)
        .then((response) => {
          // Re-read store at resolution time for latest state
          const store = useChatPanelStore.getState();
          if (!store.panelExists(panelId)) return;

          if (!isValidChatMessage(response)) {
            console.error('[useSelectionPipeline] Invalid chat message response:', response);
            store.addMessage(panelId, {
              id: `err-${Date.now()}`,
              item_id: selection.id,
              role: "system",
              content: "Analysis returned invalid data format",
              created_at: new Date().toISOString(),
            });
            store.setAnalyzing(panelId, false);
            return;
          }
          store.addMessage(panelId, response);
          store.setAnalyzing(panelId, false);
        })
        .catch((err) => {
          if (err.name === 'AbortError') return;

          const store = useChatPanelStore.getState();
          if (!store.panelExists(panelId)) return;

          store.addMessage(panelId, {
            id: `err-${Date.now()}`,
            item_id: selection.id,
            role: "system",
            content: `Analysis failed: ${err instanceof Error ? err.message : "Unknown error"}`,
            created_at: new Date().toISOString(),
          });
          store.setAnalyzing(panelId, false);
        })
        .finally(() => {
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
          useChatPanelStore.getState().removePanel(panel.id);
        }
        // Remove associated match results
        useMatchStore.getState().clearSelection(id);
        // Clean up tracking
        processedIds.current.delete(id);
      }
    }
  }, [selections]);
}
