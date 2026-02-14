#!/bin/bash
# Agentic Document Editor Launcher
# Starts llama-server in background, then launches Streamlit UI.
# Cleans up llama-server on exit.

set -e

# 1. Start the LLM Server in background
echo "Starting llama-server..."
./bin/llama-server -m ./models/llama3.gguf --parallel 4 --cont-batching --cache-reuse 512 &
SERVER_PID=$!

# Give the server a moment to start
sleep 3

# 2. Run the UI (uv will install everything on first run)
echo "Launching UI..."
uv run streamlit run main.py

# 3. Cleanup on exit
kill $SERVER_PID 2>/dev/null || true
echo "Shut down llama-server."
