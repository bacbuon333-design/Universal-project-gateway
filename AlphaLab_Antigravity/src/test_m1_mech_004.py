from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from m1_mech_004.reversion_budget import (
    BOOTSTRAP_SEED,
    IDENTITY_TOLERANCE,
    RECLAIM_LABELS,
    add_reversion_budget_variables,
    evaluate_gates,
    fit_persistence_regression,
    fixed_residual_day_block_bootstrap,
    geometry_audit,
)


def _base_frame(side: str = "LONG") -> tuple[pd.DataFrame, pd.DataFrame]:
    dt = pd.date_range("2020-01-02T00:00:00Z", periods=40, freq="1min")
    px = np.full(40, 100.0)
    df = pd.DataFrame({"datetime": dt, "open": px, "high": px + 0.1, "low": px - 0.1, "close": px})
    t = 10
    prior = 100.0
    atr = 1.0
    if side == "LONG":
        df.loc[t, ["low", "high", "close"]] = [99.0, 100.2, 99.6]
        sign = 1.0
    else:
        df.loc[t, ["low", "high", "close"]] = [99.8, 101.0, 100.4]
        sign = -1.0

    event_close = float(df.loc[t, "close"])
    frame = pd.DataFrame({
        "bar_index": [t], "datetime": [dt[t]], "year": [2020], "hour": [0], "side": [side],
        "event_class": ["ACCEPTED_BREAKOUT"], "prior_extreme": [prior], "event_close": [event_close],
        "atr14": [atr], "atr_percentile": [60.0], "path_efficiency": [0.4], "stretch_abs": [1.2],
        "energy_count": [1], "location_count": [0],
    })
    for h in (1, 3, 5, 10, 15, 30):
        future_pos = t + h
        if future_pos < len(df):
            future_close = event_close + sign * 0.2
            df.loc[future_pos, "close"] = future_close
            frame[f"exact_{h}m_available"] = True
            frame[f"signed_level_distance_atr_{h}m"] = sign * (future_close - prior) / atr
        else:
            frame[f"exact_{h}m_available"] = False
            frame[f"signed_level_distance_atr_{h}m"] = np.nan
    return df, frame


@pytest.mark.parametrize("side", ["LONG", "SHORT"])
def test_geometry_identities_and_positive_reversion(side: str):
    df, frame = _base_frame(side)
    out = add_reversion_budget_variables(df, frame)
    assert out.loc[0, "breach_excursion_atr"] > 0
    assert out.loc[0, "in_candle_reversion_atr"] >= 0
    assert abs(out.loc[0, "geometry_identity_error"]) <= IDENTITY_TOLERANCE
    assert abs(out.loc[0, "total_reversion_identity_error_5m"]) <= IDENTITY_TOLERANCE
    assert out.loc[0, "post_close_reversion_atr_5m"] == pytest.approx(0.2)


def test_total_reversion_is_computed_without_event_close_term():
    df, frame = _base_frame("LONG")
    out = add_reversion_budget_variables(df, frame)
    exc = out.loc[0, "breach_excursion_atr"]
    fut_d = frame.loc[0, "signed_level_distance_atr_5m"]
    assert out.loc[0, "total_reversion_atr_5m"] == pytest.approx(exc + fut_d)


def test_consumption_ratio_only_when_total_positive():
    df, frame = _base_frame("LONG")
    out = add_reversion_budget_variables(df, frame)
    assert np.isfinite(out.loc[0, "consumption_ratio_5m"])
    frame.loc[0, "signed_level_distance_atr_5m"] = -2.0
    out2 = add_reversion_budget_variables(df, frame)
    assert np.isnan(out2.loc[0, "consumption_ratio_5m"])


def test_missing_exact_clock_endpoint_produces_nan_future_measures():
    df, frame = _base_frame("LONG")
    frame.loc[0, "exact_5m_available"] = False
    frame.loc[0, "signed_level_distance_atr_5m"] = np.nan
    out = add_reversion_budget_variables(df, frame)
    assert np.isnan(out.loc[0, "post_close_reversion_atr_5m"])
    assert np.isnan(out.loc[0, "total_reversion_atr_5m"])


def test_fixed_reclaim_bins_are_frozen_labels():
    df, frame = _base_frame("LONG")
    out = add_reversion_budget_variables(df, frame)
    assert out.loc[0, "in_candle_reversion_bin"] in RECLAIM_LABELS


def _synthetic_persistence_frame(rho: float = 0.45, days: int = 40, per_day: int = 30) -> pd.DataFrame:
    rng = np.random.default_rng(123)
    n = days * per_day
    dt = pd.date_range("2020-01-01T00:00:00Z", periods=n, freq="1min")
    x = rng.uniform(0.05, 2.0, n)
    excursion = rng.uniform(0.02, 1.2, n)
    atrp = rng.uniform(10, 99, n)
    eff = rng.uniform(0, 1, n)
    stretch = rng.uniform(0, 3, n)
    location = rng.integers(0, 3, n)
    side = np.where(rng.random(n) > 0.5, "LONG", "SHORT")
    hour = pd.DatetimeIndex(dt).hour
    year = np.full(n, 2020)
    noise = rng.normal(0, 0.04, n)
    y_total = rho * x + 0.05 * excursion + 0.02 * eff + noise
    frame = pd.DataFrame({
        "datetime": dt, "year": year, "hour": hour, "side": side,
        "event_class": np.where(rng.random(n) > 0.5, "FAILED_AUCTION", "ACCEPTED_BREAKOUT"),
        "in_candle_reversion_atr": x, "breach_excursion_atr": excursion,
        "atr_percentile": atrp, "path_efficiency": eff, "stretch_abs": stretch,
        "location_count": location, "energy_count": rng.integers(0, 4, n),
        "exact_5m_available": True, "total_reversion_atr_5m": y_total,
        "post_close_reversion_atr_5m": y_total - x,
    })
    return frame


def test_regression_recovers_persistence_rho_below_one():
    frame = _synthetic_persistence_frame(rho=0.45)
    r = fit_persistence_regression(frame, 5, include_year_effects=False)
    assert 0.35 < r["rho_total_on_in"] < 0.55
    assert r["compensation_fraction"] > 0.4


def test_event_class_is_not_a_frozen_regression_control():
    frame = _synthetic_persistence_frame()
    r = fit_persistence_regression(frame, 5, include_year_effects=False)
    assert "event_class" not in r["controls"]


def test_day_block_bootstrap_is_deterministic_and_below_one():
    frame = _synthetic_persistence_frame(rho=0.45, days=60, per_day=25)
    a = fixed_residual_day_block_bootstrap(frame, iterations=200, seed=BOOTSTRAP_SEED)
    b = fixed_residual_day_block_bootstrap(frame, iterations=200, seed=BOOTSTRAP_SEED)
    assert a == b
    assert a["ci95_upper"] < 1.0


def test_geometry_audit_reports_exact_coverage_and_identities():
    df, frame = _base_frame("LONG")
    out = add_reversion_budget_variables(df, frame)
    a = geometry_audit(out)
    assert a["events"] == 1
    assert a["exact_5m_coverage_pct"] == 100.0
    assert a["max_abs_geometry_identity_error"] <= IDENTITY_TOLERANCE
    assert a["max_abs_total_identity_error"] <= IDENTITY_TOLERANCE


def test_gate_logic_requires_rho_below_one_and_temporal_stability():
    audit = {
        "years": list(range(2018, 2026)), "max_abs_geometry_identity_error": 0.0,
        "max_abs_total_identity_error": 0.0, "negative_excursion_count": 0,
        "negative_in_candle_reversion_count": 0, "exact_5m_coverage_pct": 99.0,
    }
    regressions = pd.DataFrame({"horizon_min": [3, 5, 10], "rho_total_on_in": [0.7, 0.6, 0.8]})
    yearly = pd.DataFrame({"year": list(range(2018, 2026)), "rho_total_on_in_5m": [0.7] * 7 + [1.1]})
    bootstrap = {"ci95_upper": 0.8}
    gates = evaluate_gates(audit, regressions, yearly, bootstrap)
    assert gates["verdict"] == "REVERSION_COMPENSATION_SUPPORTED_IN_DEVELOPMENT"


def test_gate_logic_fails_when_bootstrap_reaches_one():
    audit = {
        "years": list(range(2018, 2026)), "max_abs_geometry_identity_error": 0.0,
        "max_abs_total_identity_error": 0.0, "negative_excursion_count": 0,
        "negative_in_candle_reversion_count": 0, "exact_5m_coverage_pct": 99.0,
    }
    regressions = pd.DataFrame({"horizon_min": [3, 5, 10], "rho_total_on_in": [0.7, 0.6, 0.8]})
    yearly = pd.DataFrame({"year": list(range(2018, 2026)), "rho_total_on_in_5m": [0.7] * 8})
    gates = evaluate_gates(audit, regressions, yearly, {"ci95_upper": 1.01})
    assert not gates["G3_day_block_ci_upper_below_one"]
    assert gates["verdict"] == "REVERSION_COMPENSATION_NOT_CONFIRMED"


def test_primary_model_does_not_regress_post_close_on_in_candle():
    src = (Path(__file__).resolve().parent / "m1_mech_004" / "reversion_budget.py").read_text(encoding="utf-8")
    assert 'y = sub[f"total_reversion_atr_{horizon}m"]' in src
    assert 'y = sub[f"post_close_reversion_atr_{horizon}m"]' not in src


def test_no_execution_surface_in_mech004_source():
    here = Path(__file__).resolve().parent
    src = (here / "m1_mech_004" / "reversion_budget.py").read_text(encoding="utf-8").lower()
    runner = (here / "run_m1_mech_004.py").read_text(encoding="utf-8").lower()
    forbidden = ("order_send(", "order_check(", "trade_action_deal", "positionclose(", ".buy(", ".sell(", "run_live_bridge")
    for token in forbidden:
        assert token not in src
        assert token not in runner


def test_runner_binds_frozen_dataset_sha_and_holdout():
    here = Path(__file__).resolve().parent
    runner = (here / "run_m1_mech_004.py").read_text(encoding="utf-8")
    assert "EXPECTED_DATA_SHA256" in runner
    assert "2018-01-01T00:00:00Z" in runner
    assert "2026-01-01T00:00:00Z" in runner
    assert "STOP_BLOCKED_SEALED_HOLDOUT_ACCESS" in runner
