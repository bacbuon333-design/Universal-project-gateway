from __future__ import annotations

"""Matched-control mechanism study for ALAB-M1-MECH-003.

This module compares prior-extreme breaches that close back inside the old
range (FAILED_AUCTION treatment) with breaches that close beyond the breached
extreme (ACCEPTED_BREAKOUT control). It is research-only and deliberately
contains no strategy, PnL, order, or broker-execution logic.
"""

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Sequence, Tuple

import numpy as np
import pandas as pd

from m1_fusion.features import (
    ATR_PERCENTILE_THRESHOLD,
    EFFICIENCY_THRESHOLD,
    PATH_WINDOW,
    PRIOR_EXTREME_LOOKBACK,
    ROBUST_WINDOW,
    ROBUST_Z_THRESHOLD,
    compute_atr14,
    compute_atr_percentiles,
    compute_path_efficiency,
    compute_prior_extremes,
    compute_robust_stretch_z,
)
from m1_mech_002.state_engine import (
    EXPECTED_DATA_SHA256,
    HORIZONS_MINUTES,
    add_gap_aware_state_labels,
    build_mechanism_event_frame,
    validate_development_frame,
)

EXPERIMENT_ID = "ALAB-M1-MECH-003"
PRIMARY_HORIZON_MINUTES = 5
BOOTSTRAP_ITERATIONS = 2000
BOOTSTRAP_SEED = 20260817
MIN_COMMON_SUPPORT_TREATMENT_PCT = 70.0
MAX_MATCHED_ABS_SMD = 0.10
MIN_POSITIVE_YEARS = 6

# Frozen, outcome-blind CEM cut-points. No empirical quartiles are learned after outcomes.
ATR_PCT_EDGES: Tuple[float, ...] = (-np.inf, 50.0, 80.0, 95.0, np.inf)
EFFICIENCY_EDGES: Tuple[float, ...] = (-np.inf, 0.25, 0.50, 0.65, 0.80, np.inf)
STRETCH_ABS_EDGES: Tuple[float, ...] = (-np.inf, 1.0, 2.0, 3.0, np.inf)
SWEEP_DEPTH_ATR_EDGES: Tuple[float, ...] = (-np.inf, 0.10, 0.25, 0.50, 1.0, np.inf)

MATCH_EXACT_COLUMNS: Tuple[str, ...] = (
    "side",
    "year",
    "hour",
    "location_count",
    "atr_bin",
    "efficiency_bin",
    "stretch_bin",
    "sweep_bin",
)

BALANCE_CONTINUOUS_COLUMNS: Tuple[str, ...] = (
    "atr_percentile",
    "path_efficiency",
    "stretch_abs",
    "sweep_depth_atr",
)


@dataclass(frozen=True)
class BreachEvent:
    event_id: int
    bar_index: int
    datetime: pd.Timestamp
    side: str
    event_class: str
    prior_extreme: float
    price_open: float
    price_high: float
    price_low: float
    price_close: float
    efficiency_ratio: float
    path_eff_match: bool
    stretch_z: float
    stretch_z_match: bool
    atr14: float
    atr_percentile: float
    atr_pct_match: bool


def detect_breach_events(df: pd.DataFrame) -> List[BreachEvent]:
    """Detect treatment/control breaches using only data available at event close."""
    validate_development_frame(df)
    n = len(df)
    if n < 550:
        return []

    atr = compute_atr14(df)
    prior_high, prior_low = compute_prior_extremes(df, PRIOR_EXTREME_LOOKBACK)
    eff_ratio, is_up, is_down = compute_path_efficiency(df, PATH_WINDOW)
    stretch_z = compute_robust_stretch_z(df, ROBUST_WINDOW)
    atr_pct = compute_atr_percentiles(atr, 500)

    opens = df["open"].to_numpy(dtype=float)
    highs = df["high"].to_numpy(dtype=float)
    lows = df["low"].to_numpy(dtype=float)
    closes = df["close"].to_numpy(dtype=float)
    atr_vals = atr.to_numpy(dtype=float)
    ph = prior_high.to_numpy(dtype=float)
    pl = prior_low.to_numpy(dtype=float)
    dts = pd.DatetimeIndex(df["datetime"])

    events: List[BreachEvent] = []
    event_id = 0
    for t in range(510, n - 35):
        a = atr_vals[t]
        if not np.isfinite(a) or a <= 0:
            continue
        upper = np.isfinite(ph[t]) and highs[t] > ph[t]
        lower = np.isfinite(pl[t]) and lows[t] < pl[t]
        if upper == lower:
            continue

        if upper:
            if closes[t] < ph[t]:
                event_class = "FAILED_AUCTION"
            elif closes[t] > ph[t]:
                event_class = "ACCEPTED_BREAKOUT"
            else:
                continue
            side = "SHORT"
            prior = ph[t]
            aligned = bool(is_up[t])
            z_match = bool(stretch_z[t] >= ROBUST_Z_THRESHOLD)
        else:
            if closes[t] > pl[t]:
                event_class = "FAILED_AUCTION"
            elif closes[t] < pl[t]:
                event_class = "ACCEPTED_BREAKOUT"
            else:
                continue
            side = "LONG"
            prior = pl[t]
            aligned = bool(is_down[t])
            z_match = bool(stretch_z[t] <= -ROBUST_Z_THRESHOLD)

        e = float(eff_ratio[t])
        ap = float(atr_pct[t])
        events.append(BreachEvent(
            event_id=event_id,
            bar_index=t,
            datetime=pd.Timestamp(dts[t]),
            side=side,
            event_class=event_class,
            prior_extreme=float(prior),
            price_open=float(opens[t]),
            price_high=float(highs[t]),
            price_low=float(lows[t]),
            price_close=float(closes[t]),
            efficiency_ratio=e,
            path_eff_match=bool(aligned and e >= EFFICIENCY_THRESHOLD),
            stretch_z=float(stretch_z[t]),
            stretch_z_match=z_match,
            atr14=float(a),
            atr_percentile=ap,
            atr_pct_match=bool(ap >= ATR_PERCENTILE_THRESHOLD),
        ))
        event_id += 1
    return events


def build_counterfactual_frame(df: pd.DataFrame, events: Sequence[BreachEvent]) -> pd.DataFrame:
    """Build the neutral MECH-002 factors/outcomes for both event classes."""
    base = build_mechanism_event_frame(df, events)
    if base.empty:
        return base
    class_by_id = {int(e.event_id): e.event_class for e in events}
    base["event_class"] = base["event_id"].map(class_by_id)
    base = add_gap_aware_state_labels(df, base, horizons=HORIZONS_MINUTES)
    return base


def _cut(values: pd.Series, edges: Tuple[float, ...], labels_prefix: str) -> pd.Series:
    labels = [f"{labels_prefix}{i}" for i in range(len(edges) - 1)]
    return pd.cut(values, bins=list(edges), labels=labels, include_lowest=True, right=False).astype(str)


def add_frozen_cem_strata(frame: pd.DataFrame) -> pd.DataFrame:
    """Attach frozen coarsened-exact-matching strata; outcomes are not used."""
    out = frame.copy()
    out["atr_bin"] = _cut(out["atr_percentile"], ATR_PCT_EDGES, "A")
    out["efficiency_bin"] = _cut(out["path_efficiency"], EFFICIENCY_EDGES, "E")
    out["stretch_bin"] = _cut(out["stretch_abs"], STRETCH_ABS_EDGES, "Z")
    out["sweep_bin"] = _cut(out["sweep_depth_atr"], SWEEP_DEPTH_ATR_EDGES, "S")
    out["cem_stratum"] = out[list(MATCH_EXACT_COLUMNS)].astype(str).agg("|".join, axis=1)
    return out


def compute_cem_weights(frame: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """Keep common-support strata and create deterministic ATT-style CEM weights."""
    if "cem_stratum" not in frame.columns:
        raise ValueError("cem_stratum missing; call add_frozen_cem_strata first")
    out = frame.copy()
    counts = out.groupby(["cem_stratum", "event_class"], observed=True).size().unstack(fill_value=0)
    for col in ("FAILED_AUCTION", "ACCEPTED_BREAKOUT"):
        if col not in counts.columns:
            counts[col] = 0
    common = counts[(counts["FAILED_AUCTION"] > 0) & (counts["ACCEPTED_BREAKOUT"] > 0)].copy()
    common_ids = set(common.index.astype(str))
    out["in_common_support"] = out["cem_stratum"].isin(common_ids)
    out["cem_weight"] = 0.0

    ratio = (common["FAILED_AUCTION"] / common["ACCEPTED_BREAKOUT"]).to_dict()
    treat = out["in_common_support"] & (out["event_class"] == "FAILED_AUCTION")
    control = out["in_common_support"] & (out["event_class"] == "ACCEPTED_BREAKOUT")
    out.loc[treat, "cem_weight"] = 1.0
    out.loc[control, "cem_weight"] = out.loc[control, "cem_stratum"].map(ratio).astype(float)

    n_t = int((out["event_class"] == "FAILED_AUCTION").sum())
    n_c = int((out["event_class"] == "ACCEPTED_BREAKOUT").sum())
    n_tm = int(treat.sum())
    n_cm = int(control.sum())
    audit = {
        "strata_total": int(len(counts)),
        "strata_common_support": int(len(common)),
        "failed_auction_total": n_t,
        "accepted_breakout_total": n_c,
        "failed_auction_matched": n_tm,
        "accepted_breakout_matched": n_cm,
        "failed_auction_common_support_pct": float(n_tm / n_t * 100.0) if n_t else 0.0,
        "accepted_breakout_common_support_pct": float(n_cm / n_c * 100.0) if n_c else 0.0,
    }
    return out, audit


def _weighted_mean(x: np.ndarray, w: np.ndarray) -> float:
    ok = np.isfinite(x) & np.isfinite(w) & (w > 0)
    if not np.any(ok):
        return np.nan
    return float(np.average(x[ok], weights=w[ok]))


def _weighted_rate(mask: np.ndarray, w: np.ndarray) -> float:
    return _weighted_mean(mask.astype(float), w)


def standardized_mean_difference(frame: pd.DataFrame, column: str, *, matched_only: bool) -> float:
    sub = frame[frame["in_common_support"]].copy() if matched_only else frame.copy()
    t = sub[sub["event_class"] == "FAILED_AUCTION"]
    c = sub[sub["event_class"] == "ACCEPTED_BREAKOUT"]
    if t.empty or c.empty:
        return np.nan
    xt = t[column].to_numpy(dtype=float)
    xc = c[column].to_numpy(dtype=float)
    if matched_only:
        wt = t["cem_weight"].to_numpy(dtype=float)
        wc = c["cem_weight"].to_numpy(dtype=float)
        mt, mc = _weighted_mean(xt, wt), _weighted_mean(xc, wc)
        vt = _weighted_mean((xt - mt) ** 2, wt)
        vc = _weighted_mean((xc - mc) ** 2, wc)
    else:
        mt, mc = float(np.nanmean(xt)), float(np.nanmean(xc))
        vt, vc = float(np.nanvar(xt)), float(np.nanvar(xc))
    pooled = np.sqrt(max((vt + vc) / 2.0, 0.0))
    return 0.0 if pooled <= 1e-12 else float((mt - mc) / pooled)


def build_balance_table(frame: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for col in BALANCE_CONTINUOUS_COLUMNS:
        rows.append({
            "covariate": col,
            "smd_before": standardized_mean_difference(frame, col, matched_only=False),
            "smd_after": standardized_mean_difference(frame, col, matched_only=True),
        })
    return pd.DataFrame(rows)


def estimate_matched_effects(frame: pd.DataFrame) -> pd.DataFrame:
    """Estimate matched treatment-minus-control forward effects at frozen horizons."""
    sub = frame[frame["in_common_support"] & (frame["cem_weight"] > 0)].copy()
    rows: List[Dict[str, Any]] = []
    for h in HORIZONS_MINUTES:
        ret_col = f"signed_return_{h}m"
        state_col = f"close_state_{h}m"
        exact_col = f"exact_{h}m_available"
        t = sub[(sub["event_class"] == "FAILED_AUCTION") & sub[exact_col]]
        c = sub[(sub["event_class"] == "ACCEPTED_BREAKOUT") & sub[exact_col]]
        mt = _weighted_mean(t[ret_col].to_numpy(float), t["cem_weight"].to_numpy(float))
        mc = _weighted_mean(c[ret_col].to_numpy(float), c["cem_weight"].to_numpy(float))
        rt = _weighted_rate((t[state_col] == "SNAPBACK_SIDE").to_numpy(), t["cem_weight"].to_numpy(float))
        rc = _weighted_rate((c[state_col] == "SNAPBACK_SIDE").to_numpy(), c["cem_weight"].to_numpy(float))
        rows.append({
            "horizon_min": int(h),
            "failed_auction_n": int(len(t)),
            "accepted_breakout_n": int(len(c)),
            "failed_auction_mean_bps": mt * 10000.0,
            "accepted_breakout_mean_bps": mc * 10000.0,
            "att_mean_diff_bps": (mt - mc) * 10000.0,
            "failed_auction_snapback_state_pct": rt * 100.0,
            "accepted_breakout_snapback_state_pct": rc * 100.0,
            "snapback_state_diff_pp": (rt - rc) * 100.0,
        })
    return pd.DataFrame(rows)


def estimate_yearly_5m_effect(frame: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for year, sub in frame.groupby("year", sort=True):
        eff = estimate_matched_effects(sub)
        row = eff[eff["horizon_min"] == PRIMARY_HORIZON_MINUTES]
        if row.empty:
            continue
        r = row.iloc[0]
        rows.append({
            "year": int(year),
            "failed_auction_n": int(r["failed_auction_n"]),
            "accepted_breakout_n": int(r["accepted_breakout_n"]),
            "att_mean_diff_bps": float(r["att_mean_diff_bps"]),
            "snapback_state_diff_pp": float(r["snapback_state_diff_pp"]),
        })
    return pd.DataFrame(rows)


def day_block_bootstrap_5m(frame: pd.DataFrame, *, iterations: int = BOOTSTRAP_ITERATIONS, seed: int = BOOTSTRAP_SEED) -> Dict[str, Any]:
    """UTC-day cluster bootstrap of the matched 5m ATT with frozen CEM weights."""
    sub = frame[frame["in_common_support"] & (frame["cem_weight"] > 0) & frame["exact_5m_available"]].copy()
    if sub.empty:
        return {"iterations": int(iterations), "valid_iterations": 0}
    sub["utc_date"] = pd.to_datetime(sub["datetime"], utc=True).dt.date
    days = np.array(sorted(sub["utc_date"].unique()), dtype=object)
    day_groups = {d: g for d, g in sub.groupby("utc_date", sort=False)}
    rng = np.random.default_rng(seed)
    estimates: List[float] = []
    for _ in range(iterations):
        sampled = rng.choice(days, size=len(days), replace=True)
        t_num = t_den = c_num = c_den = 0.0
        for d in sampled:
            g = day_groups[d]
            ret = g["signed_return_5m"].to_numpy(dtype=float)
            w = g["cem_weight"].to_numpy(dtype=float)
            cls = g["event_class"].to_numpy(dtype=object)
            ok = np.isfinite(ret) & np.isfinite(w) & (w > 0)
            tm = ok & (cls == "FAILED_AUCTION")
            cm = ok & (cls == "ACCEPTED_BREAKOUT")
            t_num += float(np.sum(ret[tm] * w[tm])); t_den += float(np.sum(w[tm]))
            c_num += float(np.sum(ret[cm] * w[cm])); c_den += float(np.sum(w[cm]))
        if t_den > 0 and c_den > 0:
            estimates.append((t_num / t_den - c_num / c_den) * 10000.0)
    x = np.asarray(estimates, dtype=float)
    return {
        "iterations": int(iterations),
        "seed": int(seed),
        "unique_utc_days": int(len(days)),
        "valid_iterations": int(len(x)),
        "mean_att_bps": float(np.mean(x)) if len(x) else np.nan,
        "ci95_lower_bps": float(np.quantile(x, 0.025)) if len(x) else np.nan,
        "ci95_upper_bps": float(np.quantile(x, 0.975)) if len(x) else np.nan,
    }


def evaluate_mechanism_gates(matching_audit: Dict[str, Any], balance: pd.DataFrame, effects: pd.DataFrame, yearly: pd.DataFrame, bootstrap: Dict[str, Any]) -> Dict[str, Any]:
    primary = effects[effects["horizon_min"] == PRIMARY_HORIZON_MINUTES]
    if primary.empty:
        return {"verdict": "STOP_BLOCKED", "reason": "NO_PRIMARY_EFFECT"}
    p = primary.iloc[0]
    max_smd = float(balance["smd_after"].abs().max()) if not balance.empty else np.inf
    positive_years = int((yearly["att_mean_diff_bps"] > 0).sum()) if not yearly.empty else 0
    valid_years = int(len(yearly))
    h3 = effects.loc[effects["horizon_min"] == 3, "att_mean_diff_bps"]
    h10 = effects.loc[effects["horizon_min"] == 10, "att_mean_diff_bps"]
    secondary_positive = bool((not h3.empty and h3.iloc[0] > 0) or (not h10.empty and h10.iloc[0] > 0))

    gates = {
        "G0_common_support": matching_audit.get("failed_auction_common_support_pct", 0.0) >= MIN_COMMON_SUPPORT_TREATMENT_PCT,
        "G1_covariate_balance": bool(np.isfinite(max_smd) and max_smd <= MAX_MATCHED_ABS_SMD),
        "G2_primary_5m_att_positive": bool(p["att_mean_diff_bps"] > 0),
        "G3_day_block_ci_lower_positive": bool(bootstrap.get("ci95_lower_bps", np.nan) > 0),
        "G4_secondary_horizon_positive": secondary_positive,
        "G5_temporal_stability": bool(valid_years >= 8 and positive_years >= MIN_POSITIVE_YEARS),
    }
    verdict = "MECHANISM_SUPPORTED" if all(gates.values()) else "MECHANISM_NOT_CONFIRMED"
    return {
        **gates,
        "max_abs_smd_after": max_smd,
        "positive_years": positive_years,
        "valid_years": valid_years,
        "verdict": verdict,
    }
