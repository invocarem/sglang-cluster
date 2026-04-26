#!/bin/bash
# sglang-cluster/run_server.sh - Launch SGLang server

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/config.sh"

# Activate environment
source ~/.sglang/bin/activate

# Apply CX7 settings
if [ -f "$SCRIPT_DIR/cx7_optimize.sh" ]; then
    source "$SCRIPT_DIR/cx7_optimize.sh"
fi

# Apply NCCL settings
export NCCL_IB_DISABLE=${NCCL_IB_DISABLE:-0}
export NCCL_IB_GID_INDEX=${NCCL_IB_GID_INDEX:-3}
export NCCL_IB_TIMEOUT=${NCCL_IB_TIMEOUT:-22}
export NCCL_IB_RETRY_CNT=${NCCL_IB_RETRY_CNT:-7}
export NCCL_IB_SL=${NCCL_IB_SL:-3}
export NCCL_IB_TC=${NCCL_IB_TC:-160}
export NCCL_IB_QPS_PER_CONNECTION=${NCCL_IB_QPS_PER_CONNECTION:-4}
export NCCL_NET_GDR_LEVEL=${NCCL_NET_GDR_LEVEL:-5}
export NCCL_DEBUG=${NCCL_DEBUG:-WARN}

# Disable torchvision to avoid import errors
export SGLANG_DISABLE_TORCHVISION=1

LOG_FILE="$SCRIPT_DIR/server.log"

case "${1:-}" in
    master)
        echo "Starting master node..." | tee -a $LOG_FILE
        python -m sglang.launch_server \
            --model-path $MODEL_PATH \
            --tp-size $TP_SIZE \
            --host 0.0.0.0 \
            --port $SERVER_PORT \
            --dist-init-addr tcp://$MASTER_ADDR:$MASTER_PORT \
            --nnodes 2 \
            --node-rank 0 \
            --disable-piecewise-cuda-graph \
            2>&1 | tee -a $LOG_FILE
        ;;
    worker)
        echo "Starting worker node..." | tee -a $LOG_FILE
        sleep 10  # Wait for master
        python -m sglang.launch_server \
            --model-path $MODEL_PATH \
            --tp-size $TP_SIZE \
            --host 0.0.0.0 \
            --port $SERVER_PORT \
            --dist-init-addr tcp://$MASTER_ADDR:$MASTER_PORT \
            --nnodes 2 \
            --node-rank 1 \
            2>&1 | tee -a $LOG_FILE
        ;;
    *)
        echo "Usage: $0 {master|worker}"
        exit 1
        ;;
esac

