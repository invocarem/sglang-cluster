#!/bin/bash
# sglang-cluster/config.sh - Cluster configuration

# Node configuration
export MASTER_NODE="spark1"
export WORKER_NODE="spark2"

# Network configuration
export MASTER_PORT=29500
export SERVER_PORT=30000

# Model configuration
export MODEL_PATH="/home/chenchen/huggingface/Qwen_Qwen3.5-2B"
export TP_SIZE=2

# CX7 network interface configuration
# You have two active ports. For NCCL, we'll use the first active one
# Both ports are RoCE (RDMA over Converged Ethernet)

# NCCL settings for RoCE CX7
export NCCL_IB_DISABLE=0        # Enable IB/RoCE
export NCCL_IB_GID_INDEX=3      # RoCE v2
export NCCL_IB_TIMEOUT=22
export NCCL_IB_RETRY_CNT=7
export NCCL_IB_SL=3
export NCCL_IB_TC=160
export NCCL_IB_QPS_PER_CONNECTION=4
export NCCL_IB_CUDA_SUPPORT=1
export NCCL_NET_GDR_LEVEL=5
export NCCL_NET_GDR_READ=1
export NCCL_P2P_DISABLE=0

# RoCE specific settings
export NCCL_IB_HCA=mlx5,roce     # Use mlx5 drivers
export NCCL_IB_CUDA_SUPPORT=1
export NCCL_PROTO=Simple
export NCCL_ALGO=Ring

# Network interface binding
export CX7_IFACE="enp1s0f1np1"
export NCCL_SOCKET_IFNAME=$CX7_IFACE
export NCCL_IB_IFNAME=$CX7_IFACE

# Debug (set to INFO if you have issues, then WARN for production)
export NCCL_DEBUG=WARN

# Performance settings
export CUDA_GRAPHS=1
export SGLANG_DISABLE_TORCHVISION=1

# Set MTU to match your active ports (4096)
# You can set this but note it requires root
# ip link set dev $CX7_IFACE mtu 4096

# Benchmark command (required by benchmark_sglang.sh).
# Set this to your real SGLang benchmark command.
# Example:
# export SGLANG_BENCHMARK_CMD="python -m sglang.bench_serving --backend sglang-oai --base-url http://127.0.0.1:${SERVER_PORT} --model qwen --num-prompts 200"
# export SGLANG_BENCHMARK_CMD="python -m sglang.bench_one_batch --model-path ${MODEL_PATH}"

export SGLANG_BENCHMARK_CMD="python -m sglang.bench_serving --backend sglang-oai --base-url http://127.0.0.1:${SERVER_PORT} --model qwen --num-prompts 200"

