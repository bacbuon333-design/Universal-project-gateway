"""Independently verify a Universal Project Gateway evidence bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

CHECKSUM_MANIFEST = "manifest.sha256.json"
SHA256_PATTERN = re.compile(r"^[0-9a-fA-F]{64}$")


class EvidenceVerificationError(ValueError):
    """Raised when an evidence ledger is missing, malformed, or modified."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _normalize_relative_path(raw_path: object) -> str:
    if not isinstance(raw_path, str) or not raw_path.strip():
        raise EvidenceVerificationError("A checksum entry has an empty or non-string path")
    normalized = raw_path.replace("\\", "/")
    candidate = Path(normalized)
    if candidate.is_absolute() or ":" in normalized.split("/", 1)[0]:
        raise EvidenceVerificationError(f"Checksum path must be relative: {raw_path!r}")
    parts = tuple(part for part in normalized.split("/") if part not in ("", "."))
    if not parts or ".." in parts:
        raise EvidenceVerificationError(f"Checksum path escapes its evidence bundle: {raw_path!r}")
    return "/".join(parts)


def _digest_from_value(value: object, *, path: str) -> str:
    digest: object = value
    if isinstance(value, Mapping):
        digest = value.get("sha256", value.get("digest"))
    if not isinstance(digest, str) or not SHA256_PATTERN.fullmatch(digest):
        raise EvidenceVerificationError(f"Invalid SHA-256 digest recorded for {path!r}")
    return digest.lower()


def _entries_from_payload(payload: Any) -> dict[str, str]:
    """Accept the documented object/list checksum representations."""

    if not isinstance(payload, Mapping):
        raise EvidenceVerificationError("Checksum manifest must contain a JSON object")
    algorithm = payload.get("algorithm", "sha256")
    if not isinstance(algorithm, str) or algorithm.casefold().replace("-", "") != "sha256":
        raise EvidenceVerificationError("Checksum manifest algorithm must be SHA-256")

    raw_entries: object
    if "files" in payload:
        raw_entries = payload["files"]
    elif "checksums" in payload:
        raw_entries = payload["checksums"]
    else:
        metadata_keys = {"algorithm", "schema_version", "created_at"}
        raw_entries = {key: value for key, value in payload.items() if key not in metadata_keys}

    entries: dict[str, str] = {}
    if isinstance(raw_entries, Mapping):
        for raw_path, raw_digest in raw_entries.items():
            path = _normalize_relative_path(raw_path)
            if path in entries:
                raise EvidenceVerificationError(f"Duplicate checksum path: {path!r}")
            entries[path] = _digest_from_value(raw_digest, path=path)
    elif isinstance(raw_entries, list):
        for item in raw_entries:
            if not isinstance(item, Mapping):
                raise EvidenceVerificationError("Checksum file entries must be JSON objects")
            path = _normalize_relative_path(item.get("path", item.get("file")))
            if path in entries:
                raise EvidenceVerificationError(f"Duplicate checksum path: {path!r}")
            entries[path] = _digest_from_value(item.get("sha256", item.get("digest")), path=path)
    else:
        raise EvidenceVerificationError("Checksum files must be an object or a list")

    if not entries:
        raise EvidenceVerificationError("Checksum manifest does not cover any evidence files")
    if CHECKSUM_MANIFEST in entries:
        raise EvidenceVerificationError("Checksum manifest must not include its own digest")
    return entries


def verify_bundle(bundle: Path) -> dict[str, object]:
    bundle = bundle.expanduser().resolve()
    if not bundle.is_dir():
        raise EvidenceVerificationError(f"Evidence bundle is not a directory: {bundle}")

    manifest_path = bundle / CHECKSUM_MANIFEST
    if not manifest_path.is_file():
        raise EvidenceVerificationError(f"Missing checksum manifest: {manifest_path}")
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise EvidenceVerificationError(f"Cannot read checksum manifest: {error}") from error

    entries = _entries_from_payload(payload)
    bundle_root = bundle.resolve()
    failures: list[dict[str, str]] = []

    for relative_path, expected in sorted(entries.items()):
        candidate = (bundle / Path(relative_path)).resolve()
        try:
            candidate.relative_to(bundle_root)
        except ValueError:
            failures.append({"path": relative_path, "reason": "path_escape"})
            continue
        if not candidate.is_file():
            failures.append({"path": relative_path, "reason": "missing"})
            continue
        actual = _sha256(candidate)
        if actual != expected:
            failures.append(
                {
                    "path": relative_path,
                    "reason": "digest_mismatch",
                    "expected": expected,
                    "actual": actual,
                }
            )

    covered = set(entries)
    present: set[str] = set()
    for path in bundle.rglob("*"):
        if path.is_file():
            relative_path = path.relative_to(bundle).as_posix()
            if relative_path != CHECKSUM_MANIFEST:
                present.add(relative_path)
    for relative_path in sorted(present - covered):
        failures.append({"path": relative_path, "reason": "not_covered"})

    return {
        "ok": not failures,
        "bundle": str(bundle),
        "algorithm": "sha256",
        "files_checked": len(entries),
        "failures": failures,
    }


def _latest_bundle(jobs_root: Path) -> Path:
    candidates = list(jobs_root.glob(f"*/{CHECKSUM_MANIFEST}"))
    if not candidates:
        raise EvidenceVerificationError(f"No evidence bundles found under {jobs_root}")
    return max(candidates, key=lambda path: path.stat().st_mtime_ns).parent


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify every SHA-256 entry and coverage in a UPG evidence bundle."
    )
    parser.add_argument("bundle", nargs="?", type=Path, help="Evidence bundle directory")
    parser.add_argument(
        "--latest",
        action="store_true",
        help="Verify the newest bundle under artifacts/jobs",
    )
    args = parser.parse_args(argv)
    if args.latest and args.bundle is not None:
        parser.error("bundle and --latest are mutually exclusive")
    if not args.latest and args.bundle is None:
        parser.error("provide an evidence bundle or --latest")
    return args


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    repository_root = Path(__file__).resolve().parents[1]
    try:
        bundle = (
            _latest_bundle(repository_root / "artifacts" / "jobs") if args.latest else args.bundle
        )
        result = verify_bundle(bundle)
    except (EvidenceVerificationError, OSError) as error:
        print(json.dumps({"ok": False, "error": str(error)}, indent=2), file=sys.stderr)
        return 1

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
