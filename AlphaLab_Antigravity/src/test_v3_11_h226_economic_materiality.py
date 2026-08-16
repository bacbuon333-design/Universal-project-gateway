from __future__ import annotations

import inspect
import numpy as np
import pandas as pd

import audit_v3_11_h226_economic_materiality as v311


def test_single_frozen_horizon_is_8h():
    assert v311.HORIZON == "8h"


def test_frozen_cohorts_and_decision_pair():
    assert v311.COHORTS == ("H226-C1", "H226-C2", "H226-C3", "H226-C4")
    assert v311.DECISION_COHORTS == ("H226-C1", "H226-C4")


def test_frozen_event_sha_and_counts():
    df, _ = v311.load_frozen_events()
    assert v311.sha256_file(v311.SRC_EVENTS) == v311.V39_EVENTS_SHA256
    assert df.groupby("cohort").size().to_dict() == v311.EXPECTED_8H_COUNTS


def test_v310_parent_conclusion_and_same_sample_closure_are_frozen():
    _, prior = v311.load_frozen_events()
    assert v311.V310_FINAL_SHA == "b387e25bdf6fd814c3034f3688af50e976f5cc59"
    assert prior["mechanism_label"] == "H226 DELAYED 8H REVERSION REGIME / DIRECTION DEPENDENT — STRATEGY DESIGN NOT AUTHORIZED"


def test_no_strategy_engine_or_raw_market_reconstruction():
    src = inspect.getsource(v311)
    assert "run_strategy(" not in src
    assert "CanonicalV2ExecutionEngine" not in src
    assert "GOLD_M30_CANONICAL_V2.csv" not in src
    assert "load_authorized_canonical_v2_dataframe" not in src


def test_cost_hurdle_formula_is_frozen():
    assert abs(v311.ROUNDTRIP_PRICE_EQUIV_USD_PER_OZ - 0.32) < 1e-12
    df, _ = v311.load_frozen_events()
    r = df.iloc[0]
    expected = 0.32 / float(r["atr_prev"])
    assert abs(float(r["cost_hurdle_atr"]) - expected) < 1e-12
    assert abs(float(r["excess_reversion_atr"]) - (float(r["signed_reversion_return_atr"]) - expected)) < 1e-12


def test_exact_33_quarter_contract():
    q = v311.complete_quarters()
    assert len(q) == 33 and q[0] == "2018Q2" and q[-1] == "2026Q2"


def test_bootstrap_contract_is_frozen():
    assert v311.QUARTER_BOOT_REPS == 5000
    assert v311.QUARTER_BOOT_SEED == 311226
    assert v311.YEAR_BOOT_REPS == 5000
    assert v311.YEAR_BOOT_SEED == 311227


def test_output_dimensions_from_frozen_source():
    df, _ = v311.load_frozen_events()
    assert len(v311.build_view_summary(df)) == 20
    assert len(v311.build_year_stability(df)) == 28
    assert len(v311.build_quarter_stability(df)) == 132
    assert len(v311.build_leave_one_year_out(df)) == 28


def test_bootstrap_dimension_is_exact_8_rows():
    df, _ = v311.load_frozen_events()
    out = v311.build_bootstrap(df)
    assert len(out) == 8
    assert set(out["block_type"]) == {"QUARTER", "YEAR"}


def _decision_frames(mode: str):
    views = []
    years = []
    loo = []
    boot = []
    for cohort in v311.COHORTS:
        for view in ("FULL", "PRE_2025", "RECENT", "UP_GAP", "DOWN_GAP"):
            mean = 0.10
            median = 0.05
            if mode == "immaterial" and cohort == "H226-C4" and view == "FULL":
                mean = -0.01
            if mode == "asymmetric" and cohort == "H226-C4" and view == "UP_GAP":
                mean = -0.02
            views.append({
                "cohort": cohort,
                "view": view,
                "event_count": 100,
                "mean_raw_reversion_atr": mean + 0.10,
                "mean_excess_reversion_atr": mean,
                "median_excess_reversion_atr": median,
                "positive_excess_pct": 55.0,
                "median_cost_hurdle_atr": 0.10,
                "worst5pct_mean_excess_atr": -1.0,
            })
        for year in v311.FULL_YEARS:
            years.append({"cohort": cohort, "year": year, "positive_mean_excess": True})
            loo.append({"cohort": cohort, "excluded_year": year, "positive_mean_excess": True})
        for block_type in ("QUARTER", "YEAR"):
            boot.append({"cohort": cohort, "block_type": block_type, "ci_2_5": 0.01, "ci_97_5": 0.20})
    return pd.DataFrame(views), pd.DataFrame(years), pd.DataFrame(loo), pd.DataFrame(boot)


def test_broad_materiality_requires_full_conjunction():
    v, y, l, b = _decision_frames("broad")
    d = v311.make_decision(v, y, l, b)
    assert d["mechanism_label"] == "H226 DELAYED 8H REVERSION BROADLY ECONOMICALLY MATERIAL — H226 STRATEGY CHAPTER CLOSED; FRESH OOS REQUIRED"


def test_asymmetric_label_when_pooled_positive_but_broad_fails():
    v, y, l, b = _decision_frames("asymmetric")
    d = v311.make_decision(v, y, l, b)
    assert d["mechanism_label"] == "H226 DELAYED 8H REVERSION ECONOMICALLY ASYMMETRIC / REGIME-CONCENTRATED — H226 STRATEGY CHAPTER CLOSED; FRESH OOS REQUIRED"


def test_immaterial_label_when_decision_cohort_full_mean_nonpositive():
    v, y, l, b = _decision_frames("immaterial")
    d = v311.make_decision(v, y, l, b)
    assert d["mechanism_label"] == "H226 DELAYED 8H REVERSION ECONOMICALLY IMMATERIAL — H226 CHAPTER CLOSED"


def test_all_labels_close_same_sample_h226_and_never_authorize_strategy():
    for mode in ("broad", "asymmetric", "immaterial"):
        v, y, l, b = _decision_frames(mode)
        d = v311.make_decision(v, y, l, b)
        assert d["h226_strategy_status_remains"] == "REJECTED"
        assert d["same_sample_h226_research_closed"] is True
        assert d["strategy_design_authorized"] is False


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for t in tests:
        t()
        print(f"PASS: {t.__name__}")
    print(f"All {len(tests)} V3.11 tests passed")
