# Native Excel BOQ View — Design

## Goal

Add a third "Excel" tab to the right-side BOQ panel that renders the uploaded xlsx file with full formatting fidelity using the Univer spreadsheet engine. Users can select arbitrary cells across rows/columns and send that content to the RAG-based inspection/matching pipeline.

## Decisions

- **Component**: Univer (open-source, Apache-2.0, `dream-num/univer`)
- **Placement**: New "Excel" tab alongside existing Parsed and Raw tabs
- **Interaction**: Read-only rendering; multi-cell selection (including Ctrl+click disjoint) triggers RAG search
- **Width**: Constrained (`max-w-[900px]`) — no horizontal stretching; ready for a future 4th column

## Backend Changes

### 1. Store original xlsx on upload

Save the uploaded binary to `data/uploads/{file_id}.xlsx` during the upload flow. Currently the bytes are parsed in-memory and discarded.

### 2. New DB column

Add `stored_path` (nullable String) to `BoQFile` model pointing to the saved file.

### 3. New endpoint

`GET /api/files/{file_id}/xlsx` — returns the stored xlsx as a binary `StreamingResponse`. 404 if no stored file (older uploads before this feature).

## Frontend Changes

### 1. Packages

```
@univerjs/presets
@univerjs/preset-sheets-core
@univerjs/preset-sheets-drawing
@univerjs/preset-sheets-advanced
```

### 2. New component: `ExcelView.tsx`

Location: `src/components/spreadsheet/ExcelView.tsx`

Lifecycle:
1. On mount (or when `selectedFileId` changes): fetch xlsx blob from `GET /api/files/{fileId}/xlsx`
2. Call `univerAPI.importXLSXToSnapshotAsync(file)` to get `IWorkbookData` snapshot
3. Call `univerAPI.createWorkbook(snapshot)` to render with full formatting
4. Configure read-only mode
5. On unmount or file change: dispose Univer instance

Layout:
- Wrapper div with `max-w-[900px]`, vertical scroll for long sheets
- Horizontal scroll only if sheet content exceeds the max-width

### 3. Tab integration

In `page.tsx`, extend the Parsed/Raw toggle:
- `boqViewMode` state: `"parsed" | "raw" | "excel"`
- Add "Excel" button to the toggle group
- Render `<ExcelView />` when mode is `"excel"`

### 4. Selection → Inspection pipeline

1. Listen to `univerAPI.addEvent(univerAPI.Event.SelectionChanged, callback)` — fires on any selection change, supports disjoint Ctrl+click ranges
2. Extract selected cell text values + structural context (neighboring item numbers, units, quantities)
3. Send to `POST /api/match` (existing RAG vector search + similarity scoring)
4. Results appear in the middle MATCH RESULTS column

## What stays unchanged

- Parsed tab (SpreadsheetView) — editable working view
- Raw tab (RawSheetGrid) — raw cell text with virtual scrolling
- All existing match, chat, and agent functionality
