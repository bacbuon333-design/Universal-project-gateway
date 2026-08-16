from __future__ import annotations

import json
import os
from typing import Callable, List, Tuple

import numpy as np
import pandas as pd

from deep_quant_engine import DeepQuantEngine
from distributed_edge_v35 import evaluate_distribution

SPREAD_PIPS = 25.0
SLIPPAGE_PIPS = 0.0
COMMISSION_PER_LOT = 7.0
FIXED_LOT = 0.10


def _dt(df: pd.DataFrame) -> pd.Series:
    col = "datetime_str" if "datetime_str" in df.columns else "datetime"
    return pd.to_datetime(df[col])


def _atr14(df: pd.DataFrame) -> np.ndarray:
    h = df["high"].to_numpy(dtype=float)
    l = df["low"].to_numpy(dtype=float)
    c = df["close"].to_numpy(dtype=float)
    prev_c = np.roll(c, 1)
    prev_c[0] = c[0]
    tr = np.maximum(h - l, np.maximum(np.abs(h - prev_c), np.abs(l - prev_c)))
    return pd.Series(tr).rolling(14).mean().to_numpy()


def make_h218_signals(df: pd.DataFrame, sl_mult=1.5, tp_rr=2.0):
    """Previous-day range breakout continuation.

    The previous completed UTC day's high/low is assigned to every bar of the
    current day. Crossing compares current and previous close against that SAME
    current-day previous-day level, per the pre-implementation clarification.
    """
    c = df["close"].to_numpy(dtype=float)
    atr = _atr14(df)
    dt = _dt(df)
    day = dt.dt.date

    daily = pd.DataFrame({"day": day, "high": df["high"], "low": df["low"]}).groupby("day").agg(
        day_high=("high", "max"), day_low=("low", "min")
    )
    previous = daily.shift(1).rename(columns={"day_high": "prev_high", "day_low": "prev_low"})
    mapped = pd.DataFrame({"day": day}).join(previous, on="day")
    prev_high = mapped["prev_high"].to_numpy(dtype=float)
    prev_low = mapped["prev_low"].to_numpy(dtype=float)

    sig = np.zeros(len(df), dtype=int)
    sl = np.zeros(len(df), dtype=float)
    tp = np.zeros(len(df), dtype=float)

    for i in range(14, len(df)):
        if not (np.isfinite(atr[i]) and np.isfinite(prev_high[i]) and np.isfinite(prev_low[i])):
            continue
        cur_atr = max(float(atr[i]), 0.50)
        long_cross = c[i] > prev_high[i] and c[i - 1] <= prev_high[i]
        short_cross = c[i] < prev_low[i] and c[i - 1] >= prev_low[i]
        if long_cross:
            sig[i] = 1
        elif short_cross:
            sig[i] = -1
        else:
            continue
        sl[i] = sl_mult * cur_atr
        tp[i] = sl[i] * tp_rr

    return sig, sl, tp


def make_h219_signals(df: pd.DataFrame, n_bars=6, threshold=1.5, sl_mult=1.5, tp_rr=2.0):
    """Normalized multi-bar impulse threshold-cross continuation."""
    c = df["close"].to_numpy(dtype=float)
    atr = _atr14(df)
    z = np.full(len(df), np.nan, dtype=float)
    z[n_bars:] = (c[n_bars:] - c[:-n_bars]) / atr[n_bars:]

    sig = np.zeros(len(df), dtype=int)
    sl = np.zeros(len(df), dtype=float)
    tp = np.zeros(len(df), dtype=float)

    start = max(14, n_bars + 1)
    for i in range(start, len(df)):
        if not (np.isfinite(z[i]) and np.isfinite(z[i - 1]) and np.isfinite(atr[i])):
            continue
        cur_atr = max(float(atr[i]), 0.50)
        if z[i] > threshold and z[i - 1] <= threshold:
            sig[i] = 1
        elif z[i] < -threshold and z[i - 1] >= -threshold:
            sig[i] = -1
        else:
            continue
        sl[i] = sl_mult * cur_atr
        tp[i] = sl[i] * tp_rr

    return sig, sl, tp


def make_h220_signals(df: pd.DataFrame, threshold=1.0, sl_mult=1.5, tp_rr=2.0):
    """08:00-12:00 UTC morning signed-return carry, signaled at 12:00 close."""
    dt = _dt(df)
    atr = _atr14(df)
    day = dt.dt.date
    hour = dt.dt.hour.to_numpy()
    minute = dt.dt.minute.to_numpy()

    temp = pd.DataFrame({
        "day": day,
        "hour": dt.dt.hour,
        "open": df["open"].to_numpy(dtype=float),
        "close": df["close"].to_numpy(dtype=float),
    })
    morning = temp[(temp["hour"] >= 8) & (temp["hour"] < 12)].groupby("day").agg(
        morning_open=("open", "first"), morning_close=("close", "last")
    )
    mapped = pd.DataFrame({"day": day}).join(morning, on="day")
    morning_return = (mapped["morning_close"] - mapped["morning_open"]).to_numpy(dtype=float)

    sig = np.zeros(len(df), dtype=int)
    sl = np.zeros(len(df), dtype=float)
    tp = np.zeros(len(df), dtype=float)

    for i in range(15, len(df)):
        if not (hour[i] == 12 and minute[i] == 0):
            continue
        if not (np.isfinite(morning_return[i]) and np.isfinite(atr[i - 1]) and np.isfinite(atr[i])):
            continue
        norm_atr = max(float(atr[i - 1]), 0.50)
        morning_z = float(morning_return[i]) / norm_atr
        if morning_z > threshold:
            sig[i] = 1
        elif morning_z < -threshold:
            sig[i] = -1
        else:
            continue
        sl[i] = sl_mult * max(float(atr[i]), 0.50)
        tp[i] = sl[i] * tp_rr

    return sig, sl, tp


def build_configs() -> List[Tuple[str, str, str, Callable]]:
    configs = [
        ("H-218-C1", "PDBC", "Prev-day breakout SL1.5 RR2.0", lambda df: make_h218_signals(df, 1.5, 2.0)),
        ("H-218-C2", "PDBC", "Prev-day breakout SL1.5 RR2.5", lambda df: make_h218_signals(df, 1.5, 2.5)),
        ("H-218-C3", "PDBC", "Prev-day breakout SL2.0 RR2.0", lambda df: make_h218_signals(df, 2.0, 2.0)),
        ("H-218-C4", "PDBC", "Prev-day breakout SL2.0 RR2.5", lambda df: make_h218_signals(df, 2.0, 2.5)),
        ("H-219-C1", "NIC", "Impulse N6 K1.5 SL1.5 RR2.0", lambda df: make_h219_signals(df, 6, 1.5, 1.5, 2.0)),
        ("H-219-C2", "NIC", "Impulse N6 K2.0 SL1.5 RR2.0", lambda df: make_h219_signals(df, 6, 2.0, 1.5, 2.0)),
        ("H-219-C3", "NIC", "Impulse N12 K1.5 SL1.5 RR2.0", lambda df: make_h219_signals(df, 12, 1.5, 1.5, 2.0)),
        ("H-219-C4", "NIC", "Impulse N12 K2.0 SL1.5 RR2.0", lambda df: make_h219_signals(df, 12, 2.0, 1.5, 2.0)),
        ("H-220-C1", "LMDC", "Morning carry K1.0 SL1.5 RR2.0", lambda df: make_h220_signals(df, 1.0, 1.5, 2.0)),
        ("H-220-C2", "LMDC", "Morning carry K1.0 SL1.5 RR2.5", lambda df: make_h220_signals(df, 1.0, 1.5, 2.5)),
        ("H-220-C3", "LMDC", "Morning carry K1.5 SL1.5 RR2.0", lambda df: make_h220_signals(df, 1.5, 1.5, 2.0)),
        ("H-220-C4", "LMDC", "Morning carry K1.5 SL1.5 RR2.5", lambda df: make_h220_signals(df, 1.5, 1.5, 2.5)),
    ]
    ids = [x[0] for x in configs]
    assert len(configs) == 12 and len(set(ids)) == 12
    assert ids == [f"H-{h}-C{c}" for h in (218, 219, 220) for c in range(1, 5)]
    return configs


def run_batch() -> pd.DataFrame:
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    out_dir = os.path.join(root, "AlphaLab_Antigravity", "reports", "v3_5")
    os.makedirs(out_dir, exist_ok=True)

    engine = DeepQuantEngine("GOLD_M30.csv")
    summaries = []

    for config_id, family, description, signal_fn in build_configs():
        print(f"Running {config_id} {family}: {description}")
        raw_trades, _, _ = engine.run_strategy(
            signal_fn,
            spread_pips=SPREAD_PIPS,
            slippage_pips=SLIPPAGE_PIPS,
            commission_per_lot=COMMISSION_PER_LOT,
            fixed_lot=FIXED_LOT,
            pessimistic_ambiguous_bars=True,
        )
        if len(raw_trades) == 0:
            raise RuntimeError(f"{config_id}: engine returned zero trades")

        summary, eval_trades, qdf, r4, r8, ydf = evaluate_distribution(config_id, raw_trades)
        summary.update({
            "family": family,
            "description": description,
            "baseline_spread_pips": SPREAD_PIPS,
            "baseline_slippage_pips": SLIPPAGE_PIPS,
            "commission_per_lot": COMMISSION_PER_LOT,
            "fixed_lot": FIXED_LOT,
        })
        summaries.append(summary)

        tag = config_id.lower().replace("-", "_")
        eval_trades.to_csv(os.path.join(out_dir, f"{tag}_evaluation_trades.csv"), index=False)
        qdf.to_csv(os.path.join(out_dir, f"{tag}_quarters.csv"), index=False)
        r4.to_csv(os.path.join(out_dir, f"{tag}_rolling4q.csv"), index=False)
        r8.to_csv(os.path.join(out_dir, f"{tag}_rolling8q.csv"), index=False)
        ydf.to_csv(os.path.join(out_dir, f"{tag}_years.csv"), index=False)
        with open(os.path.join(out_dir, f"{tag}_diagnostics.json"), "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, allow_nan=True)

        print(
            f"  trades={summary['total_trades']} minQ={summary['min_trades_q']} "
            f"PF={summary['pf']:.3f} R4={summary['rolling4_positive_pct']:.1f}% "
            f"R8={summary['rolling8_positive_pct']:.1f}% years+={summary['profitable_full_year_pct']:.1f}% "
            f"status={summary['final_status']}"
        )

    out = pd.DataFrame(summaries)
    assert len(out) == 12
    assert out["config_id"].is_unique
    out.to_csv(os.path.join(out_dir, "batch1_summary.csv"), index=False)

    metadata = {
        "config_count": 12,
        "families": ["PDBC", "NIC", "LMDC"],
        "evaluation_window": "2018Q2..2026Q2",
        "rolling4_windows": 30,
        "rolling8_windows": 26,
        "full_years": "2019..2025",
        "full_gate_count": 14,
        "survivor_count": int(out["all_gates_pass"].sum()),
    }
    with open(os.path.join(out_dir, "batch1_metadata.json"), "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    return out


if __name__ == "__main__":
    run_batch()
