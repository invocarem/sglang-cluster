from __future__ import annotations

import os
import re
import subprocess
import sys
import time
from pathlib import Path

from .config import settings


class ServerLauncher:
    def __init__(self) -> None:
        self.scripts_dir = Path(settings.scripts_dir)
        self.log_path = self.scripts_dir / "server.log"
        self.sglang_python = Path.home() / ".sglang" / "bin" / "python"

    def _log(self, message: str) -> None:
        print(message, flush=True)
        with self.log_path.open("a", encoding="utf-8") as f:
            f.write(message + "\n")

    def _build_env(self) -> dict[str, str]:
        env = os.environ.copy()
        # Always derive distributed init address from MASTER_ADDR + MASTER_PORT.
        # Ignore any externally injected DIST_INIT_ADDR to avoid conflicts.
        env.pop("DIST_INIT_ADDR", None)
        # Guard against empty-but-present env vars from caller shell.
        defaults = {
            "MASTER_PORT": str(settings.master_port),
            "SERVER_PORT": str(settings.server_port),
            "MODEL_PATH": settings.model_path,
            "TP_SIZE": str(settings.tp_size),
            "MASTER_ADDR": settings.master_node,
        }
        for key, value in defaults.items():
            if not env.get(key):
                env[key] = value

        # NCCL defaults from run_server.sh
        env.setdefault("NCCL_IB_DISABLE", "0")
        env.setdefault("NCCL_IB_GID_INDEX", "3")
        env.setdefault("NCCL_IB_TIMEOUT", "22")
        env.setdefault("NCCL_IB_RETRY_CNT", "7")
        env.setdefault("NCCL_IB_SL", "3")
        env.setdefault("NCCL_IB_TC", "160")
        env.setdefault("NCCL_IB_QPS_PER_CONNECTION", "4")
        env.setdefault("NCCL_NET_GDR_LEVEL", "5")
        env.setdefault("NCCL_DEBUG", "WARN")

        env.setdefault("SGLANG_DISABLE_TORCHVISION", "1")
        return env

    def _maybe_optimize(self, env: dict[str, str]) -> None:
        if env.get("SGLANG_RUN_OPTIMIZE_ON_START", "0") != "1":
            return
        script = self.scripts_dir / "cx7_optimize.sh"
        if not script.exists():
            return
        result = subprocess.run(["bash", str(script)], check=False, cwd=str(self.scripts_dir))
        if result.returncode != 0:
            self._log("WARN: cx7_optimize.sh failed; continuing launch")

    def _sglang_python_exec(self) -> str:
        if self.sglang_python.exists():
            return str(self.sglang_python)
        return sys.executable

    @staticmethod
    def _normalize_dist_addr(host: str, port: str) -> str:
        clean_host = host.strip()
        clean_port = port.strip()
        clean_host = re.sub(r"^[a-zA-Z]+://", "", clean_host)
        clean_host = clean_host.rstrip(":")
        if not clean_host:
            clean_host = settings.master_node
        if not clean_port:
            clean_port = str(settings.master_port)
        return f"{clean_host}:{clean_port}"

    def _run(self, mode: str) -> int:
        env = self._build_env()
        self._maybe_optimize(env)

        model_path = env["MODEL_PATH"]
        server_port = env["SERVER_PORT"]
        tp_size = env["TP_SIZE"]
        master_addr = env["MASTER_ADDR"]
        master_port = env["MASTER_PORT"]
        dist_init_addr = self._normalize_dist_addr(master_addr, master_port)

        cmd = [
            self._sglang_python_exec(),
            "-m",
            "sglang.launch_server",
            "--model-path",
            model_path,
            "--host",
            "0.0.0.0",
            "--port",
            server_port,
        ]

        if mode == "start_solo":
            self._log("Starting solo node...")
            self._log(f"TP_SIZE {tp_size}")
            cmd.extend(["--tp-size", "1", "--disable-piecewise-cuda-graph"])
        elif mode == "master":
            self._log("Starting master node...")
            self._log(
                f"Resolved dist settings: MASTER_ADDR={master_addr!r} MASTER_PORT={master_port!r} "
                f"dist_init_addr={dist_init_addr!r}"
            )
            cmd.extend(
                [
                    "--tp-size",
                    tp_size,
                    "--dist-init-addr",
                    dist_init_addr,
                    "--nnodes",
                    "2",
                    "--node-rank",
                    "0",
                    "--disable-piecewise-cuda-graph",
                ]
            )
        elif mode == "worker":
            self._log("Starting worker node...")
            self._log(
                f"Resolved dist settings: MASTER_ADDR={master_addr!r} MASTER_PORT={master_port!r} "
                f"dist_init_addr={dist_init_addr!r}"
            )
            time.sleep(10)
            cmd.extend(
                [
                    "--tp-size",
                    tp_size,
                    "--dist-init-addr",
                    dist_init_addr,
                    "--nnodes",
                    "2",
                    "--node-rank",
                    "1",
                ]
            )
        else:
            raise ValueError(f"Unsupported mode: {mode}")

        proc = subprocess.Popen(
            cmd,
            cwd=str(self.scripts_dir),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        assert proc.stdout is not None
        with self.log_path.open("a", encoding="utf-8") as log_file:
            for line in proc.stdout:
                line = line.rstrip("\n")
                print(line, flush=True)
                log_file.write(line + "\n")
                log_file.flush()
        return proc.wait()

    def start(self, mode: str) -> int:
        return self._run(mode)
