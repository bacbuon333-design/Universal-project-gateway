from __future__ import annotations

import inspect
from pathlib import Path

import numpy as np
import pandas as pd

import run_v5a_independent_alpha_rr1 as exp
import distributed_edge_v35 as edge35
from canonical_v2_execution_engine import CanonicalV2ExecutionEngine
from distributed_edge_v38 import EXPECTED_GATE_NAMES


EXPECTED_IDS = ["H401-C1", "H402-C1", "H403-C1", "H404-C1"]


def base_df(n: int = 360, start: str = "2024-01-02T00:00:00Z") -> pd.DataFrame:
    ts = pd.date_range(start, periods=n, freq="30min")
    x = np.arange(n, dtype=float)
    close = 100.0 + 0.03 * np.sin(x / 5.0)
    open_ = close - 0.01 * np.cos(x / 7.0)
    high = np.maximum(open_, close) + 0.20
    low = np.minimum(open_, close) - 0.20
    return pd.DataFrame(
        {"datetime": ts, "open": open_, "high": high, "low": low, "close": close}
    )


def test_exact_four_configs_four_families_one_each():
    assert [c.config_id for c in exp.CONFIGS] == EXPECTED_IDS
    assert len(exp.CONFIGS) == 4
    assert len({c.config_id for c in exp.CONFIGS}) == 4
    assert len({c.family for c in exp.CONFIGS}) == 4
    assert all(sum(c.family == x.family for x in exp.CONFIGS) == 1 for c in exp.CONFIGS)


def test_frozen_family_parameters():
    assert exp.CONFIGS[0].params == {"LOOKBACK": 24}
    assert exp.CONFIGS[1].params == {}
    assert exp.CONFIGS[2].params == {"MIN_BODY_ATR": 0.50}
    assert exp.CONFIGS[3].params == {"PIVOT_FLANK": 2}


def test_frozen_parent_and_canonical_authority():
    assert exp.SCIENTIFIC_PARENT_COMMIT == "5a1a2f8c28f857789943295f6a59df2f1037e72b"
    assert exp.SCIENTIFIC_PARENT_TREE == "b740558d0f1b7904bd1d1f22dddb25adc91693b2"
    assert exp.CANONICAL_SHA == "c48ca44dcecae9eb1c2590c586e27c4bc5f246215c549d0d0bc1201d95d5ea1d"
    assert exp.OUT_DIR.name == "v5a"
    assert exp.RESULT_PATH.name == "V5A_INDEPENDENT_ALPHA_RR1_RESULTS.json"


def test_frozen_rr1_risk_and_cost_contract():
    assert exp.ATR_PERIOD == 14
    assert exp.COMMON_SL_ATR == 1.50
    assert exp.COMMON_TP_ATR == 1.50
    assert exp.COMMON_TP_ATR / exp.COMMON_SL_ATR == 1.0
    assert exp.SPREAD_PIPS == 25.0
    assert exp.SLIPPAGE_PIPS == 0.0
    assert exp.COMMISSION_PER_LOT == 7.0
    assert exp.FIXED_LOT == 0.10
    assert exp.MAX_HOLDING_BARS == 120


def test_exact_audited_14_gate_contract():
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


def test_runner_uses_canonical_v2_engine_only():
    src = inspect.getsource(exp)
    assert "CanonicalV2ExecutionEngine" in src
    assert "DeepQuantEngine(" not in src


def test_canonical_engine_next_bar_and_gap_safe_contract_present():
    src = inspect.getsource(CanonicalV2ExecutionEngine.run_strategy)
    assert "Signal at close i; execution at open i+1" in src
    assert "SL_GAP_OPEN_PESSIMISTIC" in src
    assert "SL_AMBIGUOUS_PESSIMISTIC" in src
    assert 'entry_bar": i + 1' in src


def test_no_closed_h226_or_fresh_oos_path_in_runner():
    src = inspect.getsource(exp).lower().replace("\\", "/")
    forbidden = [
        "gap_z", "resid_min", "signal_h226", "down_gap", "recent_regime",
        "delayed_reversion", "gold_m30_fresh_oos.csv", "alphalab_antigravity/data/oos",
    ]
    for token in forbidden:
        assert token not in src


def test_no_v4_family_implementation_reuse():
    src = inspect.getsource(exp).lower()
    forbidden = [
        "signal_h301", "signal_h302", "signal_h303", "signal_h304",
        "compression_cut", "buffer_atr", "ema24", "ema96", "rolling(48",
        "00:00", "07:30", "15:30",
    ]
    for token in forbidden:
        assert token not in src


def test_no_dynamic_grid_or_batch_two():
    src = inspect.getsource(exp).lower()
    assert "itertools.product" not in src
    assert "parametergrid" not in src
    assert exp.EXPECTED_CONFIG_IDS == EXPECTED_IDS
    assert len(exp.CONFIGS) == 4


def test_common_finalize_is_exact_rr1():
    df = base_df(80)
    a = exp.atr14(df)
    sig = np.zeros(len(df), dtype=int)
    sig[-1] = 1
    out, sl, tp = exp._finalize_common(sig, a)
    assert out[-1] == 1
    assert np.isclose(sl[-1], float(a.iloc[-1]) * 1.50)
    assert np.isclose(tp[-1], float(a.iloc[-1]) * 1.50)
    assert np.isclose(tp[-1] / sl[-1], 1.0)


def test_h401_prior_extreme_excludes_signal_bar_and_reclaims():
    src = inspect.getsource(exp.signal_h401)
    assert ".max().shift(1)" in src
    assert ".min().shift(1)" in src
    df = base_df(60)
    i = len(df) - 1
    prior_low = float(df.loc[i-24:i-1, "low"].min())
    df.loc[i, ["open", "high", "low", "close"]] = [prior_low + 0.10, prior_low + 0.20, prior_low - 0.20, prior_low + 0.05]
    sig, _, _ = exp.signal_h401({"LOOKBACK": 24})(df)
    assert sig[i] == 1


def test_h402_inside_bar_then_mother_break_fixture():
    df = base_df(60)
    m, inside, i = 57, 58, 59
    df.loc[m, ["open", "high", "low", "close"]] = [100.0, 102.0, 98.0, 100.0]
    df.loc[inside, ["open", "high", "low", "close"]] = [100.0, 101.0, 99.0, 100.2]
    df.loc[i, ["open", "high", "low", "close"]] = [101.0, 102.6, 100.8, 102.2]
    sig, _, _ = exp.signal_h402({})(df)
    assert sig[i] == 1


def test_h403_body_engulf_reversal_fixture():
    df = base_df(80)
    p, i = 78, 79
    df.loc[p, ["open", "high", "low", "close"]] = [100.5, 100.6, 99.8, 100.0]
    df.loc[i, ["open", "high", "low", "close"]] = [99.8, 101.0, 99.7, 100.8]
    sig, _, _ = exp.signal_h403({"MIN_BODY_ATR": 0.50})(df)
    assert sig[i] == 1


def test_h404_pivot_is_confirmed_only_after_two_right_bars():
    src = inspect.getsource(exp.signal_h404)
    assert "j = i - flank" in src
    assert "j + flank + 1" in src
    df = base_df(30)
    j, confirm_i, break_i = 15, 17, 18
    # Pivot high at j=15 becomes eligible only at close i=17, after ATR14 warm-up.
    df.loc[j-2:j+2, "high"] = [100.5, 101.0, 103.0, 101.2, 100.8]
    df.loc[confirm_i, "close"] = 102.0
    df.loc[break_i, ["open", "high", "low", "close"]] = [102.5, 103.8, 102.0, 103.5]
    assert np.isfinite(exp.atr14(df).iloc[break_i])
    sig, _, _ = exp.signal_h404({"PIVOT_FLANK": 2})(df)
    assert sig[confirm_i - 1] == 0
    assert sig[break_i] == 1


def test_raw_result_overwrite_guard_is_frozen():
    src = inspect.getsource(exp.run_batch)
    assert "RESULT_PATH.exists()" in src
    assert "refusing rerun/overwrite" in src


def test_governance_flags_are_fail_closed_in_runner_source():
    src = inspect.getsource(exp.run_batch)
    for token in [
        '"fresh_oos_accessed": False',
        '"closed_research_modified": False',
        '"closed_research_descendant_created": False',
        '"h226_reused": False',
        '"v4_h301_h304_reused": False',
        '"strategy_design_authorized_for_deployment": False',
        '"paper_trading_authorized": False',
        '"live_trading_authorized": False',
    ]:
        assert token in src


def test_report_generator_precommit_and_handoff_paths_exist():
    root = Path(__file__).resolve().parents[2]
    assert (root / "AlphaLab_Antigravity" / "src" / "generate_v5a_independent_alpha_rr1_report.py").exists()
    assert (root / "V5A_INDEPENDENT_ALPHA_RR1_PRECOMMIT.md").exists()
    assert (root / "V5A_EXECUTION_HANDOFF.md").exists()


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for t in tests:
        t()
        print(f"PASS: {t.__name__}")
    print(f"All {len(tests)} V5-A tests passed")
