"""Independently verify UPG checksums, event-chain continuity, and attestation."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

CHECKSUM_MANIFEST = "manifest.sha256.json"
CHAIN_FILE = "evidence_events.jsonl"
ATTESTATION_FILE = "attestation.json"
EVIDENCE_SCHEMA_VERSION = "2.0"
EVENT_SCHEMA_VERSION = "1.0"
GENESIS_EVENT_HASH = "0" * 64
COMPATIBILITY_EVIDENCE_FILES = (
    "task.json",
    "intent.json",
    "context_pack.json",
    "source_snapshot.json",
    "operations.json",
    "files_changed.json",
    "patch.diff",
    "validation.json",
    "stdout.log",
    "stderr.log",
    "environment.json",
    "final_report.json",
)
SHA256_PATTERN = re.compile(r"^[0-9a-fA-F]{64}$")
LOWER_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
COMPONENT_PATTERN = re.compile(r"^[a-z][a-z0-9_]{1,63}$")
WINDOWS_ABSOLUTE = re.compile(r"^[A-Za-z]:[\\/]")
EVENT_FIELDS = frozenset(
    {
        "schema_version",
        "hash_algorithm",
        "sequence",
        "event_type",
        "timestamp",
        "job_id",
        "project_id",
        "actor",
        "previous_event_hash",
        "payload",
        "payload_hash",
        "event_hash",
    }
)


class EvidenceVerificationError(ValueError):
    """Raised when an evidence ledger is missing, malformed, or modified."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _canonical_sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _payload_is_canonical(value: Any) -> bool:
    if value is None or isinstance(value, (bool, int)):
        return True
    if isinstance(value, float):
        return math.isfinite(value)
    if isinstance(value, str):
        return not (
            value.startswith(("/", "\\\\"))
            or WINDOWS_ABSOLUTE.match(value)
            or Path(value).is_absolute()
        )
    if isinstance(value, Mapping):
        return all(isinstance(key, str) and _payload_is_canonical(item) for key, item in value.items())
    if isinstance(value, list):
        return all(_payload_is_canonical(item) for item in value)
    return False


def _compatibility_manifest_checksum(entries: Mapping[str, str]) -> str:
    return _canonical_sha256(
        {"algorithm": "sha256", "files": dict(sorted(entries.items()))}
    )


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


def _verify_chain(
    bundle: Path,
    entries: Mapping[str, str],
    failures: list[dict[str, str]],
) -> tuple[bool, int]:
    chain_path = bundle / CHAIN_FILE
    attestation_path = bundle / ATTESTATION_FILE
    if chain_path.exists() != attestation_path.exists():
        failures.append({"path": CHAIN_FILE, "reason": "chain_incomplete"})
        return False, 0
    if not chain_path.exists():
        # A pre-v2 12-file bundle remains checksum-verifiable.
        return False, 0

    events: list[Any] = []
    try:
        lines = chain_path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError):
        failures.append({"path": CHAIN_FILE, "reason": "chain_unreadable"})
        return True, 0
    for line_number, line in enumerate(lines, start=1):
        location = f"{CHAIN_FILE}:{line_number}"
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            failures.append({"path": location, "reason": "invalid_event_json"})
            events.append(None)
            continue
        events.append(event)
        try:
            if line != _canonical_json(event):
                failures.append({"path": location, "reason": "event_not_canonical"})
        except (TypeError, ValueError):
            failures.append({"path": location, "reason": "event_not_canonical"})

    previous_hash = GENESIS_EVENT_HASH
    expected_job: str | None = None
    expected_project: str | None = None
    for index, raw_event in enumerate(events, start=1):
        location = f"{CHAIN_FILE}:{index}"
        if not isinstance(raw_event, Mapping) or set(raw_event) != EVENT_FIELDS:
            failures.append({"path": location, "reason": "invalid_event_fields"})
            continue
        event = dict(raw_event)
        if event.get("sequence") != index:
            failures.append({"path": location, "reason": "invalid_sequence"})
        if event.get("schema_version") != EVENT_SCHEMA_VERSION:
            failures.append({"path": location, "reason": "invalid_event_schema"})
        if event.get("hash_algorithm") != "sha256":
            failures.append({"path": location, "reason": "invalid_event_algorithm"})
        if not COMPONENT_PATTERN.fullmatch(str(event.get("event_type", ""))) or not (
            COMPONENT_PATTERN.fullmatch(str(event.get("actor", "")))
        ):
            failures.append({"path": location, "reason": "invalid_event_component"})
        if event.get("previous_event_hash") != previous_hash:
            failures.append({"path": location, "reason": "chain_discontinuity"})
        payload = event.get("payload")
        if not _payload_is_canonical(payload):
            failures.append({"path": location, "reason": "invalid_event_payload"})
        try:
            payload_hash = _canonical_sha256(payload)
        except (TypeError, ValueError):
            payload_hash = None
        if event.get("payload_hash") != payload_hash:
            failures.append({"path": location, "reason": "payload_hash_mismatch"})
        recorded_hash = event.get("event_hash")
        material = {key: value for key, value in event.items() if key != "event_hash"}
        try:
            event_hash = _canonical_sha256(material)
        except (TypeError, ValueError):
            event_hash = None
        if (
            not isinstance(recorded_hash, str)
            or not LOWER_SHA256_PATTERN.fullmatch(recorded_hash)
            or recorded_hash != event_hash
        ):
            failures.append({"path": location, "reason": "event_hash_mismatch"})
        if index == 1:
            expected_job = event.get("job_id") if isinstance(event.get("job_id"), str) else None
            expected_project = (
                event.get("project_id") if isinstance(event.get("project_id"), str) else None
            )
        elif event.get("job_id") != expected_job or event.get("project_id") != expected_project:
            failures.append({"path": location, "reason": "event_identity_mismatch"})
        previous_hash = recorded_hash if isinstance(recorded_hash, str) else ""

    if not events:
        failures.append({"path": CHAIN_FILE, "reason": "empty_chain"})
    try:
        attestation = json.loads(attestation_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        failures.append({"path": ATTESTATION_FILE, "reason": "invalid_attestation"})
        return True, len(events)
    if not isinstance(attestation, Mapping):
        failures.append({"path": ATTESTATION_FILE, "reason": "invalid_attestation"})
        return True, len(events)

    final_event = events[-1] if events and isinstance(events[-1], Mapping) else {}
    if final_event.get("event_type") != "evidence_finalized":
        failures.append({"path": CHAIN_FILE, "reason": "invalid_final_event"})
    if attestation.get("evidence_schema_version") != EVIDENCE_SCHEMA_VERSION:
        failures.append({"path": ATTESTATION_FILE, "reason": "invalid_attestation_schema"})
    if attestation.get("hash_algorithm") != "sha256":
        failures.append({"path": ATTESTATION_FILE, "reason": "invalid_attestation_algorithm"})
    if attestation.get("final_event_hash") != final_event.get("event_hash"):
        failures.append({"path": ATTESTATION_FILE, "reason": "final_event_hash_mismatch"})
    if (
        attestation.get("job_id") != final_event.get("job_id")
        or attestation.get("project_id") != final_event.get("project_id")
    ):
        failures.append({"path": ATTESTATION_FILE, "reason": "attestation_identity_mismatch"})

    compatibility_entries = {
        filename: entries[filename]
        for filename in COMPATIBILITY_EVIDENCE_FILES
        if filename in entries
    }
    if len(compatibility_entries) != len(COMPATIBILITY_EVIDENCE_FILES):
        failures.append({"path": CHECKSUM_MANIFEST, "reason": "compatibility_files_missing"})
    manifest_checksum = attestation.get("manifest_checksum")
    if not isinstance(manifest_checksum, Mapping) or (
        manifest_checksum.get("algorithm") != "sha256"
        or manifest_checksum.get("scope") != "compatibility_evidence_file_digests"
        or manifest_checksum.get("value")
        != _compatibility_manifest_checksum(compatibility_entries)
    ):
        failures.append({"path": ATTESTATION_FILE, "reason": "manifest_checksum_mismatch"})
    signer = attestation.get("signer")
    if not isinstance(signer, Mapping) or (
        signer.get("identity") != "universal-project-gateway-local-development"
        or signer.get("signature_algorithm") != "none"
        or signer.get("signature") is not None
    ):
        failures.append({"path": ATTESTATION_FILE, "reason": "invalid_unsigned_signer"})
    return True, len(events)


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

    chain_checked, events_checked = _verify_chain(bundle, entries, failures)

    return {
        "ok": not failures,
        "bundle": str(bundle),
        "algorithm": "sha256",
        "files_checked": len(entries),
        "chain_checked": chain_checked,
        "events_checked": events_checked,
        "failures": failures,
    }


def _latest_bundle(jobs_root: Path) -> Path:
    candidates = list(jobs_root.glob(f"*/{CHECKSUM_MANIFEST}"))
    if not candidates:
        raise EvidenceVerificationError(f"No evidence bundles found under {jobs_root}")
    return max(candidates, key=lambda path: path.stat().st_mtime_ns).parent


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Verify SHA-256 coverage plus an optional v2 event chain and attestation."
        )
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
