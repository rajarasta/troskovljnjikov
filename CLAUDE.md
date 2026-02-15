# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

BoQ (Bill of Quantities) tooling for Croatian construction cost estimation. The project evolves across git worktrees — `master` has a prototype letter guessing game, while feature branches build toward the real goal: parsing Excel BoQ files, matching against historic data, and AI-assisted price suggestions.

The LLM backend is a local llama-server (GGUF model) exposed via OpenAI-compatible API at `http://localhost:8080/v1`.

## Commands

All commands are run from the repo root.

```bash
# Run everything (starts llama-server + Streamlit UI, cleans up on exit)
./run.sh

# Run boq-matcher (rebuild frontend + start backend + frontend)
.worktrees/boq-matcher/run.sh

# Start LLM server manually
LD_LIBRARY_PATH=./bin:$LD_LIBRARY_PATH ./bin/llama-server -m ./models/llama3.gguf -ngl 99 --parallel 4 --cont-batching --cache-reuse 512 --chat-template chatml

# Start Streamlit UI
uv run streamlit run main.py

# Install/sync dependencies
uv sync
```

No automated test suite. Testing is manual via the Streamlit UI using `test_input.txt`.

## Git Worktrees

Active feature branches are developed in `.worktrees/` (gitignored). Each has its own venv and may have its own CLAUDE.md.

| Worktree | Branch | Description |
|----------|--------|-------------|
| `.worktrees/boq-editor` | `feature/boq-editor` | Tauri + React + FastAPI desktop app for BoQ editing with AI price suggestions |
| `.worktrees/boq-streamlit-ui` | `feature/boq-streamlit-ui` | Streamlit-based BoQ UI with multi-page app structure |
| `.worktrees/boq-matcher` | `feature/boq-matcher` | BoQ matching engine with FastAPI backend |

## Architecture (master branch)

`main.py` (~227 lines) is a Streamlit + PydanticAI multi-agent letter guessing game organized as:

1. **State Management** — `st.session_state.ui_state` dict tracking game phase, logs, anchors, comparisons, reconstruction progress
2. **Game State & Model** — `GameState` dataclass as PydanticAI deps; `OpenAIProvider` → local llama-server
3. **Deterministic Agents** — Pure Python functions (`anchor_agent`, `compare_agent_a/b`, `retrieval_agent`) extracting structural text features without LLM calls
4. **Guesser Agent** — PydanticAI `Agent` with `@guesser_agent.instructions` building context showing partially revealed text (`?` at current position); max 5 wrong guesses per position before revealing
5. **Game Loop** — `async run_game()` orchestrates Phase 1 → Phase 2 character-by-character LLM guessing
6. **Streamlit UI** — Two-column layout: left for upload/controls/results, right for agent activity log

## Other Files (master)

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

- **Package manager**: uv (not pip/poetry). Use `uv run` to execute commands.
- **Python**: >=3.11
- **Async**: Game loop uses `asyncio.run()` within Streamlit's synchronous model
- **Observability**: Logfire configured at module level, instruments PydanticAI agent calls
- **Model files**: `bin/` and `models/` are gitignored — llama-server binary, CUDA libs, and GGUF model must be provided separately
- **File encoding**: Upload handler tries utf-8-sig, utf-8, utf-16, cp1252, latin-1 in order
- **Domain language**: Croatian construction terminology (troškovnik = BoQ, stavka = item, jedinična cijena = unit price, količina = quantity)
