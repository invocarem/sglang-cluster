# sglang-cluster

Utilities for running SGLang cluster workflows, plus a small web UI:

- `backend/`: FastAPI service
- `frontend/`: Vite + React UI
- Python CLI in `backend/app/`: cluster and server control

## Cluster Usage

```bash
# On master node (example: spark1)
cd ~/sglang-cluster

# Update node/model/network settings first
vi config.sh

# One-command deployment + launch
python3 -m backend.app.cluster_cli launch
```

Step-by-step:

```bash
cd ~/sglang-cluster
python3 -m backend.app.cluster_cli deploy    # Sync files to worker
python3 -m backend.app.cluster_cli optimize  # Apply CX7 optimization
python3 -m backend.app.cluster_cli launch    # Start distributed server
python3 -m backend.app.cluster_cli status    # Check status
python3 -m backend.app.cluster_cli stop      # Stop everything
```

## Web UI Quick Start

### 1) Backend setup (first time only)

```bash
cd ~/sglang-cluster/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2) Frontend setup (first time only)

```bash
cd ~/sglang-cluster/frontend
npm install
```

### 3) Daily development

```bash
cd ~/sglang-cluster/frontend
npm run dev
```

`npm run dev` now:

- starts backend first if needed,
- waits for backend health (`http://127.0.0.1:18080/health`),
- then starts the frontend dev server.

Optional commands:

- `npm run dev:frontend` -> frontend only
- `npm run dev:full` -> same as `npm run dev`
