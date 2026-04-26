#!/bin/bash
# Compatibility wrapper: delegate server launch to Python backend CLI.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PYTHONPATH="$SCRIPT_DIR:${PYTHONPATH:-}"

PYTHON_BIN="$HOME/.sglang/bin/python"
if [ ! -x "$PYTHON_BIN" ]; then
    PYTHON_BIN="$(command -v python3 || true)"
fi
if [ -z "$PYTHON_BIN" ]; then
    echo "ERROR: python3 not found"
    exit 1
fi

exec "$PYTHON_BIN" -m backend.app.server_cli "$@"

