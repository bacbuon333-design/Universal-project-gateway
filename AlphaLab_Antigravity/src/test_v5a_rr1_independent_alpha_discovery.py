from __future__ import annotations

import inspect
from pathlib import Path

import numpy as np
import pandas as pd

import run_v5a_rr1_independent_alpha_discovery as exp
import distributed_edge_v35 as edge35
from canonical_v2_execution_engine import CanonicalV2ExecutionEngine
from distributed_edge_v38 import EXPECTED_GATE_NAMES

EXPECTED_IDS = ["H401-C1", "H402-C1", "H403-C1", "H404-C1"]


def base_df(n: int = 160, start: str = "2024-01-02T00:00:00Z") -> pd.DataFrame:
    ts = pd.date_range(start, periods=n, freq="30min")
    x = np.arange(n, dtype=float)
    close = 100.0 + 0.03 * np.sin(x / 7.0)
    open_ = close - 0.01 * np.cos(x / 9.0)
    high = np.maximum(open_, close) + 0.20
    low = np.minimum(open_, close) - 0.20
    return pd.DataFrame({
        "datetime": ts,
        "open": open_,
        "high": high,
        "low": low,
        "close": close,
    })


def test_exact_four_configs_four_families_one_each():
    assert [c.config_id for c in exp.CONFIGS] == EXPECTED_IDS
    assert len(exp.CONFIGS) == 4
    assert len({c.config_id for c in exp.CONFIGS}) == 4
    assert len({c.family for c in exp.CONFIGS}) == 4
    assert all(c.params == {} for c in exp.CONFIGS)


def test_frozen_family_thresholds():
    assert exp.H401_MIN_BODY_ATR == 0.80
    assert exp.H401_LONG_CLOSE_LOCATION == 0.80
    assert exp.H401_SHORT_CLOSE_LOCATION == 0.20
    assert exp.H402_WICK_BODY_MULT == 1.50
    assert exp.H402_MIN_WICK_ATR == 0.50
    assert exp.H402_LONG_CLOSE_LOCATION == 0.70
    assert exp.H402_SHORT_CLOSE_LOCATION == 0.30
    assert exp.H403_MIN_BODY_ATR == 0.60
    assert exp.H404_MIN_RANGE_ATR == 1.25
    assert exp.H404_LONG_CLOSE_LOCATION == 0.75
    assert exp.H404_SHORT_CLOSE_LOCATION == 0.25


def test_frozen_parent_canonical_authority_and_output_path():
    assert exp.SCIENTIFIC_PARENT == "5a1a2f8c28f857789943295f6a59df2f1037e72b"
    assert exp.CANONICAL_SHA == "c48ca44dcecae9eb1c2590c586e27c4bc5f246215c549d0d0bc1201d95d5ea1d"
    assert exp.OUT_DIR.name == "v5a"
    assert exp.RESULT_PATH.name == "V5A_RR1_INDEPENDENT_ALPHA_DISCOVERY_RESULTS.json"


def test_frozen_common_rr1_risk_and_cost_contract():
    assert exp.ATR_PERIOD == 14
    assert exp.COMMON_SL_ATR == 1.50
    assert exp.COMMON_TP_ATR == 1.50
    assert exp.COMMON_TP_ATR / exp.COMMON_SL_ATR == 1.0
    assert exp.SPREAD_PIPS == 25.0
    assert exp.SLIPPAGE_PIPS == 0.0
    assert exp.COMMISSION_PER_LOT == 7.0
    assert exp.FIXED_LOT == 0.10
    assert exp.MAX_HOLDING_BARS == 120


def test_exact_audited_14_gate_contract_and_windows():
    assert EXPECTED_GATE_NAMES == [
        "gate_A1", "gate_A2", "gate_A3", "gate_A4",
        "gate_B1", "gate_B2",
        "gate_D4_1", "gate_D4_2",
        "gate_D8_1", "gate_D8_2",
        "gate_Y1", "gate_Y2", "gate_E1", "gate_E2",
    ]
    assert edge35.EVAL_START == "2018Q2"
    assert edge35.EVAL_END == "2026Q2"
    assert edge35.EXPECTED_QUARTERS == 33
    assert edge35.EXPECTED_R4 == 30
    assert edge35.EXPECTED_R8 == 26
    assert edge35.FULL_YEARS == list(range(2019, 2026))


def test_gate_threshold_source_has_not_drifted():
    src = inspect.getsource(edge35.evaluate_distribution)
    required = [
        "min_q >= 5",
        "max_share <= 5.0",
        "max_median <= 3.0",
        "trade_gini < 0.30",
        "qshares[3] <= 40.0",
        "qshares[5] <= 60.0",
        "r4_pos >= 70.0",
        "r4_pf >= 65.0",
        "r8_pos >= 75.0",
        "r8_pf >= 70.0",
        "min_full_year_trades >= 20",
        "profitable_year_pct >= 70.0",
        "pf >= 1.25",
        "expectancy > 0.0",
    ]
    for token in required:
        assert token in src


def test_runner_uses_canonical_v2_engine_not_legacy_engine():
    src = inspect.getsource(exp)
    assert "CanonicalV2ExecutionEngine" in src
    assert "DeepQuantEngine(" not in src


def test_canonical_engine_next_bar_and_gap_safe_contract_present():
    src = inspect.getsource(CanonicalV2ExecutionEngine.run_strategy)
    assert "Signal at close i; execution at open i+1" in src
    assert "SL_GAP_OPEN_PESSIMISTIC" in src
    assert "SL_AMBIGUOUS_PESSIMISTIC" in src
    assert '"entry_bar": i + 1' in src


def test_no_v4_entry_function_reuse_in_runner():
    src = inspect.getsource(exp).lower()
    for token in ["signal_h301", "signal_h302", "signal_h303", "signal_h304", "h301_vcb", "h302_usrb", "h303_tper", "h304_emr"]:
        assert token not in src


def test_no_closed_gap_reversion_semantics_in_runner():
    src = inspect.getsource(exp).lower()
    for token in ["gap_z", "resid_min", "signal_h226", "down_gap", "recent_regime", "delayed_reversion"]:
        assert token not in src


def test_no_fresh_oos_dataset_path_in_runner():
    src = inspect.getsource(exp).lower().replace("\\", "/")
    assert "alphalab_antigravity/data/oos" not in src
    assert "gold_m30_fresh_oos.csv" not in src
    assert "gold_m30_fresh_oos.source.json" not in src


def test_no_dynamic_grid_or_automatic_batch_two():
    src = inspect.getsource(exp).lower()
    assert "itertools.product" not in src
    assert "parametergrid" not in src
    assert exp.EXPECTED_CONFIG_IDS == EXPECTED_IDS
    assert all(c.params == {} for c in exp.CONFIGS)


def test_common_risk_finalize_is_exact_rr1():
    df = base_df(80)
    a = exp.atr14(df)
    sig = np.zeros(len(df), dtype=int)
    sig[-1] = 1
    out, sl, tp = exp._finalize_common(sig, a)
    assert out[-1] == 1
    assert np.isclose(sl[-1], float(a.iloc[-1]) * 1.50)
    assert np.isclose(tp[-1], float(a.iloc[-1]) * 1.50)
    assert np.isclose(tp[-1] / sl[-1], 1.0)


def test_h401_impulse_body_fixture():
    df = base_df()
    i = len(df) - 1
    df.loc[i, ["open", "high", "low", "close"]] = [100.0, 101.05, 99.95, 101.0]
    sig, _, _ = exp.signal_h401({})(df)
    assert sig[i] == 1


def test_h402_lower_wick_failure_fixture():
    df = base_df()
    i = len(df) - 1
    df.loc[i, ["open", "high", "low", "close"]] = [100.10, 100.25, 99.00, 100.20]
    sig, _, _ = exp.signal_h402({})(df)
    assert sig[i] == 1


def test_h403_three_bar_absorption_fixture():
    df = base_df()
    i = len(df) - 1
    df.loc[i - 2, ["open", "high", "low", "close"]] = [100.60, 100.65, 99.85, 100.00]
    df.loc[i - 1, ["open", "high", "low", "close"]] = [100.00, 100.05, 99.35, 99.50]
    df.loc[i, ["open", "high", "low", "close"]] = [99.30, 100.40, 99.20, 100.30]
    sig, _, _ = exp.signal_h403({})(df)
    assert sig[i] == 1


def test_h404_outside_bar_closing_control_fixture():
    df = base_df()
    i = len(df) - 1
    df.loc[i - 1, ["open", "high", "low", "close"]] = [100.00, 100.40, 99.70, 100.10]
    df.loc[i, ["open", "high", "low", "close"]] = [100.00, 101.00, 99.50, 100.90]
    sig, _, _ = exp.signal_h404({})(df)
    assert sig[i] == 1


def test_h401_is_single_completed_bar_not_channel_session_or_stat_reentry():
    src = inspect.getsource(exp.signal_h401).lower()
    for token in ["rolling", "shift", "hour", "quantile", "zscore", "ema", "ewm"]:
        assert token not in src


def test_h402_is_wick_rejection_not_rolling_zscore_reentry():
    src = inspect.getsource(exp.signal_h402).lower()
    assert "lower_wick" in src and "upper_wick" in src
    for token in ["rolling", "quantile", "zscore", "ema"]:
        assert token not in src


def test_h403_uses_exact_two_prior_directional_bars_and_current_engulf():
    src = inspect.getsource(exp.signal_h403)
    assert '.shift(2)' in src
    assert '.shift(1)' in src
    assert "H403_MIN_BODY_ATR" in src


def test_h404_uses_only_immediate_prior_full_range():
    src = inspect.getsource(exp.signal_h404)
    assert 'df["high"].shift(1)' in src
    assert 'df["low"].shift(1)' in src
    assert ".rolling(" not in src


def test_raw_result_overwrite_guard_is_frozen():
    src = inspect.getsource(exp.run_batch)
    assert "RESULT_PATH.exists()" in src
    assert "refusing rerun/overwrite" in src


def test_report_generator_precommit_and_handoff_paths_exist_in_frozen_tree():
    root = Path(__file__).resolve().parents[2]
    assert (root / "AlphaLab_Antigravity" / "src" / "generate_v5a_rr1_independent_alpha_report.py").exists()
    assert (root / "V5A_RR1_INDEPENDENT_ALPHA_DISCOVERY_PRECOMMIT.md").exists()
    assert (root / "V5A_EXECUTION_HANDOFF.md").exists()


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for t in tests:
        t()
        print(f"PASS: {t.__name__}")
    print(f"All {len(tests)} V5-A tests passed")
