# Backend (FastAPI + Cassandra)

## Quick start

1. Create env and install deps:
   - `python3 -m venv .venv`
   - `source .venv/bin/activate`
   - `pip install -r requirements.txt`
2. Set env vars if needed:
   - `SGLANG_UI_API_PORT=18080`
   - `SGLANG_UI_CASSANDRA_HOSTS=127.0.0.1`
   - `SGLANG_UI_CASSANDRA_PORT=9042`
   - `SGLANG_UI_CASSANDRA_KEYSPACE=sglang_ui`
   - `SGLANG_UI_SCRIPTS_DIR=/home/chenchen/sglang-cluster`
   - `SGLANG_UI_MASTER_NODE=spark1`
   - `SGLANG_UI_WORKER_NODE=spark2`
   - `SGLANG_UI_CX7_IFACE=enp1s0f1np1`
3. Start API:
   - `python -m app.main`

If Cassandra is down/unreachable, the API now starts in an in-memory fallback mode.

`run_server.sh` no longer auto-runs CX7 optimization by default.  
To force optimization during launch: `export SGLANG_RUN_OPTIMIZE_ON_START=1`

## Endpoints

- `GET /health`
- `GET /cluster/health`
- `POST /runs` with JSON like `{"action":"start_solo","extra_args":[]}`
- `GET /runs`
- `GET /runs/{run_id}`
- `GET /runs/{run_id}/events`
- `POST /runs/{run_id}/stop`
- `WS /runs/{run_id}/ws`
- `POST /benchmarks`
- `GET /benchmarks?cluster_id=default&limit=50`

## SGLang benchmark action

The `benchmark` run action executes `benchmark_sglang.sh`, which runs the command in `SGLANG_BENCHMARK_CMD` from `config.sh`.
Set your real benchmark command there first, then trigger the `benchmark` action from UI/API.
