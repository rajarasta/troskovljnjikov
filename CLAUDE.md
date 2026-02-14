# CLAUDE.md

## Project Overview

BoQ (Bill of Quantities) editor desktop app for construction cost estimation. Upload Excel BoQ files, compare against historic data with AI-assisted price suggestions, edit and export results.

**Tech stack**: Tauri v2 + React (Vite/TypeScript) + FastAPI (Python) + SQLite + PydanticAI

## Project Structure

```
troskovljnjikov/
├── frontend/          # React + Vite + TypeScript + Tailwind + Zustand + Framer Motion
├── backend/           # Python FastAPI + openpyxl + aiosqlite + PydanticAI
├── src-tauri/         # (Phase 2) Tauri desktop shell
├── bin/               # llama-server binary (gitignored)
├── models/            # GGUF model files (gitignored)
└── run.sh             # Dev launcher (all 3 services)
```

## Commands

```bash
# Run everything (llama-server + backend + frontend)
./run.sh

# Backend only
cd backend && uv run uvicorn src.main:app --reload --port 8081

# Frontend only
cd frontend && npm run dev

# Install deps
cd backend && uv sync
cd frontend && npm install
```

## Architecture

### Backend (FastAPI)

- **Parser** (`backend/src/parser/`): Detects Excel format (Eurospin 6-col or Kaufland 7-col), classifies rows by type (chapter/section/work_item/description/priced_line), assembles logical units
- **Database** (`backend/src/db/`): SQLite with FTS5 for historic BoQ storage and full-text search
- **Agent** (`backend/src/agent/`): Price suggestion pipeline using historic data matching + PydanticAI
- **API** (`backend/src/api/`): REST + SSE endpoints for upload, units, agent suggestions, historic search, export

### Frontend (React)

- **4-panel layout**: Left-AI | Left-Historic | Middle (carousel) | Right (output)
- **Stores** (Zustand): boqStore (data), agentStore (AI state), uiStore (scroll sync)
- **SSE streaming**: Agent suggestions stream in real-time with typing animations

### Data Model

A **LogicalUnit** = Level-4 work item with title, description, and priced sub-items (a, b, c).

## Key Technical Details

- **Package managers**: uv (backend), npm (frontend)
- **Python**: >=3.11
- **LLM**: Local llama-server at http://localhost:8080/v1
- **Dev proxy**: Vite proxies /api to backend at :8081
- **Excel formats**: Two families detected automatically (Eurospin dotted hierarchy, Kaufland code-based)
