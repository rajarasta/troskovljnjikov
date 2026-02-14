"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, Loader2, MessageSquare } from "lucide-react";
import { fetchChatHistory, sendChatMessage } from "@/lib/api";
import type { BoQItem, ChatMessage as ChatMessageType } from "@/lib/types";
import ChatMessage from "./ChatMessage";
import ChatInput from "./ChatInput";

// ── Animation variants ──────────────────────────────────────────────

const backdropVariants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1 },
  exit: { opacity: 0 },
};

const drawerVariants = {
  hidden: { y: "100%" },
  visible: {
    y: 0,
    transition: { type: "spring", damping: 28, stiffness: 220 },
  },
  exit: {
    y: "100%",
    transition: { type: "spring", damping: 30, stiffness: 250 },
  },
};

// ── Component ───────────────────────────────────────────────────────

interface ChatDrawerProps {
  itemId: string | null;
  item: BoQItem | null;
  isOpen: boolean;
  onClose: () => void;
}

export default function ChatDrawer({
  itemId,
  item,
  isOpen,
  onClose,
}: ChatDrawerProps) {
  const [messages, setMessages] = useState<ChatMessageType[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const messagesContainerRef = useRef<HTMLDivElement>(null);

  // ── Fetch chat history when drawer opens ──────────────────────────

  useEffect(() => {
    if (!isOpen || !itemId) {
      setMessages([]);
      setError(null);
      return;
    }

    let cancelled = false;

    async function loadHistory() {
      setIsLoading(true);
      setError(null);
      try {
        const history = await fetchChatHistory(itemId!);
        if (!cancelled) {
          setMessages(history);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load chat history");
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    loadHistory();
    return () => {
      cancelled = true;
    };
  }, [isOpen, itemId]);

  // ── Auto-scroll on new messages ───────────────────────────────────

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // ── Send message handler ──────────────────────────────────────────

  const handleSend = useCallback(
    async (content: string) => {
      if (!itemId || isSending) return;

      // Optimistic user message
      const optimisticId = `optimistic-${Date.now()}`;
      const userMessage: ChatMessageType = {
        id: optimisticId,
        item_id: itemId,
        role: "user",
        content,
        created_at: new Date().toISOString(),
      };

      setMessages((prev) => [...prev, userMessage]);
      setIsSending(true);
      setError(null);

      try {
        const response = await sendChatMessage(itemId, content);
        setMessages((prev) => [...prev, response]);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to send message");
      } finally {
        setIsSending(false);
      }
    },
    [itemId, isSending]
  );

  // ── Truncate long descriptions for header ─────────────────────────

  const headerTitle = item
    ? item.description.length > 60
      ? `${item.description.slice(0, 57)}...`
      : item.description
    : "Chat";

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            key="chat-drawer-backdrop"
            variants={backdropVariants}
            initial="hidden"
            animate="visible"
            exit="exit"
            onClick={onClose}
            className="fixed inset-0 z-40 bg-black/30"
          />

          {/* Drawer */}
          <motion.div
            key="chat-drawer"
            variants={drawerVariants}
            initial="hidden"
            animate="visible"
            exit="exit"
            className="fixed bottom-0 left-0 right-0 z-50 h-[60vh] flex flex-col
                       glass-panel border-t border-border-default glow-cyan rounded-t-xl"
          >
            {/* Header */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-border-default shrink-0">
              <div className="flex items-center gap-2 min-w-0">
                <MessageSquare className="w-4 h-4 text-accent-cyan shrink-0" />
                <h2 className="text-sm font-semibold text-text-primary truncate">
                  Chat about{" "}
                  <span className="text-accent-cyan">{headerTitle}</span>
                </h2>
              </div>
              <button
                onClick={onClose}
                className="p-1 rounded hover:bg-bg-hover text-text-muted hover:text-text-primary transition-colors shrink-0"
                title="Close chat"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Messages area */}
            <div
              ref={messagesContainerRef}
              className="flex-1 overflow-y-auto py-3 min-h-0"
            >
              {isLoading ? (
                <div className="flex items-center justify-center h-full gap-2 text-text-secondary">
                  <Loader2 className="w-4 h-4 animate-spin text-accent-cyan" />
                  <span className="text-sm">Loading chat history...</span>
                </div>
              ) : messages.length === 0 ? (
                <div className="flex items-center justify-center h-full text-text-muted text-sm">
                  No messages yet. Start the conversation below.
                </div>
              ) : (
                <div className="flex flex-col gap-1.5">
                  {messages.map((msg) => (
                    <ChatMessage key={msg.id} message={msg} />
                  ))}
                  <div ref={messagesEndRef} />
                </div>
              )}

              {/* Error display */}
              {error && (
                <div className="mx-4 mt-2 px-3 py-2 rounded bg-status-danger/10 border border-status-danger/20 text-status-danger text-xs">
                  {error}
                </div>
              )}
            </div>

            {/* Input area */}
            <div className="shrink-0 border-t border-border-default px-2 py-2">
              <ChatInput onSend={handleSend} disabled={isSending || isLoading} />
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
