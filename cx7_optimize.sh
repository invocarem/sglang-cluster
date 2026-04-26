#!/bin/bash
# sglang-cluster/cx7_optimize.sh - CX7 network optimizations for DGX Spark

set -e

echo "Applying CX7 InfiniBand/RoCE optimizations..."

# Detect network interface
if [ -e /sys/class/infiniband/mlx5_0 ]; then
    CX7_IFACE="ib0"
    echo "Detected InfiniBand: $CX7_IFACE"
elif [ -e /sys/class/net/eth0 ]; then
    CX7_IFACE="eth0"
    echo "Detected Ethernet: $CX7_IFACE (assuming RoCE)"
else
    echo "Warning: No CX7 interface detected"
    CX7_IFACE=""
fi

# Optimize CX7 adapter settings
set_cx7_params() {
    local iface=$1
    
    # Increase MTU for better throughput
    ip link set dev $iface mtu 9000 2>/dev/null || echo "Could not set MTU"
    
    # Enable adaptive tx/rx rings
    ethtool -G $iface rx 4096 tx 4096 2>/dev/null || echo "Could not set ring sizes"
    
    # Disable flow control for better performance
    ethtool -A $iface autoneg off rx off tx off 2>/dev/null || echo "Could not disable flow control"
    
    # Use busy polling for lower latency
    sysctl -w net.core.busy_poll=50 >/dev/null 2>&1 || true
    sysctl -w net.core.busy_read=50 >/dev/null 2>&1 || true
    
    echo "✓ Optimized $iface"
}

# Set kernel parameters for RDMA/NCCL
set_kernel_params() {
    # Increase memory for RDMA
    sysctl -w vm.max_map_count=1048576 >/dev/null 2>&1
    
    # Optimize network buffers
    sysctl -w net.core.rmem_max=134217728 >/dev/null 2>&1
    sysctl -w net.core.wmem_max=134217728 >/dev/null 2>&1
    sysctl -w net.ipv4.tcp_rmem='4096 87380 134217728' >/dev/null 2>&1
    sysctl -w net.ipv4.tcp_wmem='4096 65536 134217728' >/dev/null 2>&1
    
    echo "✓ Kernel parameters optimized"
}

# Test network bandwidth
test_bandwidth() {
    echo "Testing network bandwidth (requires ib_write_bw or iperf3)..."
    if command -v ib_write_bw &> /dev/null; then
        echo "Run on master: ib_write_bw -d mlx5_0 -F"
        echo "Run on worker: ib_write_bw <master_ip> -d mlx5_0 -F"
    elif command -v iperf3 &> /dev/null; then
        echo "Run on master: iperf3 -s"
        echo "Run on worker: iperf3 -c <master_ip>"
    else
        echo "Install perftest or iperf3 for bandwidth testing"
    fi
}

if [ -n "$CX7_IFACE" ]; then
    set_cx7_params $CX7_IFACE
fi
set_kernel_params

echo "=== CX7 Optimization Complete ==="
echo "Interface: ${CX7_IFACE:-none}"
echo ""
echo "Apply NCCL settings before running SGLang:"
echo "  source ~/sglang-cluster/config.sh"
