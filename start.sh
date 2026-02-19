#!/usr/bin/env bash
# Start both backend and frontend in parallel.
# Usage: ./start.sh

trap 'kill 0' EXIT

cd "$(dirname "$0")"

# Backend
(cd backend && python -m uvicorn app.main:app --reload --port 8000) &

# Frontend
(cd frontend && npm run dev) &

wait
