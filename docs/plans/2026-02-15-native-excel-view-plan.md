# Native Excel BOQ View Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a third "Excel" tab to the BOQ panel that renders uploaded xlsx files with full formatting using the Univer spreadsheet engine, with multi-cell selection triggering RAG-based matching.

**Architecture:** Backend stores original xlsx binary on upload and serves it via a new endpoint. Frontend uses Univer's `importXLSXToSnapshotAsync` to render the file read-only. Selection events extract cell text and send it to the existing `POST /api/match` RAG pipeline.

**Tech Stack:** Univer (`@univerjs/presets`, `@univerjs/preset-sheets-core`, `@univerjs/preset-sheets-drawing`, `@univerjs/preset-sheets-advanced`), FastAPI, SQLAlchemy, Next.js/React, Zustand.

---

### Task 1: Backend — Add `stored_path` column and file storage

**Files:**
- Modify: `backend/app/models/boq.py:28-45` (BoQFile model)
- Modify: `backend/app/routers/upload.py` (save file to disk)

**Step 1: Add `stored_path` column to BoQFile model**

In `backend/app/models/boq.py`, add after `file_type` column (line 34):

```python
stored_path = Column(String, nullable=True)  # path to original xlsx on disk
```

**Step 2: Create uploads directory**

Run:
```bash
mkdir -p /media/josip-rastocic/DrugiDisk/Programi/troskovljnjikov/.worktrees/boq-matcher/backend/data/uploads
```

**Step 3: Save file bytes to disk in upload router**

In `backend/app/routers/upload.py`, add import at top:

```python
from pathlib import Path
```

After `file_bytes = await file.read()` (line 23) and `file_id = str(uuid.uuid4())` (line 24), add:

```python
# Save original file to disk for Excel view
uploads_dir = Path("data/uploads")
uploads_dir.mkdir(parents=True, exist_ok=True)
stored_path = uploads_dir / f"{file_id}.xlsx"
stored_path.write_bytes(file_bytes)
```

In the `BoQFile(...)` constructor (line 36-49), add after `file_path=file_id,`:

```python
stored_path=str(stored_path),
```

**Step 4: Delete old database so new column gets created**

The project uses `create_tables()` which calls `Base.metadata.create_all()` — this creates new tables but doesn't ALTER existing ones. Delete the DB so it gets recreated on next startup:

```bash
rm /media/josip-rastocic/DrugiDisk/Programi/troskovljnjikov/.worktrees/boq-matcher/backend/data/boq.db
```

**Step 5: Commit**

```bash
cd /media/josip-rastocic/DrugiDisk/Programi/troskovljnjikov/.worktrees/boq-matcher
git add backend/app/models/boq.py backend/app/routers/upload.py
git commit -m "feat(backend): store original xlsx file on upload"
```

---

### Task 2: Backend — New endpoint to serve xlsx file

**Files:**
- Modify: `backend/app/routers/files.py` (add endpoint)

**Step 1: Add the xlsx download endpoint**

In `backend/app/routers/files.py`, add import at top:

```python
from pathlib import Path
from fastapi.responses import FileResponse
```

Add new endpoint after the `delete_file` function (after line 43):

```python
@router.get("/files/{file_id}/xlsx")
def get_file_xlsx(file_id: str, db: Session = Depends(get_db)):
    f = db.query(BoQFile).filter(BoQFile.id == file_id).first()
    if not f:
        raise HTTPException(status_code=404, detail="File not found")
    if not f.stored_path or not Path(f.stored_path).is_file():
        raise HTTPException(status_code=404, detail="Original xlsx file not available")
    return FileResponse(
        path=f.stored_path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=f.file_name,
    )
```

**Step 2: Verify endpoint works**

Start the backend and test with curl:

```bash
cd /media/josip-rastocic/DrugiDisk/Programi/troskovljnjikov/.worktrees/boq-matcher/backend
uv run uvicorn app.main:app --reload --port 8000
```

Then in another terminal, upload a test file and try the new endpoint:

```bash
# Upload a file first, note the file_id from response
# Then: curl -o test_download.xlsx http://localhost:8000/api/files/{file_id}/xlsx
```

**Step 3: Commit**

```bash
cd /media/josip-rastocic/DrugiDisk/Programi/troskovljnjikov/.worktrees/boq-matcher
git add backend/app/routers/files.py
git commit -m "feat(backend): add endpoint to serve original xlsx file"
```

---

### Task 3: Frontend — Install Univer packages

**Files:**
- Modify: `frontend/package.json`

**Step 1: Install Univer packages**

```bash
cd /media/josip-rastocic/DrugiDisk/Programi/troskovljnjikov/.worktrees/boq-matcher/frontend
npm install @univerjs/presets @univerjs/preset-sheets-core @univerjs/preset-sheets-drawing @univerjs/preset-sheets-advanced
```

**Step 2: Verify installation**

```bash
ls node_modules/@univerjs/presets node_modules/@univerjs/preset-sheets-core node_modules/@univerjs/preset-sheets-drawing node_modules/@univerjs/preset-sheets-advanced
```

**Step 3: Commit**

```bash
cd /media/josip-rastocic/DrugiDisk/Programi/troskovljnjikov/.worktrees/boq-matcher
git add frontend/package.json frontend/package-lock.json
git commit -m "chore(frontend): install Univer spreadsheet packages"
```

---

### Task 4: Frontend — Add fetchXlsxBlob to API client

**Files:**
- Modify: `frontend/src/lib/api.ts`

**Step 1: Add the fetch function**

At the end of `frontend/src/lib/api.ts`, before the closing of the file, add:

```typescript
// ── Excel view operations ─────────────────────────────────────────

const API_URL_RESOLVED = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/** Fetch original xlsx file as a File object for Univer import */
export async function fetchXlsxFile(fileId: string): Promise<File> {
  const res = await fetch(`${API_URL_RESOLVED}/api/files/${fileId}/xlsx`);
  if (!res.ok) {
    throw new Error(`Failed to fetch xlsx: ${res.status}`);
  }
  const blob = await res.blob();
  return new File([blob], `${fileId}.xlsx`, {
    type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  });
}
```

Note: `API_URL` is already declared at line 3 of the file as a const — reuse it or use a different name if there's a scoping issue. The existing `API_URL` at line 3 works fine, so use that directly:

```typescript
export async function fetchXlsxFile(fileId: string): Promise<File> {
  const res = await fetch(`${API_URL}/api/files/${fileId}/xlsx`);
  if (!res.ok) {
    throw new Error(`Failed to fetch xlsx: ${res.status}`);
  }
  const blob = await res.blob();
  return new File([blob], `${fileId}.xlsx`, {
    type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  });
}
```

**Step 2: Commit**

```bash
cd /media/josip-rastocic/DrugiDisk/Programi/troskovljnjikov/.worktrees/boq-matcher
git add frontend/src/lib/api.ts
git commit -m "feat(frontend): add fetchXlsxFile API function"
```

---

### Task 5: Frontend — Create ExcelView component

**Files:**
- Create: `frontend/src/components/spreadsheet/ExcelView.tsx`

**Step 1: Create the component**

Create `frontend/src/components/spreadsheet/ExcelView.tsx`:

```tsx
"use client";

import { useEffect, useRef, useState } from "react";
import { useBoQStore } from "@/stores/boqStore";
import { useMatchStore } from "@/stores/matchStore";
import { fetchXlsxFile } from "@/lib/api";

import { createUniver, LocaleType, mergeLocales } from "@univerjs/presets";
import { UniverSheetsCorePreset } from "@univerjs/preset-sheets-core";
import UniverPresetSheetsCoreEnUS from "@univerjs/preset-sheets-core/locales/en-US";
import { UniverSheetsDrawingPreset } from "@univerjs/preset-sheets-drawing";
import UniverPresetSheetsDrawingEnUS from "@univerjs/preset-sheets-drawing/locales/en-US";
import { UniverSheetsAdvancedPreset } from "@univerjs/preset-sheets-advanced";
import UniverPresetSheetsAdvancedEnUS from "@univerjs/preset-sheets-advanced/locales/en-US";

import "@univerjs/preset-sheets-core/lib/index.css";
import "@univerjs/preset-sheets-drawing/lib/index.css";
import "@univerjs/preset-sheets-advanced/lib/index.css";

export default function ExcelView() {
  const selectedFileId = useBoQStore((s) => s.selectedFileId);
  const startLookup = useMatchStore((s) => s.startLookup);

  const containerRef = useRef<HTMLDivElement>(null);
  const univerRef = useRef<ReturnType<typeof createUniver> | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!selectedFileId || !containerRef.current) return;

    let disposed = false;

    async function init() {
      setLoading(true);
      setError(null);

      try {
        // Clean up previous instance
        if (univerRef.current) {
          univerRef.current.univerAPI.dispose();
          univerRef.current = null;
        }

        // Clear container
        if (containerRef.current) {
          containerRef.current.innerHTML = "";
        }

        // Fetch the xlsx file
        const file = await fetchXlsxFile(selectedFileId!);
        if (disposed) return;

        // Create Univer instance
        const result = createUniver({
          locale: LocaleType.EN_US,
          locales: {
            [LocaleType.EN_US]: mergeLocales(
              UniverPresetSheetsCoreEnUS,
              UniverPresetSheetsDrawingEnUS,
              UniverPresetSheetsAdvancedEnUS
            ),
          },
          presets: [
            UniverSheetsCorePreset({
              container: containerRef.current!,
            }),
            UniverSheetsDrawingPreset(),
            UniverSheetsAdvancedPreset(),
          ],
        });

        if (disposed) {
          result.univerAPI.dispose();
          return;
        }

        univerRef.current = result;
        const { univerAPI } = result;

        // Import the xlsx file
        const snapshot = await univerAPI.importXLSXToSnapshotAsync(file);
        if (disposed) {
          univerAPI.dispose();
          return;
        }

        univerAPI.createWorkbook(snapshot);

        // Set read-only mode
        const workbook = univerAPI.getActiveWorkbook();
        if (workbook) {
          workbook.setEditable(false);
        }

        // Listen for selection changes → trigger RAG lookup
        univerAPI.addEvent(univerAPI.Event.SelectionChanged, (params: any) => {
          const { worksheet, selections } = params;
          if (!selections || selections.length === 0 || !worksheet) return;

          // Debounce: collect text from all selected ranges
          const texts: string[] = [];
          for (const sel of selections) {
            const range = sel.range;
            if (!range) continue;
            for (let r = range.startRow; r <= range.endRow; r++) {
              for (let c = range.startColumn; c <= range.endColumn; c++) {
                const cell = worksheet.getRange(r, c, r, c);
                const value = cell?.getValue();
                if (value != null && String(value).trim()) {
                  texts.push(String(value).trim());
                }
              }
            }
          }

          if (texts.length > 0) {
            const searchText = texts.join(" ");
            startLookup(searchText);
          }
        });

        setLoading(false);
      } catch (err) {
        if (!disposed) {
          setError(
            err instanceof Error ? err.message : "Failed to load Excel file"
          );
          setLoading(false);
        }
      }
    }

    init();

    return () => {
      disposed = true;
      if (univerRef.current) {
        univerRef.current.univerAPI.dispose();
        univerRef.current = null;
      }
    };
  }, [selectedFileId, startLookup]);

  if (!selectedFileId) {
    return (
      <div className="flex items-center justify-center h-full text-text-muted text-sm">
        Upload a file to view Excel preview
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col min-h-0">
      {loading && (
        <div className="flex items-center justify-center h-full text-text-muted text-sm">
          Loading Excel view...
        </div>
      )}
      {error && (
        <div className="flex items-center justify-center h-full text-red-400 text-sm">
          {error}
        </div>
      )}
      <div
        ref={containerRef}
        className="flex-1 min-h-0 max-w-[900px]"
        style={{ display: loading || error ? "none" : "block" }}
      />
    </div>
  );
}
```

**Important notes for the implementing engineer:**
- The Univer API may have slightly different method names depending on the installed version. Check `node_modules/@univerjs/presets/lib/types.d.ts` if `importXLSXToSnapshotAsync` is not found — it might be under a different name or require the Facade API.
- The `SelectionChanged` event param structure may differ. Log `params` to inspect the actual shape.
- The `setEditable(false)` call may be on the workbook or require a different API — check Univer docs for read-only configuration.
- If Univer CSS conflicts with Tailwind, scope the container styles.

**Step 2: Verify it compiles**

```bash
cd /media/josip-rastocic/DrugiDisk/Programi/troskovljnjikov/.worktrees/boq-matcher/frontend
npm run build
```

Fix any type errors. Common issues:
- Import paths may need adjustment based on actual Univer package exports
- `LocaleType.EN_US` vs `LocaleType.En_US` — check actual enum values
- The `Event.SelectionChanged` name may be different — check with `console.log(univerAPI.Event)`

**Step 3: Commit**

```bash
cd /media/josip-rastocic/DrugiDisk/Programi/troskovljnjikov/.worktrees/boq-matcher
git add frontend/src/components/spreadsheet/ExcelView.tsx
git commit -m "feat(frontend): add ExcelView component using Univer spreadsheet"
```

---

### Task 6: Frontend — Add Excel tab to page.tsx

**Files:**
- Modify: `frontend/src/app/page.tsx:1-138`

**Step 1: Add import**

At line 16 (after `RawSheetGrid` import), add:

```typescript
import ExcelView from "@/components/spreadsheet/ExcelView";
```

**Step 2: Extend boqViewMode state**

Change line 59 from:

```typescript
const [boqViewMode, setBoqViewMode] = useState<"parsed" | "raw">("parsed");
```

to:

```typescript
const [boqViewMode, setBoqViewMode] = useState<"parsed" | "raw" | "excel">("parsed");
```

**Step 3: Add Excel button to toggle group**

In the actions prop of ColumnHeader (lines 92-113), add a third button after the "Raw" button (after line 112, before the closing `</div>`):

```tsx
<button
  onClick={() => setBoqViewMode("excel")}
  className={`px-2 py-0.5 text-[10px] font-mono rounded transition-colors ${
    boqViewMode === "excel"
      ? "bg-accent-cyan/15 text-accent-cyan"
      : "text-text-muted hover:text-text-secondary"
  }`}
>
  Excel
</button>
```

**Step 4: Add Excel view rendering**

Change the conditional rendering block (lines 116-129) from:

```tsx
{boqViewMode === "parsed" ? (
  <>
    <div className="shrink-0 p-2">
      <SheetPreview />
    </div>
    <div className="flex-1 min-h-0">
      <SpreadsheetView ref={boqScrollRef} />
    </div>
  </>
) : (
  <div className="flex-1 min-h-0">
    <RawSheetGrid />
  </div>
)}
```

to:

```tsx
{boqViewMode === "parsed" ? (
  <>
    <div className="shrink-0 p-2">
      <SheetPreview />
    </div>
    <div className="flex-1 min-h-0">
      <SpreadsheetView ref={boqScrollRef} />
    </div>
  </>
) : boqViewMode === "raw" ? (
  <div className="flex-1 min-h-0">
    <RawSheetGrid />
  </div>
) : (
  <div className="flex-1 min-h-0">
    <ExcelView />
  </div>
)}
```

**Step 5: Verify it renders**

```bash
cd /media/josip-rastocic/DrugiDisk/Programi/troskovljnjikov/.worktrees/boq-matcher/frontend
npm run dev
```

Open `http://localhost:3000`, upload an xlsx file, click the "Excel" tab. You should see Univer rendering the spreadsheet with formatting.

**Step 6: Commit**

```bash
cd /media/josip-rastocic/DrugiDisk/Programi/troskovljnjikov/.worktrees/boq-matcher
git add frontend/src/app/page.tsx
git commit -m "feat(frontend): add Excel tab to BOQ panel with Univer integration"
```

---

### Task 7: Polish — Debounce selection and handle edge cases

**Files:**
- Modify: `frontend/src/components/spreadsheet/ExcelView.tsx`

**Step 1: Add debounce to selection handler**

The `SelectionChanged` event fires on every mouse movement during drag selection. Add a debounce so the RAG search only fires after the user finishes selecting (e.g., 500ms after last change).

In `ExcelView.tsx`, add a `timeoutRef` alongside the other refs:

```typescript
const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
```

Replace the `SelectionChanged` listener body with:

```typescript
univerAPI.addEvent(univerAPI.Event.SelectionChanged, (params: any) => {
  const { worksheet, selections } = params;
  if (!selections || selections.length === 0 || !worksheet) return;

  // Debounce: wait 500ms after last selection change before searching
  if (debounceRef.current) clearTimeout(debounceRef.current);
  debounceRef.current = setTimeout(() => {
    const texts: string[] = [];
    for (const sel of selections) {
      const range = sel.range;
      if (!range) continue;
      for (let r = range.startRow; r <= range.endRow; r++) {
        for (let c = range.startColumn; c <= range.endColumn; c++) {
          const cell = worksheet.getRange(r, c, r, c);
          const value = cell?.getValue();
          if (value != null && String(value).trim()) {
            texts.push(String(value).trim());
          }
        }
      }
    }
    if (texts.length > 0) {
      startLookup(texts.join(" "));
    }
  }, 500);
});
```

In the cleanup function, also clear the timeout:

```typescript
return () => {
  disposed = true;
  if (debounceRef.current) clearTimeout(debounceRef.current);
  if (univerRef.current) {
    univerRef.current.univerAPI.dispose();
    univerRef.current = null;
  }
};
```

**Step 2: Handle file not available (pre-feature uploads)**

This is already handled — `ExcelView` will show the error state if the `/xlsx` endpoint returns 404.

**Step 3: Commit**

```bash
cd /media/josip-rastocic/DrugiDisk/Programi/troskovljnjikov/.worktrees/boq-matcher
git add frontend/src/components/spreadsheet/ExcelView.tsx
git commit -m "feat(frontend): add debounced selection-to-RAG pipeline in ExcelView"
```

---

### Task 8: End-to-end verification

**Step 1: Start backend**

```bash
cd /media/josip-rastocic/DrugiDisk/Programi/troskovljnjikov/.worktrees/boq-matcher/backend
uv run uvicorn app.main:app --reload --port 8000
```

**Step 2: Start frontend**

```bash
cd /media/josip-rastocic/DrugiDisk/Programi/troskovljnjikov/.worktrees/boq-matcher/frontend
npm run dev
```

**Step 3: Manual test checklist**

1. Upload an xlsx file with formatted cells (colors, bold, borders, merged cells)
2. Verify the file uploads successfully (Parsed tab works as before)
3. Click the "Excel" tab — verify Univer loads and shows the spreadsheet with formatting
4. Verify the view doesn't stretch horizontally beyond ~900px
5. Click a single cell — verify match results appear in the middle column after ~500ms
6. Ctrl+click multiple cells across different rows/columns — verify combined text triggers a RAG search
7. Drag-select a range of cells — verify the debounced search fires
8. Switch between Parsed, Raw, and Excel tabs — verify no crashes or memory leaks
9. Switch to a different file — verify the Excel view updates
10. Click Raw tab — verify it still works as before
