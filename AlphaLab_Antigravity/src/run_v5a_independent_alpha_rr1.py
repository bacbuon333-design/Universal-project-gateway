from __future__ import annotations

"""V5-A frozen independent alpha discovery on canonical V2 GOLD M30.

Exactly four independent price-action families x one configuration each.
Fixed common risk: SL=1.5 ATR14, TP=1.5 ATR14 (1:1 RR).
No parameter search, dynamic grid, fresh-OOS access, or legacy engine.
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
OUT_DIR = ROOT / "AlphaLab_Antigravity" / "reports" / "v5a"
RESULT_PATH = OUT_DIR / "V5A_INDEPENDENT_ALPHA_RR1_RESULTS.json"

SCIENTIFIC_PARENT_COMMIT = "5a1a2f8c28f857789943295f6a59df2f1037e72b"
SCIENTIFIC_PARENT_TREE = "b740558d0f1b7904bd1d1f22dddb25adc91693b2"
CANONICAL_SHA = "c48ca44dcecae9eb1c2590c586e27c4bc5f246215c549d0d0bc1201d95d5ea1d"
EXECUTION_CONTRACT = "CANONICAL_V2_GAP_SAFE_V3_7_3"
EVALUATOR_CONTRACT = "V3_8_WRAPPER_OVER_V3_5_FULL_14_GATES"

SPREAD_PIPS = 25.0
COMMISSION_PER_LOT = 7.0
SLIPPAGE_PIPS = 0.0
FIXED_LOT = 0.10
MAX_HOLDING_BARS = 120

ATR_PERIOD = 14
COMMON_SL_ATR = 1.50
COMMON_TP_ATR = 1.50

EXPECTED_CONFIG_IDS = ["H401-C1", "H402-C1", "H403-C1", "H404-C1"]


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


def signal_h401(
    params: Dict[str, float | int]
) -> Callable[[pd.DataFrame], Tuple[np.ndarray, np.ndarray, np.ndarray]]:
    """Liquidity sweep of a prior 24-bar extreme followed by same-bar reclaim."""
    lookback = int(params["LOOKBACK"])

    def fn(df: pd.DataFrame):
        a = atr14(df)
        prior_high = df["high"].rolling(lookback, min_periods=lookback).max().shift(1)
        prior_low = df["low"].rolling(lookback, min_periods=lookback).min().shift(1)
        long_cond = (df["low"] < prior_low) & (df["close"] > prior_low)
        short_cond = (df["high"] > prior_high) & (df["close"] < prior_high)
        sig = np.where(long_cond, 1, np.where(short_cond, -1, 0)).astype(int)
        return _finalize_common(sig, a)

    return fn


def signal_h402(
    params: Dict[str, float | int]
) -> Callable[[pd.DataFrame], Tuple[np.ndarray, np.ndarray, np.ndarray]]:
    """Breakout from a strict one-bar inside pattern relative to its mother bar."""
    del params

    def fn(df: pd.DataFrame):
        a = atr14(df)
        mother_high = df["high"].shift(2)
        mother_low = df["low"].shift(2)
        inside = (df["high"].shift(1) < mother_high) & (df["low"].shift(1) > mother_low)
        long_cond = inside & (df["close"] > mother_high)
        short_cond = inside & (df["close"] < mother_low)
        sig = np.where(long_cond, 1, np.where(short_cond, -1, 0)).astype(int)
        return _finalize_common(sig, a)

    return fn


def signal_h403(
    params: Dict[str, float | int]
) -> Callable[[pd.DataFrame], Tuple[np.ndarray, np.ndarray, np.ndarray]]:
    """Opposite-color body engulf reversal with a fixed ATR body floor."""
    min_body_atr = float(params["MIN_BODY_ATR"])

    def fn(df: pd.DataFrame):
        a = atr14(df)
        o = df["open"]
        c = df["close"]
        po = o.shift(1)
        pc = c.shift(1)
        body = (c - o).abs()
        large_enough = body >= min_body_atr * a

        long_cond = (
            (pc < po)
            & (c > o)
            & (o <= pc)
            & (c >= po)
            & large_enough
        )
        short_cond = (
            (pc > po)
            & (c < o)
            & (o >= pc)
            & (c <= po)
            & large_enough
        )
        sig = np.where(long_cond, 1, np.where(short_cond, -1, 0)).astype(int)
        return _finalize_common(sig, a)

    return fn


def signal_h404(
    params: Dict[str, float | int]
) -> Callable[[pd.DataFrame], Tuple[np.ndarray, np.ndarray, np.ndarray]]:
    """Break the latest causally confirmed 2-left/2-right swing pivot."""
    flank = int(params["PIVOT_FLANK"])
    if flank != 2:
        raise RuntimeError("H404 is frozen to pivot flank=2")

    def fn(df: pd.DataFrame):
        a = atr14(df)
        n = len(df)
        high = df["high"].to_numpy(dtype=float)
        low = df["low"].to_numpy(dtype=float)
        close = df["close"].to_numpy(dtype=float)
        sig = np.zeros(n, dtype=int)

        latest_high = np.nan
        latest_low = np.nan
        for i in range(2 * flank, n):
            # At close i, pivot candidate j=i-flank has exactly flank right bars closed.
            j = i - flank
            if j - flank >= 0:
                left_h = high[j - flank : j]
                right_h = high[j + 1 : j + flank + 1]
                left_l = low[j - flank : j]
                right_l = low[j + 1 : j + flank + 1]
                if high[j] > np.max(left_h) and high[j] > np.max(right_h):
                    latest_high = high[j]
                if low[j] < np.min(left_l) and low[j] < np.min(right_l):
                    latest_low = low[j]

            if i == 0:
                continue
            long_cond = (
                np.isfinite(latest_high)
                and close[i - 1] <= latest_high
                and close[i] > latest_high
            )
            short_cond = (
                np.isfinite(latest_low)
                and close[i - 1] >= latest_low
                and close[i] < latest_low
            )
            if long_cond:
                sig[i] = 1
            elif short_cond:
                sig[i] = -1

        return _finalize_common(sig, a)

    return fn


CONFIGS: List[ConfigSpec] = [
    ConfigSpec("H401-C1", "H401_LSR", {"LOOKBACK": 24}),
    ConfigSpec("H402-C1", "H402_IBB", {}),
    ConfigSpec("H403-C1", "H403_BER", {"MIN_BODY_ATR": 0.50}),
    ConfigSpec("H404-C1", "H404_CPB", {"PIVOT_FLANK": 2}),
]

FAMILY_BUILDERS = {
    "H401_LSR": signal_h401,
    "H402_IBB": signal_h402,
    "H403_BER": signal_h403,
    "H404_CPB": signal_h404,
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
        raise RuntimeError("V5-A fixed configuration budget drift")
    if len(CONFIGS) != 4 or len({c.config_id for c in CONFIGS}) != 4:
        raise RuntimeError("V5-A must contain exactly four unique configurations")
    if len({c.family for c in CONFIGS}) != 4:
        raise RuntimeError("V5-A must contain exactly four independent families")
    if len(EXPECTED_GATE_NAMES) != 14:
        raise RuntimeError("V5-A evaluator gate contract drift")
    if COMMON_SL_ATR != 1.50 or COMMON_TP_ATR != 1.50:
        raise RuntimeError("V5-A frozen 1:1 ATR risk contract drift")
    if RESULT_PATH.exists():
        raise RuntimeError(f"V5-A raw result already exists; refusing rerun/overwrite: {RESULT_PATH}")

    engine = CanonicalV2ExecutionEngine()
    if engine.canonical_authorization["dataset_sha256"] != CANONICAL_SHA:
        raise RuntimeError("V5-A canonical SHA drift")

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
        "V5-A HISTORICAL CANDIDATE(S) IDENTIFIED — INDEPENDENT VALIDATION REQUIRED"
        if survivors
        else "NO V5-A CONFIGURATION PASSED ALL FROZEN DISTRIBUTED-EDGE GATES"
    )

    payload: Dict[str, object] = {
        "chapter": "V5A_INDEPENDENT_ALPHA_RR1_DISCOVERY",
        "scientific_parent_commit": SCIENTIFIC_PARENT_COMMIT,
        "scientific_parent_tree": SCIENTIFIC_PARENT_TREE,
        "frozen_code_head": frozen_code_head,
        "canonical_dataset_sha256": CANONICAL_SHA,
        "execution_contract": EXECUTION_CONTRACT,
        "evaluator_contract": EVALUATOR_CONTRACT,
        "gate_names": list(EXPECTED_GATE_NAMES),
        "evaluation_contract": {
            "start": "2018Q2",
            "end": "2026Q2",
            "complete_quarters": 33,
            "complete_years": list(range(2019, 2026)),
            "rolling4_windows": 30,
            "rolling8_windows": 26,
        },
        "multiple_testing_budget": {
            "families": 4,
            "configs_per_family": 1,
            "total_configs": 4,
            "dynamic_grid_authorized": False,
            "automatic_batch_2_authorized": False,
            "post_result_tuning_authorized": False,
        },
        "common_risk_contract": {
            "atr_period": ATR_PERIOD,
            "sl_atr": COMMON_SL_ATR,
            "tp_atr": COMMON_TP_ATR,
            "risk_reward": "1:1",
            "spread_pips": SPREAD_PIPS,
            "slippage_pips": SLIPPAGE_PIPS,
            "commission_per_lot": COMMISSION_PER_LOT,
            "fixed_lot": FIXED_LOT,
            "max_holding_bars": MAX_HOLDING_BARS,
        },
        "configs": rows,
        "survivors": survivors,
        "batch_conclusion": conclusion,
        "fresh_oos_accessed": False,
        "closed_research_modified": False,
        "closed_research_descendant_created": False,
        "h226_reused": False,
        "v4_h301_h304_reused": False,
        "strategy_design_authorized_for_deployment": False,
        "paper_trading_authorized": False,
        "live_trading_authorized": False,
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    RESULT_PATH.write_text(
        json.dumps(_jsonable(payload), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(_jsonable(payload), indent=2, sort_keys=True))
    return payload


if __name__ == "__main__":
    run_batch()
