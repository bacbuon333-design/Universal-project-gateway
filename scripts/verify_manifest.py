"""Validate one or more UPG project manifests with structured output."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from universal_project_gateway.manifests import validate_manifest


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate PROJECT_MANIFEST.yaml files without registering them."
    )
    parser.add_argument("manifests", nargs="+", type=Path, help="Manifest path(s) to validate")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    reports: list[dict[str, object]] = []
    all_valid = True
    for requested_path in args.manifests:
        path = requested_path.expanduser().resolve()
        result = validate_manifest(path)
        report: dict[str, object] = {"path": str(path), **result.to_dict()}
        if result.manifest is not None:
            report["project_id"] = result.manifest.project_id
            report["project_type"] = result.manifest.project_type
        reports.append(report)
        all_valid = all_valid and result.valid

    print(
        json.dumps(
            {"ok": all_valid, "manifest_count": len(reports), "results": reports},
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if all_valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
