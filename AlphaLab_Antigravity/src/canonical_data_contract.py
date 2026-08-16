"""V3.7 canonical market-data contract.

This module is governance infrastructure only. It does not generate signals,
run strategies, or infer missing provenance from market behavior.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional
import hashlib
import json


class TimestampSemantic(str, Enum):
    BAR_OPEN_TIME = "BAR_OPEN_TIME"
    BAR_CLOSE_TIME = "BAR_CLOSE_TIME"
    UNRESOLVED = "UNRESOLVED"


class TimezoneStatus(str, Enum):
    EXPLICIT_UTC = "EXPLICIT_UTC"
    EXPLICIT_OFFSET = "EXPLICIT_OFFSET"
    NAIVE_UNRESOLVED = "NAIVE_UNRESOLVED"


class LineageStatus(str, Enum):
    VERIFIED = "VERIFIED"
    PARTIAL = "PARTIAL"
    UNRESOLVED = "UNRESOLVED"


class Eligibility(str, Enum):
    ELIGIBLE = "ELIGIBLE"
    BLOCKED = "BLOCKED"


REQUIRED_PROVENANCE_FIELDS = (
    "dataset_sha256",
    "source_type",
    "source_identifier",
    "exporter_or_extraction_method",
    "timestamp_semantic",
    "timestamp_timezone_status",
    "timestamp_timezone",
    "transform_chain",
)


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        obj = json.load(f)
    if not isinstance(obj, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return obj


def _valid_timestamp_semantic(value: Any) -> bool:
    return value in {e.value for e in TimestampSemantic}


def _valid_timezone_status(value: Any) -> bool:
    return value in {e.value for e in TimezoneStatus}


def validate_provenance_sidecar(sidecar: Dict[str, Any], actual_sha256: str) -> Dict[str, Any]:
    """Validate explicit provenance without filling gaps heuristically."""
    missing = [k for k in REQUIRED_PROVENANCE_FIELDS if k not in sidecar]
    problems: List[str] = []
    if missing:
        problems.append("missing_fields:" + ",".join(missing))

    declared_hash = sidecar.get("dataset_sha256")
    hash_match = bool(declared_hash) and declared_hash == actual_sha256
    if not hash_match:
        problems.append("dataset_sha256_mismatch_or_missing")

    sem = sidecar.get("timestamp_semantic", TimestampSemantic.UNRESOLVED.value)
    if not _valid_timestamp_semantic(sem):
        problems.append("invalid_timestamp_semantic")
        sem = TimestampSemantic.UNRESOLVED.value

    tz_status = sidecar.get("timestamp_timezone_status", TimezoneStatus.NAIVE_UNRESOLVED.value)
    if not _valid_timezone_status(tz_status):
        problems.append("invalid_timestamp_timezone_status")
        tz_status = TimezoneStatus.NAIVE_UNRESOLVED.value

    transform_chain = sidecar.get("transform_chain")
    transform_ok = isinstance(transform_chain, list) and len(transform_chain) > 0
    if not transform_ok:
        problems.append("transform_chain_missing_or_empty")

    core_fields_nonempty = all(
        sidecar.get(k) not in (None, "", [])
        for k in ("source_type", "source_identifier", "exporter_or_extraction_method")
    )
    if not core_fields_nonempty:
        problems.append("source_or_extraction_identity_incomplete")

    explicit_time = (
        sem != TimestampSemantic.UNRESOLVED.value
        and tz_status != TimezoneStatus.NAIVE_UNRESOLVED.value
        and sidecar.get("timestamp_timezone") not in (None, "", "UNRESOLVED")
    )
    if not explicit_time:
        problems.append("time_contract_unresolved")

    verified = (
        not missing
        and hash_match
        and transform_ok
        and core_fields_nonempty
        and explicit_time
        and not problems
    )

    if verified:
        lineage = LineageStatus.VERIFIED.value
    elif sidecar:
        lineage = LineageStatus.PARTIAL.value
    else:
        lineage = LineageStatus.UNRESOLVED.value

    return {
        "lineage_status": lineage,
        "hash_match": hash_match,
        "timestamp_semantic": sem,
        "timestamp_timezone_status": tz_status,
        "timestamp_timezone": sidecar.get("timestamp_timezone", "UNRESOLVED"),
        "source_type": sidecar.get("source_type", "UNRESOLVED"),
        "source_identifier": sidecar.get("source_identifier", "UNRESOLVED"),
        "exporter_or_extraction_method": sidecar.get("exporter_or_extraction_method", "UNRESOLVED"),
        "exporter_path": sidecar.get("exporter_path", "UNRESOLVED"),
        "transform_chain": sidecar.get("transform_chain", []),
        "problems": sorted(set(problems)),
    }


@dataclass
class CanonicalManifest:
    dataset_id: str
    relative_path: str
    sha256: str
    size_bytes: int
    row_count: int
    columns: List[str]
    first_timestamp: Optional[str]
    last_timestamp: Optional[str]
    timestamp_column: Optional[str]
    timestamp_parse_status: str
    timestamp_timezone_status: str
    timestamp_timezone: str
    timestamp_semantic: str
    timeframe: str
    median_delta_minutes: Optional[float]
    pct_expected_cadence: Optional[float]
    duplicate_timestamp_count: int
    non_monotonic_timestamp_count: int
    ohlc_violation_count: int
    source_type: str
    source_identifier: str
    exporter_or_extraction_method: str
    exporter_path: str
    transform_chain: List[Any]
    lineage_status: str
    structural_validation_status: str
    research_eligibility: str
    blocking_reasons: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def decide_research_eligibility(
    *,
    structural_validation_status: str,
    timestamp_semantic: str,
    timestamp_timezone_status: str,
    lineage_status: str,
    source_type: str,
    source_identifier: str,
    exporter_or_extraction_method: str,
    transform_chain: Iterable[Any],
) -> Dict[str, Any]:
    reasons: List[str] = []

    if structural_validation_status != "PASS":
        reasons.append("STRUCTURAL_VALIDATION_NOT_PASS")
    if timestamp_semantic == TimestampSemantic.UNRESOLVED.value:
        reasons.append("TIMESTAMP_SEMANTIC_UNRESOLVED")
    if timestamp_timezone_status == TimezoneStatus.NAIVE_UNRESOLVED.value:
        reasons.append("TIMESTAMP_TIMEZONE_UNRESOLVED")
    if lineage_status != LineageStatus.VERIFIED.value:
        reasons.append("LINEAGE_NOT_VERIFIED")
    if source_type in (None, "", "UNRESOLVED"):
        reasons.append("SOURCE_TYPE_UNRESOLVED")
    if source_identifier in (None, "", "UNRESOLVED"):
        reasons.append("SOURCE_IDENTIFIER_UNRESOLVED")
    if exporter_or_extraction_method in (None, "", "UNRESOLVED"):
        reasons.append("EXTRACTION_METHOD_UNRESOLVED")
    if not list(transform_chain):
        reasons.append("TRANSFORM_CHAIN_UNRESOLVED")

    return {
        "research_eligibility": Eligibility.ELIGIBLE.value if not reasons else Eligibility.BLOCKED.value,
        "blocking_reasons": reasons,
        "fail_closed": True,
    }
