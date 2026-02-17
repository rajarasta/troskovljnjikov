import { useSearchStore } from "@/stores/searchStore";
import { useChatPanelStore } from "@/stores/chatPanelStore";
import { useSelectionStore } from "@/stores/selectionStore";
import type { AgentEvent, WebQuote } from "@/lib/types";

/** Find the chat panel whose selection contains the given BoQ item ID. */
function findPanelByItemId(itemId: string) {
  const selections = useSelectionStore.getState().selections;
  const sel = selections.find((s) => s.items.some((i) => i.id === itemId));
  if (!sel) return undefined;
  return useChatPanelStore.getState().getPanelBySelection(sel.id);
}

export const searchHandlers: Record<string, (event: AgentEvent) => void> = {
  "search:started": (event) => {
    const payload = event.payload ?? {};
    const itemId = payload.item_id as string;
    useSearchStore.getState().setStarted(itemId);
  },

  "search:quote_found": (event) => {
    const payload = event.payload ?? {};
    const itemId = payload.item_id as string;
    const quote = payload.quote as WebQuote;
    useSearchStore.getState().addQuote(itemId, quote);
  },

  "search:complete": (event) => {
    const payload = event.payload ?? {};
    const itemId = payload.item_id as string;

    useSearchStore.getState().setComplete(itemId, {
      quote_count: (payload.quote_count as number) || 0,
      best_quote: (payload.best_quote as WebQuote) || null,
      computed: (payload.computed as unknown) as import("@/lib/types").ComputedTotal | null,
      reasoning: (payload.reasoning as string) || "",
      error: payload.error as string | undefined,
    });

    // Inject a search result message into the chat panel for this item
    const chatStore = useChatPanelStore.getState();
    const panel = findPanelByItemId(itemId);
    if (panel && !payload.error) {
      const bestQuote = payload.best_quote as WebQuote | null;
      const reasoning = (payload.reasoning as string) || "";
      const quoteCount = (payload.quote_count as number) || 0;

      let content = `**Web Price Search Complete** — ${quoteCount} quote(s) found\n\n`;
      if (bestQuote) {
        content += `**Best match:** ${bestQuote.product_name}\n`;
        content += `**Price:** ${bestQuote.unit_price} ${bestQuote.currency}`;
        content += bestQuote.vat_included ? " (PDV uklj.)" : " (bez PDV-a)";
        content += `\n**Vendor:** ${bestQuote.vendor}\n`;
        content += `**Confidence:** ${Math.round(bestQuote.confidence * 100)}%\n`;
        if (bestQuote.url) {
          content += `**Link:** ${bestQuote.url}\n`;
        }
      }
      if (reasoning) {
        content += `\n${reasoning}`;
      }

      chatStore.addMessage(panel.id, {
        id: `search-${itemId}-${Date.now()}`,
        item_id: itemId,
        role: "assistant",
        content,
        created_at: new Date().toISOString(),
      });
    }
  },
};
