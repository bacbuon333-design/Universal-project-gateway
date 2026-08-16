from __future__ import annotations

import inspect

import numpy as np
import pandas as pd

import audit_v3_9_loss_tail_and_h226_event as v39
from canonical_v2_research_engine import verify_canonical_v2_authorization


def test_canonical_v2_authority_is_frozen():
    a = verify_canonical_v2_authorization()
    assert a["dataset_id"] == "GOLD_M30_CANONICAL_V2"
    assert a["dataset_sha256"] == v39.FROZEN_SHA256
    assert a["research_eligibility"] == "ELIGIBLE"


def test_no_trading_engine_execution_path():
    src = inspect.getsource(v39)
    assert "run_strategy(" not in src
    assert "CanonicalV2ExecutionEngine" not in src


def test_exact_eval_quarter_contract():
    q = v39.complete_quarters()
    assert len(q) == 33
    assert q[0] == "2018Q2"
    assert q[-1] == "2026Q2"


def test_exact_horizon_contract():
    assert v39.HORIZONS == {"30m": 1, "1h": 2, "2h": 4, "4h": 8, "8h": 16}


def test_exact_h226_frozen_cohorts():
    assert v39.COHORTS == {
        "H226-C1": (0.05, 0.25),
        "H226-C2": (0.10, 0.25),
        "H226-C3": (0.05, 0.50),
        "H226-C4": (0.10, 0.50),
    }


def test_bootstrap_contract_is_frozen():
    assert v39.BOOTSTRAP_REPS == 2000
    assert v39.BOOTSTRAP_SEED == 390226
    assert v39.KEY_BOOT_HORIZONS == ("1h", "2h", "4h", "8h")


def test_negative_pool_share_uses_absolute_negative_pool():
    x = np.array([10.0, 20.0, 70.0])
    assert abs(v39._pool_share(x, 1) - 70.0) < 1e-12
    assert abs(v39._pool_share(x, 2) - 90.0) < 1e-12


def test_trade_tail_share_uses_loss_pool():
    x = np.arange(1.0, 101.0)
    # Worst 1% is the single largest loss, 100 / sum(1..100).
    expected = 100.0 / x.sum() * 100.0
    assert abs(v39._tail_share(x, 0.01) - expected) < 1e-12


def test_real_v38_loss_audit_has_exact_24_rejected_configs():
    out = v39.audit_loss_concentration()
    assert len(out) == 24
    assert set(out["v38_final_status_frozen"]) == {"REJECTED"}
    assert set(["H226-C1", "H226-C2", "H226-C3", "H226-C4"]).issubset(set(out["config_id"]))


def _decision_frames(mode: str):
    summary_rows = []
    boot_rows = []
    year_rows = []
    for cohort in v39.COHORTS:
        for h in ("2h", "4h"):
            if mode == "supported":
                mean, median, lo = 0.20, 0.10, 0.02
            elif mode == "weak":
                mean, median, lo = 0.10, -0.02, -0.05
            else:
                mean, median, lo = -0.10, -0.05, -0.20
            summary_rows.append({
                "cohort": cohort,
                "horizon": h,
                "mean_signed_reversion_atr": mean,
                "median_signed_reversion_atr": median,
                "gap_closure_pct": 60.0,
                "worst5pct_mean_signed_reversion_atr": -1.0,
            })
            boot_rows.append({
                "cohort": cohort,
                "horizon": h,
                "ci_2_5": lo,
                "ci_97_5": 0.40,
            })
        for year in v39.FULL_YEARS:
            positive = mode != "not_supported" and year <= 2022
            year_rows.append({
                "cohort": cohort,
                "horizon": "4h",
                "year": year,
                "positive_mean": positive,
            })
    return pd.DataFrame(summary_rows), pd.DataFrame(year_rows), pd.DataFrame(boot_rows)


def test_mechanism_decision_supported_requires_full_conjunction():
    s, y, b = _decision_frames("supported")
    d = v39.mechanism_decision(s, y, b)
    assert d["mechanism_label"] == "H226 GAP-REVERSION MECHANISM DESCRIPTIVELY SUPPORTED — STRATEGY STILL REJECTED"
    assert d["strategy_redesign_authorized"] is False


def test_mechanism_decision_weak_when_means_positive_but_inference_fails():
    s, y, b = _decision_frames("weak")
    d = v39.mechanism_decision(s, y, b)
    assert d["mechanism_label"] == "H226 GAP-REVERSION MECHANISM WEAK / TAIL-UNSTABLE — STRATEGY STILL REJECTED"


def test_mechanism_decision_not_supported_when_c1_c4_means_not_positive():
    s, y, b = _decision_frames("not_supported")
    d = v39.mechanism_decision(s, y, b)
    assert d["mechanism_label"] == "H226 GAP-REVERSION MECHANISM NOT SUPPORTED — STRATEGY REJECTED"


def test_decision_cohorts_are_pre_frozen_c1_and_c4():
    s, y, b = _decision_frames("weak")
    d = v39.mechanism_decision(s, y, b)
    assert d["decision_cohorts_frozen_pre_result"] == ["H226-C1", "H226-C4"]


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for t in tests:
        t()
        print(f"PASS: {t.__name__}")
    print(f"All {len(tests)} V3.9 tests passed")
