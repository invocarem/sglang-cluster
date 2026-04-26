#!/bin/bash
# sglang-cluster/setup.sh - Main deployment script

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/config.sh"

echo "=== SGLang Cluster Deployment ==="
echo "Master node: $MASTER_NODE"
echo "Worker node: $WORKER_NODE"

# Check SSH connection
check_ssh() {
    echo "Testing SSH connection to $1..."
    if ssh -o ConnectTimeout=5 $1 "echo 'OK'" 2>/dev/null | grep -q "OK"; then
        echo "✓ SSH connection successful"
        return 0
    else
        echo "✗ Cannot connect to $1"
        return 1
    fi
}

# Sync virtual environment
sync_venv() {
    echo "Syncing virtual environment to $1..."
    rsync -avz --delete --progress \
        --exclude='__pycache__' \
        --exclude='*.pyc' \
        --exclude='lib/python3.12/site-packages/*.dist-info/RECORD' \
        ~/.sglang/ $1:~/.sglang/
    echo "✓ Virtual environment synced"
}

# Sync source code
sync_source() {
    echo "Syncing source code to $1..."
    rsync -avz --delete --progress \
        --exclude='__pycache__' \
        --exclude='*.pyc' \
        --exclude='*.o' \
        --exclude='*.so' \
        --exclude='build' \
        --exclude='.git' \
        ~/code/sglang/ $1:~/code/sglang/
    echo "✓ Source code synced"
}

# Setup node-specific config
setup_node_config() {
    echo "Setting up configuration on $1..."
    ssh $1 "mkdir -p ~/sglang-cluster"
    scp "$SCRIPT_DIR/config.sh" "$1:~/sglang-cluster/"
    scp "$SCRIPT_DIR/cx7_optimize.sh" "$1:~/sglang-cluster/"
    scp "$SCRIPT_DIR/run_server.sh" "$1:~/sglang-cluster/"
    
    ssh $1 "chmod +x ~/sglang-cluster/*.sh"
    echo "✓ Node configuration complete"
}

# Main deployment
deploy_to_worker() {
    echo "=== Deploying to worker: $WORKER_NODE ==="
    
    check_ssh $WORKER_NODE || exit 1
    
    # Create directories
    ssh $WORKER_NODE "mkdir -p ~/code/sglang ~/.sglang"
    
    # Sync everything
    sync_venv $WORKER_NODE
    sync_source $WORKER_NODE
    setup_node_config $WORKER_NODE
    
    echo "✓ Deployment complete!"
}

# Optimize CX7 on both nodes
optimize_cluster() {
    echo "=== Optimizing CX7 network on cluster ==="
    
    echo "Optimizing master node..."
    sudo bash "$SCRIPT_DIR/cx7_optimize.sh"
    
    echo "Optimizing worker node..."
    ssh $WORKER_NODE "sudo bash ~/sglang-cluster/cx7_optimize.sh"
    
    echo "✓ CX7 optimization complete"
}

# Launch distributed server
launch_cluster() {
    echo "=== Launching distributed SGLang ==="
    
    # Get master IP
    MASTER_IP=$(ssh $MASTER_NODE "hostname -I | awk '{print \$1}'")
    
    echo "Starting master on $MASTER_NODE ($MASTER_IP)..."
    ssh $MASTER_NODE "cd ~/sglang-cluster && \
        export MASTER_ADDR=$MASTER_IP && \
        bash run_server.sh master" &
    
    sleep 5
    
    echo "Starting worker on $WORKER_NODE..."
    ssh $WORKER_NODE "cd ~/sglang-cluster && \
        export MASTER_ADDR=$MASTER_IP && \
        bash run_server.sh worker" &
    
    echo "Cluster launching... Check logs with: tail -f ~/sglang-cluster/server.log"
}

# Show cluster status
show_status() {
    echo "=== Cluster Status ==="
    echo "Master:"
    ssh $MASTER_NODE "ps aux | grep sglang | grep -v grep || echo 'Not running'"
    echo ""
    echo "Worker:"
    ssh $WORKER_NODE "ps aux | grep sglang | grep -v grep || echo 'Not running'"
}

# Command line interface
case "${1:-}" in
    deploy)
        deploy_to_worker
        ;;
    optimize)
        optimize_cluster
        ;;
    launch)
        deploy_to_worker
        optimize_cluster
        launch_cluster
        ;;
    status)
        show_status
        ;;
    stop)
        ssh $MASTER_NODE "pkill -f sglang" || true
        ssh $WORKER_NODE "pkill -f sglang" || true
        echo "Cluster stopped"
        ;;
    *)
        echo "Usage: $0 {deploy|optimize|launch|status|stop}"
        echo "  deploy   - Sync builds to worker node"
        echo "  optimize - Apply CX7 network optimizations"
        echo "  launch   - Full deploy, optimize, and start cluster"
        echo "  status   - Show running servers"
        echo "  stop     - Stop all servers"
        ;;
esac

