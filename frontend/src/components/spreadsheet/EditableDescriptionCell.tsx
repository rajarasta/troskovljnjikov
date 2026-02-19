"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useAutoComplete } from "@/hooks/useAutoComplete";

interface ContextItem {
  item_number: string | null;
  description: string;
}

interface EditableDescriptionCellProps {
  value: string;
  itemId: string;
  context: ContextItem[];
  textColor?: string;
  onCommit: (itemId: string, newValue: string) => void;
}

/**
 * Shared CSS for both the mirror div and the textarea so their text layout
 * is pixel-identical. Both must have the same font, padding, border-width,
 * box-sizing, word-wrap, and white-space settings.
 */
const SHARED_TEXT_STYLE =
  "text-xs whitespace-pre-wrap break-words box-border px-1 py-0.5 border border-transparent rounded leading-[1.4]";

export function EditableDescriptionCell({
  value,
  itemId,
  context,
  textColor,
  onCommit,
}: EditableDescriptionCellProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [editValue, setEditValue] = useState(value);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const { suggestion, isLoading, request, accept, dismiss } =
    useAutoComplete({ debounceMs: 500, context });

  // Sync external value when not editing
  useEffect(() => {
    if (!isEditing) {
      setEditValue(value);
    }
  }, [value, isEditing]);

  // Focus textarea when entering edit mode
  useEffect(() => {
    if (isEditing && textareaRef.current) {
      const ta = textareaRef.current;
      ta.focus();
      ta.setSelectionRange(ta.value.length, ta.value.length);
    }
  }, [isEditing]);

  // Auto-resize textarea to match the mirror div's height
  useEffect(() => {
    if (isEditing && textareaRef.current && containerRef.current) {
      const height = containerRef.current.offsetHeight;
      textareaRef.current.style.height = `${height}px`;
    }
  }, [isEditing, editValue, suggestion]);

  const enterEditMode = useCallback(() => {
    setEditValue(value);
    setIsEditing(true);
  }, [value]);

  const exitEditMode = useCallback(
    (save: boolean) => {
      dismiss();
      setIsEditing(false);
      if (save && editValue !== value) {
        onCommit(itemId, editValue);
      } else {
        setEditValue(value);
      }
    },
    [dismiss, editValue, value, onCommit, itemId],
  );

  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLTextAreaElement>) => {
      const newValue = e.target.value;
      setEditValue(newValue);
      request(newValue);
    },
    [request],
  );

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === "Tab" && suggestion) {
        e.preventDefault();
        const accepted = accept();
        if (accepted) {
          const newValue = editValue + accepted;
          setEditValue(newValue);
          // Don't commit yet — user may keep editing. Commit happens on Enter/blur.
          request(newValue);
        }
      } else if (e.key === "Escape") {
        e.preventDefault();
        exitEditMode(false);
      } else if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        exitEditMode(true);
      }
    },
    [suggestion, accept, editValue, request, exitEditMode],
  );

  const handleBlur = useCallback(() => {
    exitEditMode(true);
  }, [exitEditMode]);

  // ── Read-only mode ──────────────────────────────────────────────
  if (!isEditing) {
    return (
      <div
        onDoubleClick={enterEditMode}
        className={`cursor-text whitespace-pre-wrap break-words ${textColor || "text-text-primary"}`}
      >
        {value || "\u00A0"}
      </div>
    );
  }

  // ── Edit mode with ghost text ──────────────────────────────────
  //
  // Technique: a mirror div and a textarea share identical CSS (font, padding,
  // border-width, box-sizing, word-wrap). The mirror div is in normal flow and
  // sizes the container. The textarea is absolutely positioned on top with
  // transparent background. The mirror renders the user text + ghost suggestion;
  // only the ghost part is visible since the user text portion is invisible.
  // The textarea's own text rendering overlaps the invisible user text exactly.
  return (
    <div className="relative" onClick={(e) => e.stopPropagation()}>
      {/* Mirror layer — sizes the container and renders ghost text */}
      <div
        ref={containerRef}
        aria-hidden
        className={`${SHARED_TEXT_STYLE} pointer-events-none min-h-[1.8em]`}
      >
        {/* User text — invisible, just for layout/spacing */}
        <span className="invisible">{editValue || "\u00A0"}</span>
        {/* Ghost suggestion — visible in muted color */}
        {suggestion && (
          <span className="text-text-muted/30">{suggestion}</span>
        )}
      </div>

      {/* Actual textarea — positioned on top, transparent background */}
      <textarea
        ref={textareaRef}
        value={editValue}
        onChange={handleChange}
        onKeyDown={handleKeyDown}
        onBlur={handleBlur}
        rows={1}
        className={`
          absolute inset-0 w-full resize-none overflow-hidden
          bg-transparent text-text-primary
          outline-none focus:ring-1 focus:ring-accent-purple/30
          ${SHARED_TEXT_STYLE}
          !border-accent-purple
        `}
      />

      {/* Loading indicator */}
      {isLoading && (
        <div className="absolute top-0.5 right-1 w-3 h-3">
          <div className="w-full h-full border border-text-muted/30 border-t-accent-purple/60 rounded-full animate-spin" />
        </div>
      )}
    </div>
  );
}
