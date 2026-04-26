#!/bin/bash
# One-command setup for both nodes

cd ~/sglang-cluster

# Step 1: Edit configuration
echo "Please edit config.sh with your node hostnames:"
echo "  MASTER_NODE=\"your_master_hostname\""
echo "  WORKER_NODE=\"your_worker_hostname\""
read -p "Press Enter after editing config.sh..."

# Step 2: Deploy and launch
./setup.sh launch

# Step 3: Check status
sleep 10
./setup.sh status

echo ""
echo "Server running at: http://$(hostname -I | awk '{print $1}'):30000"
echo "Test with: curl http://localhost:30000/v1/models"

