from __future__ import annotations

import argparse

from .server_launcher import ServerLauncher


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="SGLang server launcher CLI")
    parser.add_argument(
        "mode",
        choices=["master", "worker", "start_solo", "solo"],
        help="Server mode to start",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    mode = "start_solo" if args.mode == "solo" else args.mode
    launcher = ServerLauncher()
    return launcher.start(mode)


if __name__ == "__main__":
    raise SystemExit(main())
