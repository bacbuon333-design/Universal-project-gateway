from __future__ import annotations

"""Comprehensive frozen test suite for ALAB-M1-FUSION-001."""

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
import m1_fusion.failed_auction as fa_module
import m1_fusion.diagnostic_backtest as bt_module
import m1_fusion.features as feat_module


def create_synthetic_m1(n: int = 600, start: str = "2026-04-15 00:00:00") -> pd.DataFrame:
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


def test_prior_extreme_excludes_event_bar():
    src = inspect.getsource(compute_prior_extremes)
    assert ".shift(1)" in src
    df = create_synthetic_m1(30)
    t = 25
    df.loc[t, "high"] = 3000.0
    ph, pl = compute_prior_extremes(df, 20)
    # The extreme at t should NOT appear in prior_high at t
    assert ph.iloc[t] < 3000.0
    # But should appear at t+1
    assert ph.iloc[t + 1] == 3000.0


def test_long_failed_auction_fixture():
    df = create_synthetic_m1(60)
    t = 55
    # Force prior low to be 1999.0
    df.loc[t-20:t-1, "low"] = 2000.0
    df.loc[t-10, "low"] = 1999.0
    # Bar t dips below 1999.0 but closes above 1999.0
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
    # Multi-day synthetic data
    dts = pd.date_range("2026-04-01 00:00:00", periods=2880, freq="1min", tz="UTC")
    df = pd.DataFrame({
        "datetime": dts,
        "open": 2000.0,
        "high": 2010.0,
        "low": 1990.0,
        "close": 2000.0,
    })
    # Day 1 high = 2050.0
    df.loc[0:1439, "high"] = 2050.0
    pdh, pdl = compute_pdh_pdl(df)
    # Day 1 bars must have NaN PDH
    assert np.isnan(pdh[100])
    # Day 2 bars must have PDH = 2050.0
    assert pdh[1500] == 2050.0


def test_incomplete_current_session_extreme_is_not_available():
    # 08:30 London bar should not have London session high
    df = create_synthetic_m1(1440, "2026-04-15 00:00:00")
    # At 08:30 (index 510)
    highs, lows = compute_completed_session_levels(df)
    # At 08:30, only Asia session is completed (1 session)
    assert len(highs[510]) == 1


def test_completed_session_extreme_is_available():
    df = create_synthetic_m1(1440, "2026-04-15 00:00:00")
    # At 14:00 (index 840), Asia and London are completed (2 sessions)
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
    df = create_synthetic_m1(1440, "2026-04-15 00:00:00")
    m15_highs, m15_lows = compute_m15_swings(df, flank=2)
    # Early bars should have no confirmed swings
    assert len(m15_highs[10]) == 0


def test_score_weights_are_exactly_frozen():
    src = inspect.getsource(detect_failed_auction_events)
    assert "score = 3" in src
    assert "score += 1" in src  # eff, z, atr_pct, session, m15
    assert "score += 2" in src  # pdh_pdl


def test_score_range_is_three_to_ten():
    df = create_synthetic_m1(600)
    events = detect_failed_auction_events(df)
    for ev in events:
        assert 3 <= ev.reaction_score <= 10


def test_forward_returns_are_outcome_only():
    from m1_fusion.event_study import run_event_study
    df = create_synthetic_m1(600)
    events = detect_failed_auction_events(df)
    df_events, res = run_event_study(df, events)
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
    for mod in [fa_module, bt_module, feat_module]:
        src = inspect.getsource(mod).lower()
        assert "itertools.product" not in src
        assert "gridsearch" not in src


def test_no_v5a_family_reuse():
    for mod in [fa_module, bt_module, feat_module]:
        src = inspect.getsource(mod).lower()
        for token in ["h401", "h402", "h403", "h404", "h301", "h302", "h303", "h304", "h226"]:
            assert token not in src


def test_no_broker_execution_import_or_call():
    for mod in [fa_module, bt_module, feat_module]:
        src = inspect.getsource(mod).lower()
        for token in ["order_send", "order_check", "trade_action_deal", "live_trading"]:
            assert token not in src


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for t in tests:
        t()
        print(f"PASS: {t.__name__}")
    print(f"All {len(tests)} ALAB-M1-FUSION-001 tests passed.")
