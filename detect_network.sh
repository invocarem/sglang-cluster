#!/bin/bash
# Auto-detect active RoCE interfaces

echo "Detecting active RoCE interfaces..."

# Parse ibdev2netdev properly - extract interface names from lines with "Up"
ACTIVE_IFACES=$(ibdev2netdev 2>/dev/null | grep "Up" | awk '{for(i=1;i<=NF;i++) if($i~/^en/ || $i~/^ib/ || $i~/^eth/) print $i}')

if [ -z "$ACTIVE_IFACES" ]; then
    echo "ERROR: No active RoCE interfaces found"
    echo "Full ibdev2netdev output:"
    ibdev2netdev
    exit 1
fi

echo "Found active interfaces: $ACTIVE_IFACES"

# Use the first active interface
PRIMARY_IFACE=$(echo $ACTIVE_IFACES | awk '{print $1}')
echo "Primary interface: $PRIMARY_IFACE"

# Update config.sh - use proper sed syntax
if [ -f ~/sglang-cluster/config.sh ]; then
    # Remove old CX7_IFACE line if exists
    sed -i '/^export CX7_IFACE=/d' ~/sglang-cluster/config.sh
    sed -i '/^export NCCL_SOCKET_IFNAME=/d' ~/sglang-cluster/config.sh
    sed -i '/^export NCCL_IB_IFNAME=/d' ~/sglang-cluster/config.sh
    
    # Add new lines after NCCL settings section
    sed -i "/^# Network interface binding/a export CX7_IFACE=\"$PRIMARY_IFACE\"\nexport NCCL_SOCKET_IFNAME=\$CX7_IFACE\nexport NCCL_IB_IFNAME=\$CX7_IFACE" ~/sglang-cluster/config.sh
    
    echo "✓ Config updated with interface: $PRIMARY_IFACE"
else
    echo "ERROR: config.sh not found at ~/sglang-cluster/config.sh"
    exit 1
fi

# Verify interface exists
if ip link show $PRIMARY_IFACE &>/dev/null; then
    echo ""
    echo "Interface details:"
    ip addr show $PRIMARY_IFACE | grep -E "inet |mtu"
    
    # Get IP address
    IFACE_IP=$(ip addr show $PRIMARY_IFACE | grep 'inet ' | awk '{print $2}' | cut -d/ -f1)
    if [ -n "$IFACE_IP" ]; then
        echo "IP Address: $IFACE_IP"
    else
        echo "WARNING: Interface $PRIMARY_IFACE has no IP address assigned"
        echo "You may need to configure IP on this interface"
    fi
    
    echo ""
    echo "Speed and duplex:"
    sudo ethtool $PRIMARY_IFACE 2>/dev/null | grep -E "Speed|Duplex" || echo "  (run with sudo for more details)"
else
    echo "ERROR: Interface $PRIMARY_IFACE not found!"
    echo "Available interfaces:"
    ip link show | grep -E "^[0-9]+:" | awk -F': ' '{print $2}'
    exit 1
fi

# Test connectivity to worker
WORKER_NODE=$(grep "^export WORKER_NODE=" ~/sglang-cluster/config.sh | cut -d'"' -f2)
if [ -n "$WORKER_NODE" ] && [ -n "$IFACE_IP" ]; then
    echo ""
    echo "Testing ping to $WORKER_NODE..."
    ping -c 2 $WORKER_NODE 2>/dev/null || echo "  (ping failed - check hostname resolution)"
fi

echo ""
echo "=== To use this interface, run: ==="
echo "source ~/sglang-cluster/config.sh"
