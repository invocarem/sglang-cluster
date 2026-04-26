#!/bin/bash
# CX7 RoCE optimization for DGX Spark

set -e

# Source config to get interface
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/config.sh"

echo "=== Optimizing CX7 RoCE on $CX7_IFACE ==="

# Check if interface exists
if ! ip link show $CX7_IFACE &>/dev/null; then
    echo "ERROR: Interface $CX7_IFACE not found!"
    echo "Available interfaces:"
    ip link show | grep -E "^[0-9]+:" | awk -F': ' '{print $2}'
    exit 1
fi

# Optimize MTU for RoCE (4095 max for CX7)
echo "Setting MTU to 4096..."
sudo ip link set dev $CX7_IFACE mtu 4096 2>/dev/null || echo "  (requires sudo or already set)"

# Optimize ring buffer sizes
echo "Optimizing ring buffers..."
sudo ethtool -G $CX7_IFACE rx 4096 tx 4096 2>/dev/null || echo "  (could not set ring sizes)"

# Disable flow control for RoCE (recommended for CX7)
echo "Disabling flow control..."
sudo ethtool -A $CX7_IFACE autoneg off rx off tx off 2>/dev/null || echo "  (could not disable flow control)"

# Enable adaptive interrupt moderation for better latency
echo "Setting interrupt moderation..."
sudo ethtool -C $CX7_IFACE adaptive-rx on adaptive-tx on 2>/dev/null || echo "  (could not set interrupt moderation)"

# Show current settings
echo ""
echo "=== Current $CX7_IFACE settings ==="
ip addr show $CX7_IFACE | grep -E "inet |mtu"
echo ""
ethtool $CX7_IFACE | grep -E "Speed|Duplex|auto-negotiation"
echo ""
ethtool -S $CX7_IFACE 2>/dev/null | grep -E "rx_packets|tx_packets|rx_bytes|tx_bytes" | head -4

echo ""
echo "=== CX7 Optimization Complete ==="
echo "Test RDMA connectivity:"
echo "  On master: ib_write_bw -d rocep1s0f1 -F"
echo "  On worker: ib_write_bw <master_ip> -d roceP2p1s0f1 -F"

