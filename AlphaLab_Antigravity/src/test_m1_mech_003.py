from __future__ import annotations

import inspect

import numpy as np
import pandas as pd
import pytest

from m1_mech_002.state_engine import EXPECTED_DATA_SHA256, validate_development_frame
from m1_mech_003.control_study import (
    MATCH_EXACT_COLUMNS,
    add_frozen_cem_strata,
    build_balance_table,
    compute_cem_weights,
    day_block_bootstrap_5m,
    detect_breach_events,
    evaluate_mechanism_gates,
)


def _bars(n=620):
    dt = pd.date_range("2018-01-01", periods=n, freq="min", tz="UTC")
    return pd.DataFrame({
        "datetime": dt,
        "open": np.full(n, 100.0),
        "high": np.full(n, 100.1),
        "low": np.full(n, 99.9),
        "close": np.full(n, 100.0),
    })


def test_sealed_holdout_is_blocked():
    df = _bars(20)
    df["datetime"] = pd.date_range("2017-12-31", periods=20, freq="min", tz="UTC")
    with pytest.raises(RuntimeError, match="SEALED_HOLDOUT"):
        validate_development_frame(df)


def test_upper_failed_auction_and_accepted_breakout_are_distinct():
    df = _bars()
    df.loc[510, ["open", "high", "low", "close"]] = [100.0, 101.0, 99.8, 99.95]
    df.loc[511, ["open", "high", "low", "close"]] = [100.0, 102.0, 99.8, 101.5]
    events = detect_breach_events(df)
    got = {(e.bar_index, e.event_class, e.side) for e in events}
    assert (510, "FAILED_AUCTION", "SHORT") in got
    assert (511, "ACCEPTED_BREAKOUT", "SHORT") in got


def test_lower_failed_auction_and_accepted_breakout_are_distinct():
    df = _bars()
    df.loc[510, ["open", "high", "low", "close"]] = [100.0, 100.2, 99.0, 100.05]
    df.loc[511, ["open", "high", "low", "close"]] = [100.0, 100.2, 98.0, 98.5]
    events = detect_breach_events(df)
    got = {(e.bar_index, e.event_class, e.side) for e in events}
    assert (510, "FAILED_AUCTION", "LONG") in got
    assert (511, "ACCEPTED_BREAKOUT", "LONG") in got


def test_exact_level_close_is_not_classified():
    df = _bars()
    df.loc[510, ["high", "close"]] = [101.0, 100.1]
    assert all(e.bar_index != 510 for e in detect_breach_events(df))


def test_double_breach_bar_is_excluded():
    df = _bars()
    df.loc[510, ["high", "low", "close"]] = [101.0, 99.0, 100.0]
    assert all(e.bar_index != 510 for e in detect_breach_events(df))


def _match_frame():
    rows = []
    for cls, vals in [("FAILED_AUCTION", [10.0, 11.0]), ("ACCEPTED_BREAKOUT", [9.0, 10.0, 11.0, 12.0])]:
        for i, x in enumerate(vals):
            rows.append({"event_class": cls, "side": "LONG", "year": 2020, "hour": 10, "location_count": 1, "atr_percentile": 60.0, "path_efficiency": 0.4, "stretch_abs": 1.5, "sweep_depth_atr": 0.2, "datetime": pd.Timestamp(f"2020-01-{i+1:02d}T10:00:00Z"), "exact_5m_available": True, "signed_return_5m": x / 10000.0, "close_state_5m": "SNAPBACK_SIDE"})
    return pd.DataFrame(rows)


def test_cem_control_weights_match_treatment_mass():
    weighted, audit = compute_cem_weights(add_frozen_cem_strata(_match_frame()))
    assert weighted[weighted.event_class == "FAILED_AUCTION"].cem_weight.sum() == pytest.approx(2.0)
    assert weighted[weighted.event_class == "ACCEPTED_BREAKOUT"].cem_weight.sum() == pytest.approx(2.0)
    assert audit["failed_auction_common_support_pct"] == pytest.approx(100.0)


def test_unmatched_strata_get_zero_weight():
    frame = _match_frame(); extra = frame.iloc[[0]].copy(); extra["event_class"] = "FAILED_AUCTION"; extra["year"] = 2021
    weighted, _ = compute_cem_weights(add_frozen_cem_strata(pd.concat([frame, extra], ignore_index=True)))
    row = weighted[(weighted.year == 2021) & (weighted.event_class == "FAILED_AUCTION")].iloc[0]
    assert not bool(row.in_common_support); assert row.cem_weight == 0.0


def test_matching_keys_are_outcome_free():
    forbidden = {"signed_return_5m", "close_state_5m", "mfe_5m_gap_aware", "mae_5m_gap_aware"}
    assert forbidden.isdisjoint(MATCH_EXACT_COLUMNS)


def test_balance_table_has_pre_and_post_smd():
    weighted, _ = compute_cem_weights(add_frozen_cem_strata(_match_frame()))
    balance = build_balance_table(weighted)
    assert set(balance.columns) == {"covariate", "smd_before", "smd_after"}
    assert len(balance) == 4


def test_day_block_bootstrap_is_deterministic():
    weighted, _ = compute_cem_weights(add_frozen_cem_strata(_match_frame()))
    assert day_block_bootstrap_5m(weighted, iterations=50, seed=123) == day_block_bootstrap_5m(weighted, iterations=50, seed=123)


def test_gates_do_not_confirm_without_positive_ci():
    effects = pd.DataFrame([{"horizon_min": 3, "att_mean_diff_bps": 0.1}, {"horizon_min": 5, "att_mean_diff_bps": 0.1}, {"horizon_min": 10, "att_mean_diff_bps": 0.1}])
    yearly = pd.DataFrame({"year": range(2018, 2026), "att_mean_diff_bps": [0.1]*8})
    balance = pd.DataFrame({"covariate": ["x"], "smd_after": [0.01]})
    result = evaluate_mechanism_gates({"failed_auction_common_support_pct": 90.0}, balance, effects, yearly, {"ci95_lower_bps": -0.01})
    assert result["G3_day_block_ci_lower_positive"] is False
    assert result["verdict"] == "MECHANISM_NOT_CONFIRMED"


def test_dataset_hash_is_frozen():
    assert EXPECTED_DATA_SHA256 == "10d6df33c749315824bb9552b139439e6bbfcbac1bed54f272a62696c2f4965e"


def test_control_study_has_no_execution_surface():
    import m1_mech_003.control_study as module
    src = inspect.getsource(module).lower()
    forbidden_calls = ("order_send(", "order_check(", "trade_action_deal", "positionclose(", "mt5.initialize(")
    assert not any(token in src for token in forbidden_calls)
