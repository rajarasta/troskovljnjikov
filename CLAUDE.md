# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

BoQ (Bill of Quantities) matcher web app for Croatian construction cost estimation. Upload Excel BoQ files, view them in a native spreadsheet interface, leverage AI agents for parsing and price matching against historic data via ChromaDB RAG, manage column visibility with presets, and export canonical XLSX with metadata.

**Tech stack**: Next.js 15 + React 19 + FastAPI + SQLite + ChromaDB + PydanticAI

The LLM backend is a local llama-server (GGUF model) exposed via OpenAI-compatible API at `http://localhost:8080/v1`.

## Project Structure

```
troskovljnjikov/
├── frontend/          # Next.js 15 + TypeScript + Tailwind + Zustand
│   ├── src/app/       # Next.js app router pages
│   ├── src/components/# UI components (spreadsheet, agents, chat, upload, etc.)
│   ├── src/stores/    # Zustand state management
│   └── src/lib/       # API client, types, config
├── backend/
│   ├── app/           # FastAPI main implementation (merged from boq-matcher)
│   │   ├── agents/    # PydanticAI agents (parser, matcher, pricer, vision)
│   │   ├── services/  # Core services (boq_indexer with ChromaDB, hierarchy, RAG)
│   │   ├── routers/   # API endpoints (upload, items, agents, presets, export, chat)
│   │   ├── models/    # SQLAlchemy models
│   │   └── schemas/   # Pydantic schemas
│   ├── src/           # Legacy implementation (boq-editor, may coexist)
│   ├── data/          # SQLite database
│   └── tests/         # pytest test suite
├── bin/               # llama-server binary (gitignored)
├── models/            # GGUF model files (gitignored)
├── docs/plans/        # Design and implementation documents
└── run.sh             # Dev launcher (llama-server + backend + frontend)
```

## Commands

All commands are run from the repo root.

```bash
# Run everything (llama-server + backend + frontend)
./run.sh

# Backend only
cd backend && uv run uvicorn app.main:app --reload --port 8000

# Frontend only
cd frontend && npm run dev

# Run tests
cd backend && uv run pytest

# Install/sync dependencies
cd backend && uv sync
cd frontend && npm install
```

## Git Worktrees

Active feature branches may be developed in `.worktrees/` (gitignored). The `feature/boq-matcher` branch has been merged into master.

## Architecture

### Backend (`backend/app/`)

- **Agents** (`agents/`): PydanticAI-powered AI agents
  - `parser_agent.py` — Extracts BoQ hierarchy from Excel, detects format families
  - `matcher_agent.py` — Matches items against historic data using ChromaDB
  - `pricer_agent.py` — Suggests prices based on matches and context
  - `vision_agent.py` — Analyzes uploaded photos for site conditions

- **Services** (`services/`):
  - `boq_indexer.py` — ChromaDB vector store manager, indexes historic BoQ items for RAG retrieval
  - `boq_hierarchy.py` — Detects Excel format, classifies rows, builds item hierarchy
  - `workbook_converter.py` — Converts uploaded Excel to internal format
  - `column_registry.py` — Registry of canonical BoQ columns with group resolution
  - `rag.py` — RAG retrieval utilities

- **Routers** (`routers/`): FastAPI endpoints
  - `upload.py` — File upload and format detection
  - `items.py` — BoQ item CRUD, hierarchy navigation
  - `agents.py` — AI agent pipeline endpoints (SSE streaming)
  - `presets.py` — Preset CRUD (column visibility configurations)
  - `export.py` — Canonical XLSX export with metadata sheet
  - `chat.py` — WebSocket chat interface
  - `pipeline.py` — Multi-agent pipeline orchestration

- **Database**: SQLite with SQLAlchemy ORM, stores BoQ items, presets, and metadata

### Frontend (Next.js)

- **Pages** (`src/app/`): Single-page app with multi-panel layout
- **Components** (`src/components/`):
  - `spreadsheet/` — Native Excel view with editable cells, column headers
  - `agents/` — Agent cards, timeline, panel
  - `boq/` — Match cards, navigator, status badges, quantity gauges
  - `chat/` — Chat drawer, message display, input
  - `upload/` — File upload zone, file list
  - `photos/` — Photo upload and analysis display
  - `layout/` — Top bar, pipeline bar, preset toolbar, column headers

- **Stores** (Zustand): `boqStore`, `agentStore`, `chatPanelStore`, `matchStore`, `pipelineStore`, `presetStore`, `selectionStore`
- **API Client** (`src/lib/api.ts`): Type-safe fetch wrapper for backend endpoints

### Data Flow

1. **Upload** → Excel file → `workbook_converter` → hierarchy detection → SQLite
2. **Indexing** → Historic items → `boq_indexer` → ChromaDB vector embeddings
3. **Matching** → User selects item → `matcher_agent` → ChromaDB search → ranked matches
4. **Pricing** → Matches + context → `pricer_agent` → price suggestion
5. **Export** → Preset config → `column_registry` → canonical XLSX with metadata

## Other Files

- `analyze_xlsx.py` — Standalone BoQ Excel file analyzer: detects headers, classifies row patterns (hierarchical/sequential/sparse), identifies format families across multiple files. Uses openpyxl. Hardcoded to scan `vanjski-podaci/primjeri-excel-ponuda/`.
- `vanjski-podaci/` — External data directory (untracked) with sample Excel BoQ files and a `system_prompt_template.md` for Croatian BoQ extraction rules.
- `docs/plans/` — Design and implementation plan documents.

## BoQ Unit Taxonomy

Croatian BoQ files contain 7 distinct row types. Understanding these is critical for parsing, indexing, and price history retrieval.

| # | Type | Has Price? | Indexed in RAG? |
|---|------|-----------|-----------------|
| 1 | **Section Header** — e.g. "3.1.1. Hidroizolacija podova" | No | No |
| 2 | **Simple Item** — position + description + unit + qty + price | Yes | Yes (own description) |
| 3 | **Composite Unit** — parent description + sub-items (a, b, c…) with different units/prices | Sub-items only | Yes (parent description) |
| 4 | **"Ne Nudimo" Item** — price = 0.00€, bidder declines to quote | Zero | Yes (flagged) |
| 5 | **Subtotal Row** — "UKUPNO: 19,525.75€" | Sum only | No |
| 6 | **Continuation Row** — multi-line description overflow | No | No (merged into parent) |
| 7 | **Empty/Spacer Row** | No | No |

**Composite Unit** is the key type for price history. Structure:
- Parent row: position number + bold title + long shared description (may span multiple rows)
- Sub-items (a, b, c…): each with DIFFERENT units (m², m, komad), quantities, and unit prices
- Sub-item descriptions are short labels, only meaningful with parent context
- UKUPNO subtotal row at the end

The `item_type` column on `BoQItem` classifies each row: `simple`, `composite_sub`, `ne_nudimo`, `section_header`.

## Key Technical Details

- **Package managers**: uv (backend), npm (frontend)
- **Python**: >=3.11
- **Node**: >=18 (for Next.js 15)
- **LLM**: Local llama-server at http://localhost:8080/v1
- **Backend**: FastAPI on port 8000, async/await throughout
- **Frontend**: Next.js 15 on port 3000, proxies `/api` to backend
- **Vector DB**: ChromaDB for RAG-based historic item matching
- **Observability**: Logfire configured at module level, instruments PydanticAI agent calls
- **Model files**: `bin/` and `models/` are gitignored — llama-server binary, CUDA libs, and GGUF model must be provided separately
- **File encoding**: Upload handler tries utf-8-sig, utf-8, utf-16, cp1252, latin-1 in order
- **Domain language**: Croatian construction terminology (troškovnik = BoQ, stavka = item, jedinična cijena = unit price, količina = quantity)
- **WebSocket**: Real-time updates for agent pipeline and chat
- **SSE**: Server-Sent Events for streaming agent responses
