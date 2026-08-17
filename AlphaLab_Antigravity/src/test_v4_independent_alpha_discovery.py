from __future__ import annotations

import inspect
from pathlib import Path

import numpy as np
import pandas as pd

import run_v4_independent_alpha_discovery as exp
import distributed_edge_v35 as edge35
from canonical_v2_execution_engine import CanonicalV2ExecutionEngine
from distributed_edge_v38 import EXPECTED_GATE_NAMES


EXPECTED_IDS = [
    "H301-C1", "H301-C2", "H301-C3",
    "H302-C1", "H302-C2", "H302-C3",
    "H303-C1", "H303-C2", "H303-C3",
    "H304-C1", "H304-C2", "H304-C3",
]


def base_df(n: int = 360, start: str = "2024-01-02T00:00:00Z") -> pd.DataFrame:
    ts = pd.date_range(start, periods=n, freq="30min")
    x = np.arange(n, dtype=float)
    close = 100.0 + 0.05 * np.sin(x / 5.0)
    open_ = close - 0.01 * np.cos(x / 7.0)
    high = np.maximum(open_, close) + 0.20
    low = np.minimum(open_, close) - 0.20
    return pd.DataFrame({
        "datetime": ts,
        "open": open_,
        "high": high,
        "low": low,
        "close": close,
    })


def test_exact_12_configs_and_4_families():
    assert [c.config_id for c in exp.CONFIGS] == EXPECTED_IDS
    assert len(exp.CONFIGS) == 12
    assert len({c.config_id for c in exp.CONFIGS}) == 12
    assert len({c.family for c in exp.CONFIGS}) == 4


def test_frozen_family_parameters():
    assert [c.params for c in exp.CONFIGS[:3]] == [{"L": 24}, {"L": 48}, {"L": 96}]
    assert [c.params for c in exp.CONFIGS[3:6]] == [
        {"BUFFER_ATR": 0.00}, {"BUFFER_ATR": 0.10}, {"BUFFER_ATR": 0.20}
    ]
    assert [c.params for c in exp.CONFIGS[6:9]] == [
        {"MIN_SEP_ATR": 0.25}, {"MIN_SEP_ATR": 0.50}, {"MIN_SEP_ATR": 0.75}
    ]
    assert [c.params for c in exp.CONFIGS[9:12]] == [{"Z": 1.50}, {"Z": 2.00}, {"Z": 2.50}]


def test_frozen_canonical_authority_and_output_path():
    assert exp.CANONICAL_SHA == "c48ca44dcecae9eb1c2590c586e27c4bc5f246215c549d0d0bc1201d95d5ea1d"
    assert exp.OUT_DIR.name == "v4"
    assert exp.RESULT_PATH.name == "V4_INDEPENDENT_ALPHA_DISCOVERY_RESULTS.json"


def test_frozen_common_risk_and_cost_contract():
    assert exp.ATR_PERIOD == 14
    assert exp.COMMON_SL_ATR == 1.50
    assert exp.COMMON_TP_ATR == 3.00
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


def test_runner_uses_canonical_v2_engine_not_legacy_engine():
    src = inspect.getsource(exp)
    assert "CanonicalV2ExecutionEngine" in src
    assert "DeepQuantEngine(" not in src


def test_canonical_engine_next_bar_and_gap_safe_contract_present():
    src = inspect.getsource(CanonicalV2ExecutionEngine.run_strategy)
    assert "Signal at close i; execution at open i+1" in src
    assert "SL_GAP_OPEN_PESSIMISTIC" in src
    assert "SL_AMBIGUOUS_PESSIMISTIC" in src
    assert "entry_bar\": i + 1" in src


def test_no_closed_gap_reversion_mechanism_in_runner():
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


def test_common_risk_finalize_is_identical_across_signals():
    df = base_df(80)
    a = exp.atr14(df)
    sig = np.zeros(len(df), dtype=int)
    sig[-1] = 1
    out, sl, tp = exp._finalize_common(sig, a)
    assert out[-1] == 1
    assert np.isclose(sl[-1], float(a.iloc[-1]) * 1.50)
    assert np.isclose(tp[-1], float(a.iloc[-1]) * 3.00)
    assert np.isclose(tp[-1] / sl[-1], 2.0)


def test_h301_prior_channel_excludes_signal_bar():
    src = inspect.getsource(exp.signal_h301)
    assert ".max().shift(1)" in src
    assert ".min().shift(1)" in src
    assert "quantile(0.20).shift(1)" in src


def test_h302_exact_anchor_and_one_signal_per_day_fixture():
    df = base_df(48, "2024-01-02T00:00:00Z")
    i = 16  # 08:00 UTC
    prior_high = float(df.loc[:15, "high"].max())
    df.loc[i, "open"] = prior_high + 0.30
    df.loc[i, "close"] = prior_high + 0.50
    df.loc[i, "high"] = prior_high + 0.70
    df.loc[i, "low"] = prior_high + 0.10
    sig, _, _ = exp.signal_h302({"BUFFER_ATR": 0.00})(df)
    assert sig[i] == 1
    assert int(np.count_nonzero(sig)) == 1


def test_h304_reentry_fixture():
    df = base_df(80)
    i1 = len(df) - 2
    i2 = len(df) - 1
    df.loc[i1, ["open", "high", "low", "close"]] = [90.2, 90.5, 89.5, 90.0]
    df.loc[i2, ["open", "high", "low", "close"]] = [99.5, 100.5, 99.0, 100.0]
    sig, _, _ = exp.signal_h304({"Z": 1.50})(df)
    assert sig[i2] == 1


def test_raw_result_overwrite_guard_is_frozen():
    src = inspect.getsource(exp.run_batch)
    assert "RESULT_PATH.exists()" in src
    assert "refusing rerun/overwrite" in src


def test_report_generator_and_handoff_paths_exist_in_frozen_tree():
    root = Path(__file__).resolve().parents[2]
    assert (root / "AlphaLab_Antigravity" / "src" / "generate_v4_independent_alpha_report.py").exists()
    assert (root / "V4_INDEPENDENT_ALPHA_DISCOVERY_PRECOMMIT.md").exists()
    assert (root / "V4_EXECUTION_HANDOFF.md").exists()


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for t in tests:
        t()
        print(f"PASS: {t.__name__}")
    print(f"All {len(tests)} V4 tests passed")
