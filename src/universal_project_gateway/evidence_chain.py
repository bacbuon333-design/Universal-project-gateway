"""Canonical hashing primitives for the additive evidence event chain."""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

CHAIN_FILE = "evidence_events.jsonl"
ATTESTATION_FILE = "attestation.json"
EVIDENCE_SCHEMA_VERSION = "2.0"
EVENT_SCHEMA_VERSION = "1.0"
HASH_ALGORITHM = "sha256"
GENESIS_EVENT_HASH = "0" * 64

_EVENT_FIELDS = frozenset(
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
_COMPONENT = re.compile(r"^[a-z][a-z0-9_]{1,63}$")
_HEX_DIGEST = re.compile(r"^[0-9a-f]{64}$")
_WINDOWS_ABSOLUTE = re.compile(r"^[A-Za-z]:[\\/]")


class EvidenceChainError(ValueError):
    """Raised when canonical event material is unsafe or malformed."""


def canonical_json(value: Any) -> str:
    """Serialize JSON deterministically for hashing and JSONL persistence."""

    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def normalize_event_payload(value: Any) -> Any:
    """Accept JSON values while refusing unnormalized absolute host paths."""

    if value is None or isinstance(value, (bool, int, str)):
        if isinstance(value, str) and _looks_like_absolute_path(value):
            raise EvidenceChainError(
                "absolute host paths must be normalized before evidence event hashing"
            )
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise EvidenceChainError("non-finite numbers are forbidden in evidence events")
        return value
    if isinstance(value, Mapping):
        return {
            str(key): normalize_event_payload(item)
            for key, item in sorted(value.items(), key=lambda item: str(item[0]))
        }
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [normalize_event_payload(item) for item in value]
    raise EvidenceChainError(
        f"evidence event payload contains unsupported type {type(value).__name__}"
    )


def create_event(
    *,
    sequence: int,
    event_type: str,
    timestamp: str,
    job_id: str,
    project_id: str,
    actor: str,
    previous_event_hash: str,
    payload: Any,
) -> dict[str, Any]:
    if isinstance(sequence, bool) or sequence < 1:
        raise EvidenceChainError("evidence event sequence must be a positive integer")
    for label, value in (("event_type", event_type), ("actor", actor)):
        if not isinstance(value, str) or not _COMPONENT.fullmatch(value):
            raise EvidenceChainError(f"{label} must be a bounded component identifier")
    if not isinstance(timestamp, str) or not timestamp.endswith("Z"):
        raise EvidenceChainError("evidence event timestamp must be a UTC string")
    if not isinstance(job_id, str) or not job_id:
        raise EvidenceChainError("evidence event job_id is required")
    if not isinstance(project_id, str) or not project_id:
        raise EvidenceChainError("evidence event project_id is required")
    if not _HEX_DIGEST.fullmatch(previous_event_hash):
        raise EvidenceChainError("previous_event_hash must be a lowercase SHA-256 digest")

    normalized_payload = normalize_event_payload(payload)
    event: dict[str, Any] = {
        "schema_version": EVENT_SCHEMA_VERSION,
        "hash_algorithm": HASH_ALGORITHM,
        "sequence": sequence,
        "event_type": event_type,
        "timestamp": timestamp,
        "job_id": job_id,
        "project_id": project_id,
        "actor": actor,
        "previous_event_hash": previous_event_hash,
        "payload": normalized_payload,
        "payload_hash": canonical_sha256(normalized_payload),
    }
    event["event_hash"] = canonical_sha256(event)
    return event


def verify_event_records(events: Sequence[Any]) -> list[dict[str, str]]:
    """Verify chain structure, canonical payload hashes, order, and continuity."""

    errors: list[dict[str, str]] = []
    previous_hash = GENESIS_EVENT_HASH
    expected_job: str | None = None
    expected_project: str | None = None
    for index, raw_event in enumerate(events, start=1):
        location = f"{CHAIN_FILE}:{index}"
        if not isinstance(raw_event, Mapping):
            errors.append({"code": "EVIDENCE_EVENT_INVALID", "path": location})
            continue
        event = dict(raw_event)
        if set(event) != _EVENT_FIELDS:
            errors.append({"code": "EVIDENCE_EVENT_FIELDS_INVALID", "path": location})
            continue
        if event.get("sequence") != index:
            errors.append({"code": "EVIDENCE_EVENT_SEQUENCE_INVALID", "path": location})
        if event.get("schema_version") != EVENT_SCHEMA_VERSION:
            errors.append({"code": "EVIDENCE_EVENT_SCHEMA_INVALID", "path": location})
        if event.get("hash_algorithm") != HASH_ALGORITHM:
            errors.append({"code": "EVIDENCE_EVENT_ALGORITHM_INVALID", "path": location})
        if event.get("previous_event_hash") != previous_hash:
            errors.append({"code": "EVIDENCE_EVENT_CHAIN_BROKEN", "path": location})
        payload = event.get("payload")
        try:
            normalized_payload = normalize_event_payload(payload)
            actual_payload_hash = canonical_sha256(normalized_payload)
        except (EvidenceChainError, TypeError, ValueError):
            errors.append({"code": "EVIDENCE_EVENT_PAYLOAD_INVALID", "path": location})
            actual_payload_hash = None
        if event.get("payload_hash") != actual_payload_hash:
            errors.append({"code": "EVIDENCE_EVENT_PAYLOAD_HASH_MISMATCH", "path": location})
        recorded_hash = event.get("event_hash")
        material = {key: value for key, value in event.items() if key != "event_hash"}
        try:
            actual_event_hash = canonical_sha256(material)
        except (TypeError, ValueError):
            actual_event_hash = None
        if not isinstance(recorded_hash, str) or recorded_hash != actual_event_hash:
            errors.append({"code": "EVIDENCE_EVENT_HASH_MISMATCH", "path": location})
        job_id = event.get("job_id")
        project_id = event.get("project_id")
        if index == 1:
            expected_job = job_id if isinstance(job_id, str) else None
            expected_project = project_id if isinstance(project_id, str) else None
        elif job_id != expected_job or project_id != expected_project:
            errors.append({"code": "EVIDENCE_EVENT_IDENTITY_MISMATCH", "path": location})
        previous_hash = recorded_hash if isinstance(recorded_hash, str) else ""
    if not events:
        errors.append({"code": "EVIDENCE_EVENT_CHAIN_EMPTY", "path": CHAIN_FILE})
    return errors


def compatibility_manifest_checksum(checksums: Mapping[str, str]) -> str:
    """Hash the compatibility-file digest map without circular self-reference."""

    material = {
        "algorithm": HASH_ALGORITHM,
        "files": dict(sorted((str(name), str(digest)) for name, digest in checksums.items())),
    }
    return canonical_sha256(material)


def _looks_like_absolute_path(value: str) -> bool:
    if not value or "\n" in value or "\r" in value:
        return False
    return value.startswith(("/", "\\\\")) or bool(_WINDOWS_ABSOLUTE.match(value)) or Path(
        value
    ).is_absolute()


__all__ = [
    "ATTESTATION_FILE",
    "CHAIN_FILE",
    "EVIDENCE_SCHEMA_VERSION",
    "EVENT_SCHEMA_VERSION",
    "EvidenceChainError",
    "GENESIS_EVENT_HASH",
    "HASH_ALGORITHM",
    "canonical_json",
    "canonical_sha256",
    "compatibility_manifest_checksum",
    "create_event",
    "normalize_event_payload",
    "verify_event_records",
]
