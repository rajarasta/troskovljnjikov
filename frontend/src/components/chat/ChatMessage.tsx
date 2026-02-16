"use client";

import { motion } from "framer-motion";
import type { ChatMessage as ChatMessageType } from "@/lib/types";

// ── Variants ────────────────────────────────────────────────────────

const messageVariants = {
  hidden: { opacity: 0, y: 6 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { type: "spring", damping: 20, stiffness: 300 },
  },
};

// ── Helpers ─────────────────────────────────────────────────────────

function formatTimestamp(iso: string): string {
  return new Date(iso).toLocaleTimeString("en-GB", {
    hour: "2-digit",
    minute: "2-digit",
  });
}

// ── Component ───────────────────────────────────────────────────────

interface ChatMessageProps {
  message: ChatMessageType;
}

export default function ChatMessage({ message }: ChatMessageProps) {
  const { role, content, created_at } = message;

  // System messages: centered, muted, small
  if (role === "system") {
    return (
      <motion.div
        variants={messageVariants}
        initial="hidden"
        animate="visible"
        className="flex justify-center px-4 py-1"
      >
        <div className="text-[11px] text-text-muted italic text-center max-w-[80%]">
          <p className="whitespace-pre-wrap">{content}</p>
          <span className="text-[10px] text-text-muted/60 font-mono mt-0.5 block">
            {formatTimestamp(created_at)}
          </span>
        </div>
      </motion.div>
    );
  }

  const isUser = role === "user";

  return (
    <motion.div
      variants={messageVariants}
      initial="hidden"
      animate="visible"
      className={`flex px-3 py-0.5 ${isUser ? "justify-end" : "justify-start"}`}
    >
      <div
        className={`
          max-w-[75%] px-3 py-2 rounded-lg text-sm
          ${
            isUser
              ? "bg-accent-cyan/15 border border-accent-cyan/25 text-text-primary rounded-br-sm"
              : "glass-panel text-text-primary rounded-bl-sm"
          }
        `}
      >
        <p className="whitespace-pre-wrap break-words leading-relaxed">
          {content}
        </p>
        <span
          className={`
            text-[10px] font-mono mt-1 block
            ${isUser ? "text-accent-cyan/50 text-right" : "text-text-muted"}
          `}
        >
          {formatTimestamp(created_at)}
        </span>
      </div>
    </motion.div>
  );
}
