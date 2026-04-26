#!/bin/bash
# Test CX7 RoCE connectivity between nodes

source ~/sglang-cluster/config.sh

echo "=== Testing CX7 RoCE connectivity ==="
echo "Master: $MASTER_NODE"
echo "Worker: $WORKER_NODE"
echo "Interface: $CX7_IFACE"

# Get IP addresses
MASTER_IP=$(ssh $MASTER_NODE "ip addr show $CX7_IFACE | grep 'inet ' | awk '{print \$2}' | cut -d/ -f1")
WORKER_IP=$(ssh $WORKER_NODE "ip addr show $CX7_IFACE | grep 'inet ' | awk '{print \$2}' | cut -d/ -f1")

echo "Master IP on $CX7_IFACE: $MASTER_IP"
echo "Worker IP on $CX7_IFACE: $WORKER_IP"

# Test ping
echo ""
echo "Testing ping via $CX7_IFACE..."
ping -c 3 -I $CX7_IFACE $WORKER_IP

# Test RDMA if ib_write_bw available
if command -v ib_write_bw &> /dev/null; then
    echo ""
    echo "Testing RDMA bandwidth..."
    echo "  (Run these manually for bandwidth test)"
    echo "  On worker: ib_write_bw -d $ROCE_DEVICE -F"
    echo "  On master: ib_write_bw $WORKER_IP -d $ROCE_DEVICE -F"
fi

echo ""
echo "✓ CX7 connectivity test complete"

