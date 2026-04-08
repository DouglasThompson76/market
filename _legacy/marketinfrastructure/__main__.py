from __future__ import annotations

import argparse
from pathlib import Path

from .server import run_server
from .service import MarketInfrastructureService


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the MarketInfrastructure dashboard or perform a data check."
    )
    parser.add_argument("--host", default="127.0.0.1", help="Host interface to bind.")
    parser.add_argument("--port", type=int, default=8050, help="Port to listen on.")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Load the data sources, build candidates, and print a short summary.",
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path(__file__).resolve().parent.parent,
        help="Override the project root that contains MarketSnapshot_output.csv and snapshot/.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    service = MarketInfrastructureService(project_root=args.project_root)
    if args.check:
        summary = service.describe()
        print("MarketInfrastructure data check")
        for key, value in summary.items():
            print(f"{key}: {value}")
        return
    run_server(service=service, host=args.host, port=args.port)


if __name__ == "__main__":
    main()

