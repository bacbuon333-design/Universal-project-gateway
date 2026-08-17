from __future__ import annotations

"""V4 frozen independent alpha-discovery batch on canonical V2 GOLD M30.

Exactly 4 mechanism families x 3 configurations = 12 configurations.
No parameter search, no dynamic grid, no fresh-OOS access, no legacy engine.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Tuple
import json
import subprocess

import numpy as np
import pandas as pd

from canonical_v2_execution_engine import CanonicalV2ExecutionEngine
from distributed_edge_v38 import EXPECTED_GATE_NAMES, evaluate_distribution_v38
from distributed_edge_v35 import prepare_evaluation_trades

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "AlphaLab_Antigravity" / "reports" / "v4"
RESULT_PATH = OUT_DIR / "V4_INDEPENDENT_ALPHA_DISCOVERY_RESULTS.json"

CANONICAL_SHA = "c48ca44dcecae9eb1c2590c586e27c4bc5f246215c549d0d0bc1201d95d5ea1d"

SPREAD_PIPS = 25.0
COMMISSION_PER_LOT = 7.0
SLIPPAGE_PIPS = 0.0
FIXED_LOT = 0.10
MAX_HOLDING_BARS = 120

ATR_PERIOD = 14
COMMON_SL_ATR = 1.50
COMMON_TP_ATR = 3.00

EXPECTED_CONFIG_IDS = [
    "H301-C1", "H301-C2", "H301-C3",
    "H302-C1", "H302-C2", "H302-C3",
    "H303-C1", "H303-C2", "H303-C3",
    "H304-C1", "H304-C2", "H304-C3",
]


@dataclass(frozen=True)
class ConfigSpec:
    config_id: str
    family: str
    params: Dict[str, float | int]


def git_head() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip()
    except Exception:
        return "UNAVAILABLE"


def atr14(df: pd.DataFrame) -> pd.Series:
    prev_close = df["close"].shift(1)
    tr = pd.concat(
        [
            df["high"] - df["low"],
            (df["high"] - prev_close).abs(),
            (df["low"] - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.ewm(alpha=1.0 / ATR_PERIOD, adjust=False, min_periods=ATR_PERIOD).mean()


def _finalize_common(
    sig: np.ndarray, atr: pd.Series
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    a = atr.to_numpy(dtype=float)
    out_sig = np.asarray(sig, dtype=int).copy()
    sl = np.zeros(len(out_sig), dtype=float)
    tp = np.zeros(len(out_sig), dtype=float)
    active = (out_sig != 0) & np.isfinite(a) & (a > 0)
    out_sig[~active] = 0
    sl[active] = a[active] * COMMON_SL_ATR
    tp[active] = a[active] * COMMON_TP_ATR
    return out_sig, sl, tp


def signal_h301(
    params: Dict[str, float | int]
) -> Callable[[pd.DataFrame], Tuple[np.ndarray, np.ndarray, np.ndarray]]:
    """Prior-channel compression then close breakout; calibration is causal."""
    lookback = int(params["L"])

    def fn(df: pd.DataFrame):
        a = atr14(df)
        prior_high = df["high"].rolling(lookback, min_periods=lookback).max().shift(1)
        prior_low = df["low"].rolling(lookback, min_periods=lookback).min().shift(1)
        prior_atr = a.shift(1)
        prior_width_atr = (prior_high - prior_low) / prior_atr
        compression_cut = (
            prior_width_atr.rolling(240, min_periods=240).quantile(0.20).shift(1)
        )
        compressed = prior_width_atr <= compression_cut
        long_cond = compressed & (df["close"] > prior_high)
        short_cond = compressed & (df["close"] < prior_low)
        sig = np.where(long_cond, 1, np.where(short_cond, -1, 0)).astype(int)
        return _finalize_common(sig, a)

    return fn


def signal_h302(
    params: Dict[str, float | int]
) -> Callable[[pd.DataFrame], Tuple[np.ndarray, np.ndarray, np.ndarray]]:
    """Fixed UTC 00:00-07:30 range; first 08:00-15:30 close breakout only."""
    buffer_atr = float(params["BUFFER_ATR"])

    def fn(df: pd.DataFrame):
        a = atr14(df)
        n = len(df)
        sig = np.zeros(n, dtype=int)
        ts = pd.to_datetime(df["datetime"], utc=True)
        date_values = ts.dt.date.to_numpy()
        hour = ts.dt.hour.to_numpy()
        minute = ts.dt.minute.to_numpy()
        high = df["high"].to_numpy(dtype=float)
        low = df["low"].to_numpy(dtype=float)
        close = df["close"].to_numpy(dtype=float)
        av = a.to_numpy(dtype=float)

        for day in pd.unique(date_values):
            idx = np.flatnonzero(date_values == day)
            anchor = idx[
                ((hour[idx] >= 0) & (hour[idx] <= 7))
                & ((hour[idx] < 7) | (minute[idx] <= 30))
            ]
            expected_minutes = np.arange(0, 8 * 60, 30)
            actual_minutes = hour[anchor] * 60 + minute[anchor]
            if len(anchor) != 16 or not np.array_equal(actual_minutes, expected_minutes):
                continue

            anchor_high = float(np.max(high[anchor]))
            anchor_low = float(np.min(low[anchor]))
            decision = idx[
                (hour[idx] >= 8)
                & ((hour[idx] < 15) | ((hour[idx] == 15) & (minute[idx] <= 30)))
            ]
            for i in decision:
                if not np.isfinite(av[i]) or av[i] <= 0:
                    continue
                b = buffer_atr * av[i]
                if close[i] > anchor_high + b:
                    sig[i] = 1
                    break
                if close[i] < anchor_low - b:
                    sig[i] = -1
                    break

        return _finalize_common(sig, a)

    return fn


def signal_h303(
    params: Dict[str, float | int]
) -> Callable[[pd.DataFrame], Tuple[np.ndarray, np.ndarray, np.ndarray]]:
    """EMA24/EMA96 directional separation plus pullback recapture."""
    min_sep_atr = float(params["MIN_SEP_ATR"])

    def fn(df: pd.DataFrame):
        a = atr14(df)
        fast = df["close"].ewm(span=24, adjust=False, min_periods=24).mean()
        slow = df["close"].ewm(span=96, adjust=False, min_periods=96).mean()
        sep = (fast - slow).abs() / a
        long_cond = (
            (fast > slow)
            & (sep >= min_sep_atr)
            & (df["close"].shift(1) <= fast.shift(1))
            & (df["close"] > fast)
        )
        short_cond = (
            (fast < slow)
            & (sep >= min_sep_atr)
            & (df["close"].shift(1) >= fast.shift(1))
            & (df["close"] < fast)
        )
        sig = np.where(long_cond, 1, np.where(short_cond, -1, 0)).astype(int)
        return _finalize_common(sig, a)

    return fn


def signal_h304(
    params: Dict[str, float | int]
) -> Callable[[pd.DataFrame], Tuple[np.ndarray, np.ndarray, np.ndarray]]:
    """48-bar close z-score exhaustion re-entry."""
    threshold = float(params["Z"])

    def fn(df: pd.DataFrame):
        a = atr14(df)
        mean = df["close"].rolling(48, min_periods=48).mean()
        std = df["close"].rolling(48, min_periods=48).std(ddof=0).replace(0.0, np.nan)
        z = (df["close"] - mean) / std
        long_cond = (z.shift(1) <= -threshold) & (z > -threshold)
        short_cond = (z.shift(1) >= threshold) & (z < threshold)
        sig = np.where(long_cond, 1, np.where(short_cond, -1, 0)).astype(int)
        return _finalize_common(sig, a)

    return fn


CONFIGS: List[ConfigSpec] = [
    ConfigSpec("H301-C1", "H301_VCB", {"L": 24}),
    ConfigSpec("H301-C2", "H301_VCB", {"L": 48}),
    ConfigSpec("H301-C3", "H301_VCB", {"L": 96}),
    ConfigSpec("H302-C1", "H302_USRB", {"BUFFER_ATR": 0.00}),
    ConfigSpec("H302-C2", "H302_USRB", {"BUFFER_ATR": 0.10}),
    ConfigSpec("H302-C3", "H302_USRB", {"BUFFER_ATR": 0.20}),
    ConfigSpec("H303-C1", "H303_TPER", {"MIN_SEP_ATR": 0.25}),
    ConfigSpec("H303-C2", "H303_TPER", {"MIN_SEP_ATR": 0.50}),
    ConfigSpec("H303-C3", "H303_TPER", {"MIN_SEP_ATR": 0.75}),
    ConfigSpec("H304-C1", "H304_EMR", {"Z": 1.50}),
    ConfigSpec("H304-C2", "H304_EMR", {"Z": 2.00}),
    ConfigSpec("H304-C3", "H304_EMR", {"Z": 2.50}),
]

FAMILY_BUILDERS = {
    "H301_VCB": signal_h301,
    "H302_USRB": signal_h302,
    "H303_TPER": signal_h303,
    "H304_EMR": signal_h304,
}


def _zero_trade_summary(config_id: str) -> Dict[str, object]:
    gates = {g: False for g in EXPECTED_GATE_NAMES}
    return {
        "config_id": config_id,
        "evaluation_start": "2018Q2",
        "evaluation_end": "2026Q2",
        "total_trades": 0,
        "min_trades_q": 0,
        "median_trades_q": 0.0,
        "max_trades_q": 0,
        "max_q_share_pct": 0.0,
        "max_median": 999.0,
        "trade_count_gini": 0.0,
        "net_pnl_usd": 0.0,
        "gross_profit_usd": 0.0,
        "gross_loss_usd": 0.0,
        "pf": 0.0,
        "expectancy_usd": 0.0,
        "win_rate_pct": 0.0,
        "top1_positive_q_share_pct": None,
        "top3_positive_q_share_pct": None,
        "top5_positive_q_share_pct": None,
        "top10_positive_q_share_pct": None,
        "positive_quarter_pool_applicable": False,
        "rolling4_positive_pct": 0.0,
        "rolling4_pf120_pct": 0.0,
        "rolling8_positive_pct": 0.0,
        "rolling8_pf120_pct": 0.0,
        "min_full_year_trades": 0,
        "profitable_full_year_pct": 0.0,
        **gates,
        "all_gates_pass": False,
        "primary_failure_reason": "Gate A1: no evaluation trades",
        "final_status": "REJECTED",
    }


def _jsonable(value):
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if isinstance(value, float) and not np.isfinite(value):
        return None
    return value


def run_batch() -> Dict[str, object]:
    if [c.config_id for c in CONFIGS] != EXPECTED_CONFIG_IDS:
        raise RuntimeError("V4 fixed configuration budget drift")
    if len(CONFIGS) != 12 or len({c.config_id for c in CONFIGS}) != 12:
        raise RuntimeError("V4 must contain exactly 12 unique configurations")
    if len({c.family for c in CONFIGS}) != 4:
        raise RuntimeError("V4 must contain exactly 4 mechanism families")
    if len(EXPECTED_GATE_NAMES) != 14:
        raise RuntimeError("V4 evaluator gate contract drift")
    if RESULT_PATH.exists():
        raise RuntimeError(f"V4 raw result already exists; refusing rerun/overwrite: {RESULT_PATH}")

    engine = CanonicalV2ExecutionEngine()
    if engine.canonical_authorization["dataset_sha256"] != CANONICAL_SHA:
        raise RuntimeError("V4 canonical SHA drift")

    frozen_code_head = git_head()
    rows: List[Dict[str, object]] = []

    for cfg in CONFIGS:
        signal_fn = FAMILY_BUILDERS[cfg.family](cfg.params)
        raw_trades, _, engine_summary = engine.run_strategy(
            signal_fn,
            spread_pips=SPREAD_PIPS,
            slippage_pips=SLIPPAGE_PIPS,
            commission_per_lot=COMMISSION_PER_LOT,
            fixed_lot=FIXED_LOT,
            pessimistic_ambiguous_bars=True,
            max_holding_bars=MAX_HOLDING_BARS,
        )

        eval_trades = prepare_evaluation_trades(raw_trades) if len(raw_trades) else raw_trades
        if len(eval_trades) == 0:
            summary = _zero_trade_summary(cfg.config_id)
        else:
            summary, *_ = evaluate_distribution_v38(cfg.config_id, raw_trades)

        summary["family"] = cfg.family
        summary["params"] = dict(cfg.params)
        summary["raw_trade_count_all_dates"] = int(len(raw_trades))
        summary["execution_contract"] = engine_summary.get("execution_contract")
        summary["gates_passed"] = int(sum(bool(summary[g]) for g in EXPECTED_GATE_NAMES))
        summary["final_status"] = (
            "HISTORICAL_CANDIDATE_ONLY" if bool(summary["all_gates_pass"]) else "REJECTED"
        )
        rows.append(summary)

    survivors = [r["config_id"] for r in rows if bool(r["all_gates_pass"])]
    conclusion = (
        "V4 HISTORICAL CANDIDATE(S) IDENTIFIED — INDEPENDENT VALIDATION REQUIRED"
        if survivors
        else "NO V4 CONFIGURATION PASSED ALL FROZEN DISTRIBUTED-EDGE GATES"
    )

    payload: Dict[str, object] = {
        "chapter": "V4_INDEPENDENT_ALPHA_DISCOVERY",
        "frozen_code_head": frozen_code_head,
        "canonical_dataset_sha256": CANONICAL_SHA,
        "execution_contract": "CANONICAL_V2_GAP_SAFE_V3_7_3",
        "evaluator_contract": "V3_8_WRAPPER_OVER_V3_5_FULL_14_GATES",
        "gate_names": list(EXPECTED_GATE_NAMES),
        "multiple_testing_budget": {
            "families": 4,
            "configs_per_family": 3,
            "total_configs": 12,
            "automatic_batch_2_authorized": False,
        },
        "common_risk_contract": {
            "atr_period": ATR_PERIOD,
            "sl_atr": COMMON_SL_ATR,
            "tp_atr": COMMON_TP_ATR,
            "spread_pips": SPREAD_PIPS,
            "slippage_pips": SLIPPAGE_PIPS,
            "commission_per_lot": COMMISSION_PER_LOT,
            "fixed_lot": FIXED_LOT,
            "max_holding_bars": MAX_HOLDING_BARS,
        },
        "configs": rows,
        "survivors": survivors,
        "survivor_count": len(survivors),
        "batch_conclusion": conclusion,
        "fresh_oos_accessed": False,
        "closed_research_modified": False,
        "closed_research_descendant_created": False,
        "strategy_design_authorized_for_deployment": False,
        "live_trading_authorized": False,
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    RESULT_PATH.write_text(
        json.dumps(_jsonable(payload), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(conclusion)
    print(f"raw_result={RESULT_PATH}")
    print(f"survivors={survivors}")
    return payload


if __name__ == "__main__":
    run_batch()
