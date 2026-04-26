from __future__ import annotations

import argparse
import sys

from .cluster_manager import ClusterManager


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="SGLang cluster control CLI")
    parser.add_argument(
        "action",
        choices=["deploy", "optimize", "launch", "status", "stop"],
        help="Cluster action to run",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    manager = ClusterManager()
    try:
        manager.run_action(args.action)
    except Exception as exc:  # noqa: BLE001
        print(f"[error] {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
