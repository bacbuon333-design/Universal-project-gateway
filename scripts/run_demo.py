"""Run the packaged deterministic UPG demo from the repository root."""

from __future__ import annotations

import json
from pathlib import Path

from universal_project_gateway.demo import run_demo


def main() -> int:
    result = run_demo(Path(__file__).resolve().parents[1])
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
