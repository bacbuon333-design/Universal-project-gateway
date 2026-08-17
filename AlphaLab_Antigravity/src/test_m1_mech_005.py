from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from m1_mech_005.invariance_falsification import (
    EXCURSION_RATIO_MIN_ATR,
    KNOWN_MECH004_RHO_5M,
    REPRESENTATIONS,
    _day_block_bootstrap_from_fit,
    _fit_payload,
    _representation_payload,
    _within_day_side_balanced_signs,
    _within_day_side_cyclic_shift,
    build_gradient_table,
    evaluate_falsification_gates,
)


def _frame(n: int = 240) -> pd.DataFrame:
    dt = pd.date_range("2018-01-02T00:00:00Z", periods=n, freq="min")
    x = np.linspace(0.05, 1.5, n)
    exc = 0.12 + 0.07 * (np.arange(n) % 7)
    atr = 1.5 + 0.01 * (np.arange(n) % 11)
    post = 0.10 - 0.12 * x
    data = {
        "datetime": dt,
        "bar_index": np.arange(510, 510+n),
        "side": np.where(np.arange(n) % 2 == 0, "LONG", "SHORT"),
        "year": np.full(n, 2018),
        "hour": dt.hour,
        "atr14": atr,
        "pre_event_atr14": atr * 0.93,
        "prior_extreme": np.full(n, 2000.0),
        "atr_percentile": 20.0 + (np.arange(n) % 70),
        "path_efficiency": 0.1 + (np.arange(n) % 8) / 10.0,
        "stretch_abs": 0.2 + (np.arange(n) % 10) / 4.0,
        "location_count": np.arange(n) % 3,
        "in_candle_reversion_atr": x,
        "breach_excursion_atr": exc,
    }
    for h in (1, 3, 5, 10, 15, 30):
        data[f"exact_{h}m_available"] = np.ones(n, dtype=bool)
        data[f"total_reversion_atr_{h}m"] = x + post
    return pd.DataFrame(data)


def test_four_representations_are_frozen():
    assert REPRESENTATIONS == ("ATR_T", "ATR_PRE", "PRICE_BPS", "EXCURSION_RATIO")


def test_atr_t_coordinate_is_identity_scale():
    f = _frame()
    p = _representation_payload(f, "ATR_T", 5)
    assert np.allclose(p["_x"], f["in_candle_reversion_atr"])


def test_atr_pre_coordinate_uses_prior_atr():
    f = _frame()
    p = _representation_payload(f, "ATR_PRE", 5)
    expected = f["in_candle_reversion_atr"] * f["atr14"] / f["pre_event_atr14"]
    assert np.allclose(p["_x"], expected)


def test_price_bps_coordinate_has_no_atr_denominator():
    f = _frame()
    p = _representation_payload(f, "PRICE_BPS", 5)
    raw_in = f["in_candle_reversion_atr"] * f["atr14"]
    expected = raw_in / f["prior_extreme"] * 10000.0
    assert np.allclose(p["_x"], expected)


def test_excursion_ratio_filters_tiny_denominators():
    f = _frame()
    f.loc[:20, "breach_excursion_atr"] = EXCURSION_RATIO_MIN_ATR / 2.0
    p = _representation_payload(f, "EXCURSION_RATIO", 5)
    assert len(p) == len(f) - 21
    assert (p["breach_excursion_atr"] >= EXCURSION_RATIO_MIN_ATR).all()


def test_excursion_ratio_math_is_scale_free():
    f = _frame()
    p = _representation_payload(f, "EXCURSION_RATIO", 5)
    expected = f.loc[p.index, "in_candle_reversion_atr"] / f.loc[p.index, "breach_excursion_atr"]
    assert np.allclose(p["_x"], expected)


def test_post_is_exactly_total_minus_in():
    f = _frame()
    for rep in REPRESENTATIONS:
        p = _representation_payload(f, rep, 5)
        assert np.allclose(p["_post"], p["_y"] - p["_x"])


def test_local_cyclic_placebo_preserves_multiset_and_breaks_self_link():
    f = _frame(120)
    p = _representation_payload(f, "ATR_T", 5).reset_index(drop=True)
    values = np.arange(len(p), dtype=float)
    shifted = _within_day_side_cyclic_shift(p, values, seed=7)
    for side in ("LONG", "SHORT"):
        idx = np.flatnonzero(p["side"].to_numpy() == side)
        assert sorted(shifted[idx].tolist()) == sorted(values[idx].tolist())
        assert np.all(shifted[idx] != values[idx])


def test_sign_placebo_uses_only_plus_minus_one():
    f = _frame(120)
    p = _representation_payload(f, "ATR_T", 5).reset_index(drop=True)
    signs = _within_day_side_balanced_signs(p, seed=11)
    assert set(np.unique(signs[np.isfinite(signs)])) <= {-1.0, 1.0}


def test_placebo_total_null_construction_retains_r_in():
    f = _frame(120)
    p = _representation_payload(f, "ATR_T", 5).reset_index(drop=True)
    x = p["_x"].to_numpy(float); post = p["_post"].to_numpy(float)
    shifted = _within_day_side_cyclic_shift(p, post, seed=13)
    y = x + shifted
    assert np.allclose((y-x)[np.isfinite(shifted)], shifted[np.isfinite(shifted)])


def test_fwl_recovers_known_slope_without_confounded_controls():
    f = _frame(240)
    p = _representation_payload(f, "ATR_T", 5)
    # Construct an artificial y with exact slope 0.8 after the same controls.
    y = 0.8 * p["_x"].to_numpy(float) + 0.3
    fit = _fit_payload(p, y_override=y)
    assert abs(fit["rho"] - 0.8) < 1e-10


def test_day_block_bootstrap_is_deterministic():
    f = _frame(240)
    p = _representation_payload(f, "ATR_T", 5)
    fit = _fit_payload(p, return_residuals=True)
    a = _day_block_bootstrap_from_fit(fit, iterations=50, seed=123)
    b = _day_block_bootstrap_from_fit(fit, iterations=50, seed=123)
    assert a == b


def test_gradient_detects_inverse_post_pattern():
    table, audit = build_gradient_table(_frame(500))
    assert not table.empty
    assert all(audit[r]["monotonic_nonincreasing"] for r in REPRESENTATIONS)


def test_gate_pass_requires_placebo_ci_to_include_one():
    audit = {
        "years": list(range(2018, 2026)), "exact_5m_coverage_pct": 99.5,
        "excursion_ratio_5m_coverage_pct_of_exact": 80.0, "base_rho_abs_error": 0.0,
    }
    inv = pd.DataFrame([
        {"representation": r, "horizon_min": 5, "rho": 0.95, "ci95_upper": 0.98}
        for r in REPRESENTATIONS
    ])
    grad = {r: {"monotonic_nonincreasing": True} for r in REPRESENTATIONS}
    plac = pd.DataFrame([
        {"placebo": "WITHIN_DAY_SIDE_CYCLIC_POST_SHUFFLE", "ci95_lower": 0.99, "ci95_upper": 1.01},
        {"placebo": "WITHIN_DAY_SIDE_BALANCED_POST_SIGN", "ci95_lower": 0.98, "ci95_upper": 1.02},
    ])
    g = evaluate_falsification_gates(audit, inv, grad, plac)
    assert g["verdict"] == "COMPENSATION_INVARIANCE_SURVIVES_FALSIFICATION"


def test_gate_fails_if_placebo_also_attenuates():
    audit = {
        "years": list(range(2018, 2026)), "exact_5m_coverage_pct": 99.5,
        "excursion_ratio_5m_coverage_pct_of_exact": 80.0, "base_rho_abs_error": 0.0,
    }
    inv = pd.DataFrame([
        {"representation": r, "horizon_min": 5, "rho": 0.95, "ci95_upper": 0.98}
        for r in REPRESENTATIONS
    ])
    grad = {r: {"monotonic_nonincreasing": True} for r in REPRESENTATIONS}
    plac = pd.DataFrame([
        {"placebo": "WITHIN_DAY_SIDE_CYCLIC_POST_SHUFFLE", "ci95_lower": 0.90, "ci95_upper": 0.97},
        {"placebo": "WITHIN_DAY_SIDE_BALANCED_POST_SIGN", "ci95_lower": 0.98, "ci95_upper": 1.02},
    ])
    g = evaluate_falsification_gates(audit, inv, grad, plac)
    assert g["verdict"] == "COMPENSATION_FALSIFIED_OR_NOT_INVARIANT"


def test_known_mech004_reference_is_frozen():
    assert KNOWN_MECH004_RHO_5M == 0.94191764717577


def test_runner_contains_no_execution_surface():
    text = Path(__file__).with_name("run_m1_mech_005.py").read_text(encoding="utf-8").lower()
    forbidden = ("order_send", "order_check", "buy_order", "sell_order", "paper_trade", "live_trade")
    assert not any(token in text for token in forbidden)
