"use client";

import { useState, useCallback, useRef, type KeyboardEvent } from "react";
import { SendHorizonal } from "lucide-react";

// ── Component ───────────────────────────────────────────────────────

interface ChatInputProps {
  onSend: (message: string) => void;
  disabled?: boolean;
}

export default function ChatInput({ onSend, disabled = false }: ChatInputProps) {
  const [value, setValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const canSend = value.trim().length > 0 && !disabled;

  const handleSend = useCallback(() => {
    const trimmed = value.trim();
    if (!trimmed || disabled) return;

    onSend(trimmed);
    setValue("");

    // Reset textarea height
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  }, [value, disabled, onSend]);

  const handleKeyDown = useCallback(
    (e: KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSend();
      }
    },
    [handleSend]
  );

  const handleInput = useCallback(() => {
    const textarea = textareaRef.current;
    if (!textarea) return;

    // Auto-resize: reset then grow to content, max 4 lines (~80px)
    textarea.style.height = "auto";
    textarea.style.height = `${Math.min(textarea.scrollHeight, 80)}px`;
  }, []);

  return (
    <div className="glass-panel flex items-end gap-2 px-3 py-2">
      <textarea
        ref={textareaRef}
        value={value}
        onChange={(e) => {
          setValue(e.target.value);
          handleInput();
        }}
        onKeyDown={handleKeyDown}
        disabled={disabled}
        placeholder={disabled ? "Sending..." : "Type a message..."}
        rows={1}
        className="flex-1 resize-none bg-transparent text-sm text-text-primary placeholder:text-text-muted
                   outline-none border border-transparent rounded px-2 py-1.5
                   focus:border-accent-cyan/40 transition-colors duration-200
                   disabled:opacity-50 disabled:cursor-not-allowed
                   max-h-20 leading-snug"
      />
      <button
        onClick={handleSend}
        disabled={!canSend}
        className="shrink-0 p-1.5 rounded transition-all duration-150
                   disabled:opacity-30 disabled:cursor-not-allowed
                   enabled:hover:bg-accent-cyan/15 enabled:active:scale-95
                   text-accent-cyan"
        title="Send message"
      >
        <SendHorizonal className="w-4 h-4" />
      </button>
    </div>
  );
}
