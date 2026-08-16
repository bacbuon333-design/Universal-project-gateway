"""Unit tests for V3.7 canonical-data governance.

These tests deliberately distinguish structural integrity from provenance.
"""
from __future__ import annotations

from pathlib import Path
import json
import tempfile

import pandas as pd

from canonical_data_contract import (
    Eligibility,
    LineageStatus,
    TimestampSemantic,
    TimezoneStatus,
    decide_research_eligibility,
    sha256_file,
    validate_provenance_sidecar,
)
from audit_v3_7_canonical_data import analyze_structure


def _valid_sidecar(dataset_hash: str) -> dict:
    return {
        "dataset_sha256": dataset_hash,
        "source_type": "BROKER_EXPORT",
        "source_identifier": "EXAMPLE_SOURCE_ID",
        "exporter_or_extraction_method": "documented_exporter_v1",
        "exporter_path": "tools/export_example.py",
        "timestamp_semantic": "BAR_OPEN_TIME",
        "timestamp_timezone_status": "EXPLICIT_UTC",
        "timestamp_timezone": "UTC",
        "transform_chain": [
            {"step": 1, "operation": "source_export", "time_shift": "NONE"}
        ],
    }


def test_exact_hash_complete_sidecar_can_verify_lineage():
    sidecar = _valid_sidecar("abc123")
    out = validate_provenance_sidecar(sidecar, "abc123")
    assert out["lineage_status"] == LineageStatus.VERIFIED.value
    assert out["timestamp_semantic"] == TimestampSemantic.BAR_OPEN_TIME.value
    assert out["timestamp_timezone_status"] == TimezoneStatus.EXPLICIT_UTC.value
    assert out["problems"] == []


def test_hash_mismatch_cannot_verify_lineage():
    sidecar = _valid_sidecar("wrong")
    out = validate_provenance_sidecar(sidecar, "actual")
    assert out["lineage_status"] != LineageStatus.VERIFIED.value
    assert "dataset_sha256_mismatch_or_missing" in out["problems"]


def test_unresolved_timestamp_semantic_blocks_research():
    d = decide_research_eligibility(
        structural_validation_status="PASS",
        timestamp_semantic="UNRESOLVED",
        timestamp_timezone_status="EXPLICIT_UTC",
        lineage_status="VERIFIED",
        source_type="BROKER_EXPORT",
        source_identifier="SRC",
        exporter_or_extraction_method="exporter",
        transform_chain=[{"operation": "export"}],
    )
    assert d["research_eligibility"] == Eligibility.BLOCKED.value
    assert "TIMESTAMP_SEMANTIC_UNRESOLVED" in d["blocking_reasons"]


def test_naive_timezone_blocks_research():
    d = decide_research_eligibility(
        structural_validation_status="PASS",
        timestamp_semantic="BAR_OPEN_TIME",
        timestamp_timezone_status="NAIVE_UNRESOLVED",
        lineage_status="VERIFIED",
        source_type="BROKER_EXPORT",
        source_identifier="SRC",
        exporter_or_extraction_method="exporter",
        transform_chain=[{"operation": "export"}],
    )
    assert d["research_eligibility"] == Eligibility.BLOCKED.value
    assert "TIMESTAMP_TIMEZONE_UNRESOLVED" in d["blocking_reasons"]


def test_partial_lineage_blocks_research_even_when_ohlc_is_clean():
    d = decide_research_eligibility(
        structural_validation_status="PASS",
        timestamp_semantic="BAR_OPEN_TIME",
        timestamp_timezone_status="EXPLICIT_UTC",
        lineage_status="PARTIAL",
        source_type="BROKER_EXPORT",
        source_identifier="SRC",
        exporter_or_extraction_method="exporter",
        transform_chain=[{"operation": "export"}],
    )
    assert d["research_eligibility"] == Eligibility.BLOCKED.value
    assert "LINEAGE_NOT_VERIFIED" in d["blocking_reasons"]


def test_complete_verified_contract_can_be_eligible():
    d = decide_research_eligibility(
        structural_validation_status="PASS",
        timestamp_semantic="BAR_CLOSE_TIME",
        timestamp_timezone_status="EXPLICIT_OFFSET",
        lineage_status="VERIFIED",
        source_type="VENUE_EXPORT",
        source_identifier="SRC",
        exporter_or_extraction_method="exporter",
        transform_chain=[{"operation": "export"}],
    )
    assert d["research_eligibility"] == Eligibility.ELIGIBLE.value
    assert d["blocking_reasons"] == []


def _write_csv(path: Path, rows: list[dict]) -> None:
    pd.DataFrame(rows).to_csv(path, index=False)


def test_structural_clean_m30_does_not_itself_prove_time_semantics():
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "bars.csv"
        _write_csv(
            p,
            [
                {"datetime_str": "2026-01-01 08:00:00", "open": 100, "high": 102, "low": 99, "close": 101},
                {"datetime_str": "2026-01-01 08:30:00", "open": 101, "high": 103, "low": 100, "close": 102},
                {"datetime_str": "2026-01-01 09:00:00", "open": 102, "high": 104, "low": 101, "close": 103},
            ],
        )
        out = analyze_structure(p)
        assert out["structural_validation_status"] == "PASS"
        assert out["median_delta_minutes"] == 30.0
        assert out["pct_expected_cadence"] == 100.0
        assert out["timestamp_timezone_status_from_csv"] == "NAIVE_UNRESOLVED"


def test_structural_duplicate_timestamp_fails():
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "bars.csv"
        _write_csv(
            p,
            [
                {"datetime_str": "2026-01-01 08:00:00", "open": 100, "high": 102, "low": 99, "close": 101},
                {"datetime_str": "2026-01-01 08:00:00", "open": 101, "high": 103, "low": 100, "close": 102},
            ],
        )
        out = analyze_structure(p)
        assert out["structural_validation_status"] == "FAIL"
        assert out["duplicate_timestamp_count"] == 1


def test_structural_ohlc_violation_fails():
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "bars.csv"
        _write_csv(
            p,
            [
                {"datetime_str": "2026-01-01 08:00:00", "open": 100, "high": 99, "low": 98, "close": 101},
                {"datetime_str": "2026-01-01 08:30:00", "open": 101, "high": 103, "low": 100, "close": 102},
            ],
        )
        out = analyze_structure(p)
        assert out["structural_validation_status"] == "FAIL"
        assert out["ohlc_violation_count"] > 0


def test_sha256_is_deterministic():
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "x.txt"
        p.write_text("canonical-data\n", encoding="utf-8")
        assert sha256_file(p) == sha256_file(p)


if __name__ == "__main__":
    tests = [
        test_exact_hash_complete_sidecar_can_verify_lineage,
        test_hash_mismatch_cannot_verify_lineage,
        test_unresolved_timestamp_semantic_blocks_research,
        test_naive_timezone_blocks_research,
        test_partial_lineage_blocks_research_even_when_ohlc_is_clean,
        test_complete_verified_contract_can_be_eligible,
        test_structural_clean_m30_does_not_itself_prove_time_semantics,
        test_structural_duplicate_timestamp_fails,
        test_structural_ohlc_violation_fails,
        test_sha256_is_deterministic,
    ]
    for fn in tests:
        fn()
        print(f"PASS: {fn.__name__}")
    print(f"All {len(tests)} tests passed.")
