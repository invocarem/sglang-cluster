### usage


```
# On master node (spark1)
cd ~/sglang-cluster

# First, edit config.sh with your node names
vi config.sh  # Set MASTER_NODE and WORKER_NODE

# One-command deployment and launch
./quick_start.sh

# Or step by step:
./setup.sh deploy   # Sync builds to worker
./setup.sh optimize # Optimize CX7 on both nodes  
./setup.sh launch   # Start distributed server
./setup.sh status   # Check status
./setup.sh stop     # Stop everything

```
