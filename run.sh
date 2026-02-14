#!/bin/bash
# Troskovljnjikov Dev Launcher
# Starts llama-server, FastAPI backend, and React frontend.
# Cleans up all processes on exit.

set -e
DIR="$(cd "$(dirname "$0")" && pwd)"

cleanup() {
    echo "Shutting down..."
    kill $FRONTEND_PID 2>/dev/null || true
    kill $BACKEND_PID 2>/dev/null || true
    kill $LLAMA_PID 2>/dev/null || true
    echo "All processes stopped."
}
trap cleanup EXIT INT TERM

# 1. Start llama-server
echo "Starting llama-server..."
LD_LIBRARY_PATH="$DIR/bin:$LD_LIBRARY_PATH" "$DIR/bin/llama-server" \
    -m "$DIR/models/llama3.gguf" -ngl 99 --parallel 4 \
    --cont-batching --cache-reuse 512 --chat-template chatml &
LLAMA_PID=$!
sleep 3

# 2. Start FastAPI backend
echo "Starting backend on :8081..."
cd "$DIR/backend" && uv run uvicorn src.main:app --reload --port 8081 --host 127.0.0.1 &
BACKEND_PID=$!
cd "$DIR"
sleep 2

# 3. Start React frontend (Vite dev server)
echo "Starting frontend on :5173..."
cd "$DIR/frontend" && npm run dev &
FRONTEND_PID=$!
cd "$DIR"

echo ""
echo "Ready! Open http://localhost:5173"
echo "Press Ctrl+C to stop all services."
echo ""

wait
