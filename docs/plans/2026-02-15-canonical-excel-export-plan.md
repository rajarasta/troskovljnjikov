# Canonical Excel Export Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a preset-driven canonical Excel export system to the boq-matcher app, allowing users to select column presets, toggle individual columns on/off, and export standardized XLSX files with metadata sheets.

**Architecture:** New `Preset` model + CRUD API on the backend. New `presetStore` + toolbar strip UI on the frontend. The existing 6-column export endpoint is replaced with a preset-driven exporter that reads active columns from query params and generates multi-sheet XLSX with provenance metadata.

**Tech Stack:** FastAPI, SQLAlchemy, openpyxl (backend); React 19, Zustand 5, Tailwind 4 (frontend)

**Design doc:** `docs/plans/2026-02-15-canonical-excel-export-design.md`

**Working directory:** `/media/josip-rastocic/DrugiDisk/Programi/troskovljnjikov/.worktrees/boq-matcher`

---

## Task 1: Preset Model & Default Seed Data

**Files:**
- Create: `backend/app/models/preset.py`
- Create: `backend/app/data/default_presets.json`
- Modify: `backend/app/models/boq.py` (import Base, add to __all__ if used)
- Modify: `backend/app/database.py` (import Preset so create_all picks it up)

**Step 1: Create the default presets JSON**

Create `backend/app/data/default_presets.json`:

```json
[
  {
    "id": "simple",
    "name": "Jednostavni",
    "description": "Standard 6-column BoQ",
    "groups": ["core"],
    "is_default": true
  },
  {
    "id": "mat_rad",
    "name": "Materijal + Rad",
    "description": "Material/labor split pricing",
    "groups": ["core", "mat_rad"],
    "is_default": true
  },
  {
    "id": "multi_zona",
    "name": "Multi-zona",
    "description": "Multiple quantity zones",
    "groups": ["core", "multi_qty"],
    "is_default": true
  },
  {
    "id": "s_bilješkama",
    "name": "S bilješkama",
    "description": "Items with notes, drawings, LLM responses",
    "groups": ["core", "annotation"],
    "is_default": true
  },
  {
    "id": "puni_pregled",
    "name": "Puni pregled",
    "description": "Full internal tracking",
    "groups": ["core", "mat_rad", "annotation", "status", "meta"],
    "is_default": true
  },
  {
    "id": "mat_rad_bilješke",
    "name": "Mat+Rad s bilješkama",
    "description": "Labor split + annotation for review rounds",
    "groups": ["core", "mat_rad", "annotation"],
    "is_default": true
  }
]
```

**Step 2: Create the Preset SQLAlchemy model**

Create `backend/app/models/preset.py`:

```python
from sqlalchemy import Column, String, Boolean, JSON, DateTime
from datetime import datetime
from app.database import Base


class Preset(Base):
    __tablename__ = "presets"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(String, default="")
    groups = Column(JSON, nullable=False)  # e.g. ["core", "mat_rad"]
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
```

**Step 3: Register the model in database.py**

In `backend/app/database.py`, add an import so `create_all` picks up the table:

```python
import app.models.preset  # noqa: F401  — register Preset table
```

**Step 4: Add seed logic**

In `backend/app/database.py`, after `create_tables()`, add a `seed_default_presets()` function:

```python
import json
from pathlib import Path

def seed_default_presets():
    """Insert default presets if they don't exist."""
    from app.models.preset import Preset
    db = SessionLocal()
    try:
        existing = db.query(Preset).filter(Preset.is_default == True).count()
        if existing > 0:
            return
        data_path = Path(__file__).parent / "data" / "default_presets.json"
        presets = json.loads(data_path.read_text())
        for p in presets:
            db.add(Preset(**p))
        db.commit()
    finally:
        db.close()
```

Call `seed_default_presets()` in the app lifespan (in `main.py`), right after `create_tables()`.

**Step 5: Commit**

```bash
git add backend/app/models/preset.py backend/app/data/default_presets.json
git commit -m "feat: add Preset model and default seed data"
```

---

## Task 2: Preset Pydantic Schemas

**Files:**
- Create: `backend/app/schemas/preset.py`

**Step 1: Write the schemas**

Create `backend/app/schemas/preset.py`:

```python
from pydantic import BaseModel


class PresetBase(BaseModel):
    name: str
    description: str = ""
    groups: list[str]


class PresetCreate(PresetBase):
    pass


class PresetUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    groups: list[str] | None = None


class PresetSchema(PresetBase):
    id: str
    is_default: bool

    model_config = {"from_attributes": True}
```

**Step 2: Commit**

```bash
git add backend/app/schemas/preset.py
git commit -m "feat: add Preset pydantic schemas"
```

---

## Task 3: Preset CRUD Router

**Files:**
- Create: `backend/app/routers/presets.py`
- Modify: `backend/app/main.py` (register router)

**Step 1: Write the router**

Create `backend/app/routers/presets.py`:

```python
import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.preset import Preset
from app.schemas.preset import PresetCreate, PresetUpdate, PresetSchema

router = APIRouter()


@router.get("/presets", response_model=list[PresetSchema])
def list_presets(db: Session = Depends(get_db)):
    return db.query(Preset).order_by(Preset.is_default.desc(), Preset.name).all()


@router.get("/presets/{preset_id}", response_model=PresetSchema)
def get_preset(preset_id: str, db: Session = Depends(get_db)):
    preset = db.query(Preset).filter(Preset.id == preset_id).first()
    if not preset:
        raise HTTPException(404, "Preset not found")
    return preset


@router.post("/presets", response_model=PresetSchema, status_code=201)
def create_preset(body: PresetCreate, db: Session = Depends(get_db)):
    preset = Preset(
        id=str(uuid.uuid4()),
        name=body.name,
        description=body.description,
        groups=body.groups,
        is_default=False,
    )
    db.add(preset)
    db.commit()
    db.refresh(preset)
    return preset


@router.put("/presets/{preset_id}", response_model=PresetSchema)
def update_preset(preset_id: str, body: PresetUpdate, db: Session = Depends(get_db)):
    preset = db.query(Preset).filter(Preset.id == preset_id).first()
    if not preset:
        raise HTTPException(404, "Preset not found")
    if preset.is_default:
        raise HTTPException(403, "Cannot modify default presets")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(preset, field, value)
    db.commit()
    db.refresh(preset)
    return preset


@router.delete("/presets/{preset_id}", status_code=204)
def delete_preset(preset_id: str, db: Session = Depends(get_db)):
    preset = db.query(Preset).filter(Preset.id == preset_id).first()
    if not preset:
        raise HTTPException(404, "Preset not found")
    if preset.is_default:
        raise HTTPException(403, "Cannot delete default presets")
    db.delete(preset)
    db.commit()
```

**Step 2: Register the router in main.py**

In `backend/app/main.py`, add:

```python
from app.routers import presets

app.include_router(presets.router, prefix="/api", tags=["presets"])
```

**Step 3: Commit**

```bash
git add backend/app/routers/presets.py
git commit -m "feat: add Preset CRUD API endpoints"
```

---

## Task 4: Column Registry & Resolution Logic

**Files:**
- Create: `backend/app/services/column_registry.py`

This is the core logic that maps group names to column definitions and resolves a preset + overrides into a concrete column list.

**Step 1: Write the column registry**

Create `backend/app/services/column_registry.py`:

```python
"""
Master column registry for canonical BoQ export.

Each column belongs to a group. A preset activates groups.
Individual column overrides can toggle columns on/off beyond the preset.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ColumnDef:
    key: str
    group: str
    label_hr: str        # Croatian header name
    col_type: str        # "string" | "text" | "float" | "image" | "enum" | "date"
    fmt: str             # Excel number format or alignment hint
    width: int           # Column width in characters
    always_on: bool = False


COLUMN_REGISTRY: list[ColumnDef] = [
    # ── core (always on) ──────────────────────────────────────────
    ColumnDef("item_number",  "core", "R.br.",        "string", "left",      10, True),
    ColumnDef("description",  "core", "Opis stavke",  "text",   "left",      50, True),
    ColumnDef("unit",         "core", "Jed.mj.",      "string", "center",     8, True),
    ColumnDef("quantity",     "core", "Količina",     "float",  '#,##0.00',  12, True),
    ColumnDef("unit_price",   "core", "Jed. cijena",  "float",  '#,##0.00',  14, True),
    ColumnDef("total",        "core", "Ukupno",       "float",  '#,##0.00',  14, True),

    # ── mat_rad ───────────────────────────────────────────────────
    ColumnDef("material_price", "mat_rad", "Cijena materijala", "float", '#,##0.00', 14),
    ColumnDef("labor_price",    "mat_rad", "Cijena rada",       "float", '#,##0.00', 14),
    ColumnDef("material_total", "mat_rad", "Ukupno materijal",  "float", '#,##0.00', 14),
    ColumnDef("labor_total",    "mat_rad", "Ukupno rad",        "float", '#,##0.00', 14),

    # ── annotation ────────────────────────────────────────────────
    ColumnDef("notes",        "annotation", "Bilješke",     "text",  "left",  30),
    ColumnDef("drawing",      "annotation", "Crtež",        "image", "left",  15),
    ColumnDef("llm_response", "annotation", "LLM odgovor",  "text",  "left",  30),

    # ── status ────────────────────────────────────────────────────
    ColumnDef("status",     "status", "Status", "enum",  "center",    12),
    ColumnDef("updated_at", "status", "Datum",  "date",  "DD.MM.YYYY", 12),

    # ── meta ──────────────────────────────────────────────────────
    ColumnDef("full_description",   "meta", "Puni opis",        "text",   "left",   50),
    ColumnDef("parent_item_number", "meta", "Nadređena stavka", "string", "left",   12),
    ColumnDef("item_type",          "meta", "Tip stavke",       "enum",   "center", 12),
]

# Lookup by key
_BY_KEY: dict[str, ColumnDef] = {c.key: c for c in COLUMN_REGISTRY}

# Lookup by group
_BY_GROUP: dict[str, list[ColumnDef]] = {}
for c in COLUMN_REGISTRY:
    _BY_GROUP.setdefault(c.group, []).append(c)


def resolve_columns(
    groups: list[str],
    include_columns: list[str] | None = None,
    exclude_columns: list[str] | None = None,
) -> list[ColumnDef]:
    """
    Resolve a list of active groups + per-column overrides into
    the final ordered list of columns for export/display.
    """
    include_columns = set(include_columns or [])
    exclude_columns = set(exclude_columns or [])

    active_keys: set[str] = set()
    for group in groups:
        for col in _BY_GROUP.get(group, []):
            active_keys.add(col.key)

    # Apply overrides
    active_keys |= include_columns
    active_keys -= exclude_columns

    # Always keep always_on columns
    for col in COLUMN_REGISTRY:
        if col.always_on:
            active_keys.add(col.key)

    # Return in registry order
    return [c for c in COLUMN_REGISTRY if c.key in active_keys]


def get_all_groups() -> list[str]:
    """Return all distinct group names in registry order."""
    seen: set[str] = set()
    groups: list[str] = []
    for c in COLUMN_REGISTRY:
        if c.group not in seen:
            seen.add(c.group)
            groups.append(c.group)
    return groups
```

**Step 2: Commit**

```bash
git add backend/app/services/column_registry.py
git commit -m "feat: add column registry with group resolution logic"
```

---

## Task 5: Extend BoQItem Model with New Fields

**Files:**
- Modify: `backend/app/models/boq.py` (add columns to BoQItem)
- Modify: `backend/app/schemas/boq.py` (add fields to BoQItemSchema)
- Modify: `frontend/src/lib/types.ts` (add fields to BoQItem interface)

**Step 1: Add columns to the SQLAlchemy model**

In `backend/app/models/boq.py`, add to `BoQItem`:

```python
    # ── mat_rad fields ──
    material_price = Column(Float, nullable=True)
    labor_price = Column(Float, nullable=True)
    material_total = Column(Float, nullable=True)
    labor_total = Column(Float, nullable=True)

    # ── annotation fields ──
    notes = Column(Text, nullable=True)
    drawing_path = Column(String, nullable=True)  # path to uploaded image
    llm_response = Column(Text, nullable=True)
```

**Step 2: Add fields to Pydantic schema**

In `backend/app/schemas/boq.py`, add to `BoQItemSchema`:

```python
    material_price: float | None = None
    labor_price: float | None = None
    material_total: float | None = None
    labor_total: float | None = None
    notes: str | None = None
    drawing_path: str | None = None
    llm_response: str | None = None
```

**Step 3: Add fields to frontend type**

In `frontend/src/lib/types.ts`, add to `BoQItem`:

```typescript
  material_price: number | null;
  labor_price: number | null;
  material_total: number | null;
  labor_total: number | null;
  notes: string | null;
  drawing_path: string | null;
  llm_response: string | null;
```

**Step 4: Commit**

```bash
git add backend/app/models/boq.py backend/app/schemas/boq.py frontend/src/lib/types.ts
git commit -m "feat: extend BoQItem with mat_rad, annotation fields"
```

**Note:** Since there are no Alembic migrations (tables created via `create_all`), the existing `boq.db` will need to be deleted and recreated to pick up the new columns. This is acceptable for development.

---

## Task 6: Canonical XLSX Export Endpoint

**Files:**
- Modify: `backend/app/routers/export.py` (replace existing XLSX export)

**Step 1: Rewrite the XLSX export endpoint**

Replace the existing `GET /api/export/{file_id}/xlsx` handler with a preset-driven version. The endpoint signature becomes:

```
GET /api/export/{file_id}/xlsx?preset_id=simple&include=notes,drawing&exclude=
```

The full implementation:

```python
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.drawing.image import Image as XlImage
from io import BytesIO
from pathlib import Path
import os

from app.services.column_registry import resolve_columns, ColumnDef
from app.models.preset import Preset


STATUS_COLORS = {
    "PENDING":     "FFF9C4",
    "ACCEPTED":    "C8E6C9",
    "REFUSED":     "FFCDD2",
    "NEGOTIATED":  "BBDEFB",
    "EXPIRED":     "E0E0E0",
}

ITEM_TYPE_STYLES = {
    "section_header": {"bold": True, "fill": "D9D9D9"},
    "ne_nudimo":      {"strikethrough": True, "fill": "FFCDD2"},
}

HEADER_FILL = PatternFill("solid", fgColor="1a1a2e")
HEADER_FONT = Font(bold=True, color="FFFFFF", size=10)
HEADER_ALIGN = Alignment(horizontal="center", vertical="center", wrap_text=True)
THIN_BORDER = Border(
    left=Side(style="thin", color="CCCCCC"),
    right=Side(style="thin", color="CCCCCC"),
    top=Side(style="thin", color="CCCCCC"),
    bottom=Side(style="thin", color="CCCCCC"),
)


@router.get("/export/{file_id}/xlsx")
def export_xlsx(
    file_id: str,
    preset_id: str = "simple",
    include: str = "",
    exclude: str = "",
    db: Session = Depends(get_db),
):
    # Load file and items
    boq_file = db.query(BoQFile).filter(BoQFile.id == file_id).first()
    if not boq_file:
        raise HTTPException(404, "File not found")

    items = db.query(BoQItem).filter(BoQItem.file_id == file_id).order_by(BoQItem.row).all()

    # Load preset
    preset = db.query(Preset).filter(Preset.id == preset_id).first()
    if not preset:
        raise HTTPException(404, f"Preset '{preset_id}' not found")

    # Resolve active columns
    inc = [c.strip() for c in include.split(",") if c.strip()]
    exc = [c.strip() for c in exclude.split(",") if c.strip()]
    columns = resolve_columns(preset.groups, inc, exc)

    # Build workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "Troškovnik"

    _write_troskovnik_sheet(ws, boq_file, items, columns, preset, db)
    _write_metadata_sheet(wb, boq_file, items, columns, preset)

    # Add legend sheet if status group is active
    if any(c.key == "status" for c in columns):
        _write_legend_sheet(wb)

    # Stream response
    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    # File name: {project}_{preset}_{date}.xlsx
    project = (boq_file.project_name or "export").replace(" ", "_")[:30]
    preset_slug = preset.name.replace(" ", "_").replace("+", "")[:20]
    from datetime import datetime
    date_str = datetime.now().strftime("%Y%m%d")
    filename = f"{project}_{preset_slug}_{date_str}.xlsx"

    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
```

Helper functions `_write_troskovnik_sheet`, `_write_metadata_sheet`, `_write_legend_sheet` handle each sheet:

**`_write_troskovnik_sheet`**: Writes rows 1-2 (title + metadata), row 4 (headers), rows 5+ (data), last row (UKUPNO total). Applies `ITEM_TYPE_STYLES` per row based on `item_type`. Handles the `drawing` column by embedding images via `ws.add_image(XlImage(...))`. Applies Croatian number formatting.

**`_write_metadata_sheet`**: Key-value pairs: Izvorni fajl, Projekt, Preset, Aktivni stupci, Datum izvoza, Verzija sheme, Broj stavki, Ukupno.

**`_write_legend_sheet`**: Status color legend table.

**Step 2: Commit**

```bash
git add backend/app/routers/export.py
git commit -m "feat: preset-driven canonical XLSX export with metadata sheet"
```

---

## Task 7: Drawing Upload Endpoint

**Files:**
- Modify: `backend/app/routers/items.py` (add upload endpoint)

**Step 1: Add the drawing upload endpoint**

In `backend/app/routers/items.py`, add:

```python
@router.post("/items/{item_id}/drawing")
async def upload_drawing(
    item_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    item = db.query(BoQItem).filter(BoQItem.id == item_id).first()
    if not item:
        raise HTTPException(404, "Item not found")

    upload_dir = Path("uploads/drawings")
    upload_dir.mkdir(parents=True, exist_ok=True)

    ext = Path(file.filename).suffix or ".png"
    dest = upload_dir / f"{item_id}{ext}"
    content = await file.read()
    dest.write_bytes(content)

    item.drawing_path = str(dest)
    db.commit()
    return {"drawing_path": str(dest)}
```

**Step 2: Serve uploaded images statically**

In `backend/app/main.py`, mount the uploads directory:

```python
from fastapi.staticfiles import StaticFiles

app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
```

**Step 3: Commit**

```bash
git add backend/app/routers/items.py backend/app/main.py
git commit -m "feat: add drawing upload endpoint and static serving"
```

---

## Task 8: Frontend — Preset Types & API Functions

**Files:**
- Modify: `frontend/src/lib/types.ts` (add Preset interface)
- Modify: `frontend/src/lib/api.ts` (add preset API calls)

**Step 1: Add Preset type**

In `frontend/src/lib/types.ts`, add:

```typescript
export interface Preset {
  id: string;
  name: string;
  description: string;
  groups: string[];
  is_default: boolean;
}
```

**Step 2: Add API functions**

In `frontend/src/lib/api.ts`, add:

```typescript
export async function fetchPresets(): Promise<Preset[]> {
  const res = await fetch(`${API_URL}/api/presets`);
  if (!res.ok) throw new Error("Failed to fetch presets");
  return res.json();
}

export async function createPreset(data: { name: string; description?: string; groups: string[] }): Promise<Preset> {
  const res = await fetch(`${API_URL}/api/presets`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error("Failed to create preset");
  return res.json();
}

export async function deletePreset(presetId: string): Promise<void> {
  const res = await fetch(`${API_URL}/api/presets/${presetId}`, { method: "DELETE" });
  if (!res.ok) throw new Error("Failed to delete preset");
}

export function getCanonicalExportUrl(
  fileId: string,
  presetId: string,
  include: string[] = [],
  exclude: string[] = [],
): string {
  const params = new URLSearchParams({ preset_id: presetId });
  if (include.length) params.set("include", include.join(","));
  if (exclude.length) params.set("exclude", exclude.join(","));
  return `${API_URL}/api/export/${fileId}/xlsx?${params}`;
}
```

**Step 3: Commit**

```bash
git add frontend/src/lib/types.ts frontend/src/lib/api.ts
git commit -m "feat: add Preset types and API client functions"
```

---

## Task 9: Frontend — Preset Zustand Store

**Files:**
- Create: `frontend/src/stores/presetStore.ts`

**Step 1: Write the store**

Create `frontend/src/stores/presetStore.ts`:

```typescript
import { create } from "zustand";
import type { Preset } from "@/lib/types";
import * as api from "@/lib/api";

/**
 * Column group → column keys mapping.
 * Mirrors backend column_registry.py groups.
 */
const GROUP_COLUMNS: Record<string, string[]> = {
  core: ["item_number", "description", "unit", "quantity", "unit_price", "total"],
  mat_rad: ["material_price", "labor_price", "material_total", "labor_total"],
  multi_qty: [],  // dynamic, populated per-file
  annotation: ["notes", "drawing", "llm_response"],
  status: ["status", "updated_at"],
  meta: ["full_description", "parent_item_number", "item_type"],
};

interface PresetState {
  presets: Preset[];
  activePresetId: string;
  columnOverrides: { include: Set<string>; exclude: Set<string> };
  isLoading: boolean;

  loadPresets: () => Promise<void>;
  selectPreset: (id: string) => void;
  toggleColumn: (columnKey: string) => void;
  resetToPreset: () => void;
  saveAsNewPreset: (name: string) => Promise<void>;
  getActiveColumns: () => string[];
}

export const usePresetStore = create<PresetState>((set, get) => ({
  presets: [],
  activePresetId: "simple",
  columnOverrides: { include: new Set(), exclude: new Set() },
  isLoading: false,

  loadPresets: async () => {
    set({ isLoading: true });
    try {
      const presets = await api.fetchPresets();
      set({ presets, isLoading: false });
    } catch {
      set({ isLoading: false });
    }
  },

  selectPreset: (id: string) => {
    set({
      activePresetId: id,
      columnOverrides: { include: new Set(), exclude: new Set() },
    });
  },

  toggleColumn: (columnKey: string) => {
    const { columnOverrides, activePresetId, presets } = get();
    const preset = presets.find((p) => p.id === activePresetId);
    if (!preset) return;

    const presetColumns = new Set(
      preset.groups.flatMap((g) => GROUP_COLUMNS[g] ?? []),
    );
    const newInclude = new Set(columnOverrides.include);
    const newExclude = new Set(columnOverrides.exclude);

    if (presetColumns.has(columnKey)) {
      // Column is part of preset — toggle exclude
      if (newExclude.has(columnKey)) {
        newExclude.delete(columnKey);
      } else {
        newExclude.add(columnKey);
      }
    } else {
      // Column is NOT part of preset — toggle include
      if (newInclude.has(columnKey)) {
        newInclude.delete(columnKey);
      } else {
        newInclude.add(columnKey);
      }
    }

    set({ columnOverrides: { include: newInclude, exclude: newExclude } });
  },

  resetToPreset: () => {
    set({ columnOverrides: { include: new Set(), exclude: new Set() } });
  },

  saveAsNewPreset: async (name: string) => {
    const activeColumns = get().getActiveColumns();
    // Reverse-resolve which groups cover these columns
    const groups = Object.entries(GROUP_COLUMNS)
      .filter(([, cols]) => cols.length > 0 && cols.every((c) => activeColumns.includes(c)))
      .map(([group]) => group);

    const preset = await api.createPreset({ name, groups });
    set((s) => ({
      presets: [...s.presets, preset],
      activePresetId: preset.id,
      columnOverrides: { include: new Set(), exclude: new Set() },
    }));
  },

  getActiveColumns: () => {
    const { activePresetId, presets, columnOverrides } = get();
    const preset = presets.find((p) => p.id === activePresetId);
    if (!preset) return GROUP_COLUMNS.core;

    const presetColumns = new Set(
      preset.groups.flatMap((g) => GROUP_COLUMNS[g] ?? []),
    );

    // Apply overrides
    for (const col of columnOverrides.include) presetColumns.add(col);
    for (const col of columnOverrides.exclude) presetColumns.delete(col);

    // Ensure core always present
    for (const col of GROUP_COLUMNS.core) presetColumns.add(col);

    return [...presetColumns];
  },
}));
```

**Step 2: Commit**

```bash
git add frontend/src/stores/presetStore.ts
git commit -m "feat: add presetStore with column toggle logic"
```

---

## Task 10: Frontend — Toolbar Strip Component

**Files:**
- Create: `frontend/src/components/layout/PresetToolbar.tsx`
- Modify: `frontend/src/app/page.tsx` (add toolbar above the BoQ table area)

**Step 1: Create the toolbar component**

Create `frontend/src/components/layout/PresetToolbar.tsx`:

```tsx
"use client";

import { useEffect } from "react";
import { usePresetStore } from "@/stores/presetStore";
import { useBoQStore } from "@/stores/boqStore";
import * as api from "@/lib/api";

const ALL_OPTIONAL_COLUMNS = [
  { key: "material_price", label: "Cijena mat." },
  { key: "labor_price", label: "Cijena rada" },
  { key: "notes", label: "Bilješke" },
  { key: "drawing", label: "Crtež" },
  { key: "llm_response", label: "LLM" },
  { key: "status", label: "Status" },
  { key: "full_description", label: "Puni opis" },
  { key: "item_type", label: "Tip" },
];

export function PresetToolbar() {
  const {
    presets,
    activePresetId,
    loadPresets,
    selectPreset,
    toggleColumn,
    getActiveColumns,
  } = usePresetStore();
  const selectedFileId = useBoQStore((s) => s.selectedFileId);

  useEffect(() => {
    loadPresets();
  }, [loadPresets]);

  const activeColumns = getActiveColumns();

  const handleExport = () => {
    if (!selectedFileId) return;
    const { columnOverrides } = usePresetStore.getState();
    const url = api.getCanonicalExportUrl(
      selectedFileId,
      activePresetId,
      [...columnOverrides.include],
      [...columnOverrides.exclude],
    );
    window.open(url, "_blank");
  };

  return (
    <div className="flex items-center gap-3 px-3 py-2 bg-zinc-900 border-b border-zinc-800 text-sm">
      {/* Preset dropdown */}
      <label className="text-zinc-400 shrink-0">Preset:</label>
      <select
        value={activePresetId}
        onChange={(e) => selectPreset(e.target.value)}
        className="bg-zinc-800 text-zinc-100 border border-zinc-700 rounded px-2 py-1 text-sm"
      >
        {presets.map((p) => (
          <option key={p.id} value={p.id}>
            {p.name}
          </option>
        ))}
      </select>

      {/* Column toggle chips */}
      <div className="flex items-center gap-1 overflow-x-auto">
        {ALL_OPTIONAL_COLUMNS.map((col) => {
          const isActive = activeColumns.includes(col.key);
          return (
            <button
              key={col.key}
              onClick={() => toggleColumn(col.key)}
              className={`px-2 py-0.5 rounded-full text-xs whitespace-nowrap transition-colors ${
                isActive
                  ? "bg-blue-600 text-white"
                  : "bg-zinc-800 text-zinc-500 hover:text-zinc-300"
              }`}
            >
              {isActive ? "" : "+"}{col.label}
            </button>
          );
        })}
      </div>

      {/* Export button */}
      <button
        onClick={handleExport}
        disabled={!selectedFileId}
        className="ml-auto shrink-0 px-3 py-1 bg-emerald-600 hover:bg-emerald-500 disabled:bg-zinc-700 disabled:text-zinc-500 text-white rounded text-sm transition-colors"
      >
        Export XLSX
      </button>
    </div>
  );
}
```

**Step 2: Wire into the main page**

In `frontend/src/app/page.tsx`, import and render `<PresetToolbar />` above the main grid layout. The exact placement depends on the existing layout structure — it goes right above the BoQ table/spreadsheet column.

**Step 3: Commit**

```bash
git add frontend/src/components/layout/PresetToolbar.tsx frontend/src/app/page.tsx
git commit -m "feat: add PresetToolbar with dropdown, column chips, export button"
```

---

## Task 11: Frontend — Dynamic Column Rendering in Table

**Files:**
- Modify: `frontend/src/lib/boqTableConfig.ts` (extend with all columns + filter function)

**Step 1: Extend the column config**

Replace the hardcoded `BOQ_COLUMNS` array in `boqTableConfig.ts` with a full registry + a `getVisibleColumns()` function:

```typescript
import { usePresetStore } from "@/stores/presetStore";

export interface BoQColumn {
  key: string;
  label: string;
  width: string | undefined;
  align: "left" | "right" | "center";
}

const ALL_BOQ_COLUMNS: BoQColumn[] = [
  { key: "item_number",      label: "#",               width: "60px",    align: "left" },
  { key: "description",      label: "Opis stavke",     width: undefined, align: "left" },
  { key: "unit",             label: "Jed.",            width: "60px",    align: "left" },
  { key: "quantity",         label: "Količina",        width: "80px",    align: "right" },
  { key: "unit_price",       label: "Jed. cijena",     width: "100px",   align: "right" },
  { key: "total",            label: "Ukupno",          width: "100px",   align: "right" },
  { key: "material_price",   label: "Cijena mat.",     width: "100px",   align: "right" },
  { key: "labor_price",      label: "Cijena rada",     width: "100px",   align: "right" },
  { key: "material_total",   label: "Uk. materijal",   width: "100px",   align: "right" },
  { key: "labor_total",      label: "Uk. rad",         width: "100px",   align: "right" },
  { key: "notes",            label: "Bilješke",        width: "150px",   align: "left" },
  { key: "drawing",          label: "Crtež",           width: "80px",    align: "center" },
  { key: "llm_response",     label: "LLM",             width: "150px",   align: "left" },
  { key: "status",           label: "Status",          width: "90px",    align: "center" },
  { key: "updated_at",       label: "Datum",           width: "90px",    align: "center" },
  { key: "full_description", label: "Puni opis",       width: "200px",   align: "left" },
  { key: "parent_item_number", label: "Nadređena",     width: "80px",    align: "left" },
  { key: "item_type",        label: "Tip",             width: "80px",    align: "center" },
];

export function getVisibleColumns(): BoQColumn[] {
  const activeKeys = usePresetStore.getState().getActiveColumns();
  return ALL_BOQ_COLUMNS.filter((c) => activeKeys.includes(c.key));
}

// Keep legacy export for components that haven't migrated yet
export const BOQ_COLUMNS = ALL_BOQ_COLUMNS.slice(0, 6);
```

**Step 2: Commit**

```bash
git add frontend/src/lib/boqTableConfig.ts
git commit -m "feat: extend boqTableConfig with all canonical columns and visibility filter"
```

---

## Task 12: Backend Tests — Preset CRUD & Export

**Files:**
- Create: `backend/tests/test_presets.py`

**Step 1: Write the tests**

```python
"""Tests for preset CRUD and canonical export."""


def test_list_default_presets(client):
    """Default presets are seeded on startup."""
    res = client.get("/api/presets")
    assert res.status_code == 200
    presets = res.json()
    assert len(presets) >= 6
    assert all(p["is_default"] for p in presets[:6])


def test_create_custom_preset(client):
    """User can create a custom preset."""
    res = client.post("/api/presets", json={
        "name": "Test preset",
        "description": "For testing",
        "groups": ["core", "annotation"],
    })
    assert res.status_code == 201
    data = res.json()
    assert data["name"] == "Test preset"
    assert data["is_default"] is False
    assert "annotation" in data["groups"]


def test_delete_default_preset_blocked(client):
    """Cannot delete a default preset."""
    res = client.get("/api/presets")
    default_id = res.json()[0]["id"]
    res = client.delete(f"/api/presets/{default_id}")
    assert res.status_code == 403


def test_delete_custom_preset(client):
    """Can delete a user-created preset."""
    create = client.post("/api/presets", json={
        "name": "Temp",
        "groups": ["core"],
    })
    pid = create.json()["id"]
    res = client.delete(f"/api/presets/{pid}")
    assert res.status_code == 204


def test_canonical_export_with_preset(client, sample_xlsx_path):
    """Export XLSX using a preset produces a valid file."""
    # Upload a file first
    with open(sample_xlsx_path, "rb") as f:
        upload = client.post("/api/upload", files={"file": ("test.xlsx", f)})
    file_id = upload.json()["file_id"]

    # Export with default simple preset
    res = client.get(f"/api/export/{file_id}/xlsx?preset_id=simple")
    assert res.status_code == 200
    assert "spreadsheetml" in res.headers["content-type"]

    # Export with full preset
    res = client.get(f"/api/export/{file_id}/xlsx?preset_id=puni_pregled")
    assert res.status_code == 200


def test_export_unknown_preset_404(client, sample_xlsx_path):
    """Export with nonexistent preset returns 404."""
    with open(sample_xlsx_path, "rb") as f:
        upload = client.post("/api/upload", files={"file": ("test.xlsx", f)})
    file_id = upload.json()["file_id"]

    res = client.get(f"/api/export/{file_id}/xlsx?preset_id=nonexistent")
    assert res.status_code == 404
```

**Step 2: Run tests**

```bash
cd backend && uv run pytest tests/test_presets.py -v
```

Expected: All 6 tests pass.

**Step 3: Commit**

```bash
git add backend/tests/test_presets.py
git commit -m "test: add preset CRUD and canonical export tests"
```

---

## Task Summary

| Task | Component | New/Modify | Estimated Steps |
|------|-----------|------------|-----------------|
| 1 | Preset Model + Seed Data | New | 5 |
| 2 | Preset Pydantic Schemas | New | 2 |
| 3 | Preset CRUD Router | New | 3 |
| 4 | Column Registry | New | 2 |
| 5 | Extend BoQItem Fields | Modify | 4 |
| 6 | Canonical XLSX Export | Modify | 2 |
| 7 | Drawing Upload Endpoint | Modify | 3 |
| 8 | Frontend Types & API | Modify | 3 |
| 9 | Preset Zustand Store | New | 2 |
| 10 | Toolbar Strip Component | New | 3 |
| 11 | Dynamic Column Rendering | Modify | 2 |
| 12 | Backend Tests | New | 3 |

**Execution order:** Tasks 1-4 (backend foundation) → Task 5 (model changes) → Tasks 6-7 (backend features) → Tasks 8-11 (frontend) → Task 12 (tests). Tasks 1-4 can be parallelized. Tasks 8-11 can be parallelized.
