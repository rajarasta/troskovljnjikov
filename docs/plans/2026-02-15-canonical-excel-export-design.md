# Canonical Excel Export Design

**Date:** 2026-02-15
**Status:** Approved
**Branch:** TBD (implementation)

## Goal

Define a standardized Excel export format for internal BoQ development versioning. Regardless of what messy Excel format comes in (Eurospin, Kaufland, public tenders, etc.), the output always follows the same canonical structure. This makes cross-project comparison and change tracking straightforward.

## Approach: Column-Group Schema with Presets

One master schema defines all possible columns organized into **groups**. Each "schema" (preset) is a named combination of which groups are active. Columns are toggleable on/off per-export.

---

## Section 1: Master Column Registry

Every possible column lives in a single registry. Each column belongs to a group and has formatting rules.

| Group | Column Key | Croatian Name | Type | Format | Always On? |
|-------|-----------|---------------|------|--------|------------|
| **core** | `item_number` | R.br. | string | left | yes |
| **core** | `description` | Opis stavke | text | left, wrap | yes |
| **core** | `unit` | Jed.mj. | string | center | yes |
| **core** | `quantity` | Količina | float | `#.##0,00` | yes |
| **core** | `unit_price` | Jed. cijena | float | `#.##0,00` | yes |
| **core** | `total` | Ukupno | float | `#.##0,00` | yes |
| **mat_rad** | `material_price` | Cijena materijala | float | `#.##0,00` | no |
| **mat_rad** | `labor_price` | Cijena rada | float | `#.##0,00` | no |
| **mat_rad** | `material_total` | Ukupno materijal | float | `#.##0,00` | no |
| **mat_rad** | `labor_total` | Ukupno rad | float | `#.##0,00` | no |
| **multi_qty** | `qty_zone_*` | Količina (zona N) | float | `#.##0,00` | no |
| **annotation** | `notes` | Bilješke | text | left, wrap | no |
| **annotation** | `drawing` | Crtež | image | embedded | no |
| **annotation** | `llm_response` | LLM odgovor | text | left, wrap | no |
| **status** | `status` | Status | enum | center | no |
| **status** | `updated_at` | Datum | date | `DD.MM.YYYY` | no |
| **meta** | `full_description` | Puni opis | text | left, wrap | no |
| **meta** | `parent_item_number` | Nadređena stavka | string | left | no |
| **meta** | `item_type` | Tip stavke | enum | center | no |

The **core** group is always present. Everything else is toggleable.

---

## Section 2: Presets

A preset is a named configuration defining which column groups are active.

```json
{
  "id": "simple",
  "name": "Jednostavni",
  "description": "Standard 6-column BoQ",
  "groups": ["core"]
}
```

### Starter presets

| # | Preset Name | Active Groups | Use Case |
|---|-------------|---------------|----------|
| 1 | **Jednostavni** | core | Basic qty x price BoQs |
| 2 | **Materijal + Rad** | core, mat_rad | Material/labor split pricing |
| 3 | **Multi-zona** | core, multi_qty | Multiple quantity zones (floors, areas) |
| 4 | **S bilješkama** | core, annotation | Items with notes, drawings, LLM responses |
| 5 | **Puni pregled** | core, mat_rad, annotation, status, meta | Full internal tracking |
| 6 | **Mat+Rad s bilješkama** | core, mat_rad, annotation | Labor split + annotation for review rounds |

Custom override: beyond presets, individual columns can be toggled on/off before export. The preset is the starting point.

Presets are stored in the database (SQLite via SQLAlchemy) with default presets seeded on first run.

---

## Section 3: Preset Control System in the App

### Backend

```
backend/app/
  models/preset.py        # SQLAlchemy model
  schemas/preset.py       # Pydantic schemas
  routers/presets.py      # CRUD endpoints
  data/default_presets.json  # 6 starter presets (seeded on first run)
```

**API endpoints:**

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/api/presets` | List all presets (defaults + user-created) |
| `POST` | `/api/presets` | Create custom preset |
| `PUT` | `/api/presets/{id}` | Update preset |
| `DELETE` | `/api/presets/{id}` | Delete custom preset (defaults protected) |
| `GET` | `/api/export/{file_id}/xlsx?preset={id}&columns={overrides}` | Export with preset + optional per-column overrides |

### Frontend: Zustand Store

New `presetStore.ts`:

```typescript
interface PresetState {
  presets: Preset[];
  activePresetId: string;
  columnOverrides: Set<string>;  // per-column toggles on top of preset

  loadPresets: () => Promise<void>;
  selectPreset: (id: string) => void;
  toggleColumn: (columnKey: string) => void;
  resetToPreset: () => void;
  saveAsNewPreset: (name: string) => Promise<void>;
}
```

### Frontend: UI — Toolbar Strip

Horizontal bar above the BoQ table:

```
┌─────────────────────────────────────────────────────────────┐
│ Preset: [Jednostavni ▾]  │  Columns: [+Bilješke] [+Crtež]  │  [Export ▾] │
└─────────────────────────────────────────────────────────────┘
│                        BoQ Table                             │
```

- **Preset dropdown** — select from presets
- **Column chips** — quick toggles for individual columns beyond preset defaults
- **Export button** — dropdown with format choice (XLSX/PDF), exports with current visible columns

### Drawing column behavior

- **In table UI**: Thumbnail with click-to-expand + upload dropzone per cell
- **In Excel export**: Images embedded via openpyxl `add_image()`, row heights auto-adjusted
- **Storage**: `uploads/drawings/{item_id}.png` on backend

---

## Section 4: Canonical Excel Export Format

### Sheet structure

| Sheet | Content | Always present? |
|-------|---------|----------------|
| **Troškovnik** | BoQ data with active columns | Yes |
| **Metadata** | Export provenance (preset, source, timestamp, columns) | Yes |
| **Legenda** | Color/status legend | Only with status group |

### Troškovnik sheet layout

```
Row 1:  [Project name]                          (merged, bold 14pt)
Row 2:  [Source file: X | Preset: Y | Date: Z]  (merged, italic gray)
Row 3:  (empty spacer)
Row 4:  [Column headers]                         (dark blue bg #1a1a2e, white bold)
Row 5+: [Data rows]
  ...
Last:   [UKUPNO:]  [grand total]                 (bold, top border)
```

### Styling rules

| Element | Style |
|---------|-------|
| Section headers (`item_type = section_header`) | Bold, gray background, merged description across data columns |
| Composite parent rows | Bold description, no price |
| "Ne nudimo" items | Strikethrough, light red background |
| Subtotal rows | Bold, top border, right-aligned sum |
| Numbers | Croatian formatting: `1.234,56` (dot thousands, comma decimal) |
| Description column | Word-wrap enabled, auto row height |
| Drawing cells | Image anchored in cell, row height = max(image height, 60px) |

### Status column colors

| Status | Color | Croatian |
|--------|-------|----------|
| PENDING | `#FFF9C4` (light yellow) | Na čekanju |
| ACCEPTED | `#C8E6C9` (light green) | Prihvaćeno |
| REFUSED | `#FFCDD2` (light red) | Odbijeno |
| NEGOTIATED | `#BBDEFB` (light blue) | Dogovoreno |
| EXPIRED | `#E0E0E0` (gray) | Isteklo |

### Metadata sheet

Key-value table:

```
Key                    Value
Izvorni fajl           Eurospin_ponuda_2024.xlsx
Projekt                Eurospin Osijek - rekonstrukcija
Preset                 Materijal + Rad
Aktivni stupci         R.br., Opis, Jed.mj., Količina, ...
Datum izvoza           15.02.2026. 14:30
Verzija sheme          1.0
Broj stavki            142
Ukupno                 1.234.567,89 EUR
```

### File naming convention

```
{project_name}_{preset_name}_{YYYYMMDD}.xlsx
```

Example: `Eurospin_Osijek_MatRad_20260215.xlsx`

---

## Section 5: Data Flow — Import to Canonical Export

```
Upload Excel ──▶ Parse & Detect ──▶ Map to BoQItem ──▶ Store in DB
  (any format)    (boq_indexer +      model              (items, units,
                   boq_hierarchy)                         statuses)
                                                              │
                   Generate .xlsx ◀── Select Preset + ◀───────┘
                   (openpyxl)         Toggle Columns
                        │
                        ▼
                   Canonical Export
                   (self-documenting
                    with metadata)
```

### New vs. existing components

| Component | Status | Work Needed |
|-----------|--------|-------------|
| Upload + parse | Exists | No changes |
| BoQItem model | Exists | Add `material_price`, `labor_price`, `drawing_path` fields |
| Preset model + API | New | Backend CRUD + seed defaults |
| Preset store (frontend) | New | Zustand store + toolbar UI |
| Column visibility in table | New | Dynamic column rendering |
| Drawing upload/embed | New | Upload endpoint + cell embedding |
| Canonical export endpoint | Extend existing | Replace current 6-col export with preset-driven export |
| Metadata sheet | New | Added to export logic |

### Unchanged

- Original numbering/hierarchy preserved as-is
- changesStore diffing still works on core fields
- matchStore lookups can optionally populate `llm_response` column
- Upload/parsing flow untouched
