# Inline Chat Layout Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the boq-matcher 4-column layout (Sidebar | Match Details | Current BOQ | Working Copy) with a new layout (Chat | Regex Results | Current BOQ | Edited) featuring per-selection inline chat and deterministic comparison pipeline.

**Architecture:** Multi-area selection in Current BOQ triggers two parallel pipelines: (1) deterministic regex/text matching displayed in column 2, and (2) LLM auto-analysis injected as the first message in per-selection chat panels in column 1. The sidebar moves to a top bar with popovers.

**Tech Stack:** Next.js 15, React 19, TypeScript, Zustand 5, Tailwind CSS v4, Framer Motion 11, FastAPI, SQLite, PydanticAI

---

All file paths are relative to `.worktrees/boq-matcher/`.

## Task 1: Create Selection Store

**Files:**
- Create: `frontend/src/stores/selectionStore.ts`

**Step 1: Create the store**

```typescript
import { create } from "zustand";
import type { BoQItem } from "@/lib/types";

const SELECTION_COLORS = [
  "cyan",
  "purple",
  "amber",
  "emerald",
  "rose",
  "sky",
] as const;

export type SelectionColor = (typeof SELECTION_COLORS)[number];

export interface BoQSelection {
  id: string;
  startIndex: number;
  endIndex: number;
  items: BoQItem[];
  color: SelectionColor;
}

interface SelectionState {
  selections: BoQSelection[];
  activeSelectionId: string | null;
  dragAnchorIndex: number | null;

  addSelection: (startIndex: number, endIndex: number, items: BoQItem[]) => string;
  removeSelection: (id: string) => void;
  setActive: (id: string | null) => void;
  clearAll: () => void;
  setDragAnchor: (index: number | null) => void;
}

let selectionCounter = 0;

export const useSelectionStore = create<SelectionState>((set, get) => ({
  selections: [],
  activeSelectionId: null,
  dragAnchorIndex: null,

  addSelection: (startIndex, endIndex, items) => {
    const id = `sel-${++selectionCounter}-${Date.now()}`;
    const colorIndex = get().selections.length % SELECTION_COLORS.length;
    const color = SELECTION_COLORS[colorIndex];
    const selection: BoQSelection = {
      id,
      startIndex: Math.min(startIndex, endIndex),
      endIndex: Math.max(startIndex, endIndex),
      items,
      color,
    };
    set((s) => ({
      selections: [...s.selections, selection],
      activeSelectionId: id,
    }));
    return id;
  },

  removeSelection: (id) => {
    set((s) => ({
      selections: s.selections.filter((sel) => sel.id !== id),
      activeSelectionId: s.activeSelectionId === id ? null : s.activeSelectionId,
    }));
  },

  setActive: (id) => set({ activeSelectionId: id }),
  clearAll: () => set({ selections: [], activeSelectionId: null }),
  setDragAnchor: (index) => set({ dragAnchorIndex: index }),
}));
```

**Step 2: Verify the store compiles**

Run from `frontend/`:
```bash
npx tsc --noEmit src/stores/selectionStore.ts
```
Expected: no errors.

**Step 3: Commit**

```bash
git add frontend/src/stores/selectionStore.ts
git commit -m "feat: add selection store for multi-area BoQ selection"
```

---

## Task 2: Create Chat Panel Store

**Files:**
- Create: `frontend/src/stores/chatPanelStore.ts`

**Step 1: Create the store**

```typescript
import { create } from "zustand";
import type { ChatMessage } from "@/lib/types";

export interface ChatPanel {
  id: string;
  selectionId: string;
  label: string;
  messages: ChatMessage[];
  isAnalyzing: boolean;
  isSending: boolean;
  error: string | null;
}

interface ChatPanelState {
  panels: ChatPanel[];
  activePanelId: string | null;

  createPanel: (selectionId: string, label: string) => string;
  removePanel: (panelId: string) => void;
  setActive: (panelId: string | null) => void;
  addMessage: (panelId: string, message: ChatMessage) => void;
  setAnalyzing: (panelId: string, analyzing: boolean) => void;
  setSending: (panelId: string, sending: boolean) => void;
  setError: (panelId: string, error: string | null) => void;
  getPanelBySelection: (selectionId: string) => ChatPanel | undefined;
}

let panelCounter = 0;

export const useChatPanelStore = create<ChatPanelState>((set, get) => ({
  panels: [],
  activePanelId: null,

  createPanel: (selectionId, label) => {
    const existing = get().panels.find((p) => p.selectionId === selectionId);
    if (existing) {
      set({ activePanelId: existing.id });
      return existing.id;
    }
    const id = `chat-${++panelCounter}-${Date.now()}`;
    const panel: ChatPanel = {
      id,
      selectionId,
      label,
      messages: [],
      isAnalyzing: false,
      isSending: false,
      error: null,
    };
    set((s) => ({
      panels: [...s.panels, panel],
      activePanelId: id,
    }));
    return id;
  },

  removePanel: (panelId) => {
    set((s) => ({
      panels: s.panels.filter((p) => p.id !== panelId),
      activePanelId: s.activePanelId === panelId ? null : s.activePanelId,
    }));
  },

  setActive: (panelId) => set({ activePanelId: panelId }),

  addMessage: (panelId, message) => {
    set((s) => ({
      panels: s.panels.map((p) =>
        p.id === panelId ? { ...p, messages: [...p.messages, message] } : p,
      ),
    }));
  },

  setAnalyzing: (panelId, analyzing) => {
    set((s) => ({
      panels: s.panels.map((p) =>
        p.id === panelId ? { ...p, isAnalyzing: analyzing } : p,
      ),
    }));
  },

  setSending: (panelId, sending) => {
    set((s) => ({
      panels: s.panels.map((p) =>
        p.id === panelId ? { ...p, isSending: sending } : p,
      ),
    }));
  },

  setError: (panelId, error) => {
    set((s) => ({
      panels: s.panels.map((p) =>
        p.id === panelId ? { ...p, error } : p,
      ),
    }));
  },

  getPanelBySelection: (selectionId) => {
    return get().panels.find((p) => p.selectionId === selectionId);
  },
}));
```

**Step 2: Verify compiles**

```bash
npx tsc --noEmit src/stores/chatPanelStore.ts
```

**Step 3: Commit**

```bash
git add frontend/src/stores/chatPanelStore.ts
git commit -m "feat: add chat panel store for per-selection conversations"
```

---

## Task 3: Add Selection-Based Match API

**Files:**
- Modify: `frontend/src/lib/api.ts` — add `matchSelection()` function
- Modify: `frontend/src/lib/types.ts` — add `SelectionMatchRequest` type

**Step 1: Add type**

In `frontend/src/lib/types.ts`, add after the `ChatMessage` interface:

```typescript
// ── Selection Models ────────────────────────────────────────────────

export interface SelectionMatchRequest {
  descriptions: string[];
  quantities: number[];
  threshold?: number;
  max_results?: number;
}

export interface SelectionAnalysisRequest {
  item_descriptions: string[];
  match_context: MatchResult[];
}
```

**Step 2: Add API functions**

In `frontend/src/lib/api.ts`, add:

```typescript
/** Match multiple items from a selection at once */
export async function matchSelection(
  request: SelectionMatchRequest,
): Promise<MatchResponse> {
  const res = await fetch(`${API_BASE}/match`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      description: request.descriptions.join("\n"),
      quantity: request.quantities[0] ?? 0,
      threshold: request.threshold ?? 0.3,
      max_results: request.max_results ?? 20,
    }),
  });
  if (!res.ok) throw new Error(`Match failed: ${res.statusText}`);
  return res.json();
}

/** Request LLM analysis for a selection */
export async function analyzeSelection(
  selectionId: string,
  itemDescriptions: string[],
  matchContext: string,
): Promise<ChatMessage> {
  // Reuse the chat endpoint — send as a "system" initiated message
  // The selectionId is used as the item_id for now
  const res = await fetch(`${API_BASE}/chat/${selectionId}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      content: `[AUTO-ANALYSIS]\nSelected items:\n${itemDescriptions.join("\n")}\n\nMatch context:\n${matchContext}`,
    }),
  });
  if (!res.ok) throw new Error(`Analysis failed: ${res.statusText}`);
  return res.json();
}
```

**Step 3: Commit**

```bash
git add frontend/src/lib/types.ts frontend/src/lib/api.ts
git commit -m "feat: add selection-based match and analysis API functions"
```

---

## Task 4: Update SpreadsheetView for Multi-Selection

**Files:**
- Modify: `frontend/src/components/spreadsheet/SpreadsheetView.tsx`

This is the biggest UI change. Replace single-row click with multi-area selection (click, shift+click, drag).

**Step 1: Rewrite SpreadsheetView**

Replace the existing `handleRowClick` and row rendering logic. Key changes:

- Import `useSelectionStore` instead of relying solely on `selectedRow`
- Add `onMouseDown` / `onMouseMove` / `onMouseUp` handlers on `<tbody>` for drag selection
- Shift+click extends from last anchor
- Plain click creates a new single-row selection
- Each selection's rows get a colored left border + tinted background from `selection.color`
- Keep the `forwardRef` pattern for scroll sync

```typescript
// Replace the handleRowClick callback with:
const { selections, activeSelectionId, addSelection, setActive, setDragAnchor, dragAnchorIndex } = useSelectionStore();

const handleMouseDown = useCallback((index: number, e: React.MouseEvent) => {
  if (e.shiftKey && dragAnchorIndex !== null) {
    // Shift+click: extend selection from anchor
    const start = Math.min(dragAnchorIndex, index);
    const end = Math.max(dragAnchorIndex, index);
    const selectedItems = items.slice(start, end + 1);
    addSelection(start, end, selectedItems);
  } else {
    // Plain click: start new potential drag
    setDragAnchor(index);
  }
}, [items, dragAnchorIndex, addSelection, setDragAnchor]);

const handleMouseUp = useCallback((index: number) => {
  if (dragAnchorIndex === null) return;
  const start = Math.min(dragAnchorIndex, index);
  const end = Math.max(dragAnchorIndex, index);
  const selectedItems = items.slice(start, end + 1);
  addSelection(start, end, selectedItems);
}, [items, dragAnchorIndex, addSelection]);
```

- For row styling, build a map: `rowIndex → selection color` from all selections
- Active selection's rows get a stronger highlight

**Step 2: Verify the component renders without errors**

Run from `frontend/`:
```bash
npm run build
```
Expected: build succeeds.

**Step 3: Commit**

```bash
git add frontend/src/components/spreadsheet/SpreadsheetView.tsx
git commit -m "feat: add multi-area selection to SpreadsheetView"
```

---

## Task 5: Create TopBar Component

**Files:**
- Create: `frontend/src/components/layout/TopBar.tsx`

Moves sidebar content (upload, files, navigator, photos) into a horizontal bar with popovers.

**Step 1: Create TopBar**

```typescript
"use client";

import { useState, useRef, useEffect } from "react";
import { Upload, FolderOpen, TreePine, Camera } from "lucide-react";
import { useBoQStore } from "@/stores/boqStore";
import UploadZone from "@/components/upload/UploadZone";
import FileList from "@/components/upload/FileList";
import BoQNavigator from "@/components/boq/BoQNavigator";
import PhotoUpload from "@/components/photos/PhotoUpload";

type PopoverKey = "upload" | "files" | "navigator" | "photos" | null;

export default function TopBar({ isConnected }: { isConnected: boolean }) {
  const [openPopover, setOpenPopover] = useState<PopoverKey>(null);
  const { items, selectedRow, selectRow } = useBoQStore();
  const popoverRef = useRef<HTMLDivElement>(null);

  // Close popover on outside click
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (popoverRef.current && !popoverRef.current.contains(e.target as Node)) {
        setOpenPopover(null);
      }
    }
    if (openPopover) document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [openPopover]);

  const toggle = (key: PopoverKey) =>
    setOpenPopover((prev) => (prev === key ? null : key));

  const buttonClass = (key: PopoverKey) => `
    flex items-center gap-1.5 px-3 py-1.5 rounded text-xs transition-all duration-150
    ${openPopover === key
      ? "bg-accent-cyan/10 text-accent-cyan border border-accent-cyan/20"
      : "text-text-muted hover:text-text-secondary hover:bg-bg-hover border border-transparent"
    }
  `;

  return (
    <div className="relative flex items-center gap-2 px-4 py-2 border-b border-border-default bg-bg-secondary/50">
      {/* Buttons */}
      <button onClick={() => toggle("upload")} className={buttonClass("upload")}>
        <Upload className="w-3.5 h-3.5" /> Upload
      </button>
      <button onClick={() => toggle("files")} className={buttonClass("files")}>
        <FolderOpen className="w-3.5 h-3.5" /> Files
        <span className="text-[10px] text-text-muted">
          ({useBoQStore.getState().files.length})
        </span>
      </button>
      <button onClick={() => toggle("navigator")} className={buttonClass("navigator")}>
        <TreePine className="w-3.5 h-3.5" /> Navigator
      </button>
      <button onClick={() => toggle("photos")} className={buttonClass("photos")}>
        <Camera className="w-3.5 h-3.5" /> Photos
      </button>

      {/* Spacer + connection status */}
      <div className="flex-1" />
      <span className={`w-1.5 h-1.5 rounded-full ${isConnected ? "bg-status-success" : "bg-status-danger"}`} />
      <span className="text-[10px] text-text-muted font-mono uppercase tracking-wider">
        {isConnected ? "Connected" : "Disconnected"}
      </span>

      {/* Popover panel */}
      {openPopover && (
        <div
          ref={popoverRef}
          className="absolute top-full left-0 mt-1 z-50 w-80 max-h-96 overflow-y-auto glass-panel border border-border-default rounded-lg shadow-xl p-3"
        >
          {openPopover === "upload" && <UploadZone />}
          {openPopover === "files" && <FileList />}
          {openPopover === "navigator" && (
            <BoQNavigator
              items={items}
              selectedId={selectedRow?.id ?? null}
              onSelect={(item) => { selectRow(item); setOpenPopover(null); }}
            />
          )}
          {openPopover === "photos" && <PhotoUpload />}
        </div>
      )}
    </div>
  );
}
```

**Step 2: Verify compiles**

```bash
npm run build
```

**Step 3: Commit**

```bash
git add frontend/src/components/layout/TopBar.tsx
git commit -m "feat: add TopBar component replacing sidebar"
```

---

## Task 6: Create ChatPanel Component

**Files:**
- Create: `frontend/src/components/chat/ChatPanel.tsx`

A compact inline chat panel for a single selection. Reuses `ChatMessage` and `ChatInput`.

**Step 1: Create the component**

```typescript
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
```

**Step 2: Verify compiles**

```bash
npm run build
```

**Step 3: Commit**

```bash
git add frontend/src/components/chat/ChatPanel.tsx
git commit -m "feat: add inline ChatPanel component for per-selection chat"
```

---

## Task 7: Create ChatPanelList Component

**Files:**
- Create: `frontend/src/components/chat/ChatPanelList.tsx`

Column 1 wrapper: scrollable stacked list of `ChatPanel` components.

**Step 1: Create the component**

```typescript
"use client";

import { useEffect, useRef } from "react";
import { MessageSquare } from "lucide-react";
import { useChatPanelStore } from "@/stores/chatPanelStore";
import ColumnHeader from "@/components/layout/ColumnHeader";
import ChatPanelComponent from "./ChatPanel";

export default function ChatPanelList() {
  const panels = useChatPanelStore((s) => s.panels);
  const activePanelId = useChatPanelStore((s) => s.activePanelId);
  const activeRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to active panel
  useEffect(() => {
    if (activePanelId && activeRef.current) {
      activeRef.current.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }
  }, [activePanelId]);

  return (
    <div className="glass-panel flex flex-col min-h-0">
      <ColumnHeader
        title="Chat"
        accent="cyan"
        badge={panels.length > 0 ? `${panels.length}` : undefined}
      />
      <div className="flex-1 overflow-y-auto p-2 space-y-2">
        {panels.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full gap-2 text-text-muted select-none">
            <MessageSquare className="w-8 h-8 opacity-40" />
            <p className="text-xs text-center">
              Select rows in Current BOQ to start a conversation
            </p>
          </div>
        ) : (
          panels.map((panel) => (
            <div
              key={panel.id}
              ref={panel.id === activePanelId ? activeRef : undefined}
            >
              <ChatPanelComponent panelId={panel.id} />
            </div>
          ))
        )}
      </div>
    </div>
  );
}
```

**Step 2: Verify compiles**

```bash
npm run build
```

**Step 3: Commit**

```bash
git add frontend/src/components/chat/ChatPanelList.tsx
git commit -m "feat: add ChatPanelList component for column 1"
```

---

## Task 8: Create RegexResultCard and RegexResultList Components

**Files:**
- Create: `frontend/src/components/boq/RegexResultCard.tsx`
- Create: `frontend/src/components/boq/RegexResultList.tsx`

Column 2: deterministic pipeline results per selection. Reuses `MatchCard` patterns.

**Step 1: Create RegexResultCard**

This adapts the existing `MatchCard` with diff highlighting. Shows per-match: description with diffs highlighted, unit/qty/price, source metadata, APPLY button.

```typescript
"use client";

import { useMemo } from "react";
import { ArrowRight } from "lucide-react";
import { useBoQStore } from "@/stores/boqStore";
import type { MatchResult } from "@/lib/types";
import StatusBadge from "./StatusBadge";
import QuantityGauge from "./QuantityGauge";

interface RegexResultCardProps {
  match: MatchResult;
  sourceDescription: string;
}

/** Highlight words in `text` that differ from `reference` */
function highlightDiffs(text: string, reference: string): React.ReactNode[] {
  const textWords = text.split(/\s+/);
  const refWords = new Set(reference.toLowerCase().split(/\s+/));
  return textWords.map((word, i) => {
    const isDiff = !refWords.has(word.toLowerCase());
    return (
      <span key={i}>
        {i > 0 && " "}
        <span className={isDiff ? "bg-accent-amber/20 text-accent-amber rounded px-0.5" : ""}>
          {word}
        </span>
      </span>
    );
  });
}

function formatNumber(value: number): string {
  return value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

export default function RegexResultCard({ match, sourceDescription }: RegexResultCardProps) {
  const updateWorkingItem = useBoQStore((s) => s.updateWorkingItem);

  const highlighted = useMemo(
    () => highlightDiffs(match.item.description, sourceDescription),
    [match.item.description, sourceDescription],
  );

  const handleApply = () => {
    updateWorkingItem(match.item.id, { unit_price: match.item.unit_price });
  };

  return (
    <div className="glass-panel p-2 rounded-lg border border-border-default/50 text-xs space-y-1.5">
      {/* Description with diffs */}
      <p className="text-text-primary leading-relaxed whitespace-pre-wrap">
        {highlighted}
      </p>

      {/* Metadata row */}
      <div className="flex items-center gap-2 text-text-muted">
        <span className="font-mono">{match.item.unit}</span>
        <span className="font-mono">{match.item.quantity}</span>
        <span className="flex-1" />
        <span className="font-mono font-semibold text-text-primary">
          {formatNumber(match.item.unit_price)}
        </span>
        <span className="font-mono">
          {formatNumber(match.item.total)}
        </span>
      </div>

      {/* Source + actions */}
      <div className="flex items-center gap-2">
        {match.item.project_name && (
          <span className="text-[10px] text-text-muted truncate">
            {match.item.project_name}
          </span>
        )}
        {match.item.date && (
          <span className="text-[10px] text-text-muted">{match.item.date}</span>
        )}
        {match.quantity_comparison && (
          <QuantityGauge comparison={match.quantity_comparison} />
        )}
        <span className="flex-1" />
        <button
          onClick={handleApply}
          className="flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-medium
                     bg-accent-cyan/10 text-accent-cyan border border-accent-cyan/20
                     hover:bg-accent-cyan/20 transition-colors"
        >
          APPLY <ArrowRight className="w-2.5 h-2.5" />
        </button>
      </div>

      {/* Similarity badge */}
      <div className="flex items-center gap-1">
        <div
          className="h-1 rounded-full bg-accent-cyan/30"
          style={{ width: `${match.similarity * 100}%` }}
        />
        <span className="text-[9px] text-text-muted font-mono">
          {(match.similarity * 100).toFixed(0)}%
        </span>
      </div>
    </div>
  );
}
```

**Step 2: Create RegexResultList**

```typescript
"use client";

import { useMemo } from "react";
import { Search } from "lucide-react";
import { useSelectionStore } from "@/stores/selectionStore";
import { useMatchStore } from "@/stores/matchStore";
import ColumnHeader from "@/components/layout/ColumnHeader";
import RegexResultCard from "./RegexResultCard";

function formatNumber(value: number): string {
  return value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

export default function RegexResultList() {
  const selections = useSelectionStore((s) => s.selections);
  const activeSelectionId = useSelectionStore((s) => s.activeSelectionId);
  const { matches, stats, isSearching } = useMatchStore();

  const activeSelection = useMemo(
    () => selections.find((s) => s.id === activeSelectionId),
    [selections, activeSelectionId],
  );

  const sourceDescription = activeSelection
    ? activeSelection.items.map((i) => i.description).join(" ")
    : "";

  return (
    <div className="glass-panel flex flex-col min-h-0">
      <ColumnHeader
        title="Match Results"
        accent="purple"
        badge={matches.length > 0 ? `${matches.length}` : undefined}
      />

      {/* Stats header */}
      {stats && matches.length > 0 && (
        <div className="px-3 py-1.5 border-b border-border-default/50 flex items-center gap-3 text-[10px] text-text-muted">
          <span>AVG: <span className="text-text-primary font-mono">{formatNumber(stats.avgPrice)}</span></span>
          <span>MIN: <span className="text-text-primary font-mono">{formatNumber(stats.minPrice)}</span></span>
          <span>MAX: <span className="text-text-primary font-mono">{formatNumber(stats.maxPrice)}</span></span>
        </div>
      )}

      <div className="flex-1 overflow-y-auto p-2 space-y-2">
        {isSearching ? (
          <div className="flex items-center justify-center h-full gap-2 text-text-secondary text-xs">
            <Search className="w-4 h-4 animate-pulse text-accent-purple" />
            Searching...
          </div>
        ) : matches.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full gap-2 text-text-muted select-none">
            <Search className="w-8 h-8 opacity-40" />
            <p className="text-xs text-center">
              Select rows in Current BOQ to see matches
            </p>
          </div>
        ) : (
          matches.map((match) => (
            <RegexResultCard
              key={match.item.id}
              match={match}
              sourceDescription={sourceDescription}
            />
          ))
        )}
      </div>
    </div>
  );
}
```

**Step 3: Verify compiles**

```bash
npm run build
```

**Step 4: Commit**

```bash
git add frontend/src/components/boq/RegexResultCard.tsx frontend/src/components/boq/RegexResultList.tsx
git commit -m "feat: add RegexResultCard and RegexResultList for column 2"
```

---

## Task 9: Create Selection-Triggered Pipeline Hook

**Files:**
- Create: `frontend/src/hooks/useSelectionPipeline.ts`

Watches `useSelectionStore` — when a new selection is added, triggers: (1) match lookup for column 2, (2) LLM analysis for column 1.

**Step 1: Create the hook**

```typescript
import { useEffect, useRef } from "react";
import { useSelectionStore } from "@/stores/selectionStore";
import { useChatPanelStore } from "@/stores/chatPanelStore";
import { useMatchStore } from "@/stores/matchStore";
import { analyzeSelection } from "@/lib/api";
import type { ChatMessage } from "@/lib/types";

/**
 * Watches selection store. When a new selection is created:
 * 1. Triggers match lookup (deterministic pipeline → column 2)
 * 2. Creates a chat panel and requests LLM analysis → column 1
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
          : `Rows ${selection.items[0]?.item_number ?? selection.startIndex}–${selection.items[selection.items.length - 1]?.item_number ?? selection.endIndex}`;

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
```

**Step 2: Verify compiles**

```bash
npm run build
```

**Step 3: Commit**

```bash
git add frontend/src/hooks/useSelectionPipeline.ts
git commit -m "feat: add useSelectionPipeline hook to trigger analysis on selection"
```

---

## Task 10: Rewire page.tsx to New Layout

**Files:**
- Modify: `frontend/src/app/page.tsx`

Replace the entire 4-column grid with the new layout: TopBar + (Chat | Regex | Current BOQ | Edited).

**Step 1: Rewrite page.tsx**

Key changes:
- Remove: sidebar column (Col 1), `LeftTab` state, all sidebar-related JSX
- Remove: old Match Details column (Col 2)
- Remove: `ChatDrawer` import and usage
- Remove: `isChatOpen` state
- Add: `TopBar` at top
- Add: Column 1 = `ChatPanelList`
- Add: Column 2 = `RegexResultList`
- Keep: Column 3 = `SpreadsheetView` (with scroll sync)
- Keep: Column 4 = `EditableSheet` (with scroll sync)
- Add: `useSelectionPipeline()` hook call
- Grid class: `grid-cols-[280px_280px_1fr_1fr]`

The structure becomes:

```tsx
<div className="h-screen flex flex-col overflow-hidden">
  {/* Top bar (replaces sidebar) */}
  <TopBar isConnected={isConnected} />

  {/* Pipeline bar */}
  <div className="px-3 pt-2">
    <AnimatePresence>
      <PipelineBar />
    </AnimatePresence>
  </div>

  {/* Main four-column grid */}
  <main className="flex-1 grid grid-cols-[280px_280px_1fr_1fr] gap-3 p-3 min-h-0">
    {/* Col 1: Chat panels */}
    <ChatPanelList />

    {/* Col 2: Regex / deterministic results */}
    <RegexResultList />

    {/* Col 3: Current BOQ */}
    <div className="glass-panel flex flex-col min-h-0">
      <ColumnHeader title="Current BOQ" accent="cyan" badge={`${items.length} items`} />
      <div className="shrink-0 p-2">
        <SheetPreview />
      </div>
      <div className="flex-1 min-h-0" onScroll={handleBoqScroll}>
        <SpreadsheetView ref={boqScrollRef} />
      </div>
    </div>

    {/* Col 4: Edited (Working Copy) */}
    <div className="glass-panel flex flex-col min-h-0">
      <ColumnHeader title="Edited" accent="purple" badge="editable" />
      <div className="flex-1 min-h-0" onScroll={handleWorkingScroll}>
        <EditableSheet ref={workingScrollRef} />
      </div>
    </div>
  </main>

  <AgentActivityButton />
  <AgentPanel />
</div>
```

**Step 2: Verify build**

```bash
npm run build
```

**Step 3: Manual smoke test**

```bash
npm run dev
```

Open http://localhost:3000, verify:
- Top bar shows Upload/Files/Navigator/Photos buttons
- 4 columns render (Chat empty, Regex empty, Current BOQ, Edited)
- Upload a file → items appear in columns 3 & 4
- Click/drag rows in column 3 → chat panel appears in column 1, matches in column 2
- Scroll sync works between columns 3 & 4

**Step 4: Commit**

```bash
git add frontend/src/app/page.tsx
git commit -m "feat: rewire page layout to chat/regex/current/edited columns"
```

---

## Task 11: Implement Row Alignment Between Columns 3 & 4

**Files:**
- Create: `frontend/src/hooks/useRowAlignment.ts`
- Modify: `frontend/src/components/spreadsheet/SpreadsheetView.tsx` — add `data-row-index` attributes
- Modify: `frontend/src/components/spreadsheet/EditableSheet.tsx` — add `data-row-index` attributes

**Step 1: Create alignment hook**

```typescript
import { useEffect, useRef, useCallback } from "react";
import { useBoQStore } from "@/stores/boqStore";

/**
 * Synchronizes row heights between Current BOQ and Working Copy.
 * When item counts match, forces each row pair to max(height_a, height_b).
 * When counts differ, resets to natural heights (scroll sync only).
 */
export function useRowAlignment(
  boqRef: React.RefObject<HTMLDivElement | null>,
  workingRef: React.RefObject<HTMLDivElement | null>,
) {
  const items = useBoQStore((s) => s.items);
  const workingItems = useBoQStore((s) => s.workingItems);
  const aligned = useRef(false);

  const alignRows = useCallback(() => {
    if (!boqRef.current || !workingRef.current) return;

    const boqRows = boqRef.current.querySelectorAll<HTMLTableRowElement>("tbody tr[data-row-index]");
    const workingRows = workingRef.current.querySelectorAll<HTMLTableRowElement>("tbody tr[data-row-index]");

    // Reset all heights first
    boqRows.forEach((r) => (r.style.height = ""));
    workingRows.forEach((r) => (r.style.height = ""));

    if (items.length !== workingItems.length) {
      aligned.current = false;
      return;
    }

    // Force equal heights
    const count = Math.min(boqRows.length, workingRows.length);
    for (let i = 0; i < count; i++) {
      const h = Math.max(boqRows[i].offsetHeight, workingRows[i].offsetHeight);
      boqRows[i].style.height = `${h}px`;
      workingRows[i].style.height = `${h}px`;
    }
    aligned.current = true;
  }, [boqRef, workingRef, items.length, workingItems.length]);

  // Re-align on item changes
  useEffect(() => {
    // Small delay to let DOM render
    const timer = setTimeout(alignRows, 50);
    return () => clearTimeout(timer);
  }, [alignRows]);

  // Re-align on window resize
  useEffect(() => {
    window.addEventListener("resize", alignRows);
    return () => window.removeEventListener("resize", alignRows);
  }, [alignRows]);

  return { alignRows };
}
```

**Step 2: Add `data-row-index` to both table components**

In `SpreadsheetView.tsx`, add to each `<tr>`:
```tsx
<tr key={item.id} data-row-index={index} onClick={...} className={...}>
```

In `EditableSheet.tsx`, add to each `<tr>`:
```tsx
<tr key={wItem.id} data-row-index={index} onClick={...} className={...}>
```

**Step 3: Wire the hook in page.tsx**

In `page.tsx`, after the scroll refs:
```typescript
import { useRowAlignment } from "@/hooks/useRowAlignment";
// ...
useRowAlignment(boqScrollRef, workingScrollRef);
```

**Step 4: Verify build + manual test**

```bash
npm run build && npm run dev
```

Verify: rows in columns 3 & 4 have matching heights when item counts are equal.

**Step 5: Commit**

```bash
git add frontend/src/hooks/useRowAlignment.ts frontend/src/components/spreadsheet/SpreadsheetView.tsx frontend/src/components/spreadsheet/EditableSheet.tsx frontend/src/app/page.tsx
git commit -m "feat: add row alignment between Current BOQ and Working Copy"
```

---

## Task 12: Backend — Selection-Based Chat Endpoint

**Files:**
- Modify: `backend/app/routers/chat.py` — make chat endpoint accept selection IDs (not just item IDs)

**Step 1: Update chat router**

The current endpoint is `POST /api/chat/{item_id}`. The frontend will now send selection IDs (e.g. `sel-1-1708012345`) as the `item_id`. The backend needs to handle this gracefully:

- If `item_id` starts with `sel-`, treat it as a selection-based chat (no DB item lookup, use the provided context from the message body)
- Otherwise, behave as before (look up the item in DB for context)

In `backend/app/routers/chat.py`, modify the `send_message` function:

```python
@router.post("/{item_id}", response_model=ChatMessageSchema)
async def send_message(item_id: str, request: ChatRequest, db: Session = Depends(get_db)):
    # For selection-based chats, skip item lookup
    if item_id.startswith("sel-"):
        item_context = ""  # Context is embedded in the message content
    else:
        item = db.query(BoQItem).filter(BoQItem.id == item_id).first()
        if not item:
            raise HTTPException(status_code=404, detail="Item not found")
        item_context = f"Item: {item.item_number} - {item.description}\nUnit: {item.unit}, Qty: {item.quantity}, Price: {item.unit_price}"

    # ... rest of existing logic (build prompt, call LLM, persist messages)
```

Also update the `get_history` endpoint to handle selection IDs:

```python
@router.get("/{item_id}", response_model=list[ChatMessageSchema])
async def get_history(item_id: str, db: Session = Depends(get_db)):
    messages = db.query(ChatMessage).filter(ChatMessage.item_id == item_id).order_by(ChatMessage.created_at).all()
    return messages
```

This already works since `item_id` is a string column — selection IDs will just be stored as-is.

**Step 2: Verify backend starts**

```bash
cd backend && uv run uvicorn app.main:app --reload
```

**Step 3: Commit**

```bash
git add backend/app/routers/chat.py
git commit -m "feat: support selection-based chat in chat endpoint"
```

---

## Task 13: Final Integration Smoke Test

**Step 1: Start both servers**

```bash
# Terminal 1 — backend
cd .worktrees/boq-matcher/backend && uv run uvicorn app.main:app --reload --port 8000

# Terminal 2 — frontend
cd .worktrees/boq-matcher/frontend && npm run dev
```

**Step 2: Manual test checklist**

- [ ] Top bar renders with Upload/Files/Navigator/Photos buttons
- [ ] Upload a file via top bar popover
- [ ] Current BOQ (col 3) shows items
- [ ] Edited (col 4) shows matching items, scroll-synced
- [ ] Click a row in col 3 → selection highlight appears
- [ ] Drag across rows → multi-row selection
- [ ] Chat panel appears in col 1 with "Analyzing..." indicator
- [ ] Match results appear in col 2
- [ ] LLM analysis lands as first message in chat panel
- [ ] Type a follow-up in chat → assistant responds
- [ ] Click APPLY on a match card → price updates in col 4
- [ ] Multiple selections create multiple panels in col 1
- [ ] Row heights align between col 3 and col 4
- [ ] Close a chat panel → selection removed

**Step 3: Final commit**

```bash
git add -A
git commit -m "feat: complete inline chat layout with 4-column design"
```
