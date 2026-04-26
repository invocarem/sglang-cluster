import { useEffect, useMemo, useRef, useState } from "react";

type RunAction =
  | "deploy"
  | "start_master"
  | "start_worker"
  | "start_solo"
  | "status"
  | "stop"
  | "benchmark";

type RunSummary = {
  run_id: string;
  action: RunAction;
  status: string;
  created_at: string;
  updated_at: string;
  exit_code?: number | null;
};

type ClusterHealth = {
  master: {
    node: string;
    reachable: boolean;
    iface: string;
    iface_has_ip: boolean;
    sglang_running: boolean;
    detail: string;
  };
  worker: {
    node: string;
    reachable: boolean;
    iface: string;
    iface_has_ip: boolean;
    sglang_running: boolean;
    detail: string;
  };
};

type Benchmark = {
  benchmark_id: string;
  cluster_id: string;
  ts: string;
  model: string;
  qps: number;
  p50_ms: number;
  p95_ms: number;
  p99_ms: number;
  tokens_per_sec: number;
  note: string;
};

const API_BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:18080";

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const resp = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!resp.ok) {
    throw new Error(`${resp.status} ${resp.statusText}`);
  }
  return resp.json() as Promise<T>;
}

export function App() {
  const [runs, setRuns] = useState([] as RunSummary[]);
  const [selectedRunId, setSelectedRunId] = useState("");
  const [action, setAction] = useState("deploy" as RunAction);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [logs, setLogs] = useState([] as string[]);
  const [health, setHealth] = useState(null as ClusterHealth | null);
  const [benchmarks, setBenchmarks] = useState([] as Benchmark[]);
  const wsRef = useRef(null as WebSocket | null);

  const selectedRun = useMemo(
    () => runs.find((r: RunSummary) => r.run_id === selectedRunId),
    [runs, selectedRunId]
  );

  async function refreshRuns() {
    const data = await api<RunSummary[]>("/runs");
    setRuns(
      [...data].sort(
        (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
      )
    );
    if (!selectedRunId && data.length > 0) {
      setSelectedRunId(data[0].run_id);
    }
  }

  async function createRun() {
    setLoading(true);
    setError("");
    try {
      const run = await api<RunSummary>("/runs", {
        method: "POST",
        body: JSON.stringify({ action, extra_args: [] }),
      });
      setSelectedRunId(run.run_id);
      await refreshRuns();
    } catch (err: any) {
      setError(`Failed to start action "${action}": ${String(err?.message ?? err)}`);
    } finally {
      setLoading(false);
    }
  }

  async function refreshHealth() {
    const data = await api<ClusterHealth>("/cluster/health");
    setHealth(data);
  }

  async function refreshBenchmarks() {
    const data = await api<Benchmark[]>("/benchmarks?cluster_id=default&limit=20");
    setBenchmarks(data);
  }

  async function saveQuickBenchmark() {
    await api<Benchmark>("/benchmarks", {
      method: "POST",
      body: JSON.stringify({
        cluster_id: "default",
        model: "manual-entry",
        qps: 0,
        p50_ms: 0,
        p95_ms: 0,
        p99_ms: 0,
        tokens_per_sec: 0,
        note: "placeholder benchmark; wire real parser next",
      }),
    });
    await refreshBenchmarks();
  }

  async function stopRun() {
    if (!selectedRunId) return;
    try {
      setError("");
      await api(`/runs/${selectedRunId}/stop`, { method: "POST" });
      await refreshRuns();
    } catch (err: any) {
      setError(`Failed to stop run: ${String(err?.message ?? err)}`);
    }
  }

  useEffect(() => {
    refreshRuns().catch(console.error);
    refreshHealth().catch((err: any) => setError(`Health check failed: ${String(err?.message ?? err)}`));
    refreshBenchmarks().catch((err: any) =>
      setError(`Benchmark refresh failed: ${String(err?.message ?? err)}`)
    );
    const timer = setInterval(() => refreshRuns().catch(console.error), 4000);
    const healthTimer = setInterval(() => refreshHealth().catch(console.error), 10000);
    return () => {
      clearInterval(timer);
      clearInterval(healthTimer);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    setLogs([]);
    if (!selectedRunId) return;
    const wsUrl = API_BASE.replace("http://", "ws://").replace("https://", "wss://");
    const ws = new WebSocket(`${wsUrl}/runs/${selectedRunId}/ws`);
    wsRef.current = ws;
    ws.onmessage = (ev) => {
      setLogs((prev: string[]) => [...prev.slice(-500), ev.data]);
    };
    ws.onerror = () => {
      setLogs((prev: string[]) => [...prev, "[ws error]"]);
    };
    return () => ws.close();
  }, [selectedRunId]);

  return (
    <div className="page">
      <h1>SGLang Cluster UI</h1>
      <div className="toolbar">
        <select value={action} onChange={(e: any) => setAction(e.target.value as RunAction)}>
          <option value="deploy">deploy</option>
          <option value="start_master">start_master</option>
          <option value="start_worker">start_worker</option>
          <option value="start_solo">start_solo</option>
          <option value="status">status</option>
          <option value="stop">stop</option>
          <option value="benchmark">benchmark</option>
        </select>
        <button onClick={createRun} disabled={loading}>
          {loading ? "Starting..." : "Start Action"}
        </button>
        <button onClick={refreshRuns}>Refresh Runs</button>
        <button onClick={refreshHealth}>Refresh Health</button>
        <button onClick={saveQuickBenchmark}>Save Benchmark Row</button>
      </div>
      {error && (
        <section className="panel">
          <strong>Error:</strong> {error}
        </section>
      )}

      <div className="grid">
        <section className="panel">
          <h2>Runs</h2>
          <div className="list">
            {runs.map((run: RunSummary) => (
              <button
                key={run.run_id}
                className={`run ${run.run_id === selectedRunId ? "active" : ""}`}
                onClick={() => setSelectedRunId(run.run_id)}
              >
                <div>
                  <strong>{run.action}</strong> - {run.status}
                </div>
                <small>{run.run_id}</small>
              </button>
            ))}
            {runs.length === 0 && <p>No runs yet.</p>}
          </div>
        </section>

        <section className="panel">
          <h2>Selected Run</h2>
          {selectedRun ? (
            <>
              <p>
                <strong>ID:</strong> {selectedRun.run_id}
              </p>
              <p>
                <strong>Status:</strong> {selectedRun.status}
              </p>
              <p>
                <strong>Action:</strong> {selectedRun.action}
              </p>
              <p>
                <strong>Exit code:</strong> {String(selectedRun.exit_code ?? "n/a")}
              </p>
              <button onClick={stopRun}>Stop Selected Run</button>
            </>
          ) : (
            <p>Select a run.</p>
          )}
        </section>
      </div>

      <section className="panel">
        <h2>Live Logs</h2>
        <pre className="logs">{logs.join("\n")}</pre>
      </section>

      <div className="grid">
        <section className="panel">
          <h2>Cluster Health</h2>
          {health ? (
            <>
              <p>
                <strong>Master:</strong> {health.master.node} / reachable=
                {String(health.master.reachable)} / running={String(health.master.sglang_running)}
              </p>
              <p>
                <strong>Worker:</strong> {health.worker.node} / reachable=
                {String(health.worker.reachable)} / running={String(health.worker.sglang_running)}
              </p>
            </>
          ) : (
            <p>No health data yet.</p>
          )}
        </section>
        <section className="panel">
          <h2>Benchmarks (latest)</h2>
          <div className="list">
            {benchmarks.map((b: Benchmark) => (
              <div key={b.benchmark_id} className="run">
                <div>
                  <strong>{b.model}</strong> qps={b.qps} tok/s={b.tokens_per_sec}
                </div>
                <small>
                  p50={b.p50_ms} p95={b.p95_ms} p99={b.p99_ms}
                </small>
              </div>
            ))}
            {benchmarks.length === 0 && <p>No benchmarks yet.</p>}
          </div>
        </section>
      </div>
    </div>
  );
}
