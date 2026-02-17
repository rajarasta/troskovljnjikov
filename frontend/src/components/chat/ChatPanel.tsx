"use client";

import { useCallback, useEffect, useMemo, useRef } from "react";
import { X, Loader2, MessageSquare } from "lucide-react";
import { useChatPanelStore } from "@/stores/chatPanelStore";
import { useSelectionStore } from "@/stores/selectionStore";
import { sendChatMessageStreaming, sendChatMessageWithImage, triggerPriceSearch, triggerBatchPriceSearch } from "@/lib/api";
import { useSearchStore } from "@/stores/searchStore";
import type { ChatMessage as ChatMessageType } from "@/lib/types";
import ChatMessage from "./ChatMessage";
import ChatInput from "./ChatInput";

interface ChatPanelProps {
  panelId: string;
  embedded?: boolean;
}

export default function ChatPanelComponent({ panelId, embedded }: ChatPanelProps) {
  const panel = useChatPanelStore((s) => s.panels.find((p) => p.id === panelId));
  const activePanelId = useChatPanelStore((s) => s.activePanelId);
  const setActive = useChatPanelStore((s) => s.setActive);
  const setSelectionActive = useSelectionStore((s) => s.setActive);
  const messagesContainerRef = useRef<HTMLDivElement>(null);
  const prevActiveRef = useRef(false);

  const isActive = activePanelId === panelId;

  const scrollToBottom = useCallback(() => {
    const el = messagesContainerRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, []);

  // Auto-scroll on new messages
  useEffect(() => {
    if (isActive && panel?.messages.length) {
      scrollToBottom();
    }
  }, [panel?.messages.length, isActive, scrollToBottom]);

  // Auto-scroll when panel becomes active
  useEffect(() => {
    if (isActive && !prevActiveRef.current) {
      scrollToBottom();
    }
    prevActiveRef.current = isActive;
  }, [isActive, scrollToBottom]);

  const handleClick = useCallback(() => {
    if (!panel) return;
    setActive(panelId);
    setSelectionActive(panel.selectionId);
  }, [panelId, panel, setActive, setSelectionActive]);

  const handleClose = useCallback((e: React.MouseEvent) => {
    e.stopPropagation();
    if (!panel) return;
    // Remove the associated selection - panel removal will be handled by useSelectionPipeline cleanup
    const removeSelection = useSelectionStore.getState().removeSelection;
    removeSelection(panel.selectionId);
  }, [panel]);

  // Resolve selection to BoQ item IDs for search status tracking.
  // Subscribe to selection list (stable ref) and derive IDs in useMemo to avoid
  // creating a new array on every store update (which would cause infinite re-renders).
  const selections = useSelectionStore((s) => s.selections);
  const selectionItemIds = useMemo(() => {
    if (!panel) return [] as string[];
    const sel = selections.find((s) => s.id === panel.selectionId);
    return sel ? sel.items.map((i) => i.id) : ([] as string[]);
  }, [selections, panel]);
  const isSearching = useSearchStore((s) =>
    selectionItemIds.some((id) => s.status[id] === "searching")
  );

  const handleSearchPrices = useCallback(async () => {
    if (!panel) return;
    try {
      // Resolve selection to actual BoQ item IDs (selectionId is a selection store ID, not a DB item ID)
      const selection = useSelectionStore.getState().selections.find((s) => s.id === panel.selectionId);
      const itemIds = selection ? selection.items.map((i) => i.id) : [];
      if (itemIds.length === 0) return;

      if (itemIds.length === 1) {
        await triggerPriceSearch(itemIds[0], {
          description: selection?.items[0].full_description || selection?.items[0].description,
        });
      } else {
        // Build descriptions map for synthetic items
        const descriptions: Record<string, string> = {};
        selection?.items.forEach((item) => {
          if (item.id.startsWith("excel-cell-")) {
            descriptions[item.id] = item.full_description || item.description || "";
          }
        });
        await triggerBatchPriceSearch(itemIds, {
          descriptions: Object.keys(descriptions).length > 0 ? descriptions : undefined,
        });
      }
    } catch (err) {
      const store = useChatPanelStore.getState();
      store.setError(panelId, err instanceof Error ? err.message : "Search failed");
    }
  }, [panel, panelId]);

  const handleSend = useCallback(async (content: string, image?: File) => {
    if (!panel) return;
    const store = useChatPanelStore.getState();
    const optimisticId = `opt-${Date.now()}`;

    // Create local image preview URL for display
    const imageUrl = image ? URL.createObjectURL(image) : undefined;

    const userMsg: ChatMessageType = {
      id: optimisticId,
      item_id: panel.selectionId,
      role: "user",
      content,
      created_at: new Date().toISOString(),
      image_url: imageUrl,
    };
    store.addMessage(panelId, userMsg);
    store.setSending(panelId, true);
    store.setError(panelId, null);
    try {
      if (image) {
        // Image messages use the non-streaming path
        const response = await sendChatMessageWithImage(panel.selectionId, content, image);
        useChatPanelStore.getState().addMessage(panelId, response);
        useChatPanelStore.getState().setSending(panelId, false);
      } else {
        // Create a placeholder streaming message that WS tokens will fill
        const streamingMsg: ChatMessageType = {
          id: `streaming-${Date.now()}`,
          item_id: panel.selectionId,
          role: "assistant",
          content: "",
          created_at: new Date().toISOString(),
        };
        useChatPanelStore.getState().addMessage(panelId, streamingMsg);

        // Fire the streaming request — tokens arrive via WS (chat:token events)
        // The final persisted message replaces the streaming placeholder
        const finalMsg = await sendChatMessageStreaming(panel.selectionId, content);
        // Replace streaming placeholder with final persisted message
        useChatPanelStore.setState((s) => ({
          panels: s.panels.map((p) =>
            p.id === panelId
              ? { ...p, messages: p.messages.map((m) => m.id.startsWith("streaming-") ? finalMsg : m) }
              : p,
          ),
        }));
        useChatPanelStore.getState().setSending(panelId, false);
      }
    } catch (err) {
      useChatPanelStore.getState().setError(panelId, err instanceof Error ? err.message : "Failed to send");
      useChatPanelStore.getState().setSending(panelId, false);
    }
  }, [panel, panelId]);

  if (!panel) return null;

  // Embedded mode: no outer wrapper or header, used inside ChatPanelList tabs
  if (embedded) {
    return (
      <div className="flex flex-col h-full overflow-hidden">
        <div ref={messagesContainerRef} className="flex-1 overflow-y-auto min-h-0">
          {panel.messages.length === 0 && !panel.isAnalyzing ? (
            <div className="text-[10px] text-text-muted px-3 py-2">
              Waiting for analysis...
            </div>
          ) : (
            <div className="flex flex-col gap-1 py-1">
              {panel.messages.map((msg) => (
                <ChatMessage key={msg.id} message={msg} />
              ))}
            </div>
          )}
          {panel.error && (
            <div className="mx-2 mb-1 px-2 py-1 rounded bg-status-danger/10 border border-status-danger/20 text-status-danger text-[10px]">
              {panel.error}
            </div>
          )}
        </div>
        <div className="shrink-0 border-t border-border-default/50 px-2 py-1.5">
          <ChatInput
            onSend={handleSend}
            onSearchPrices={handleSearchPrices}
            disabled={panel.isSending || panel.isAnalyzing}
            isSearching={isSearching}
          />
        </div>
      </div>
    );
  }

  return (
    <div
      onClick={handleClick}
      className={`
        flex flex-col rounded-lg border transition-all duration-150 overflow-hidden
        ${isActive
          ? "border-accent-cyan/40 glow-cyan bg-bg-primary"
          : "border-border-default bg-bg-secondary/50 hover:border-border-default/80"
        }
      `}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-2 border-b border-border-default/50 shrink-0">
        <div className="flex items-center gap-1.5 min-w-0">
          {panel.isAnalyzing ? (
            <Loader2 className="w-3 h-3 text-accent-cyan animate-spin shrink-0" />
          ) : (
            <MessageSquare className="w-3 h-3 text-accent-cyan shrink-0" />
          )}
          <span className="text-[11px] font-medium text-text-primary truncate">
            {panel.label}
          </span>
        </div>
        <button
          onClick={handleClose}
          className="p-0.5 rounded hover:bg-bg-hover text-text-muted hover:text-text-primary transition-colors shrink-0"
        >
          <X className="w-3 h-3" />
        </button>
      </div>

      {/* Messages */}
      <div ref={messagesContainerRef} className={`overflow-y-auto ${isActive ? "max-h-64" : "max-h-20"} transition-all duration-200`}>
        {panel.messages.length === 0 && !panel.isAnalyzing ? (
          <div className="text-[10px] text-text-muted px-3 py-2">
            Waiting for analysis...
          </div>
        ) : (
          <div className="flex flex-col gap-1 py-1">
            {panel.messages.map((msg) => (
              <ChatMessage key={msg.id} message={msg} />
            ))}
          </div>
        )}
        {panel.error && (
          <div className="mx-2 mb-1 px-2 py-1 rounded bg-status-danger/10 border border-status-danger/20 text-status-danger text-[10px]">
            {panel.error}
          </div>
        )}
      </div>

      {/* Input (only shown when active) */}
      {isActive && (
        <div className="shrink-0 border-t border-border-default/50 px-2 py-1.5">
          <ChatInput
            onSend={handleSend}
            onSearchPrices={handleSearchPrices}
            disabled={panel.isSending || panel.isAnalyzing}
            isSearching={isSearching}
          />
        </div>
      )}
    </div>
  );
}
