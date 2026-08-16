from __future__ import annotations

import numpy as np
import pandas as pd

from canonical_v2_execution_engine import CanonicalV2ExecutionEngine, assert_post_evaluation_buffer
from deep_quant_engine import STANDARD_SPECS


def _engine(rows):
    eng = object.__new__(CanonicalV2ExecutionEngine)
    df = pd.DataFrame(rows)
    df["datetime"] = pd.to_datetime(df["datetime"], utc=True)
    df["year"] = df["datetime"].dt.year
    df["quarter"] = df["datetime"].dt.tz_localize(None).dt.to_period("Q").astype(str)
    eng.df = df
    eng.spec = STANDARD_SPECS["GOLD"]
    eng.pip_size = eng.spec.pip_size
    eng.data_file = "SYNTHETIC"
    eng.resolved_path = "SYNTHETIC"
    return eng


def _bars(values):
    out = []
    base = pd.Timestamp("2020-01-01T00:00:00Z")
    for i, (o, h, l, c) in enumerate(values):
        out.append({"datetime": base + pd.Timedelta(minutes=30*i), "open":o, "high":h, "low":l, "close":c})
    return out


def _signal(n, at, direction, sl, tp):
    s = np.zeros(n, dtype=int)
    sd = np.zeros(n, dtype=float)
    td = np.zeros(n, dtype=float)
    s[at] = direction
    sd[at] = sl
    td[at] = tp
    return lambda df: (s.copy(), sd.copy(), td.copy())


def _run(values, at=0, direction=1, sl=5.0, tp=5.0, spread=0.0):
    eng = _engine(_bars(values))
    return eng.run_strategy(_signal(len(values), at, direction, sl, tp), spread_pips=spread, commission_per_lot=0.0)


def test_close_signal_enters_next_open():
    t, _, _ = _run([(90,91,89,90),(100,103,99,101),(101,103,100,102)], tp=2)
    assert len(t) == 1
    assert t.iloc[0]["entry_bar"] == 1
    assert t.iloc[0]["entry_price"] == 100.0


def test_entry_bar_stop_is_managed():
    t, _, _ = _run([(90,91,89,90),(100,101,94,96),(96,97,95,96)], sl=5, tp=20)
    assert len(t) == 1
    assert t.iloc[0]["exit_bar"] == 1
    assert t.iloc[0]["exit_price"] == 95.0
    assert t.iloc[0]["exit_reason"] == "SL"


def test_entry_bar_target_is_managed():
    t, _, _ = _run([(90,91,89,90),(100,106,99,105),(105,106,104,105)], sl=20, tp=5)
    assert len(t) == 1
    assert t.iloc[0]["exit_bar"] == 1
    assert t.iloc[0]["exit_price"] == 105.0


def test_ambiguous_bar_is_stop_first():
    t, _, _ = _run([(90,91,89,90),(100,106,94,100),(100,101,99,100)], sl=5, tp=5)
    assert t.iloc[0]["exit_reason"] == "SL_AMBIGUOUS_PESSIMISTIC"
    assert t.iloc[0]["exit_price"] == 95.0


def test_buy_adverse_gap_stop_fills_worse_open():
    t, _, _ = _run([(90,91,89,90),(100,102,96,100),(90,92,89,91),(91,92,90,91)], sl=5, tp=20)
    assert t.iloc[0]["exit_reason"] == "SL_GAP_OPEN_PESSIMISTIC"
    assert t.iloc[0]["exit_price"] == 90.0
    assert t.iloc[0]["exit_price"] < t.iloc[0]["sl"]


def test_sell_adverse_gap_stop_fills_worse_ask_open():
    t, _, _ = _run([(90,91,89,90),(100,104,98,100),(110,112,109,111),(111,112,110,111)], direction=-1, sl=5, tp=20)
    assert t.iloc[0]["exit_reason"] == "SL_GAP_OPEN_PESSIMISTIC"
    assert t.iloc[0]["exit_price"] == 110.0
    assert t.iloc[0]["exit_price"] > t.iloc[0]["sl"]


def test_normal_buy_stop_without_gap_uses_stop_price():
    t, _, _ = _run([(90,91,89,90),(100,102,96,100),(100,101,94,95),(95,96,94,95)], sl=5, tp=20)
    assert t.iloc[0]["exit_reason"] == "SL"
    assert t.iloc[0]["exit_price"] == 95.0


def test_favorable_tp_gap_does_not_receive_price_improvement():
    t, _, _ = _run([(90,91,89,90),(100,103,98,100),(110,112,109,111),(111,112,110,111)], sl=20, tp=5)
    assert t.iloc[0]["exit_reason"] == "TP"
    assert t.iloc[0]["exit_price"] == 105.0


def test_buy_entry_pays_frozen_spread():
    t, _, _ = _run([(90,91,89,90),(100,104,99,103),(103,104,102,103)], sl=20, tp=2, spread=25.0)
    assert abs(t.iloc[0]["entry_price"] - 100.25) < 1e-12


def test_sell_entry_remains_bid_and_exit_ask_side():
    t, _, _ = _run([(90,91,89,90),(100,101,96,97),(97,98,95,96)], direction=-1, sl=20, tp=2, spread=25.0)
    assert abs(t.iloc[0]["entry_price"] - 100.0) < 1e-12
    assert abs(t.iloc[0]["exit_price"] - 98.0) < 1e-12


def test_commission_contract_is_preserved():
    eng = _engine(_bars([(90,91,89,90),(100,103,99,102),(102,103,101,102)]))
    t, _, _ = eng.run_strategy(_signal(3,0,1,20,2), spread_pips=0, commission_per_lot=7.0, fixed_lot=0.10)
    assert len(t) == 1
    assert abs(t.iloc[0]["pnl_usd"] - 19.3) < 1e-9


def test_one_position_rule_ignores_signal_while_active():
    values = [(90,91,89,90),(100,101,99,100),(100,101,99,100),(100,110,99,109),(109,110,108,109)]
    eng = _engine(_bars(values))
    s = np.array([1,1,0,0,0])
    sd = np.array([20.,20.,0.,0.,0.])
    td = np.array([5.,5.,0.,0.,0.])
    t, _, _ = eng.run_strategy(lambda df:(s,sd,td), spread_pips=0, commission_per_lot=0)
    assert len(t) == 1
    assert t.iloc[0]["entry_bar"] == 1


def test_real_canonical_v2_authorization_is_required():
    eng = CanonicalV2ExecutionEngine()
    assert eng.canonical_authorization["dataset_id"] == "GOLD_M30_CANONICAL_V2"
    assert eng.canonical_authorization["research_eligibility"] == "ELIGIBLE"


def test_post_evaluation_buffer_passes_for_2026q2_120_bars():
    eng = CanonicalV2ExecutionEngine()
    result = assert_post_evaluation_buffer(eng.df, pd.Timestamp("2026-06-30T23:30:00Z"), 120)
    assert result["pass"] is True
    assert result["available_buffer_minutes"] >= result["required_buffer_minutes"]


if __name__ == "__main__":
    tests = [v for k,v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for t in tests:
        t()
        print(f"PASS: {t.__name__}")
    print(f"All {len(tests)} V3.7.3 tests passed")
