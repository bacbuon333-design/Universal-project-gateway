from __future__ import annotations

import inspect
import numpy as np
import pandas as pd

import audit_v3_10_h226_delayed_reversion as v310


def test_single_frozen_horizon_is_8h():
    assert v310.HORIZON == "8h"


def test_frozen_cohorts_and_decision_pair():
    assert v310.COHORTS == ("H226-C1", "H226-C2", "H226-C3", "H226-C4")
    assert v310.DECISION_COHORTS == ("H226-C1", "H226-C4")


def test_exact_33_quarter_contract():
    q = v310.complete_quarters()
    assert len(q) == 33
    assert q[0] == "2018Q2" and q[-1] == "2026Q2"


def test_bootstrap_contract_is_frozen():
    assert v310.QUARTER_BOOT_REPS == 5000
    assert v310.QUARTER_BOOT_SEED == 310226
    assert v310.YEAR_BOOT_REPS == 5000
    assert v310.YEAR_BOOT_SEED == 310227


def test_cost_scale_contract_is_diagnostic_only():
    assert abs(v310.ROUNDTRIP_PRICE_EQUIV_USD_PER_OZ - 0.32) < 1e-12
    src = inspect.getsource(v310.make_decision)
    assert "median_cost_hurdle_atr" not in src
    assert "mean_to_median_cost_hurdle_ratio" not in src


def test_no_trading_engine_or_raw_market_reconstruction_path():
    src = inspect.getsource(v310)
    assert "run_strategy(" not in src
    assert "CanonicalV2ExecutionEngine" not in src
    assert "load_authorized_canonical_v2_dataframe" not in src
    assert "GOLD_M30_CANONICAL_V2.csv" not in src


def test_real_v39_source_verifies_and_8h_events_have_four_cohorts():
    df, source = v310.load_frozen_8h_events()
    assert source["metadata"]["artifact_generation_parent_sha"] == v310.V39_FROZEN_CODE_HEAD
    assert source["metadata"]["canonical_dataset_sha256"] == v310.CANONICAL_SHA
    assert set(df["cohort"].unique()) == set(v310.COHORTS)
    assert set(df["horizon"].astype(str).unique()) == {"8h"}


def test_view_summary_has_exact_24_rows():
    df, _ = v310.load_frozen_8h_events()
    out = v310.build_view_summary(df)
    assert len(out) == 24
    assert set(out["view"]) == {"FULL", "PRE_2025", "RECENT", "UP_GAP", "DOWN_GAP", "LEAVE_2025_2026_OUT"}


def test_year_stability_has_exact_28_rows():
    df, _ = v310.load_frozen_8h_events()
    out = v310.build_year_stability(df)
    assert len(out) == 28
    assert set(out["year"]) == set(v310.FULL_YEARS)


def test_quarter_stability_has_exact_132_rows():
    df, _ = v310.load_frozen_8h_events()
    out = v310.build_quarter_stability(df)
    assert len(out) == 132
    assert set(out["quarter"]) == set(v310.complete_quarters())


def test_leave_one_year_out_has_exact_28_rows():
    df, _ = v310.load_frozen_8h_events()
    out = v310.build_leave_one_year_out(df)
    assert len(out) == 28
    assert set(out["excluded_year"]) == set(v310.FULL_YEARS)


def _decision_frames(mode: str):
    view_rows = []
    year_rows = []
    loo_rows = []
    boot_rows = []
    for cohort in v310.COHORTS:
        for view in ("FULL", "PRE_2025", "RECENT", "UP_GAP", "DOWN_GAP", "LEAVE_2025_2026_OUT"):
            mean = 0.10
            median = 0.05
            if mode == "not_supported" and cohort == "H226-C4" and view == "FULL":
                mean = -0.02
            if mode == "regime" and cohort == "H226-C4" and view == "RECENT":
                mean = -0.02
            view_rows.append({
                "cohort": cohort, "view": view, "event_count": 100,
                "mean_signed_reversion_atr": mean, "median_signed_reversion_atr": median,
            })
        for year in v310.FULL_YEARS:
            year_rows.append({"cohort": cohort, "year": year, "positive_mean": True})
            loo_rows.append({"cohort": cohort, "excluded_year": year, "positive_mean": True})
        for block_type in ("QUARTER", "YEAR"):
            lo = 0.01
            if mode == "regime" and cohort == "H226-C1" and block_type == "YEAR":
                lo = -0.01
            boot_rows.append({"cohort": cohort, "block_type": block_type, "ci_2_5": lo, "ci_97_5": 0.20})
    return pd.DataFrame(view_rows), pd.DataFrame(year_rows), pd.DataFrame(loo_rows), pd.DataFrame(boot_rows)


def test_robust_decision_requires_full_conjunction():
    v, y, l, b = _decision_frames("robust")
    d = v310.make_decision(v, y, l, b)
    assert d["mechanism_label"] == "H226 DELAYED 8H REVERSION ROBUSTLY SUPPORTED — STRATEGY DESIGN NOT AUTHORIZED"
    assert d["strategy_design_authorized"] is False


def test_regime_dependent_label_when_pooled_means_positive_but_robustness_fails():
    v, y, l, b = _decision_frames("regime")
    d = v310.make_decision(v, y, l, b)
    assert d["mechanism_label"] == "H226 DELAYED 8H REVERSION REGIME / DIRECTION DEPENDENT — STRATEGY DESIGN NOT AUTHORIZED"


def test_not_supported_when_one_decision_cohort_full_mean_nonpositive():
    v, y, l, b = _decision_frames("not_supported")
    d = v310.make_decision(v, y, l, b)
    assert d["mechanism_label"] == "H226 DELAYED 8H REVERSION NOT SUPPORTED — H226 CHAPTER CLOSED"


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for t in tests:
        t()
        print(f"PASS: {t.__name__}")
    print(f"All {len(tests)} V3.10 tests passed")
