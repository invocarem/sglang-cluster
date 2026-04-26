from __future__ import annotations

import asyncio
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from .config import settings


class RunManager:
    def __init__(self, store: Any) -> None:
        self.store = store
        self._tasks: dict[UUID, asyncio.Task] = {}
        self._procs: dict[UUID, asyncio.subprocess.Process] = {}
        self._subscribers: dict[UUID, list[asyncio.Queue[str]]] = defaultdict(list)

    def build_command(self, action: str, extra_args: list[str]) -> list[str]:
        scripts_dir = Path(settings.scripts_dir)
        if action == "deploy":
            return [sys.executable, "-m", "backend.app.cluster_cli", "deploy", *extra_args]
        if action == "status":
            return [sys.executable, "-m", "backend.app.cluster_cli", "status", *extra_args]
        if action == "stop":
            return [sys.executable, "-m", "backend.app.cluster_cli", "stop", *extra_args]
        if action == "start_master":
            return [sys.executable, "-m", "backend.app.server_cli", "master", *extra_args]
        if action == "start_worker":
            return [sys.executable, "-m", "backend.app.server_cli", "worker", *extra_args]
        if action == "start_solo":
            return [sys.executable, "-m", "backend.app.server_cli", "start_solo", *extra_args]
        if action == "benchmark":
            return ["bash", str(scripts_dir / "benchmark_sglang.sh"), *extra_args]
        raise ValueError(f"Unsupported action: {action}")

    @staticmethod
    def _extract_metric(text: str, patterns: list[str]) -> float | None:
        for pattern in patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                try:
                    return float(match.group(1))
                except ValueError:
                    continue
        return None

    def _maybe_store_benchmark(self, run_id: UUID, output_lines: list[str]) -> None:
        text = "\n".join(output_lines)
        qps = self._extract_metric(text, [r"\bqps\b\s*[:=]\s*([0-9.]+)", r"throughput.*?([0-9.]+)\s*req/s"])
        p50 = self._extract_metric(text, [r"\bp50\b\s*[:=]\s*([0-9.]+)", r"p50.*?([0-9.]+)\s*ms"])
        p95 = self._extract_metric(text, [r"\bp95\b\s*[:=]\s*([0-9.]+)", r"p95.*?([0-9.]+)\s*ms"])
        p99 = self._extract_metric(text, [r"\bp99\b\s*[:=]\s*([0-9.]+)", r"p99.*?([0-9.]+)\s*ms"])
        tok_s = self._extract_metric(
            text,
            [r"(?:tokens_per_sec|tok/s|tokens/s)\s*[:=]\s*([0-9.]+)", r"output token throughput.*?([0-9.]+)"],
        )

        if qps is None and p50 is None and p95 is None and p99 is None and tok_s is None:
            return

        self.store.insert_benchmark(
            benchmark_id=uuid4(),
            cluster_id="default",
            model="from-benchmark-action",
            qps=qps or 0.0,
            p50_ms=p50 or 0.0,
            p95_ms=p95 or 0.0,
            p99_ms=p99 or 0.0,
            tokens_per_sec=tok_s or 0.0,
            note=f"run_id={run_id}",
        )

    def subscribe(self, run_id: UUID) -> asyncio.Queue[str]:
        q: asyncio.Queue[str] = asyncio.Queue()
        self._subscribers[run_id].append(q)
        return q

    def unsubscribe(self, run_id: UUID, q: asyncio.Queue[str]) -> None:
        if run_id in self._subscribers and q in self._subscribers[run_id]:
            self._subscribers[run_id].remove(q)

    async def _publish(self, run_id: UUID, line: str) -> None:
        for q in self._subscribers[run_id]:
            await q.put(line)

    async def start(self, run_id: UUID, action: str, extra_args: list[str]) -> None:
        self.store.create_run(run_id, action=action, status="pending")
        task = asyncio.create_task(self._run(run_id, action, extra_args))
        self._tasks[run_id] = task

    async def _run(self, run_id: UUID, action: str, extra_args: list[str]) -> None:
        cmd = self.build_command(action, extra_args)
        self.store.update_run(run_id, status="running")
        self.store.append_event(run_id, "info", f"$ {' '.join(cmd)}")
        await self._publish(run_id, f"$ {' '.join(cmd)}")
        output_lines: list[str] = []
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=settings.scripts_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
            self._procs[run_id] = proc
            assert proc.stdout is not None
            async for raw in proc.stdout:
                line = raw.decode(errors="replace").rstrip()
                output_lines.append(line)
                self.store.append_event(run_id, "info", line)
                await self._publish(run_id, line)

            rc = await proc.wait()
            if action == "benchmark" and rc == 0:
                self._maybe_store_benchmark(run_id, output_lines)
            status = "success" if rc == 0 else "failed"
            self.store.update_run(run_id, status=status, exit_code=rc)
            self.store.append_event(run_id, "info", f"[done] exit_code={rc}")
            await self._publish(run_id, f"[done] exit_code={rc}")
        except asyncio.CancelledError:
            self.store.update_run(run_id, status="stopped", exit_code=None)
            self.store.append_event(run_id, "error", "[cancelled]")
            await self._publish(run_id, "[cancelled]")
            raise
        except Exception as exc:  # noqa: BLE001
            self.store.update_run(run_id, status="failed", exit_code=-1)
            msg = f"[error] {exc}"
            self.store.append_event(run_id, "error", msg)
            await self._publish(run_id, msg)
        finally:
            self._tasks.pop(run_id, None)
            self._procs.pop(run_id, None)

    async def stop(self, run_id: UUID) -> bool:
        proc = self._procs.get(run_id)
        if proc is not None and proc.returncode is None:
            proc.terminate()
            self.store.append_event(run_id, "info", "[terminate sent]")
            return True
        task = self._tasks.get(run_id)
        if task and not task.done():
            task.cancel()
            return True
        return False
