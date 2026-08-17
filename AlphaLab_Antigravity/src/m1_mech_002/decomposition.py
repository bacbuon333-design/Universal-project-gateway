from __future__ import annotations

"""Descriptive factor decomposition for ALAB-M1-MECH-002.

This module does not select winning subgroups. Empirical quartiles are
descriptive diagnostics on the already-seen 2018-2025 development set only.
"""

from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd

from .state_engine import HORIZONS_MINUTES, summarize_tail_distribution


def _quantile_bucket(series: pd.Series, q: int, prefix: str) -> Tuple[pd.Series, List[float]]:
    clean = series.replace([np.inf, -np.inf], np.nan)
    valid = clean.dropna()
    if valid.empty:
        return pd.Series("NA", index=series.index, dtype=object), []
    _, edges = pd.qcut(valid, q=q, retbins=True, duplicates="drop")
    edges = np.unique(edges)
    if len(edges) < 2:
        return pd.Series("Q1", index=series.index, dtype=object), [float(edges[0])] if len(edges) else []
    labels = [f"{prefix}{i+1}" for i in range(len(edges) - 1)]
    bucket = pd.cut(clean, bins=edges, labels=labels, include_lowest=True, duplicates="drop")
    return bucket.astype(object).fillna("NA"), [float(x) for x in edges]


def add_descriptive_factor_bins(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    out = df.copy()
    cutpoints: Dict[str, Any] = {}
    specs = (
        ("path_efficiency", 4, "Q"),
        ("stretch_abs", 4, "Q"),
        ("sweep_depth_atr", 4, "Q"),
        ("reclaim_depth_atr", 4, "Q"),
        ("event_range_atr", 4, "Q"),
        ("close_location_snapback", 4, "Q"),
    )
    for col, q, prefix in specs:
        out[f"{col}_quartile"], edges = _quantile_bucket(out[col], q, prefix)
        cutpoints[f"{col}_quartile_edges"] = edges

    out["volatility_state"] = pd.cut(
        out["atr_percentile"],
        bins=[-np.inf, 50.0, 80.0, 95.0, np.inf],
        labels=["0-49", "50-79", "80-94", "95-100"],
        right=False,
    ).astype(object)

    out["energy_state"] = out["energy_count"].map({0: "E0", 1: "E1", 2: "E2", 3: "E3"})
    out["location_state"] = out["location_count"].map({0: "L0", 1: "L1", 2: "L2", 3: "L3"})
    return out, cutpoints


def summarize_factor(df: pd.DataFrame, factor: str, horizon: int = 5) -> pd.DataFrame:
    ret_col = f"signed_return_{horizon}m"
    rows: List[Dict[str, Any]] = []
    for value, sub in df.groupby(factor, dropna=False, sort=True):
        s = summarize_tail_distribution(sub[ret_col])
        s.update(
            {
                "factor": factor,
                "factor_value": str(value),
                "events_total": int(len(sub)),
                "exact_horizon_events": int(sub[f"exact_{horizon}m_available"].sum()),
                "gap_contaminated_pct": float((1.0 - sub[f"continuous_{horizon}m_path"].mean()) * 100.0),
                "mean_mfe_bps": float(sub[f"mfe_{horizon}m_gap_aware"].mean() * 10000.0),
                "mean_mae_bps": float(sub[f"mae_{horizon}m_gap_aware"].mean() * 10000.0),
            }
        )
        rows.append(s)
    return pd.DataFrame(rows)


def build_factor_summary(df: pd.DataFrame, horizon: int = 5) -> pd.DataFrame:
    factors = [
        "side",
        "energy_state",
        "location_state",
        "path_efficiency_quartile",
        "stretch_abs_quartile",
        "volatility_state",
        "sweep_depth_atr_quartile",
        "reclaim_depth_atr_quartile",
        "event_range_atr_quartile",
        "close_location_snapback_quartile",
        "pdh_pdl_match",
        "session_level_match",
        "m15_swing_zone_match",
    ]
    frames = [summarize_factor(df, f, horizon) for f in factors]
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def build_location_energy_matrix(df: pd.DataFrame, horizon: int = 5) -> pd.DataFrame:
    rows: List[Dict[str, Any]] = []
    for (loc, energy), sub in df.groupby(["location_state", "energy_state"], dropna=False):
        s = summarize_tail_distribution(sub[f"signed_return_{horizon}m"])
        s.update(
            {
                "location_state": str(loc),
                "energy_state": str(energy),
                "mean_mfe_bps": float(sub[f"mfe_{horizon}m_gap_aware"].mean() * 10000.0),
                "mean_mae_bps": float(sub[f"mae_{horizon}m_gap_aware"].mean() * 10000.0),
                "reaccepted_within_5m_pct": float((sub["path_state_5m"] == "REACCEPTED_BREAKOUT_SIDE").mean() * 100.0),
            }
        )
        rows.append(s)
    return pd.DataFrame(rows)


def build_transition_summary(df: pd.DataFrame) -> pd.DataFrame:
    rows: List[Dict[str, Any]] = []
    for h in HORIZONS_MINUTES:
        col = f"close_state_{h}m"
        for state, sub in df.groupby(col, dropna=False):
            rows.append(
                {
                    "horizon_min": h,
                    "state": str(state),
                    "n_events": int(len(sub)),
                    "pct_events": float(len(sub) / len(df) * 100.0) if len(df) else 0.0,
                }
            )
    return pd.DataFrame(rows)


def build_tail_risk_summary(df: pd.DataFrame) -> pd.DataFrame:
    rows: List[Dict[str, Any]] = []
    for h in HORIZONS_MINUTES:
        s = summarize_tail_distribution(df[f"signed_return_{h}m"])
        s["horizon_min"] = h
        s["mean_mfe_bps"] = float(df[f"mfe_{h}m_gap_aware"].mean() * 10000.0)
        s["mean_mae_bps"] = float(df[f"mae_{h}m_gap_aware"].mean() * 10000.0)
        rows.append(s)
    return pd.DataFrame(rows)
