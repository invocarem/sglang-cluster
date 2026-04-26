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

### Web UI scaffold

Backend:

```
cd ~/sglang-cluster/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m app.main
```

Frontend:

```
cd ~/sglang-cluster/frontend
npm install
npm run dev
```
