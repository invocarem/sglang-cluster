#!/bin/bash
# Run SGLang benchmark command and emit parsable metrics.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/config.sh"

if [ -f ~/.sglang/bin/activate ]; then
  source ~/.sglang/bin/activate
fi

if [ -z "${SGLANG_BENCHMARK_CMD:-}" ]; then
  echo "ERROR: SGLANG_BENCHMARK_CMD is not set in config.sh"
  echo "Set it to your real SGLang benchmark command, for example:"
  echo "  export SGLANG_BENCHMARK_CMD='python -m sglang.bench_serving --backend sglang-oai --base-url http://127.0.0.1:${SERVER_PORT} --model qwen --num-prompts 200'"
  exit 2
fi

echo "=== Running SGLang benchmark ==="
echo "Command: $SGLANG_BENCHMARK_CMD"

# Run exactly the user's benchmark command and stream output.
bash -lc "$SGLANG_BENCHMARK_CMD"
