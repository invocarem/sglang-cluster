from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


RunAction = Literal["deploy", "start_master", "start_worker", "start_solo", "status", "stop", "benchmark"]
RunStatus = Literal["pending", "running", "success", "failed", "stopped"]


class CreateRunRequest(BaseModel):
    action: RunAction
    extra_args: list[str] = Field(default_factory=list)


class RunSummary(BaseModel):
    run_id: str
    action: RunAction
    status: RunStatus
    created_at: datetime
    updated_at: datetime
    exit_code: Optional[int] = None


class RunEvent(BaseModel):
    run_id: str
    ts: datetime
    level: Literal["info", "error"]
    line: str


class CreateBenchmarkRequest(BaseModel):
    cluster_id: str = "default"
    model: str
    qps: float
    p50_ms: float
    p95_ms: float
    p99_ms: float
    tokens_per_sec: float
    note: str = ""


class BenchmarkRecord(BaseModel):
    benchmark_id: str
    cluster_id: str
    ts: datetime
    model: str
    qps: float
    p50_ms: float
    p95_ms: float
    p99_ms: float
    tokens_per_sec: float
    note: str


class NodeHealth(BaseModel):
    node: str
    reachable: bool
    iface: str
    iface_has_ip: bool
    sglang_running: bool
    detail: str


class ClusterHealth(BaseModel):
    master: NodeHealth
    worker: NodeHealth
