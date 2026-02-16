import { useChatPanelStore } from "@/stores/chatPanelStore";
import type { AgentEvent } from "@/lib/types";

export const chatHandlers: Record<string, (event: AgentEvent) => void> = {
  "chat:token": (event) => {
    const payload = event.payload ?? {};
    const chatStore = useChatPanelStore.getState();
    const itemId = payload.item_id as string;
    const token = payload.token as string;
    const panel = chatStore.getPanelBySelection(itemId);
    if (panel) {
      const lastMsg = panel.messages[panel.messages.length - 1];
      if (lastMsg && lastMsg.role === "assistant" && lastMsg.id.startsWith("streaming-")) {
        const updatedMessages = [...panel.messages];
        updatedMessages[updatedMessages.length - 1] = {
          ...lastMsg,
          content: lastMsg.content + token,
        };
        useChatPanelStore.setState((s) => ({
          panels: s.panels.map((p) =>
            p.id === panel.id ? { ...p, messages: updatedMessages } : p,
          ),
        }));
      }
    }
  },

  "chat:complete": (event) => {
    const payload = event.payload ?? {};
    const chatStore = useChatPanelStore.getState();
    const itemId = payload.item_id as string;
    const panel = chatStore.getPanelBySelection(itemId);
    if (panel) {
      chatStore.setSending(panel.id, false);
    }
  },
};
