from __future__ import annotations

"""V5-A frozen RR 1:1 independent alpha-discovery batch on canonical V2 GOLD M30.

Exactly 4 new mechanism families x 1 fixed configuration = 4 configurations.
No parameter search, no dynamic grid, no fresh-OOS access, no V4 entry reuse,
no H226 lineage, and no legacy engine.
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
RESULT_PATH = OUT_DIR / "V5A_RR1_INDEPENDENT_ALPHA_DISCOVERY_RESULTS.json"

SCIENTIFIC_PARENT = "5a1a2f8c28f857789943295f6a59df2f1037e72b"
CANONICAL_SHA = "c48ca44dcecae9eb1c2590c586e27c4bc5f246215c549d0d0bc1201d95d5ea1d"

SPREAD_PIPS = 25.0
COMMISSION_PER_LOT = 7.0
SLIPPAGE_PIPS = 0.0
FIXED_LOT = 0.10
MAX_HOLDING_BARS = 120

ATR_PERIOD = 14
COMMON_SL_ATR = 1.50
COMMON_TP_ATR = 1.50

H401_MIN_BODY_ATR = 0.80
H401_LONG_CLOSE_LOCATION = 0.80
H401_SHORT_CLOSE_LOCATION = 0.20

H402_WICK_BODY_MULT = 1.50
H402_MIN_WICK_ATR = 0.50
H402_LONG_CLOSE_LOCATION = 0.70
H402_SHORT_CLOSE_LOCATION = 0.30

H403_MIN_BODY_ATR = 0.60

H404_MIN_RANGE_ATR = 1.25
H404_LONG_CLOSE_LOCATION = 0.75
H404_SHORT_CLOSE_LOCATION = 0.25

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


def _close_location(df: pd.DataFrame) -> pd.Series:
    span = (df["high"] - df["low"]).replace(0.0, np.nan)
    return (df["close"] - df["low"]) / span


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
    """Single completed-bar impulse body plus extreme closing control."""
    if params:
        raise RuntimeError("H401 has no tunable parameters in V5-A")

    def fn(df: pd.DataFrame):
        a = atr14(df)
        body = (df["close"] - df["open"]).abs()
        body_atr = body / a
        cl = _close_location(df)
        long_cond = (
            (df["close"] > df["open"])
            & (body_atr >= H401_MIN_BODY_ATR)
            & (cl >= H401_LONG_CLOSE_LOCATION)
        )
        short_cond = (
            (df["close"] < df["open"])
            & (body_atr >= H401_MIN_BODY_ATR)
            & (cl <= H401_SHORT_CLOSE_LOCATION)
        )
        sig = np.where(long_cond, 1, np.where(short_cond, -1, 0)).astype(int)
        return _finalize_common(sig, a)

    return fn


def signal_h402(
    params: Dict[str, float | int]
) -> Callable[[pd.DataFrame], Tuple[np.ndarray, np.ndarray, np.ndarray]]:
    """Completed-bar wick failure / auction rejection reversal."""
    if params:
        raise RuntimeError("H402 has no tunable parameters in V5-A")

    def fn(df: pd.DataFrame):
        a = atr14(df)
        body = (df["close"] - df["open"]).abs()
        lower_wick = np.minimum(df["open"], df["close"]) - df["low"]
        upper_wick = df["high"] - np.maximum(df["open"], df["close"])
        cl = _close_location(df)
        long_cond = (
            (lower_wick >= H402_WICK_BODY_MULT * body)
            & (lower_wick >= H402_MIN_WICK_ATR * a)
            & (cl >= H402_LONG_CLOSE_LOCATION)
        )
        short_cond = (
            (upper_wick >= H402_WICK_BODY_MULT * body)
            & (upper_wick >= H402_MIN_WICK_ATR * a)
            & (cl <= H402_SHORT_CLOSE_LOCATION)
        )
        sig = np.where(long_cond, 1, np.where(short_cond, -1, 0)).astype(int)
        return _finalize_common(sig, a)

    return fn


def signal_h403(
    params: Dict[str, float | int]
) -> Callable[[pd.DataFrame], Tuple[np.ndarray, np.ndarray, np.ndarray]]:
    """Two same-direction bars followed by opposite body absorption/engulf."""
    if params:
        raise RuntimeError("H403 has no tunable parameters in V5-A")

    def fn(df: pd.DataFrame):
        a = atr14(df)
        body = (df["close"] - df["open"]).abs()
        long_cond = (
            (df["close"].shift(2) < df["open"].shift(2))
            & (df["close"].shift(1) < df["open"].shift(1))
            & (df["close"] > df["open"])
            & (body >= H403_MIN_BODY_ATR * a)
            & (df["open"] < df["close"].shift(1))
            & (df["close"] > df["open"].shift(1))
        )
        short_cond = (
            (df["close"].shift(2) > df["open"].shift(2))
            & (df["close"].shift(1) > df["open"].shift(1))
            & (df["close"] < df["open"])
            & (body >= H403_MIN_BODY_ATR * a)
            & (df["open"] > df["close"].shift(1))
            & (df["close"] < df["open"].shift(1))
        )
        sig = np.where(long_cond, 1, np.where(short_cond, -1, 0)).astype(int)
        return _finalize_common(sig, a)

    return fn


def signal_h404(
    params: Dict[str, float | int]
) -> Callable[[pd.DataFrame], Tuple[np.ndarray, np.ndarray, np.ndarray]]:
    """Strict outside bar plus range expansion and extreme closing control."""
    if params:
        raise RuntimeError("H404 has no tunable parameters in V5-A")

    def fn(df: pd.DataFrame):
        a = atr14(df)
        bar_range = df["high"] - df["low"]
        cl = _close_location(df)
        outside = (df["high"] > df["high"].shift(1)) & (df["low"] < df["low"].shift(1))
        expanded = bar_range >= H404_MIN_RANGE_ATR * a
        long_cond = outside & expanded & (df["close"] > df["open"]) & (cl >= H404_LONG_CLOSE_LOCATION)
        short_cond = outside & expanded & (df["close"] < df["open"]) & (cl <= H404_SHORT_CLOSE_LOCATION)
        sig = np.where(long_cond, 1, np.where(short_cond, -1, 0)).astype(int)
        return _finalize_common(sig, a)

    return fn


CONFIGS: List[ConfigSpec] = [
    ConfigSpec("H401-C1", "H401_IBC", {}),
    ConfigSpec("H402-C1", "H402_WFR", {}),
    ConfigSpec("H403-C1", "H403_TBAR", {}),
    ConfigSpec("H404-C1", "H404_OBCC", {}),
]

FAMILY_BUILDERS = {
    "H401_IBC": signal_h401,
    "H402_WFR": signal_h402,
    "H403_TBAR": signal_h403,
    "H404_OBCC": signal_h404,
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
        raise RuntimeError("V5-A must contain exactly four mechanism families")
    if any(c.params for c in CONFIGS):
        raise RuntimeError("V5-A authorizes exactly one fixed configuration per family")
    if len(EXPECTED_GATE_NAMES) != 14:
        raise RuntimeError("V5-A evaluator gate contract drift")
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
        summary["final_status"] = "HISTORICAL_CANDIDATE_ONLY" if bool(summary["all_gates_pass"]) else "REJECTED"
        rows.append(summary)

    survivors = [r["config_id"] for r in rows if bool(r["all_gates_pass"])]
    conclusion = (
        "V5-A HISTORICAL CANDIDATE(S) IDENTIFIED — INDEPENDENT VALIDATION REQUIRED"
        if survivors
        else "NO V5-A CONFIGURATION PASSED ALL FROZEN DISTRIBUTED-EDGE GATES"
    )

    payload: Dict[str, object] = {
        "chapter": "V5A_RR1_INDEPENDENT_ALPHA_DISCOVERY",
        "scientific_parent": SCIENTIFIC_PARENT,
        "frozen_code_head": frozen_code_head,
        "canonical_dataset_sha256": CANONICAL_SHA,
        "execution_contract": "CANONICAL_V2_GAP_SAFE_V3_7_3",
        "evaluator_contract": "V3_8_WRAPPER_OVER_V3_5_FULL_14_GATES",
        "gate_names": list(EXPECTED_GATE_NAMES),
        "multiple_testing_budget": {
            "families": 4,
            "configs_per_family": 1,
            "total_configs": 4,
            "automatic_batch_2_authorized": False,
        },
        "common_risk_contract": {
            "atr_period": ATR_PERIOD,
            "sl_atr": COMMON_SL_ATR,
            "tp_atr": COMMON_TP_ATR,
            "rr": "1:1",
            "spread_pips_engine_units": SPREAD_PIPS,
            "gold_pip_size": 0.01,
            "spread_price_usd_per_oz": 0.25,
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
        "v4_failed_entry_semantics_reused": False,
        "h226_lineage_reused": False,
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
