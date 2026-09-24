from __future__ import annotations

import argparse
import json
from pathlib import Path

from .analysis import ProjectPaths, run_analysis


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the AI CapitalGraph research pipeline.")
    parser.add_argument("command", choices=["analyse"], nargs="?", default="analyse")
    parser.add_argument("--root", type=Path, default=project_root())
    args = parser.parse_args()
    summary = run_analysis(ProjectPaths(args.root.resolve()))
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

