#!/bin/bash
# sglang-cluster/config.sh - Cluster configuration

# Node configuration (update these!)
export MASTER_NODE="spark1"      # Your master node hostname
export WORKER_NODE="spark2"       # Your worker node hostname

# Network configuration
export MASTER_PORT=29500
export SERVER_PORT=30000

# Model configuration
export MODEL_PATH="/home/chenchen/huggingface/Qwen_Qwen3.5-2B"
export TP_SIZE=2  # Tensor parallelism across both nodes

# CX7 network settings
#export CX7_IFACE="ib0"  # InfiniBand interface, or eth0 for RoCE


# Head: often uses this host’s cluster NIC (example — replace with yours).
NCCL_SOCKET_IFNAME=enp1s0f1np1
GLOO_SOCKET_IFNAME=enp1s0f1np1

# Rendezvous: usually head’s IP + same port as SGLang --dist-init-addr.
export MASTER_ADDR=192.168.100.11
export MASTER_PORT=50000
export DIST_INIT_ADDR=192.168.100.11:50000

export NNODES=2
export NODE_RANK=0

export NCCL_IB_HCA=rocep1s0f1


export CUDA_VISIBLE_DEVICES=0
export NCCL_DEBUG=INFO

export NCCL_IB_DISABLE=0
export NCCL_IB_GID_INDEX=3
export NCCL_IB_TIMEOUT=22
export NCCL_IB_RETRY_CNT=7

export WORLD_SIZE=2
export MASTER_ADDR=192.168.100.11


# Performance settings
export CUDA_GRAPHS=1
#export SGLANG_DISABLE_TORCHVISION=1  # Skip torchvision import
