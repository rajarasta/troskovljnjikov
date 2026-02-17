"use client";

import { useState, useCallback, useRef, type KeyboardEvent } from "react";
import { SendHorizonal, ImagePlus, X, Globe, Loader2 } from "lucide-react";

// ── Component ───────────────────────────────────────────────────────

interface ChatInputProps {
  onSend: (message: string, image?: File) => void;
  onSearchPrices?: () => void;
  disabled?: boolean;
  searchDisabled?: boolean;
  isSearching?: boolean;
}

export default function ChatInput({
  onSend,
  onSearchPrices,
  disabled = false,
  searchDisabled = false,
  isSearching = false,
}: ChatInputProps) {
  const [value, setValue] = useState("");
  const [image, setImage] = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const canSend = (value.trim().length > 0 || image !== null) && !disabled;

  const handleSend = useCallback(() => {
    const trimmed = value.trim();
    if ((!trimmed && !image) || disabled) return;

    onSend(trimmed || "(image)", image ?? undefined);
    setValue("");
    setImage(null);
    setImagePreview(null);

    // Reset textarea height
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  }, [value, image, disabled, onSend]);

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

  const handleImageSelect = useCallback(() => {
    fileInputRef.current?.click();
  }, []);

  const handleFileChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (!file) return;
      setImage(file);
      const url = URL.createObjectURL(file);
      setImagePreview(url);
      // Reset input so same file can be re-selected
      e.target.value = "";
    },
    []
  );

  const handleRemoveImage = useCallback(() => {
    if (imagePreview) URL.revokeObjectURL(imagePreview);
    setImage(null);
    setImagePreview(null);
  }, [imagePreview]);

  return (
    <div className="glass-panel flex flex-col gap-1.5 px-3 py-2">
      {/* Image preview */}
      {imagePreview && (
        <div className="relative inline-block self-start">
          <img
            src={imagePreview}
            alt="Attached"
            className="h-16 rounded border border-border-default object-cover"
          />
          <button
            onClick={handleRemoveImage}
            className="absolute -top-1.5 -right-1.5 p-0.5 rounded-full bg-bg-primary border border-border-default
                       text-text-muted hover:text-status-danger transition-colors"
          >
            <X className="w-3 h-3" />
          </button>
        </div>
      )}

      {/* Input row */}
      <div className="flex items-end gap-1.5">
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          className="hidden"
          onChange={handleFileChange}
        />
        <button
          onClick={handleImageSelect}
          disabled={disabled}
          className="shrink-0 p-1.5 rounded transition-all duration-150
                     disabled:opacity-30 disabled:cursor-not-allowed
                     enabled:hover:bg-accent-cyan/15 enabled:active:scale-95
                     text-text-muted hover:text-accent-cyan"
          title="Attach image"
        >
          <ImagePlus className="w-4 h-4" />
        </button>
        {onSearchPrices && (
          <button
            onClick={onSearchPrices}
            disabled={disabled || searchDisabled || isSearching}
            className="shrink-0 p-1.5 rounded transition-all duration-150
                       disabled:opacity-30 disabled:cursor-not-allowed
                       enabled:hover:bg-accent-purple/15 enabled:active:scale-95
                       text-text-muted hover:text-accent-purple"
            title="Search web prices"
          >
            {isSearching ? (
              <Loader2 className="w-4 h-4 animate-spin text-accent-purple" />
            ) : (
              <Globe className="w-4 h-4" />
            )}
          </button>
        )}
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
    </div>
  );
}
