from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from datetime import timezone
from uuid import UUID, uuid4

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .db import create_store
from .run_manager import RunManager
from .schemas import (
    BenchmarkRecord,
    ClusterHealth,
    CreateBenchmarkRequest,
    CreateRunRequest,
    NodeHealth,
    RunEvent,
    RunSummary,
)


store, db_ready, db_backend = create_store()
manager = RunManager(store)


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield
    store.close()


app = FastAPI(title="sglang-cluster-ui backend", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def to_summary(row: dict) -> RunSummary:
    return RunSummary(
        run_id=str(row["run_id"]),
        action=row["action"],
        status=row["status"],
        created_at=row["created_at"].astimezone(timezone.utc),
        updated_at=row["updated_at"].astimezone(timezone.utc),
        exit_code=row.get("exit_code"),
    )


@app.get("/health")
async def health() -> dict:
    return {"ok": True, "db_ready": db_ready, "db_backend": db_backend}


@app.post("/runs", response_model=RunSummary)
async def create_run(payload: CreateRunRequest) -> RunSummary:
    run_id = uuid4()
    await manager.start(run_id, payload.action, payload.extra_args)
    row = store.get_run(run_id)
    if not row:
        raise HTTPException(status_code=500, detail="Run creation failed")
    return to_summary(row)


@app.get("/runs", response_model=list[RunSummary])
async def list_runs(limit: int = 100) -> list[RunSummary]:
    return [to_summary(r) for r in store.list_runs(limit=limit, lookback_days=7)]


@app.get("/runs/{run_id}", response_model=RunSummary)
async def get_run(run_id: UUID) -> RunSummary:
    row = store.get_run(run_id)
    if not row:
        raise HTTPException(status_code=404, detail="Run not found")
    return to_summary(row)


@app.get("/runs/{run_id}/events", response_model=list[RunEvent])
async def list_events(run_id: UUID) -> list[RunEvent]:
    rows = store.list_events(run_id, 500)
    return [
        RunEvent(
            run_id=str(r["run_id"]),
            ts=r["ts"].astimezone(timezone.utc),
            level=r["level"],
            line=r["line"],
        )
        for r in rows
    ]


@app.post("/runs/{run_id}/stop")
async def stop_run(run_id: UUID) -> dict:
    ok = await manager.stop(run_id)
    return {"ok": ok}


@app.websocket("/runs/{run_id}/ws")
async def ws_logs(websocket: WebSocket, run_id: UUID):
    await websocket.accept()
    q = manager.subscribe(run_id)
    # Push recent events first so refresh shows context.
    for event in store.list_events(run_id, 200):
        await websocket.send_text(event["line"])
    try:
        while True:
            line = await asyncio.wait_for(q.get(), timeout=30)
            await websocket.send_text(line)
    except asyncio.TimeoutError:
        await websocket.send_text("[idle]")
    except WebSocketDisconnect:
        pass
    finally:
        manager.unsubscribe(run_id, q)


async def run_remote_check(node: str, iface: str) -> NodeHealth:
    probe = (
        "set -e;"
        f"ip addr show {iface} >/dev/null 2>&1;"
        f"ip addr show {iface} | awk '/inet /{{print $2}}' | head -1;"
        "ps aux | grep -E 'sglang|python.*launch_server' | grep -v grep >/dev/null 2>&1 && echo __RUNNING__ || echo __NOT_RUNNING__"
    )
    proc = await asyncio.create_subprocess_exec(
        "ssh",
        "-o",
        "ConnectTimeout=5",
        node,
        probe,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    out, err = await proc.communicate()
    if proc.returncode != 0:
        detail = err.decode(errors="replace").strip() or "unreachable or command failed"
        return NodeHealth(
            node=node,
            reachable=False,
            iface=iface,
            iface_has_ip=False,
            sglang_running=False,
            detail=detail,
        )

    text = out.decode(errors="replace").strip()
    lines = [ln for ln in text.splitlines() if ln.strip()]
    ip_line = ""
    running = False
    for line in lines:
        if line == "__RUNNING__":
            running = True
        elif line == "__NOT_RUNNING__":
            running = False
        elif "/" in line:
            ip_line = line
    return NodeHealth(
        node=node,
        reachable=True,
        iface=iface,
        iface_has_ip=bool(ip_line),
        sglang_running=running,
        detail=f"iface_ip={ip_line or 'none'}",
    )


@app.get("/cluster/health", response_model=ClusterHealth)
async def cluster_health() -> ClusterHealth:
    master, worker = await asyncio.gather(
        run_remote_check(settings.master_node, settings.cx7_iface),
        run_remote_check(settings.worker_node, settings.cx7_iface),
    )
    return ClusterHealth(master=master, worker=worker)


@app.post("/benchmarks", response_model=BenchmarkRecord)
async def create_benchmark(payload: CreateBenchmarkRequest) -> BenchmarkRecord:
    benchmark_id = uuid4()
    store.insert_benchmark(
        benchmark_id=benchmark_id,
        cluster_id=payload.cluster_id,
        model=payload.model,
        qps=payload.qps,
        p50_ms=payload.p50_ms,
        p95_ms=payload.p95_ms,
        p99_ms=payload.p99_ms,
        tokens_per_sec=payload.tokens_per_sec,
        note=payload.note,
    )
    rows = store.list_benchmarks(payload.cluster_id, limit=1)
    if not rows:
        raise HTTPException(status_code=500, detail="Failed to save benchmark")
    row = rows[0]
    return BenchmarkRecord(
        benchmark_id=str(row["benchmark_id"]),
        cluster_id=row["cluster_id"],
        ts=row["ts"].astimezone(timezone.utc),
        model=row["model"],
        qps=row["qps"],
        p50_ms=row["p50_ms"],
        p95_ms=row["p95_ms"],
        p99_ms=row["p99_ms"],
        tokens_per_sec=row["tokens_per_sec"],
        note=row["note"] or "",
    )


@app.get("/benchmarks", response_model=list[BenchmarkRecord])
async def list_benchmarks(cluster_id: str = "default", limit: int = 50) -> list[BenchmarkRecord]:
    rows = store.list_benchmarks(cluster_id=cluster_id, limit=limit)
    return [
        BenchmarkRecord(
            benchmark_id=str(r["benchmark_id"]),
            cluster_id=r["cluster_id"],
            ts=r["ts"].astimezone(timezone.utc),
            model=r["model"],
            qps=r["qps"],
            p50_ms=r["p50_ms"],
            p95_ms=r["p95_ms"],
            p99_ms=r["p99_ms"],
            tokens_per_sec=r["tokens_per_sec"],
            note=r["note"] or "",
        )
        for r in rows
    ]


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host=settings.api_host, port=settings.api_port, reload=False)
