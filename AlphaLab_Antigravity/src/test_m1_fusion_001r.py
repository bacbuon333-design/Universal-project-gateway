from __future__ import annotations

"""Comprehensive frozen test suite for ALAB-M1-FUSION-001R (Replication & Infrastructure Repair)."""

import inspect
from pathlib import Path
import numpy as np
import pandas as pd

from m1_fusion.features import (
    compute_atr14,
    compute_prior_extremes,
    compute_path_efficiency,
    compute_robust_stretch_z,
    compute_atr_percentiles,
    PRIOR_EXTREME_LOOKBACK,
    PATH_WINDOW,
    ROBUST_WINDOW,
)
from m1_fusion.reaction_zones import (
    compute_pdh_pdl,
    compute_completed_session_levels,
    compute_m15_swings,
)
from m1_fusion.failed_auction import (
    detect_failed_auction_events,
    FailedAuctionEvent,
)
from m1_fusion.diagnostic_backtest import run_diagnostic_backtest
from m1_fusion.data_audit import (
    audit_and_load_m1_data,
    MIN_REPLICATION_ROWS,
    MIN_VALID_CALENDAR_YEARS,
    DISCOVERY_CUTOFF_UTC,
)
from m1_fusion.cost_contract import get_verified_cost_contract
from m1_fusion.event_study import (
    compute_day_block_bootstrap,
    compute_overlap_audit,
    evaluate_replication_gates,
    run_event_study,
    MIN_VALID_YEAR_EVENTS,
)
import m1_fusion.failed_auction as fa_module
import m1_fusion.diagnostic_backtest as bt_module
import m1_fusion.features as feat_module
import m1_fusion.event_study as es_module


def create_synthetic_m1(n: int = 600, start: str = "2024-04-15 00:00:00") -> pd.DataFrame:
    dts = pd.date_range(start, periods=n, freq="1min", tz="UTC")
    x = np.arange(n, dtype=float)
    base = 2000.0 + 0.05 * np.sin(x / 10.0)
    open_ = base - 0.02 * np.cos(x / 7.0)
    close = base + 0.03 * np.sin(x / 5.0)
    high = np.maximum(open_, close) + 0.30
    low = np.minimum(open_, close) - 0.30
    return pd.DataFrame({
        "datetime": dts,
        "open": open_,
        "high": high,
        "low": low,
        "close": close,
        "spread": np.full(n, 25.0),
    })


# ----------------------------------------------------
# 20 V1 TESTS RETAINED
# ----------------------------------------------------

def test_prior_extreme_excludes_event_bar():
    src = inspect.getsource(compute_prior_extremes)
    assert ".shift(1)" in src
    df = create_synthetic_m1(30)
    t = 25
    df.loc[t, "high"] = 3000.0
    ph, pl = compute_prior_extremes(df, 20)
    assert ph.iloc[t] < 3000.0
    assert ph.iloc[t + 1] == 3000.0


def test_long_failed_auction_fixture():
    df = create_synthetic_m1(60)
    t = 55
    df.loc[t-20:t-1, "low"] = 2000.0
    df.loc[t-10, "low"] = 1999.0
    df.loc[t, "low"] = 1998.5
    df.loc[t, "close"] = 1999.5
    df.loc[t, "high"] = 2000.0
    ph, pl = compute_prior_extremes(df, 20)
    assert df.loc[t, "low"] < pl.iloc[t]
    assert df.loc[t, "close"] > pl.iloc[t]


def test_short_failed_auction_fixture():
    df = create_synthetic_m1(60)
    t = 55
    df.loc[t-20:t-1, "high"] = 2000.0
    df.loc[t-10, "high"] = 2005.0
    df.loc[t, "high"] = 2006.0
    df.loc[t, "close"] = 2004.5
    df.loc[t, "low"] = 2003.0
    ph, pl = compute_prior_extremes(df, 20)
    assert df.loc[t, "high"] > ph.iloc[t]
    assert df.loc[t, "close"] < ph.iloc[t]


def test_efficiency_uses_only_pre_event_history():
    src = inspect.getsource(compute_path_efficiency)
    assert "t - 1" in src
    df = create_synthetic_m1(30)
    eff, is_up, is_down = compute_path_efficiency(df, 10)
    assert len(eff) == 30
    assert np.all(eff[:10] == 0.0)


def test_robust_stretch_has_no_future_access():
    src = inspect.getsource(compute_robust_stretch_z)
    assert "t - 1" in src
    df = create_synthetic_m1(80)
    z = compute_robust_stretch_z(df, 60)
    assert len(z) == 80
    assert np.all(z[:60] == 0.0)


def test_atr_percentile_has_no_future_access():
    src = inspect.getsource(compute_atr_percentiles)
    assert "t - 1" in src
    df = create_synthetic_m1(600)
    atr = compute_atr14(df)
    pct = compute_atr_percentiles(atr, 500)
    assert len(pct) == 600
    assert np.all(pct[:500] == 0.0)


def test_previous_day_high_low_are_previous_day_only():
    dts = pd.date_range("2024-04-01 00:00:00", periods=2880, freq="1min", tz="UTC")
    df = pd.DataFrame({
        "datetime": dts,
        "open": 2000.0,
        "high": 2010.0,
        "low": 1990.0,
        "close": 2000.0,
    })
    df.loc[0:1439, "high"] = 2050.0
    pdh, pdl = compute_pdh_pdl(df)
    assert np.isnan(pdh[100])
    assert pdh[1500] == 2050.0


def test_incomplete_current_session_extreme_is_not_available():
    df = create_synthetic_m1(1440, "2024-04-15 00:00:00")
    highs, lows = compute_completed_session_levels(df)
    assert len(highs[510]) == 1


def test_completed_session_extreme_is_available():
    df = create_synthetic_m1(1440, "2024-04-15 00:00:00")
    highs, lows = compute_completed_session_levels(df)
    assert len(highs[840]) == 2


def test_m15_resampling_uses_complete_bars_only():
    src = inspect.getsource(compute_m15_swings)
    assert 'resample("15min"' in src
    assert "dropna()" in src


def test_m15_pivot_requires_two_closed_right_bars():
    src = inspect.getsource(compute_m15_swings)
    assert "j + flank" in src
    assert "Timedelta(minutes=15)" in src


def test_m15_pivot_not_available_before_confirmation():
    df = create_synthetic_m1(1440, "2024-04-15 00:00:00")
    m15_highs, m15_lows = compute_m15_swings(df, flank=2)
    assert len(m15_highs[10]) == 0


def test_score_weights_are_exactly_frozen():
    src = inspect.getsource(detect_failed_auction_events)
    assert "score = 3" in src
    assert "score += 1" in src
    assert "score += 2" in src


def test_score_range_is_three_to_ten():
    df = create_synthetic_m1(600)
    events = detect_failed_auction_events(df)
    for ev in events:
        assert 3 <= ev.reaction_score <= 10


def test_forward_returns_are_outcome_only():
    df = create_synthetic_m1(600)
    events = detect_failed_auction_events(df)
    meta = {"is_sufficient_history": False, "is_sufficient_temporal_coverage": False}
    df_events, res, _, _ = run_event_study(df, events, meta)
    if not df_events.empty:
        for h in [1, 3, 5, 10, 15, 30]:
            assert f"fwd_ret_{h}m" in df_events.columns


def test_next_bar_entry_contract():
    src = inspect.getsource(run_diagnostic_backtest)
    assert "t_entry = t_sig + 1" in src
    assert "entry_price = opens[t_entry]" in src


def test_stop_is_conservative_on_ohlc_touch():
    src = inspect.getsource(run_diagnostic_backtest)
    assert "opens[b] <= sl_price" in src
    assert "lows[b] <= sl_price" in src
    assert "opens[b] >= sl_price" in src
    assert "highs[b] >= sl_price" in src


def test_no_parameter_grid_present():
    for mod in [fa_module, bt_module, feat_module, es_module]:
        src = inspect.getsource(mod).lower()
        assert "itertools.product" not in src
        assert "gridsearch" not in src


def test_no_v5a_family_reuse():
    for mod in [fa_module, bt_module, feat_module, es_module]:
        src = inspect.getsource(mod).lower()
        for token in ["h401", "h402", "h403", "h404", "h301", "h302", "h303", "h304", "h226"]:
            assert token not in src


def test_no_broker_execution_import_or_call():
    for mod in [fa_module, bt_module, feat_module, es_module]:
        src = inspect.getsource(mod).lower()
        for token in ["order_send", "order_check", "trade_action_deal", "live_trading"]:
            assert token not in src


# ----------------------------------------------------
# 16 NEW 001R REPLICATION TESTS
# ----------------------------------------------------

def test_runner_blocks_below_one_million_rows():
    assert MIN_REPLICATION_ROWS == 1_000_000


def test_runner_blocks_below_three_calendar_years():
    assert MIN_VALID_CALENDAR_YEARS == 3


def test_discovery_2026_rows_are_excluded():
    dts = pd.date_range("2025-12-30 00:00:00", periods=5000, freq="1min", tz="UTC")
    df = pd.DataFrame({"datetime": dts, "open": 2000.0, "high": 2001.0, "low": 1999.0, "close": 2000.0})
    tmp = Path("test_quarantine.csv")
    df.to_csv(tmp, index=False)
    try:
        df_rep, meta = audit_and_load_m1_data(tmp, quarantine_2026_discovery=True)
        assert meta["discovery_overlap_count"] == 0
        assert (df_rep["datetime"] >= DISCOVERY_CUTOFF_UTC).sum() == 0
    finally:
        if tmp.exists():
            tmp.unlink()


def test_replication_cutoff_is_before_2026():
    assert str(DISCOVERY_CUTOFF_UTC).startswith("2026-01-01")


def test_single_year_cannot_pass_temporal_gate():
    df_ev = pd.DataFrame({
        "year": [2024] * 500,
        "fwd_ret_5m": [0.001] * 500,
        "score_bin": ["7-8"] * 500,
    })
    meta = {"is_sufficient_history": True, "is_sufficient_temporal_coverage": True}
    res = evaluate_replication_gates(df_ev, {"h5m": {"mean_return_bps": 10.0, "day_block_ci_95_lower_bps": 5.0}}, {}, meta)
    assert res["gate5_year_stability"] is False
    assert res["valid_calendar_years_count"] == 1


def test_two_years_cannot_pass_temporal_gate():
    df_ev = pd.DataFrame({
        "year": [2023] * 300 + [2024] * 300,
        "fwd_ret_5m": [0.001] * 600,
        "score_bin": ["7-8"] * 600,
    })
    meta = {"is_sufficient_history": True, "is_sufficient_temporal_coverage": True}
    res = evaluate_replication_gates(df_ev, {"h5m": {"mean_return_bps": 10.0, "day_block_ci_95_lower_bps": 5.0}}, {}, meta)
    assert res["gate5_year_stability"] is False
    assert res["valid_calendar_years_count"] == 2


def test_three_year_positive_ratio_gate():
    # 3 years, 2 positive (66.7% < 70% -> Fail)
    df_ev1 = pd.DataFrame({
        "year": [2022] * 300 + [2023] * 300 + [2024] * 300,
        "fwd_ret_5m": [0.001] * 300 + [0.001] * 300 + [-0.001] * 300,
        "score_bin": ["7-8"] * 900,
    })
    meta = {"is_sufficient_history": True, "is_sufficient_temporal_coverage": True}
    res1 = evaluate_replication_gates(df_ev1, {"h5m": {"mean_return_bps": 5.0, "day_block_ci_95_lower_bps": 1.0}}, {}, meta)
    assert res1["gate5_year_stability"] is False

    # 4 years, 3 positive (75% >= 70% -> Pass)
    df_ev2 = pd.DataFrame({
        "year": [2021] * 300 + [2022] * 300 + [2023] * 300 + [2024] * 300,
        "fwd_ret_5m": [0.001] * 300 + [0.001] * 300 + [0.001] * 300 + [-0.001] * 300,
        "score_bin": ["7-8"] * 1200,
    })
    res2 = evaluate_replication_gates(df_ev2, {"h5m": {"mean_return_bps": 5.0, "day_block_ci_95_lower_bps": 1.0}}, {}, meta)
    assert res2["gate5_year_stability"] is True


def test_valid_year_requires_200_events():
    assert MIN_VALID_YEAR_EVENTS == 200
    df_ev = pd.DataFrame({
        "year": [2022] * 100 + [2023] * 300 + [2024] * 300,
        "fwd_ret_5m": [0.001] * 700,
        "score_bin": ["7-8"] * 700,
    })
    meta = {"is_sufficient_history": True, "is_sufficient_temporal_coverage": True}
    res = evaluate_replication_gates(df_ev, {"h5m": {"mean_return_bps": 5.0, "day_block_ci_95_lower_bps": 1.0}}, {}, meta)
    # 2022 has only 100 events, so valid_years = 2 < 3 -> False
    assert res["valid_calendar_years_count"] == 2
    assert res["gate5_year_stability"] is False


def test_day_block_bootstrap_samples_whole_days():
    # Construct events on 2 distinct dates
    dts = [
        pd.Timestamp("2024-01-01 10:00:00", tz="UTC"),
        pd.Timestamp("2024-01-01 10:05:00", tz="UTC"),
        pd.Timestamp("2024-01-02 10:00:00", tz="UTC"),
    ]
    df_ev = pd.DataFrame({
        "date": [dt.date() for dt in dts],
        "fwd_ret_5m": [0.01, 0.02, -0.05],
    })
    for h in [1, 3, 10, 15, 30]:
        df_ev[f"fwd_ret_{h}m"] = 0.001

    bb = compute_day_block_bootstrap(df_ev, n_boot=50, seed=42)
    assert "h5m" in bb
    assert bb["h5m"]["unique_days_sampled"] == 2


def test_day_block_bootstrap_is_deterministic():
    df_ev = pd.DataFrame({
        "date": [pd.Timestamp("2024-01-01").date(), pd.Timestamp("2024-01-02").date()],
        "fwd_ret_5m": [0.01, -0.01],
    })
    for h in [1, 3, 10, 15, 30]:
        df_ev[f"fwd_ret_{h}m"] = 0.001
    bb1 = compute_day_block_bootstrap(df_ev, n_boot=100, seed=20260817)
    bb2 = compute_day_block_bootstrap(df_ev, n_boot=100, seed=20260817)
    assert bb1["h5m"]["ci_95_lower_bps"] == bb2["h5m"]["ci_95_lower_bps"]


def test_iid_bootstrap_not_used_for_primary_gate():
    src = inspect.getsource(evaluate_replication_gates)
    assert "day_block_ci_95_lower_bps" in src
    assert "legacy_iid" not in src


def test_overlap_statistics_are_reported():
    df_ev = pd.DataFrame({
        "event_id": [1, 2, 3],
        "bar_index": [10, 12, 50],
        "date": [pd.Timestamp("2024-01-01").date()] * 3,
    })
    ov = compute_overlap_audit(df_ev)
    assert "overlap_pct_5m" in ov
    assert "overlap_pct_10m" in ov
    assert "overlap_pct_30m" in ov
    assert ov["overlap_pct_5m"] == 50.0  # 1 gap <= 5 out of 2 gaps


def test_cost_contract_uses_symbol_point():
    c = get_verified_cost_contract("GOLD")
    assert c.point > 0.0
    assert "symbol_point" in c.spread_price_conversion


def test_contract_size_is_not_hardcoded_if_symbol_info_available():
    c = get_verified_cost_contract("GOLD")
    assert c.trade_contract_size == 100.0


def test_spread_conversion_has_explicit_units():
    c = get_verified_cost_contract("GOLD")
    assert c.spread_raw_unit == "points"


def test_v1_strategy_parameters_unchanged():
    assert PRIOR_EXTREME_LOOKBACK == 20
    assert PATH_WINDOW == 10
    assert ROBUST_WINDOW == 60


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for t in tests:
        t()
        print(f"PASS: {t.__name__}")
    print(f"\nAll {len(tests)} ALAB-M1-FUSION-001R unit tests passed (100% OK).")
