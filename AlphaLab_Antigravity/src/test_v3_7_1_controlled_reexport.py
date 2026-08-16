"""Unit tests for V3.7.1 controlled canonical re-export governance."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import tempfile

import pandas as pd

import export_v3_7_1_mt5_canonical_gold_m30 as ex
from canonical_data_contract import validate_provenance_sidecar

UTC = timezone.utc


def sample_rates():
    base = int(datetime(2026, 1, 2, 8, 0, tzinfo=UTC).timestamp())
    return [
        {
            "time": base,
            "open": 2000.0,
            "high": 2002.0,
            "low": 1999.0,
            "close": 2001.0,
            "tick_volume": 100,
            "spread": 25,
            "real_volume": 0,
        },
        {
            "time": base + 1800,
            "open": 2001.0,
            "high": 2003.0,
            "low": 2000.0,
            "close": 2002.0,
            "tick_volume": 120,
            "spread": 25,
            "real_volume": 0,
        },
        {
            "time": base + 3600,
            "open": 2002.0,
            "high": 2004.0,
            "low": 2001.0,
            "close": 2003.0,
            "tick_volume": 130,
            "spread": 25,
            "real_volume": 0,
        },
    ]


def test_last_completed_bar_excludes_current_forming_bar():
    now = datetime(2026, 8, 16, 6, 43, 12, tzinfo=UTC)
    assert ex.last_completed_m30_open(now) == datetime(2026, 8, 16, 6, 0, tzinfo=UTC)


def test_exact_boundary_still_returns_prior_completed_bar():
    now = datetime(2026, 8, 16, 6, 30, 0, tzinfo=UTC)
    assert ex.last_completed_m30_open(now) == datetime(2026, 8, 16, 6, 0, tzinfo=UTC)


def test_normalize_rates_sorts_and_emits_explicit_utc_timestamp():
    rates = list(reversed(sample_rates()))
    df = ex.normalize_rates(rates)
    assert list(df.columns) == ex.CANONICAL_COLUMNS
    assert df["time"].is_monotonic_increasing
    assert df.iloc[0]["timestamp_utc"].endswith("Z")
    assert df.iloc[0]["timestamp_utc"] == "2026-01-02T08:00:00Z"


def test_duplicate_epoch_is_rejected():
    rates = sample_rates()
    rates.append(dict(rates[0]))
    try:
        ex.normalize_rates(rates)
    except ValueError as exc:
        assert "Duplicate raw epoch timestamp" in str(exc)
    else:
        raise AssertionError("duplicate epoch must be rejected")


def test_structural_clean_m30_passes():
    df = ex.normalize_rates(sample_rates())
    end = datetime(2026, 1, 2, 9, 0, tzinfo=UTC)
    out = ex.structural_audit(df, end)
    assert out["status"] == "PASS"
    assert out["median_delta_minutes"] == 30.0
    assert out["ohlc"]["total_violation_count"] == 0


def test_structural_invalid_ohlc_fails():
    rates = sample_rates()
    rates[1]["high"] = 1990.0
    df = ex.normalize_rates(rates)
    end = datetime(2026, 1, 2, 9, 0, tzinfo=UTC)
    out = ex.structural_audit(df, end)
    assert out["status"] == "FAIL"
    assert "OHLC_VALIDATION_FAILED" in out["problems"]


def test_structural_bar_after_requested_end_fails():
    df = ex.normalize_rates(sample_rates())
    end = datetime(2026, 1, 2, 8, 30, tzinfo=UTC)
    out = ex.structural_audit(df, end)
    assert out["status"] == "FAIL"
    assert "BAR_AFTER_REQUESTED_LAST_COMPLETED_OPEN" in out["problems"]


def test_coverage_requires_2018q2_history():
    df = ex.normalize_rates(sample_rates())
    out = ex.coverage_audit(df, datetime(2026, 1, 2, 9, 0, tzinfo=UTC))
    assert out["status"] == "FAIL"
    assert "HISTORY_DOES_NOT_COVER_2018Q2_START" in out["reasons"]


def test_coverage_accepts_market_closure_lag_under_five_days():
    first = int(datetime(2018, 3, 30, 0, 0, tzinfo=UTC).timestamp())
    last = int(datetime(2026, 8, 14, 20, 0, tzinfo=UTC).timestamp())
    rates = [
        {"time": first, "open": 1.0, "high": 1.1, "low": 0.9, "close": 1.0, "tick_volume": 1, "spread": 1, "real_volume": 0},
        {"time": last, "open": 1.0, "high": 1.1, "low": 0.9, "close": 1.0, "tick_volume": 1, "spread": 1, "real_volume": 0},
    ]
    df = pd.DataFrame(rates)
    df.insert(1, "timestamp_utc", pd.to_datetime(df["time"], unit="s", utc=True).dt.strftime("%Y-%m-%dT%H:%M:%SZ"))
    df = df[ex.CANONICAL_COLUMNS]
    out = ex.coverage_audit(df, datetime(2026, 8, 16, 6, 0, tzinfo=UTC))
    assert out["status"] == "PASS"


def test_exact_hash_sidecar_with_open_utc_contract_verifies():
    sidecar = {
        "dataset_sha256": "abc",
        "source_type": "METATRADER5_TERMINAL_BROKER_FEED",
        "source_identifier": "broker=X|server=Y|symbol=GOLD",
        "exporter_or_extraction_method": "MetaTrader5.copy_rates_range",
        "timestamp_semantic": "BAR_OPEN_TIME",
        "timestamp_timezone_status": "EXPLICIT_UTC",
        "timestamp_timezone": "UTC",
        "transform_chain": ["extract", "serialize", "hash"],
    }
    result = validate_provenance_sidecar(sidecar, "abc")
    assert result["lineage_status"] == "VERIFIED"
    assert result["timestamp_semantic"] == "BAR_OPEN_TIME"
    assert result["timestamp_timezone_status"] == "EXPLICIT_UTC"


def test_wrong_hash_sidecar_cannot_verify():
    sidecar = {
        "dataset_sha256": "wrong",
        "source_type": "METATRADER5_TERMINAL_BROKER_FEED",
        "source_identifier": "broker=X|server=Y|symbol=GOLD",
        "exporter_or_extraction_method": "MetaTrader5.copy_rates_range",
        "timestamp_semantic": "BAR_OPEN_TIME",
        "timestamp_timezone_status": "EXPLICIT_UTC",
        "timestamp_timezone": "UTC",
        "transform_chain": ["extract", "serialize", "hash"],
    }
    result = validate_provenance_sidecar(sidecar, "actual")
    assert result["lineage_status"] != "VERIFIED"


def test_deterministic_csv_serialization_same_input_same_hash():
    df = ex.normalize_rates(sample_rates())
    with tempfile.TemporaryDirectory() as td:
        p1 = Path(td) / "a.csv"
        p2 = Path(td) / "b.csv"
        ex.deterministic_csv_write(df, p1)
        ex.deterministic_csv_write(df, p2)
        assert p1.read_bytes() == p2.read_bytes()
        assert ex.sha256_file(p1) == ex.sha256_file(p2)


def test_exporter_contract_has_no_silent_symbol_fallback():
    # The frozen public function accepts exactly the caller-supplied symbol.
    # There is deliberately no GOLD/XAUUSD fallback list in the exporter.
    assert not hasattr(ex, "SYMBOL_CANDIDATES")


def test_official_contract_is_open_time_and_utc():
    assert ex.TimestampSemantic.BAR_OPEN_TIME.value == "BAR_OPEN_TIME"
    assert ex.TimezoneStatus.EXPLICIT_UTC.value == "EXPLICIT_UTC"
    joined = " ".join(x["contract"] for x in ex.OFFICIAL_DOC_REFERENCES)
    assert "open time" in joined.lower()
    assert "utc" in joined.lower()


if __name__ == "__main__":
    tests = [name for name, obj in sorted(globals().items()) if name.startswith("test_") and callable(obj)]
    for name in tests:
        globals()[name]()
        print(f"PASS: {name}")
    print(f"\nAll {len(tests)} tests passed successfully!")
