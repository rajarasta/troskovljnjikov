#!/usr/bin/env bash
set -euo pipefail

# BOQ Matcher - One-click launcher
# Starts: llama-server (LLM) + FastAPI backend + Next.js frontend
# Ctrl-C stops everything.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MAIN_REPO="$(cd "$SCRIPT_DIR/../.." 2>/dev/null && pwd || echo "$SCRIPT_DIR")"

# ── Config ───────────────────────────────────────────────────────────

LLM_PORT=8095
BACKEND_PORT=8000
FRONTEND_PORT=3000

# llama-server binary and model (from main repo)
LLAMA_BIN="${MAIN_REPO}/bin/llama-server"
LLAMA_MODEL="${MAIN_REPO}/models/llama3.gguf"

# ── Colors ───────────────────────────────────────────────────────────

RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
PURPLE='\033[0;35m'
DIM='\033[2m'
RESET='\033[0m'

log() { echo -e "${DIM}[$(date +%H:%M:%S)]${RESET} $1"; }

# ── Cleanup on exit ─────────────────────────────────────────────────

PIDS=()
cleanup() {
    log "${RED}Shutting down...${RESET}"
    for pid in "${PIDS[@]}"; do
        kill "$pid" 2>/dev/null || true
    done
    wait 2>/dev/null
    log "${GREEN}All processes stopped.${RESET}"
}
trap cleanup EXIT INT TERM

# ── 0. Kill stale processes on our ports ─────────────────────────────

kill_port() {
    local port=$1
    if fuser "${port}/tcp" >/dev/null 2>&1; then
        log "${RED}Killing stale process(es) on port ${port}...${RESET}"
        fuser -k "${port}/tcp" >/dev/null 2>&1 || true
        sleep 1
    fi
}

kill_port "$FRONTEND_PORT"
kill_port "$BACKEND_PORT"

# ── 1. Start llama-server (if binary exists) ────────────────────────

if [[ -x "$LLAMA_BIN" && -f "$LLAMA_MODEL" ]]; then
    log "${CYAN}Starting llama-server on port ${LLM_PORT}...${RESET}"
    LD_LIBRARY_PATH="${MAIN_REPO}/bin:${LD_LIBRARY_PATH:-}" \
        "$LLAMA_BIN" \
        -m "$LLAMA_MODEL" \
        -ngl 99 \
        --parallel 4 \
        --cont-batching \
        --cache-reuse 512 \
        --chat-template chatml \
        --port "$LLM_PORT" \
        > /dev/null 2>&1 &
    PIDS+=($!)
    log "${GREEN}llama-server started (PID ${PIDS[-1]})${RESET}"
    sleep 2
else
    log "${RED}llama-server or model not found — skipping LLM server${RESET}"
    log "${DIM}  Expected: ${LLAMA_BIN}${RESET}"
    log "${DIM}  Model:    ${LLAMA_MODEL}${RESET}"
fi

# ── 2. Install/sync backend dependencies ─────────────────────────────

log "${PURPLE}Syncing backend dependencies...${RESET}"
cd "$SCRIPT_DIR/backend"
uv sync --quiet
log "${GREEN}Backend dependencies synced.${RESET}"

# ── 3. Install & build Next.js frontend ─────────────────────────────

log "${CYAN}Installing frontend dependencies...${RESET}"
cd "$SCRIPT_DIR/frontend"
npm install --silent
log "${GREEN}Frontend dependencies installed.${RESET}"

log "${CYAN}Building Next.js frontend...${RESET}"
npm run build
log "${GREEN}Frontend built.${RESET}"

# ── 4. Start FastAPI backend ────────────────────────────────────────

log "${PURPLE}Starting FastAPI backend on port ${BACKEND_PORT}...${RESET}"
cd "$SCRIPT_DIR/backend"
uv run uvicorn app.main:app \
    --host 0.0.0.0 \
    --port "$BACKEND_PORT" \
    --reload \
    &
PIDS+=($!)
log "${GREEN}Backend started (PID ${PIDS[-1]})${RESET}"

# ── 5. Start Next.js frontend (production) ──────────────────────────

log "${CYAN}Starting Next.js frontend on port ${FRONTEND_PORT}...${RESET}"
cd "$SCRIPT_DIR/frontend"
npm run start -- -p "$FRONTEND_PORT" &
PIDS+=($!)
log "${GREEN}Frontend started (PID ${PIDS[-1]})${RESET}"

# ── Ready ────────────────────────────────────────────────────────────

echo ""
log "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
log "${GREEN}  BOQ Matcher is running!${RESET}"
log "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo ""
log "  ${CYAN}Frontend${RESET}:  http://localhost:${FRONTEND_PORT}"
log "  ${PURPLE}Backend${RESET}:   http://localhost:${BACKEND_PORT}"
log "  ${DIM}API docs${RESET}:  http://localhost:${BACKEND_PORT}/docs"
log "  ${DIM}LLM${RESET}:       http://localhost:${LLM_PORT}/v1"
echo ""
log "${DIM}Press Ctrl-C to stop all services.${RESET}"

# Wait for all background processes
wait
