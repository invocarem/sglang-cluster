#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRONTEND_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
ROOT_DIR="$(cd "$FRONTEND_DIR/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
BACKEND_HEALTH_URL="${BACKEND_HEALTH_URL:-http://127.0.0.1:18080/health}"
backend_started_by_script=0
backend_pid=""

pick_python() {
  if [ -x "$BACKEND_DIR/.venv/bin/python" ]; then
    echo "$BACKEND_DIR/.venv/bin/python"
    return
  fi
  if command -v python3 >/dev/null 2>&1; then
    command -v python3
    return
  fi
  echo "ERROR: python3 not found and backend .venv is missing." >&2
  exit 1
}

is_backend_healthy() {
  curl -fsS "$BACKEND_HEALTH_URL" >/dev/null 2>&1
}

cleanup() {
  if [ "$backend_started_by_script" -eq 1 ] && [ -n "$backend_pid" ]; then
    echo "Stopping backend (pid $backend_pid)..."
    kill "$backend_pid" >/dev/null 2>&1 || true
  fi
}

trap cleanup EXIT INT TERM

if is_backend_healthy; then
  echo "Backend is already running at $BACKEND_HEALTH_URL"
else
  PYTHON_BIN="$(pick_python)"
  echo "Starting backend with $PYTHON_BIN..."
  (
    cd "$BACKEND_DIR"
    exec "$PYTHON_BIN" -m app.main
  ) &
  backend_pid="$!"
  backend_started_by_script=1

  echo "Waiting for backend to become healthy..."
  for _ in {1..30}; do
    if is_backend_healthy; then
      echo "Backend is healthy."
      break
    fi
    sleep 1
  done

  if ! is_backend_healthy; then
    echo "ERROR: Backend did not become healthy within 30s." >&2
    exit 1
  fi
fi

echo "Starting frontend dev server..."
cd "$FRONTEND_DIR"
npm run dev:frontend
