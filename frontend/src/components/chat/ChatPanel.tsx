"use client";

import { useCallback, useEffect, useRef } from "react";
import { X, Loader2, MessageSquare } from "lucide-react";
import { useChatPanelStore } from "@/stores/chatPanelStore";
import { useSelectionStore } from "@/stores/selectionStore";
import { sendChatMessage } from "@/lib/api";
import type { ChatMessage as ChatMessageType } from "@/lib/types";
import ChatMessage from "./ChatMessage";
import ChatInput from "./ChatInput";

interface ChatPanelProps {
  panelId: string;
}

export default function ChatPanelComponent({ panelId }: ChatPanelProps) {
  const panel = useChatPanelStore((s) => s.panels.find((p) => p.id === panelId));
  const activePanelId = useChatPanelStore((s) => s.activePanelId);
  const { removePanel, setActive, addMessage, setSending, setError } = useChatPanelStore();
  const setSelectionActive = useSelectionStore((s) => s.setActive);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const isActive = activePanelId === panelId;

  // Auto-scroll on new messages
  useEffect(() => {
    if (isActive) {
      messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [panel?.messages.length, isActive]);

  const handleClick = useCallback(() => {
    if (!panel) return;
    setActive(panelId);
    setSelectionActive(panel.selectionId);
  }, [panelId, panel, setActive, setSelectionActive]);

  const handleClose = useCallback((e: React.MouseEvent) => {
    e.stopPropagation();
    if (!panel) return;
    removePanel(panelId);
  }, [panelId, panel, removePanel]);

  const handleSend = useCallback(async (content: string) => {
    if (!panel) return;
    const optimisticId = `opt-${Date.now()}`;
    const userMsg: ChatMessageType = {
      id: optimisticId,
      item_id: panel.selectionId,
      role: "user",
      content,
      created_at: new Date().toISOString(),
    };
    addMessage(panelId, userMsg);
    setSending(panelId, true);
    setError(panelId, null);
    try {
      const response = await sendChatMessage(panel.selectionId, content);
      addMessage(panelId, response);
    } catch (err) {
      setError(panelId, err instanceof Error ? err.message : "Failed to send");
    } finally {
      setSending(panelId, false);
    }
  }, [panel, panelId, addMessage, setSending, setError]);

  if (!panel) return null;

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
      <div className={`overflow-y-auto ${isActive ? "max-h-64" : "max-h-20"} transition-all duration-200`}>
        {panel.messages.length === 0 && !panel.isAnalyzing ? (
          <div className="text-[10px] text-text-muted px-3 py-2">
            Waiting for analysis...
          </div>
        ) : (
          <div className="flex flex-col gap-1 py-1">
            {panel.messages.map((msg) => (
              <ChatMessage key={msg.id} message={msg} />
            ))}
            <div ref={messagesEndRef} />
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
          <ChatInput onSend={handleSend} disabled={panel.isSending || panel.isAnalyzing} />
        </div>
      )}
    </div>
  );
}
