from __future__ import annotations

import inspect

import pandas as pd

import audit_v3_12_fresh_oos_readiness as audit
import fresh_oos_v312_contract as v312


def test_frozen_cutoff_and_first_decision_quarter():
    assert v312.CANONICAL_FREEZE_CUTOFF == pd.Timestamp("2026-08-14T23:30:00Z")
    assert v312.BRIDGE_QUARTER == "2026Q3"
    assert v312.FIRST_DECISION_QUARTER == "2026Q4"


def test_canonical_authority_is_frozen():
    out = v312.verify_frozen_canonical_cutoff()
    assert out["dataset_sha256"] == v312.CANONICAL_SHA256
    assert out["last_bar_open_utc"] == v312.CANONICAL_FREEZE_CUTOFF.isoformat()


def test_maturity_thresholds_are_frozen():
    assert v312.MIN_COMPLETE_QUARTERS == 8
    assert v312.MIN_C1_EVENTS == 160
    assert v312.MIN_C4_EVENTS == 100
    assert v312.MIN_C1_PER_QUARTER == 10
    assert v312.MIN_C4_PER_QUARTER == 5


def test_no_complete_decision_quarter_before_2026q4_closes():
    assert v312.complete_decision_quarters(pd.Timestamp("2026-12-15T00:00:00Z")) == []


def test_eight_complete_quarters_at_2028q4_start():
    q = v312.complete_decision_quarters(pd.Timestamp("2028-10-01T00:00:00Z"))
    assert q == [
        "2026Q4", "2027Q1", "2027Q2", "2027Q3", "2027Q4",
        "2028Q1", "2028Q2", "2028Q3",
    ]


def test_waiting_status_when_no_fresh_bars():
    empty = pd.DataFrame(columns=["quarter", "c1_events", "c4_events"])
    a = v312.assess_maturity(empty, pd.Timestamp("2026-08-16T10:00:00Z"), has_fresh_bars=False)
    assert a.status == v312.WAITING
    assert not any(a.checks.values())


def test_accruing_when_complete_quarters_are_insufficient():
    counts = pd.DataFrame([
        {"quarter": "2026Q4", "c1_events": 1000, "c4_events": 1000},
    ])
    a = v312.assess_maturity(counts, pd.Timestamp("2027-04-01T00:00:00Z"), has_fresh_bars=True)
    assert a.status == v312.ACCRUING
    assert a.checks["eight_complete_quarters"] is False


def test_maturity_requires_full_conjunction():
    quarters = v312.complete_decision_quarters(pd.Timestamp("2028-10-01T00:00:00Z"))
    counts = pd.DataFrame([
        {"quarter": q, "c1_events": 20, "c4_events": 13} for q in quarters
    ])
    a = v312.assess_maturity(counts, pd.Timestamp("2028-10-01T00:00:00Z"), has_fresh_bars=True)
    assert a.status == v312.MATURE
    assert all(a.checks.values())
    assert a.c1_total == 160
    assert a.c4_total == 104


def test_large_totals_cannot_hide_a_quiet_complete_quarter():
    quarters = v312.complete_decision_quarters(pd.Timestamp("2028-10-01T00:00:00Z"))
    rows = [{"quarter": q, "c1_events": 30, "c4_events": 20} for q in quarters]
    rows[-1]["c1_events"] = 0
    rows[-1]["c4_events"] = 0
    a = v312.assess_maturity(pd.DataFrame(rows), pd.Timestamp("2028-10-01T00:00:00Z"), has_fresh_bars=True)
    assert a.c1_total >= v312.MIN_C1_EVENTS
    assert a.c4_total >= v312.MIN_C4_EVENTS
    assert a.checks["c1_each_quarter_min"] is False
    assert a.checks["c4_each_quarter_min"] is False
    assert a.status == v312.ACCRUING


def test_temporal_partition_rejects_backfill_at_cutoff():
    df = pd.DataFrame({
        "timestamp_utc": [v312.CANONICAL_FREEZE_CUTOFF.isoformat(), "2026-08-15T00:00:00Z"],
        "open": [1.0, 1.0], "high": [1.0, 1.0], "low": [1.0, 1.0], "close": [1.0, 1.0],
    })
    try:
        v312.validate_oos_temporal_partition(df)
    except RuntimeError as exc:
        assert "overlap/backfill" in str(exc)
    else:
        raise AssertionError("Backfill at canonical cutoff must be rejected")


def test_readiness_counter_output_contains_only_counts():
    canonical = pd.DataFrame({
        "timestamp_utc": pd.date_range("2026-08-10", periods=200, freq="30min", tz="UTC").astype(str),
        "open": 100.0, "high": 101.0, "low": 99.0, "close": 100.0,
    })
    fresh = pd.DataFrame({
        "timestamp_utc": pd.date_range("2026-10-01", periods=100, freq="30min", tz="UTC").astype(str),
        "open": 100.0, "high": 101.0, "low": 99.0, "close": 100.0,
    })
    out = v312.count_readiness_events(canonical, fresh)
    assert list(out.columns) == ["quarter", "c1_events", "c4_events"]


def test_readiness_auditor_contains_no_outcome_evaluation_tokens():
    src = inspect.getsource(audit)
    for token in v312.forbidden_outcome_tokens():
        assert token not in src
    assert "run_strategy(" not in src
    assert "CanonicalV2ExecutionEngine" not in src


def test_readiness_metadata_hardcodes_no_strategy_authorization():
    src = inspect.getsource(audit.run_readiness_audit)
    assert '"outcome_metrics_computed": False' in src
    assert '"trading_engine_called": False' in src
    assert '"strategy_executed": False' in src
    assert '"strategy_design_authorized": False' in src
    assert '"same_sample_h226_research_closed": True' in src


def test_v311_parent_and_closure_are_frozen_in_auditor():
    src = inspect.getsource(audit.run_readiness_audit)
    assert "b821248667badea5e763173101c52ef95dbcf5d4" in src
    assert v312.FIRST_DECISION_QUARTER == "2026Q4"


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for t in tests:
        t()
        print(f"PASS: {t.__name__}")
    print(f"All {len(tests)} V3.12 tests passed")
