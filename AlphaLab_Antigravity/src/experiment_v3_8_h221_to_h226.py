from __future__ import annotations

"""V3.8 frozen new-mechanism batch on canonical V2 Gold M30.

Exactly 6 families x 4 configs = 24 configurations.
No parameter search, no strategy mutation, no legacy engine/data execution.
"""

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Callable, Dict, List, Tuple
import json
import subprocess

import numpy as np
import pandas as pd

from canonical_v2_execution_engine import CanonicalV2ExecutionEngine
from distributed_edge_v38 import EXPECTED_GATE_NAMES, evaluate_distribution_v38

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "AlphaLab_Antigravity" / "reports" / "v3_8"
CANONICAL_SHA = "c48ca44dcecae9eb1c2590c586e27c4bc5f246215c549d0d0bc1201d95d5ea1d"

SPREAD_PIPS = 25.0
COMMISSION_PER_LOT = 7.0
SLIPPAGE_PIPS = 0.0
FIXED_LOT = 0.10
MAX_HOLDING_BARS = 120


@dataclass(frozen=True)
class ConfigSpec:
    config_id: str
    family: str
    params: Dict[str, float | int]


def git_head() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
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
    return tr.ewm(alpha=1.0 / 14.0, adjust=False, min_periods=14).mean()


def _finalize(sig: np.ndarray, atr: pd.Series, sl_mult: float, rr: float) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    a = atr.to_numpy(dtype=float)
    sl = np.zeros(len(sig), dtype=float)
    tp = np.zeros(len(sig), dtype=float)
    active = (sig != 0) & np.isfinite(a) & (a > 0)
    sig = sig.copy()
    sig[~active] = 0
    sl[active] = a[active] * sl_mult
    tp[active] = sl[active] * rr
    return sig.astype(int), sl, tp


def signal_h221(params: Dict[str, float | int]) -> Callable[[pd.DataFrame], Tuple[np.ndarray, np.ndarray, np.ndarray]]:
    W = float(params["W"])
    rmin = float(params["RMIN"])

    def fn(df: pd.DataFrame):
        a = atr14(df)
        rng = (df["high"] - df["low"]).astype(float)
        safe_rng = rng.replace(0.0, np.nan)
        upper = df["high"] - df[["open", "close"]].max(axis=1)
        lower = df[["open", "close"]].min(axis=1) - df["low"]
        cl = (df["close"] - df["low"]) / safe_rng
        range_atr = rng / a
        long_cond = (lower / safe_rng >= W) & (cl >= 0.70) & (range_atr >= rmin)
        short_cond = (upper / safe_rng >= W) & (cl <= 0.30) & (range_atr >= rmin)
        sig = np.where(long_cond, 1, np.where(short_cond, -1, 0)).astype(int)
        return _finalize(sig, a, 1.25, 2.0)

    return fn


def signal_h222(params: Dict[str, float | int]) -> Callable[[pd.DataFrame], Tuple[np.ndarray, np.ndarray, np.ndarray]]:
    K = int(params["K"])
    zmin = float(params["Z"])

    def fn(df: pd.DataFrame):
        a = atr14(df)
        delta = df["close"].diff()
        all_up = pd.Series(True, index=df.index)
        all_down = pd.Series(True, index=df.index)
        for j in range(K):
            d = delta.shift(j)
            all_up &= d > 0
            all_down &= d < 0
        magnitude = (df["close"] - df["close"].shift(K)).abs() / a
        short_cond = all_up & (magnitude >= zmin)
        long_cond = all_down & (magnitude >= zmin)
        sig = np.where(long_cond, 1, np.where(short_cond, -1, 0)).astype(int)
        return _finalize(sig, a, 1.50, 2.0)

    return fn


def signal_h223(params: Dict[str, float | int]) -> Callable[[pd.DataFrame], Tuple[np.ndarray, np.ndarray, np.ndarray]]:
    N = int(params["N"])
    buffer = float(params["BUFFER"])

    def fn(df: pd.DataFrame):
        a = atr14(df)
        n = len(df)
        sig = np.zeros(n, dtype=int)
        hi = df["high"].to_numpy(dtype=float)
        lo = df["low"].to_numpy(dtype=float)
        close = df["close"].to_numpy(dtype=float)
        av = a.to_numpy(dtype=float)
        for i in range(N + 1, n):
            if not np.isfinite(av[i]) or av[i] <= 0:
                continue
            mother = i - N - 1
            mh, ml = hi[mother], lo[mother]
            inside = True
            for j in range(mother + 1, i):
                if not (hi[j] < mh and lo[j] > ml):
                    inside = False
                    break
            if not inside:
                continue
            b = buffer * av[i]
            if close[i] > mh + b:
                sig[i] = 1
            elif close[i] < ml - b:
                sig[i] = -1
        return _finalize(sig, a, 1.25, 2.0)

    return fn


def signal_h224(params: Dict[str, float | int]) -> Callable[[pd.DataFrame], Tuple[np.ndarray, np.ndarray, np.ndarray]]:
    cl_min = float(params["CL"])
    rmin = float(params["RMIN"])

    def fn(df: pd.DataFrame):
        a = atr14(df)
        rng = df["high"] - df["low"]
        safe_rng = rng.replace(0.0, np.nan)
        cl = (df["close"] - df["low"]) / safe_rng
        outside = (df["high"] > df["high"].shift(1)) & (df["low"] < df["low"].shift(1))
        large = (rng / a) >= rmin
        long_cond = outside & large & (cl >= cl_min)
        short_cond = outside & large & (cl <= (1.0 - cl_min))
        sig = np.where(long_cond, 1, np.where(short_cond, -1, 0)).astype(int)
        return _finalize(sig, a, 1.50, 2.0)

    return fn


def signal_h225(params: Dict[str, float | int]) -> Callable[[pd.DataFrame], Tuple[np.ndarray, np.ndarray, np.ndarray]]:
    L = int(params["L"])
    k = float(params["K"])

    def fn(df: pd.DataFrame):
        a = atr14(df)
        ema = df["close"].ewm(span=L, adjust=False, min_periods=L).mean()
        z = (df["close"] - ema) / a
        turn_up = df["close"] > df["close"].shift(1)
        turn_down = df["close"] < df["close"].shift(1)
        long_cond = (z <= -k) & turn_up
        short_cond = (z >= k) & turn_down
        sig = np.where(long_cond, 1, np.where(short_cond, -1, 0)).astype(int)
        return _finalize(sig, a, 1.50, 2.0)

    return fn


def signal_h226(params: Dict[str, float | int]) -> Callable[[pd.DataFrame], Tuple[np.ndarray, np.ndarray, np.ndarray]]:
    gmin = float(params["G"])
    resid_min = float(params["RESID"])

    def fn(df: pd.DataFrame):
        a = atr14(df)
        n = len(df)
        sig = np.zeros(n, dtype=int)
        ts = pd.to_datetime(df["datetime"], utc=True)
        date = ts.dt.date.to_numpy()
        op = df["open"].to_numpy(dtype=float)
        close = df["close"].to_numpy(dtype=float)
        av = a.to_numpy(dtype=float)
        eps = 1e-12
        for i in range(1, n):
            if date[i] == date[i - 1]:
                continue
            if not np.isfinite(av[i - 1]) or av[i - 1] <= 0 or not np.isfinite(av[i]) or av[i] <= 0:
                continue
            prev_close = close[i - 1]
            gap = op[i] - prev_close
            gap_abs = abs(gap)
            if gap_abs <= eps or gap_abs / av[i - 1] < gmin:
                continue
            # If first bar crossed through prior close, the gap is already fully closed/overshot.
            if (gap > 0 and close[i] <= prev_close) or (gap < 0 and close[i] >= prev_close):
                continue
            residual = abs(close[i] - prev_close) / max(gap_abs, eps)
            if residual < resid_min:
                continue
            sig[i] = -1 if gap > 0 else 1
        return _finalize(sig, a, 1.25, 2.0)

    return fn


CONFIGS: List[ConfigSpec] = [
    ConfigSpec("H221-C1", "H221_WRR", {"W": 0.45, "RMIN": 0.50}),
    ConfigSpec("H221-C2", "H221_WRR", {"W": 0.55, "RMIN": 0.50}),
    ConfigSpec("H221-C3", "H221_WRR", {"W": 0.45, "RMIN": 0.80}),
    ConfigSpec("H221-C4", "H221_WRR", {"W": 0.55, "RMIN": 0.80}),
    ConfigSpec("H222-C1", "H222_CRE", {"K": 3, "Z": 1.50}),
    ConfigSpec("H222-C2", "H222_CRE", {"K": 3, "Z": 2.00}),
    ConfigSpec("H222-C3", "H222_CRE", {"K": 4, "Z": 1.50}),
    ConfigSpec("H222-C4", "H222_CRE", {"K": 4, "Z": 2.00}),
    ConfigSpec("H223-C1", "H223_IBC", {"N": 1, "BUFFER": 0.00}),
    ConfigSpec("H223-C2", "H223_IBC", {"N": 1, "BUFFER": 0.10}),
    ConfigSpec("H223-C3", "H223_IBC", {"N": 2, "BUFFER": 0.00}),
    ConfigSpec("H223-C4", "H223_IBC", {"N": 2, "BUFFER": 0.10}),
    ConfigSpec("H224-C1", "H224_OSR", {"CL": 0.70, "RMIN": 1.00}),
    ConfigSpec("H224-C2", "H224_OSR", {"CL": 0.80, "RMIN": 1.00}),
    ConfigSpec("H224-C3", "H224_OSR", {"CL": 0.70, "RMIN": 1.50}),
    ConfigSpec("H224-C4", "H224_OSR", {"CL": 0.80, "RMIN": 1.50}),
    ConfigSpec("H225-C1", "H225_EDR", {"L": 48, "K": 1.50}),
    ConfigSpec("H225-C2", "H225_EDR", {"L": 48, "K": 2.00}),
    ConfigSpec("H225-C3", "H225_EDR", {"L": 96, "K": 1.50}),
    ConfigSpec("H225-C4", "H225_EDR", {"L": 96, "K": 2.00}),
    ConfigSpec("H226-C1", "H226_DRGR", {"G": 0.05, "RESID": 0.25}),
    ConfigSpec("H226-C2", "H226_DRGR", {"G": 0.10, "RESID": 0.25}),
    ConfigSpec("H226-C3", "H226_DRGR", {"G": 0.05, "RESID": 0.50}),
    ConfigSpec("H226-C4", "H226_DRGR", {"G": 0.10, "RESID": 0.50}),
]

FAMILY_BUILDERS = {
    "H221_WRR": signal_h221,
    "H222_CRE": signal_h222,
    "H223_IBC": signal_h223,
    "H224_OSR": signal_h224,
    "H225_EDR": signal_h225,
    "H226_DRGR": signal_h226,
}


def run_batch() -> pd.DataFrame:
    if len(CONFIGS) != 24 or len({c.config_id for c in CONFIGS}) != 24:
        raise RuntimeError("V3.8 multiple-testing budget drift")
    if len({c.family for c in CONFIGS}) != 6:
        raise RuntimeError("V3.8 must contain exactly 6 mechanism families")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    engine = CanonicalV2ExecutionEngine()
    if engine.canonical_authorization["dataset_sha256"] != CANONICAL_SHA:
        raise RuntimeError("V3.8 canonical SHA drift")

    frozen_code_head = git_head()
    rows: List[Dict] = []

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

        summary, eval_trades, qdf, r4, r8, ydf = evaluate_distribution_v38(cfg.config_id, raw_trades)
        summary["family"] = cfg.family
        summary["params_json"] = json.dumps(cfg.params, sort_keys=True)
        summary["raw_trade_count_all_dates"] = int(len(raw_trades))
        summary["execution_contract"] = engine_summary.get("execution_contract")
        rows.append(summary)

        stem = cfg.config_id.lower().replace("-", "_")
        eval_trades.to_csv(OUT_DIR / f"{stem}_trades.csv", index=False)
        qdf.to_csv(OUT_DIR / f"{stem}_quarters.csv", index=False)
        r4.to_csv(OUT_DIR / f"{stem}_rolling4.csv", index=False)
        r8.to_csv(OUT_DIR / f"{stem}_rolling8.csv", index=False)
        ydf.to_csv(OUT_DIR / f"{stem}_years.csv", index=False)

    all_configs = pd.DataFrame(rows).sort_values("config_id").reset_index(drop=True)
    all_configs.to_csv(OUT_DIR / "v3_8_all_configs.csv", index=False)

    gate_cols = ["config_id", "family", *EXPECTED_GATE_NAMES, "all_gates_pass", "primary_failure_reason", "final_status"]
    all_configs[gate_cols].to_csv(OUT_DIR / "v3_8_gate_matrix.csv", index=False)

    survivors = all_configs[all_configs["all_gates_pass"] == True]["config_id"].tolist()
    batch_conclusion = (
        "ONE OR MORE V3.8 HISTORICAL DISTRIBUTED SURVIVORS REQUIRE A SEPARATE PRECOMMITTED STABILITY BATCH"
        if survivors
        else "NO V3.8 CONFIGURATION PASSED ALL FROZEN DISTRIBUTED-EDGE GATES"
    )

    metadata = {
        "batch": "V3.8 H221-H226",
        "artifact_generation_parent_sha": frozen_code_head,
        "canonical_dataset_id": "GOLD_M30_CANONICAL_V2",
        "canonical_dataset_sha256": CANONICAL_SHA,
        "execution_engine": "CanonicalV2ExecutionEngine",
        "execution_contract": "CANONICAL_V2_GAP_SAFE_V3_7_3",
        "evaluation_entry_quarters": ["2018Q2", "2026Q2"],
        "complete_years": list(range(2019, 2026)),
        "configuration_count": 24,
        "family_count": 6,
        "spread_pips": SPREAD_PIPS,
        "commission_per_lot_usd": COMMISSION_PER_LOT,
        "slippage_pips": SLIPPAGE_PIPS,
        "fixed_lot": FIXED_LOT,
        "max_holding_bars": MAX_HOLDING_BARS,
        "gate_count": len(EXPECTED_GATE_NAMES),
        "gate_names": EXPECTED_GATE_NAMES,
        "survivors": survivors,
        "batch_conclusion": batch_conclusion,
        "configs": [asdict(c) for c in CONFIGS],
    }
    (OUT_DIR / "v3_8_metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")

    return all_configs


if __name__ == "__main__":
    df = run_batch()
    cols = ["config_id", "family", "total_trades", "pf", "expectancy_usd", "all_gates_pass", "primary_failure_reason"]
    print(df[cols].to_string(index=False))
