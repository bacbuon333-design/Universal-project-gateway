from __future__ import annotations

import inspect

import numpy as np
import pandas as pd

from m1_fusion.failed_auction import FailedAuctionEvent
from m1_mech_002.state_engine import (
    add_gap_aware_state_labels,
    build_mechanism_event_frame,
    summarize_tail_distribution,
    validate_development_frame,
)
import m1_mech_002.state_engine as state_module
import run_m1_mech_002 as runner_module


def _df(periods: int = 120, start: str = "2018-01-02 00:00:00") -> pd.DataFrame:
    dt = pd.date_range(start, periods=periods, freq="1min", tz="UTC")
    x = np.arange(periods, dtype=float)
    close = 100.0 + x * 0.01
    return pd.DataFrame(
        {
            "datetime": dt,
            "open": close - 0.01,
            "high": close + 0.10,
            "low": close - 0.10,
            "close": close,
            "spread": 25.0,
            "tick_volume": 10.0,
            "real_volume": 0.0,
        }
    )


def _event(df: pd.DataFrame, t: int, side: str) -> FailedAuctionEvent:
    c = float(df.loc[t, "close"])
    if side == "LONG":
        prior = c - 0.02
        low = prior - 0.10
        high = c + 0.10
    else:
        prior = c + 0.02
        high = prior + 0.10
        low = c - 0.10
    return FailedAuctionEvent(
        event_id=1,
        bar_index=t,
        datetime=df.loc[t, "datetime"],
        side=side,
        failed_auction=True,
        prior_extreme=prior,
        price_open=float(df.loc[t, "open"]),
        price_high=high,
        price_low=low,
        price_close=c,
        efficiency_ratio=0.7,
        path_eff_match=True,
        stretch_z=(-2.5 if side == "LONG" else 2.5),
        stretch_z_match=True,
        atr14=0.20,
        atr_percentile=90.0,
        atr_pct_match=True,
        pdh_pdl_match=False,
        session_level_match=False,
        m15_swing_match=False,
        reaction_score=6,
        score_bin="5-6",
    )


def test_sealed_holdout_rejected():
    df = _df(start="2017-12-31 23:00:00")
    try:
        validate_development_frame(df)
    except RuntimeError as exc:
        assert "SEALED_HOLDOUT" in str(exc)
    else:
        raise AssertionError("pre-2018 holdout access must fail closed")


def test_2026_rejected():
    df = _df(start="2026-01-01 00:00:00")
    try:
        validate_development_frame(df)
    except RuntimeError as exc:
        assert "DISCOVERY_LEAKAGE" in str(exc)
    else:
        raise AssertionError("2026 access must fail closed")


def test_rejection_geometry_is_side_normalized():
    df = _df(periods=600)
    frame = build_mechanism_event_frame(df, [_event(df, 550, "LONG"), _event(df, 551, "SHORT")])
    assert len(frame) == 2
    assert (frame["sweep_depth_atr"] > 0).all()
    assert (frame["reclaim_depth_atr"] > 0).all()
    assert ((frame["close_location_snapback"] >= 0) & (frame["close_location_snapback"] <= 1)).all()


def test_exact_close_label_survives_intermediate_gap_but_path_is_not_contiguous():
    df = _df(periods=650)
    event_time = df.loc[550, "datetime"]
    missing_ts = event_time + pd.Timedelta(minutes=2)
    df_gap = df[df["datetime"] != missing_ts].reset_index(drop=True)
    t_gap = int(df_gap.index[df_gap["datetime"] == event_time][0])
    ev = _event(df_gap, t_gap, "LONG")
    frame = build_mechanism_event_frame(df_gap, [ev])
    labeled = add_gap_aware_state_labels(df_gap, frame)
    assert bool(labeled.loc[0, "exact_5m_available"])
    assert not bool(labeled.loc[0, "continuous_5m_path"])
    assert labeled.loc[0, "close_state_5m"] != "GAP_CONTAMINATED"


def test_missing_exact_horizon_is_gap_contaminated():
    df = _df(periods=650)
    event_time = df.loc[550, "datetime"]
    missing_ts = event_time + pd.Timedelta(minutes=5)
    df_gap = df[df["datetime"] != missing_ts].reset_index(drop=True)
    t_gap = int(df_gap.index[df_gap["datetime"] == event_time][0])
    ev = _event(df_gap, t_gap, "LONG")
    frame = build_mechanism_event_frame(df_gap, [ev])
    labeled = add_gap_aware_state_labels(df_gap, frame)
    assert not bool(labeled.loc[0, "exact_5m_available"])
    assert labeled.loc[0, "close_state_5m"] == "GAP_CONTAMINATED"


def test_primary_state_is_close_based_not_intrabar_sequence():
    src = inspect.getsource(add_gap_aware_state_labels)
    assert 'state[exact & (signed_dist > 0.0)] = "SNAPBACK_SIDE"' in src
    assert 'state[exact & (signed_dist < 0.0)] = "BREAKOUT_SIDE"' in src
    assert "first-passage" not in src.lower()


def test_session_retention_is_clock_time_based():
    src = inspect.getsource(state_module)
    assert "pd.Timedelta(hours=24)" in src
    assert "t - s[0] <= 1440" not in src


def test_m15_zone_width_is_preserved_and_used():
    src = inspect.getsource(state_module)
    assert "M15_SWING_ZONE_ATR = 0.10" in src
    assert "_candle_intersects_any_zone(l, h, sw_levels, sw_widths)" in src


def test_activity_fields_are_raw_proxies_not_order_flow_claims():
    src = inspect.getsource(state_module)
    assert '"tick_volume_raw"' in src
    assert '"spread_points_raw"' in src
    assert "order flow" in src.lower()


def test_tail_summary_expected_shortfall():
    s = pd.Series([-0.10, -0.05, 0.0, 0.01, 0.02, 0.03, 0.10])
    out = summarize_tail_distribution(s)
    assert out["n"] == 7
    assert out["adverse_es_5_bps"] < 0
    assert out["favorable_es_5_bps"] > 0


def test_runner_contains_no_strategy_or_broker_execution():
    src = inspect.getsource(runner_module).lower()
    forbidden = ["order_send", "order_check", "run_diagnostic_backtest", "profit_factor", "take_profit"]
    for token in forbidden:
        assert token not in src


def test_runner_binds_expected_dataset_hash():
    src = inspect.getsource(runner_module)
    assert "EXPECTED_DATA_SHA256" in src
    assert "STOP_BLOCKED_DATASET_HASH_MISMATCH" in src
