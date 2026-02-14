# Agentic Document Editor v1 — Design

## Goal

Build a Streamlit + PydanticAI multi-agent document analysis app backed by a local llama-server. This is the foundation for future work on Croatian language models, BoQ parsing, vision agents, and edge-deployed multi-model systems.

## Architecture

Single-file Streamlit app (`main.py`) with PydanticAI agent orchestration connecting to a local llama-server via OpenAI-compatible API.

## Files

| File | Purpose |
|------|---------|
| `main.py` | All logic: state management, schemas, agents, tools, Streamlit UI |
| `pyproject.toml` | Dependencies managed by `uv` |
| `run.sh` | One-click launcher: starts llama-server in background, runs Streamlit, cleans up on exit |

## Agents

1. **Orchestrator** — Main agent. Receives user file content as deps. Delegates analysis to registered tools.
2. **Confirmation Agent** — Transient specialist. Spawned via `verify_logic` tool to double-check orchestrator proposals. Returns `ConfirmationVerdict` (approved: bool, reason: str). Unspawns after returning.

## Tools (registered on Orchestrator)

1. `get_anchor_letters(ctx)` — Extracts 2nd and penultimate characters from text content. Updates UI state with results.
2. `verify_logic(ctx, proposal)` — Spawns confirmation agent to evaluate a proposal string. Logs activity. Updates summary state.

## UI Layout (Streamlit)

- **Left column (2/3 width):** File uploader (.txt, .xlsx) → "Start Multi-Agent Analysis" button → Document Summary display
- **Right column (1/3 width):** Agent Activity Log (reverse chronological) → Extracted Anchors (JSON view)
- **State:** `st.session_state.ui_state` dict with `summary`, `logs`, `anchors` keys

## Data Flow

1. User uploads file → content decoded to UTF-8 string
2. User clicks "Start Analysis" → `asyncio.run(orchestrator.run(..., deps=content))`
3. Orchestrator calls `get_anchor_letters` → extracts chars → updates `st.session_state`
4. Orchestrator calls `verify_logic` with proposal → confirmation agent spawns, evaluates, returns verdict → logs updated
5. UI renders summary, logs, and anchors from session state

## Dependencies

- `pydantic-ai` — Agent orchestration
- `streamlit` — UI framework
- `pandas` + `openpyxl` — Excel file reading
- `openai` — OpenAI-compatible client (for llama-server)
- `httpx` — HTTP client (pydantic-ai dependency)

## LLM Backend

- Local llama-server at `http://localhost:8080/v1`
- Model name: `llama3`
- Launcher: `./bin/llama-server -m ./models/llama3.gguf --parallel 4 --cont-batching --cache-reuse 512`

## Future Iterations (not in scope)

- Croatian text embeddings finetune
- Vision model for image/document search
- PDF support (structured + unstructured)
- BoQ (Bill of Quantities) parsing
- Edge deployment with split agentic models (3B Ministral, 7B Qwen, 14B Ministral Thinking, 20B GPT OSS)
- Rich prompt-based document editing and parsing
