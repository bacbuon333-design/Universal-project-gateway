from __future__ import annotations

import inspect

import numpy as np
import pandas as pd

import experiment_v3_8_h221_to_h226 as exp
from distributed_edge_v38 import EXPECTED_GATE_NAMES, evaluate_distribution_v38


def base_df(n: int = 160) -> pd.DataFrame:
    ts = pd.date_range("2024-01-02T00:00:00Z", periods=n, freq="30min")
    x = np.arange(n, dtype=float)
    close = 100.0 + 0.15 * np.sin(x / 3.0)
    open_ = close - 0.03 * np.cos(x / 5.0)
    high = np.maximum(open_, close) + 0.30
    low = np.minimum(open_, close) - 0.30
    return pd.DataFrame({
        "datetime": ts,
        "open": open_,
        "high": high,
        "low": low,
        "close": close,
    })


def test_exact_24_configs_and_6_families():
    assert len(exp.CONFIGS) == 24
    assert len({c.config_id for c in exp.CONFIGS}) == 24
    assert len({c.family for c in exp.CONFIGS}) == 6
    assert [c.config_id for c in exp.CONFIGS[:4]] == ["H221-C1", "H221-C2", "H221-C3", "H221-C4"]
    assert [c.config_id for c in exp.CONFIGS[-4:]] == ["H226-C1", "H226-C2", "H226-C3", "H226-C4"]


def test_frozen_canonical_v2_authority():
    assert exp.CANONICAL_SHA == "c48ca44dcecae9eb1c2590c586e27c4bc5f246215c549d0d0bc1201d95d5ea1d"
    assert exp.OUT_DIR.name == "v3_8"


def test_frozen_cost_and_execution_contract_constants():
    assert exp.SPREAD_PIPS == 25.0
    assert exp.COMMISSION_PER_LOT == 7.0
    assert exp.SLIPPAGE_PIPS == 0.0
    assert exp.FIXED_LOT == 0.10
    assert exp.MAX_HOLDING_BARS == 120
    src = inspect.getsource(exp)
    assert "CanonicalV2ExecutionEngine" in src
    assert "DeepQuantEngine(" not in src


def test_h221_wick_rejection_long_fixture():
    df = base_df()
    i = len(df) - 1
    df.loc[i, ["open", "high", "low", "close"]] = [100.0, 101.0, 97.0, 100.8]
    sig, sl, tp = exp.signal_h221({"W": 0.45, "RMIN": 0.50})(df)
    assert sig[i] == 1
    assert sl[i] > 0 and tp[i] == 2.0 * sl[i]


def test_h222_consecutive_run_exhaustion_long_fixture():
    df = base_df()
    start = len(df) - 5
    closes = [104.0, 102.5, 101.0, 99.5, 98.0]
    for j, c in enumerate(closes):
        idx = start + j
        df.loc[idx, "close"] = c
        df.loc[idx, "open"] = c + 0.10
        df.loc[idx, "high"] = c + 0.35
        df.loc[idx, "low"] = c - 0.35
    sig, _, _ = exp.signal_h222({"K": 4, "Z": 1.50})(df)
    assert sig[len(df) - 1] == 1


def test_h223_inside_bar_breakout_long_fixture():
    df = base_df()
    mother = len(df) - 3
    inside = len(df) - 2
    signal = len(df) - 1
    df.loc[mother, ["open", "high", "low", "close"]] = [100.0, 102.0, 98.0, 100.0]
    df.loc[inside, ["open", "high", "low", "close"]] = [100.0, 101.0, 99.0, 100.2]
    df.loc[signal, ["open", "high", "low", "close"]] = [101.0, 103.5, 100.5, 103.0]
    sig, _, _ = exp.signal_h223({"N": 1, "BUFFER": 0.0})(df)
    assert sig[signal] == 1


def test_h224_outside_bar_sweep_long_fixture():
    df = base_df()
    prev = len(df) - 2
    cur = len(df) - 1
    df.loc[prev, ["open", "high", "low", "close"]] = [100.0, 101.0, 99.0, 100.0]
    df.loc[cur, ["open", "high", "low", "close"]] = [99.5, 104.0, 96.0, 103.5]
    sig, _, _ = exp.signal_h224({"CL": 0.70, "RMIN": 1.00})(df)
    assert sig[cur] == 1


def test_h225_ema_deviation_reversion_long_fixture():
    df = base_df()
    # Create a deep two-bar downside displacement, then a small turn upward.
    i1 = len(df) - 2
    i2 = len(df) - 1
    df.loc[i1, ["open", "high", "low", "close"]] = [84.0, 84.5, 79.5, 80.0]
    df.loc[i2, ["open", "high", "low", "close"]] = [80.5, 82.5, 80.0, 82.0]
    sig, _, _ = exp.signal_h225({"L": 48, "K": 1.50})(df)
    assert sig[i2] == 1


def test_h226_daily_reopen_gap_reversion_short_fixture():
    df = base_df(120)
    # Put a UTC date boundary at the final bar and create a positive gap that remains open.
    i = len(df) - 1
    prev = i - 1
    df.loc[prev, "datetime"] = pd.Timestamp("2024-01-04T23:30:00Z")
    df.loc[i, "datetime"] = pd.Timestamp("2024-01-05T00:00:00Z")
    prev_close = float(df.loc[prev, "close"])
    df.loc[i, "open"] = prev_close + 1.0
    df.loc[i, "close"] = prev_close + 0.7
    df.loc[i, "high"] = prev_close + 1.2
    df.loc[i, "low"] = prev_close + 0.5
    sig, _, _ = exp.signal_h226({"G": 0.05, "RESID": 0.25})(df)
    assert sig[i] == -1


def _all_quarters() -> list[str]:
    out = []
    for year in range(2018, 2027):
        for q in range(1, 5):
            label = f"{year}Q{q}"
            if "2018Q2" <= label <= "2026Q2":
                out.append(label)
    return out


def test_full_14_gate_evaluator_can_pass_only_by_conjunction():
    rows = []
    for q in _all_quarters():
        year = int(q[:4])
        quarter = int(q[-1])
        month = 1 + (quarter - 1) * 3
        for k in range(10):
            rows.append({
                "entry_time": pd.Timestamp(year=year, month=month, day=2, hour=k % 10),
                "pnl_usd": 1.0,
            })
    trades = pd.DataFrame(rows)
    summary, _, qdf, r4, r8, ydf = evaluate_distribution_v38("SYNTH-PASS", trades)
    assert len(EXPECTED_GATE_NAMES) == 14
    assert all(summary[g] for g in EXPECTED_GATE_NAMES)
    assert summary["all_gates_pass"] is True
    assert len(qdf) == 33
    assert len(r4) == 30
    assert len(r8) == 26
    assert ydf[ydf["is_complete_calendar_year"]]["year"].tolist() == list(range(2019, 2026))


def test_gate_conjunction_fails_when_economics_fail():
    rows = []
    for q in _all_quarters():
        year = int(q[:4])
        quarter = int(q[-1])
        month = 1 + (quarter - 1) * 3
        for k in range(10):
            rows.append({
                "entry_time": pd.Timestamp(year=year, month=month, day=2, hour=k % 10),
                "pnl_usd": -1.0,
            })
    summary, *_ = evaluate_distribution_v38("SYNTH-FAIL", pd.DataFrame(rows))
    assert summary["gate_E1"] is False
    assert summary["gate_E2"] is False
    assert summary["all_gates_pass"] is False


def test_no_closed_family_ids_in_config_budget():
    ids = " ".join(c.config_id for c in exp.CONFIGS)
    for old in range(204, 221):
        assert f"H{old}-" not in ids


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for t in tests:
        t()
        print(f"PASS: {t.__name__}")
    print(f"All {len(tests)} V3.8 tests passed")
