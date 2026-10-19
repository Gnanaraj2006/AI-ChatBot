#!/usr/bin/env bash
set -e

echo "===================================================="
echo "    Starting StudySphere AI Container Service"
echo "===================================================="

# Ensure data directories exist
mkdir -p /app/data/uploads /app/data/chroma_db

# Check environment variables
PORT=${PORT:-8000}
HOST=${HOST:-0.0.0.0}
WORKERS=${WEB_CONCURRENCY:-2}

echo "Binding to $HOST:$PORT with $WORKERS worker processes"

exec python -m uvicorn app.main:app --host "$HOST" --port "$PORT" --workers "$WORKERS"
