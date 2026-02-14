# Inline Chat Layout Design

**Date**: 2026-02-15
**Worktree**: `.worktrees/boq-matcher` (branch `feature/boq-matcher`)
**Stack**: Next.js 15, React 19, Zustand, Tailwind CSS v4, FastAPI

## Overview

Replace the current 4-column layout (Sidebar | Match Details | Current BOQ | Working Copy) with a new 4-column layout focused on per-selection inline chat and deterministic comparison. The sidebar moves to a top bar.

## Layout

```
┌─────────────────────────────────────────────────────────────────────┐
│ TOP BAR: [Upload] [Files ▾] [Navigator ▾] [Photos ▾]   ● Connected │
├─────────────────────────────────────────────────────────────────────┤
│ Pipeline Bar                                                        │
├────────────┬──────────────┬───────────────────┬─────────────────────┤
│ 1. CHAT    │ 2. REGEX     │ 3. CURRENT BOQ    │ 4. EDITED           │
│            │              │ (read-only)       │ (Working Copy)      │
│ Stacked    │ Deterministic│ Original          │ Editable copy       │
│ mini-chat  │ pipeline     │ spreadsheet       │ with changes        │
│ panels     │ results      │                   │                     │
├────────────┴──────────────┴───────────────────┴─────────────────────┤
│                                                   [▶ Agents (N)]    │
└─────────────────────────────────────────────────────────────────────┘
```

- Grid: `grid-cols-[280px_280px_1fr_1fr]`
- Columns 1 & 2: fixed width, scroll independently but panels are keyed to the same selections
- Columns 3 & 4: share remaining space, scroll-synced

## Data Flow

```
Selection in Column 3 (Current BOQ)
    ├──→ Deterministic pipeline → Column 2 (regex matches, price comparisons)
    └──→ LLM analysis (using Column 2 context) → Column 1 (first chat message)
              └──→ User follow-ups (optional)
```

## Column 1: Chat Panels

Vertically stacked mini-chat panels, one per active selection.

- **Creation**: User selects area in Current BOQ → chat panel appears
- **First message**: Auto-generated LLM analysis of the selection, informed by deterministic results from Column 2
- **Follow-ups**: User can optionally type questions in the input at the bottom of each panel
- **Active panel**: The panel matching the current selection is highlighted and auto-scrolled into view
- **Cross-linking**: Clicking a panel highlights its corresponding selection in Column 3

### Chat Panel Structure

```
┌─────────────────────────┐
│ Rows 1.0–3.0        [x] │  ← header (selection label + close)
├─────────────────────────┤
│ 🤖 LLM analysis...      │  ← first auto-message
│                         │
│ 👤 What about...?        │  ← user follow-up
│ 🤖 Response...           │  ← assistant response
├─────────────────────────┤
│ [Type a message...]     │  ← input
└─────────────────────────┘
```

### State: `useChatPanelStore` (Zustand)

```typescript
interface ChatPanel {
  id: string;
  selectionId: string;
  messages: ChatMessage[];
  isAnalyzing: boolean;
}

interface ChatPanelState {
  panels: ChatPanel[];
  activePanelId: string | null;
  createPanel: (selectionId: string) => void;
  removePanel: (panelId: string) => void;
  addMessage: (panelId: string, message: ChatMessage) => void;
  setActive: (panelId: string) => void;
}
```

## Column 2: Deterministic Pipeline Results

Vertically stacked result cards, one per selection. Pure deterministic — no LLM.

### Per-selection card contents

- **Stats header**: AVG, MIN, MAX prices across matches + Collapse All toggle
- **Match cards** (one per historic hit):
  - Description text with regex-detected differences highlighted against selection
  - Unit | Quantity | Price bar chart | Unit Price | Total
  - Source metadata (troskovnik name, date)
  - QTY ratio badge (e.g. "4.6x")
  - APPLY button → pushes price to Working Copy (Column 4)
  - Status badge
- **Price divergence view**: When same description appears with different prices, show dates + price deltas + the deterministic text diff explaining the variance

## Column 3: Current BOQ (read-only)

Enhanced from current `SpreadsheetView` with multi-area selection:

### Selection model

- **Click** a cell → selects single cell
- **Click-drag** across rows → selects rectangular region
- **Shift+click** → extends selection to current row
- Multiple selections can coexist (each gets a unique highlight color)
- Each selection is stored as:

```typescript
interface BoQSelection {
  id: string;
  startRow: number;
  endRow: number;
  items: BoQItem[];
  color: string;  // from a small palette
}
```

### State: `useSelectionStore` (Zustand)

```typescript
interface SelectionState {
  selections: BoQSelection[];
  activeSelectionId: string | null;
  addSelection: (startRow: number, endRow: number) => void;
  removeSelection: (id: string) => void;
  setActive: (id: string) => void;
  clearAll: () => void;
}
```

## Column 4: Edited (Working Copy)

Existing `EditableSheet` with enhanced alignment:

- Row-level alignment with Column 3 when `items.length === workingItems.length` (force equal row heights via `max(height_current, height_working)` per row pair)
- When row counts differ (user inserted a row), drop row-level alignment, keep scroll-offset sync only
- Scroll sync uses existing `isSyncing` ref pattern

## Top Bar

Replaces the old sidebar. Contains:

- **Upload button**: Opens file picker (replaces `UploadZone`)
- **Files dropdown/popover**: List of uploaded files (replaces `FileList`)
- **Navigator dropdown/popover**: Hierarchical item tree (replaces `BoQNavigator`)
- **Photos dropdown/popover**: Photo upload + analysis (replaces `PhotoUpload` / `PhotoAnalysis`)
- **Connection status**: Existing dot + label

## Key Implementation Notes

- The existing `ChatDrawer` component (full-screen overlay) is replaced by inline `ChatPanel` components
- The existing `MatchList` component logic moves into Column 2 result cards
- The existing single `selectedRow` in `boqStore` is replaced by multi-selection in `useSelectionStore`
- Backend API for chat (`fetchChatHistory`, `sendChatMessage`) is reused but keyed by selection ID instead of item ID
- Backend API for matches (`startLookup` in `matchStore`) is reused, triggered per selection
