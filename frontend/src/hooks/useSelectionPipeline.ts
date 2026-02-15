import { useEffect, useRef } from "react";
import { useSelectionStore } from "@/stores/selectionStore";
import { useChatPanelStore } from "@/stores/chatPanelStore";
import { useMatchStore } from "@/stores/matchStore";
import { analyzeSelection } from "@/lib/api";
import type { ChatMessage } from "@/lib/types";

/**
 * Watches selection store. When a new selection is created:
 * 1. Triggers match lookup (deterministic pipeline -> column 2)
 * 2. Creates a chat panel and requests LLM analysis -> column 1
 */
export function useSelectionPipeline() {
  const selections = useSelectionStore((s) => s.selections);
  const startLookup = useMatchStore((s) => s.startLookup);
  const { createPanel, addMessage, setAnalyzing } = useChatPanelStore();
  const processedIds = useRef(new Set<string>());

  useEffect(() => {
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

      analyzeSelection(selection.id, descriptions, combinedDesc)
        .then((response) => {
          addMessage(panelId, response);
          setAnalyzing(panelId, false);
        })
        .catch((err) => {
          const errorMsg: ChatMessage = {
            id: `err-${Date.now()}`,
            item_id: selection.id,
            role: "system",
            content: `Analysis failed: ${err instanceof Error ? err.message : "Unknown error"}`,
            created_at: new Date().toISOString(),
          };
          addMessage(panelId, errorMsg);
          setAnalyzing(panelId, false);
        });
    }

    // Clean up processed IDs for removed selections
    const currentIds = new Set(selections.map((s) => s.id));
    for (const id of processedIds.current) {
      if (!currentIds.has(id)) processedIds.current.delete(id);
    }
  }, [selections, startLookup, createPanel, addMessage, setAnalyzing]);
}
