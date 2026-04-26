from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from cassandra.cluster import Cluster

from .config import settings


class CassandraStore:
    def __init__(self) -> None:
        self.cluster = Cluster(
            contact_points=[h.strip() for h in settings.cassandra_hosts.split(",") if h.strip()],
            port=settings.cassandra_port,
        )
        self.session = self.cluster.connect()
        self._bootstrap()

    def _bootstrap(self) -> None:
        keyspace = settings.cassandra_keyspace
        self.session.execute(
            f"""
            CREATE KEYSPACE IF NOT EXISTS {keyspace}
            WITH replication = {{'class': 'SimpleStrategy', 'replication_factor': 1}}
            """
        )
        self.session.set_keyspace(keyspace)
        self.session.execute(
            """
            CREATE TABLE IF NOT EXISTS runs (
                run_id uuid PRIMARY KEY,
                action text,
                status text,
                created_at timestamp,
                updated_at timestamp,
                exit_code int
            )
            """
        )
        self.session.execute(
            """
            CREATE TABLE IF NOT EXISTS runs_by_day (
                day text,
                created_at timestamp,
                run_id uuid,
                action text,
                status text,
                updated_at timestamp,
                exit_code int,
                PRIMARY KEY ((day), created_at, run_id)
            ) WITH CLUSTERING ORDER BY (created_at DESC, run_id ASC)
            """
        )
        self.session.execute(
            """
            CREATE TABLE IF NOT EXISTS run_events (
                run_id uuid,
                ts timeuuid,
                level text,
                line text,
                PRIMARY KEY ((run_id), ts)
            ) WITH CLUSTERING ORDER BY (ts ASC)
            """
        )
        self.session.execute(
            """
            CREATE TABLE IF NOT EXISTS benchmarks_by_cluster (
                cluster_id text,
                ts timeuuid,
                benchmark_id uuid,
                model text,
                qps double,
                p50_ms double,
                p95_ms double,
                p99_ms double,
                tokens_per_sec double,
                note text,
                PRIMARY KEY ((cluster_id), ts, benchmark_id)
            ) WITH CLUSTERING ORDER BY (ts DESC, benchmark_id ASC)
            """
        )

    def create_run(self, run_id: UUID, action: str, status: str) -> None:
        now = datetime.now(timezone.utc)
        day = now.strftime("%Y-%m-%d")
        self.session.execute(
            """
            INSERT INTO runs (run_id, action, status, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (run_id, action, status, now, now),
        )
        self.session.execute(
            """
            INSERT INTO runs_by_day (day, created_at, run_id, action, status, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (day, now, run_id, action, status, now),
        )

    def update_run(self, run_id: UUID, status: str, exit_code: int | None = None) -> None:
        now = datetime.now(timezone.utc)
        self.session.execute(
            """
            UPDATE runs SET status=%s, updated_at=%s, exit_code=%s WHERE run_id=%s
            """,
            (status, now, exit_code, run_id),
        )
        row = self.get_run(run_id)
        if row:
            day = row["created_at"].astimezone(timezone.utc).strftime("%Y-%m-%d")
            self.session.execute(
                """
                UPDATE runs_by_day SET status=%s, updated_at=%s, exit_code=%s
                WHERE day=%s AND created_at=%s AND run_id=%s
                """,
                (status, now, exit_code, day, row["created_at"], run_id),
            )

    def append_event(self, run_id: UUID, level: str, line: str) -> None:
        self.session.execute(
            """
            INSERT INTO run_events (run_id, ts, level, line)
            VALUES (%s, now(), %s, %s)
            """,
            (run_id, level, line[:8000]),
        )

    def get_run(self, run_id: UUID) -> dict | None:
        row = self.session.execute("SELECT * FROM runs WHERE run_id=%s", (run_id,)).one()
        return row._asdict() if row else None

    def list_runs(self, limit: int = 50, lookback_days: int = 7) -> list[dict]:
        now = datetime.now(timezone.utc)
        out: list[dict] = []
        for i in range(lookback_days):
            day = (now.replace(hour=0, minute=0, second=0, microsecond=0)).strftime("%Y-%m-%d")
            rows = self.session.execute(
                "SELECT * FROM runs_by_day WHERE day=%s LIMIT %s",
                (day, max(1, limit - len(out))),
            )
            out.extend([r._asdict() for r in rows])
            if len(out) >= limit:
                break
            now = now - timedelta(days=1)
        return out[:limit]

    def list_events(self, run_id: UUID, limit: int = 500) -> list[dict]:
        rows = self.session.execute(
            "SELECT run_id, toTimestamp(ts) AS ts, level, line FROM run_events WHERE run_id=%s LIMIT %s",
            (run_id, limit),
        )
        return [r._asdict() for r in rows]

    def insert_benchmark(
        self,
        benchmark_id: UUID,
        cluster_id: str,
        model: str,
        qps: float,
        p50_ms: float,
        p95_ms: float,
        p99_ms: float,
        tokens_per_sec: float,
        note: str,
    ) -> None:
        self.session.execute(
            """
            INSERT INTO benchmarks_by_cluster
            (cluster_id, ts, benchmark_id, model, qps, p50_ms, p95_ms, p99_ms, tokens_per_sec, note)
            VALUES (%s, now(), %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (cluster_id, benchmark_id, model, qps, p50_ms, p95_ms, p99_ms, tokens_per_sec, note),
        )

    def list_benchmarks(self, cluster_id: str, limit: int = 100) -> list[dict]:
        rows = self.session.execute(
            """
            SELECT cluster_id, toTimestamp(ts) AS ts, benchmark_id, model, qps, p50_ms, p95_ms, p99_ms, tokens_per_sec, note
            FROM benchmarks_by_cluster WHERE cluster_id=%s LIMIT %s
            """,
            (cluster_id, limit),
        )
        return [r._asdict() for r in rows]

    def close(self) -> None:
        self.cluster.shutdown()


class InMemoryStore:
    def __init__(self) -> None:
        self._runs: dict[UUID, dict] = {}
        self._events: dict[UUID, list[dict]] = {}
        self._benchmarks: dict[str, list[dict]] = {}

    def create_run(self, run_id: UUID, action: str, status: str) -> None:
        now = datetime.now(timezone.utc)
        self._runs[run_id] = {
            "run_id": run_id,
            "action": action,
            "status": status,
            "created_at": now,
            "updated_at": now,
            "exit_code": None,
        }

    def update_run(self, run_id: UUID, status: str, exit_code: int | None = None) -> None:
        row = self._runs.get(run_id)
        if not row:
            return
        row["status"] = status
        row["updated_at"] = datetime.now(timezone.utc)
        row["exit_code"] = exit_code

    def append_event(self, run_id: UUID, level: str, line: str) -> None:
        events = self._events.setdefault(run_id, [])
        events.append(
            {
                "run_id": run_id,
                "ts": datetime.now(timezone.utc),
                "level": level,
                "line": line[:8000],
            }
        )

    def get_run(self, run_id: UUID) -> dict | None:
        return self._runs.get(run_id)

    def list_runs(self, limit: int = 50, lookback_days: int = 7) -> list[dict]:
        _ = lookback_days
        rows = list(self._runs.values())
        rows.sort(key=lambda r: r["created_at"], reverse=True)
        return rows[:limit]

    def list_events(self, run_id: UUID, limit: int = 500) -> list[dict]:
        return self._events.get(run_id, [])[-limit:]

    def insert_benchmark(
        self,
        benchmark_id: UUID,
        cluster_id: str,
        model: str,
        qps: float,
        p50_ms: float,
        p95_ms: float,
        p99_ms: float,
        tokens_per_sec: float,
        note: str,
    ) -> None:
        rows = self._benchmarks.setdefault(cluster_id, [])
        rows.append(
            {
                "benchmark_id": benchmark_id,
                "cluster_id": cluster_id,
                "ts": datetime.now(timezone.utc),
                "model": model,
                "qps": qps,
                "p50_ms": p50_ms,
                "p95_ms": p95_ms,
                "p99_ms": p99_ms,
                "tokens_per_sec": tokens_per_sec,
                "note": note,
            }
        )

    def list_benchmarks(self, cluster_id: str, limit: int = 100) -> list[dict]:
        rows = self._benchmarks.get(cluster_id, [])
        return list(reversed(rows))[:limit]

    def close(self) -> None:
        return


def create_store() -> tuple[CassandraStore | InMemoryStore, bool, str]:
    try:
        return CassandraStore(), True, "cassandra"
    except Exception as exc:  # noqa: BLE001
        return InMemoryStore(), False, f"in-memory fallback ({exc})"
