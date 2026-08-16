from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pandas as pd

import canonical_research_engine as cre


def _adapter_prepare(df: pd.DataFrame) -> pd.DataFrame:
    obj = object.__new__(cre.CanonicalDeepQuantEngine)
    return cre.CanonicalDeepQuantEngine._prepare_dataframe(obj, df)


def _sample_ohlc(n: int = 2) -> dict:
    return {
        "open": [100.0] * n,
        "high": [101.0] * n,
        "low": [99.0] * n,
        "close": [100.5] * n,
    }


def test_real_canonical_authorization_passes():
    a = cre.verify_canonical_authorization()
    assert a["dataset_sha256"] == cre.FROZEN_SHA256
    assert a["timestamp_semantic"] == "BAR_OPEN_TIME"
    assert a["timestamp_timezone"] == "UTC"
    assert a["research_eligibility"] == "ELIGIBLE"


def test_timestamp_utc_has_priority_over_numeric_time():
    df = pd.DataFrame({
        "time": [1, 2],
        "timestamp_utc": ["2020-01-01T00:00:00+00:00", "2020-01-01T00:30:00+00:00"],
        **_sample_ohlc(),
    })
    out = _adapter_prepare(df)
    assert out["datetime"].iloc[0].year == 2020
    assert str(out["datetime"].dt.tz) == "UTC"


def test_numeric_time_fallback_is_unix_seconds_not_nanoseconds():
    df = pd.DataFrame({
        "time": [1577836800, 1577838600],
        **_sample_ohlc(),
    })
    out = _adapter_prepare(df)
    assert out["datetime"].iloc[0].isoformat() == "2020-01-01T00:00:00+00:00"
    assert out["datetime"].iloc[1].isoformat() == "2020-01-01T00:30:00+00:00"


def test_legacy_datetime_str_behavior_remains_calendar_correct():
    df = pd.DataFrame({
        "datetime_str": ["2020-01-01 00:00:00", "2020-01-01 00:30:00"],
        **_sample_ohlc(),
    })
    out = _adapter_prepare(df)
    assert out["datetime"].iloc[0] == pd.Timestamp("2020-01-01 00:00:00")
    assert out["quarter"].iloc[0] == "2020Q1"


def test_wrong_csv_hash_is_blocked():
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "bad.csv"
        p.write_bytes(cre.CANONICAL_CSV.read_bytes() + b"\n")
        try:
            cre.verify_canonical_authorization(csv_path=p)
            raise AssertionError("hash mismatch should block")
        except RuntimeError as e:
            assert "SHA mismatch" in str(e)


def test_blocked_decision_is_blocked():
    with tempfile.TemporaryDirectory() as td:
        d = json.loads(cre.DECISION_JSON.read_text(encoding="utf-8"))
        d["research_eligibility"] = "BLOCKED"
        p = Path(td) / "decision.json"
        p.write_text(json.dumps(d), encoding="utf-8")
        try:
            cre.verify_canonical_authorization(decision_path=p)
            raise AssertionError("blocked decision should block")
        except RuntimeError as e:
            assert "decision.eligibility" in str(e)


def test_manifest_semantic_mismatch_is_blocked():
    with tempfile.TemporaryDirectory() as td:
        m = json.loads(cre.MANIFEST_JSON.read_text(encoding="utf-8"))
        m["timestamp_semantic"] = "BAR_CLOSE_TIME"
        p = Path(td) / "manifest.json"
        p.write_text(json.dumps(m), encoding="utf-8")
        try:
            cre.verify_canonical_authorization(manifest_path=p)
            raise AssertionError("semantic mismatch should block")
        except RuntimeError as e:
            assert "manifest.timestamp_semantic" in str(e)


def test_real_canonical_engine_calendar_is_not_1970():
    snap = cre.canonical_engine_compatibility_snapshot()
    assert snap["min_year"] == 2018
    assert snap["max_year"] == 2026
    assert snap["first_datetime"].startswith("2018-02-22T18:30:00")
    assert snap["last_datetime"].startswith("2026-08-14T23:30:00")


def test_real_canonical_engine_contains_frozen_research_boundary_quarters():
    snap = cre.canonical_engine_compatibility_snapshot()
    assert snap["contains_2018Q2"] is True
    assert snap["contains_2026Q2"] is True


def test_real_canonical_engine_resolves_gold_economics():
    snap = cre.canonical_engine_compatibility_snapshot()
    assert snap["instrument_symbol"] == "GOLD"
    assert snap["instrument_asset_class"] == "COMMODITY"


def test_loader_preserves_row_count_and_ohlc_columns():
    df, _ = cre.load_authorized_canonical_dataframe()
    assert len(df) == 100000
    assert {"open", "high", "low", "close"}.issubset(df.columns)


def test_no_strategy_execution_in_compatibility_snapshot():
    # The compatibility path constructs the engine and inspects its prepared
    # dataframe only. It does not call run_strategy.
    assert "run_strategy" not in cre.canonical_engine_compatibility_snapshot.__code__.co_names


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for t in tests:
        t()
        print(f"PASS: {t.__name__}")
    print(f"All {len(tests)} V3.7.2 tests passed")
