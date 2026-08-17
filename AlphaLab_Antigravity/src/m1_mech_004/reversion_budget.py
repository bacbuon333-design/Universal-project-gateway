from __future__ import annotations

"""Continuous reversion-timing study for ALAB-M1-MECH-004.

Research-only. No strategy, PnL, order, broker, paper-trading or live-trading logic.
The primary inferential outcome is future TOTAL reversion from the event extreme,
not post-close reversion, to avoid algebraic coupling with the event close.
"""

from typing import Any, Dict, Iterable, List, Sequence, Tuple

import numpy as np
import pandas as pd

from m1_mech_002.state_engine import HORIZONS_MINUTES
from m1_mech_003.control_study import BreachEvent, build_counterfactual_frame, detect_breach_events

EXPERIMENT_ID = "ALAB-M1-MECH-004"
PRIMARY_HORIZON_MINUTES = 5
BOOTSTRAP_ITERATIONS = 2000
BOOTSTRAP_SEED = 20260817
MIN_EXACT_5M_COVERAGE_PCT = 98.0
MIN_ATTENUATED_YEARS = 6
IDENTITY_TOLERANCE = 1e-10

RECLAIM_EDGES: Tuple[float, ...] = (0.0, 0.25, 0.50, 1.00, 2.00, np.inf)
RECLAIM_LABELS: Tuple[str, ...] = ("R0", "R1", "R2", "R3", "R4")


def add_reversion_budget_variables(
    df: pd.DataFrame,
    frame: pd.DataFrame,
    horizons: Iterable[int] = HORIZONS_MINUTES,
) -> pd.DataFrame:
    """Attach event geometry plus exact-clock total/post-close reversion measures."""
    if frame.empty:
        return frame.copy()

    horizons = tuple(sorted(set(int(h) for h in horizons)))
    if PRIMARY_HORIZON_MINUTES not in horizons:
        raise ValueError("MECH-004 requires the frozen +5m primary horizon.")

    out = frame.copy()
    idx = out["bar_index"].to_numpy(dtype=int)
    side_sign = np.where(out["side"].to_numpy(dtype=object) == "LONG", 1.0, -1.0)
    prior = out["prior_extreme"].to_numpy(dtype=float)
    event_close = out["event_close"].to_numpy(dtype=float)
    atr = out["atr14"].to_numpy(dtype=float)

    highs = df["high"].to_numpy(dtype=float)
    lows = df["low"].to_numpy(dtype=float)
    event_extreme = np.where(side_sign > 0, lows[idx], highs[idx])

    excursion = side_sign * (prior - event_extreme) / atr
    in_reclaim = side_sign * (event_close - event_extreme) / atr
    close_distance = side_sign * (event_close - prior) / atr

    out["event_extreme"] = event_extreme
    out["breach_excursion_atr"] = excursion
    out["in_candle_reversion_atr"] = in_reclaim
    out["event_close_signed_level_distance_atr"] = close_distance
    out["geometry_identity_error"] = in_reclaim - (excursion + close_distance)

    out["in_candle_reversion_bin"] = pd.cut(
        out["in_candle_reversion_atr"],
        bins=list(RECLAIM_EDGES),
        labels=list(RECLAIM_LABELS),
        include_lowest=True,
        right=False,
    ).astype(object)

    for h in horizons:
        dist_col = f"signed_level_distance_atr_{h}m"
        exact_col = f"exact_{h}m_available"
        if dist_col not in out.columns or exact_col not in out.columns:
            raise ValueError(f"Missing MECH-003 exact-clock columns for horizon {h}m")

        future_distance = out[dist_col].to_numpy(dtype=float)
        exact = out[exact_col].to_numpy(dtype=bool)

        # Descriptive only: this contains -D_t and must not be the primary
        # regression outcome against R_in.
        post = future_distance - close_distance
        post[~exact] = np.nan

        # Primary future-state quantity: excursion + future signed distance.
        # This equals s*(C_{t+h}-X_t)/ATR_t and does not use event close.
        total = excursion + future_distance
        total[~exact] = np.nan

        total_identity = total - (in_reclaim + post)
        total_identity[~exact] = np.nan

        consumption = np.full(len(out), np.nan, dtype=float)
        valid_ratio = exact & np.isfinite(total) & (total > 0.0)
        consumption[valid_ratio] = in_reclaim[valid_ratio] / total[valid_ratio]

        out[f"post_close_reversion_atr_{h}m"] = post
        out[f"total_reversion_atr_{h}m"] = total
        out[f"total_reversion_identity_error_{h}m"] = total_identity
        out[f"consumption_ratio_{h}m"] = consumption

    return out


def build_counterfactual_reversion_frame(
    df: pd.DataFrame,
    events: Sequence[BreachEvent] | None = None,
) -> pd.DataFrame:
    ev = list(events) if events is not None else detect_breach_events(df)
    base = build_counterfactual_frame(df, ev)
    return add_reversion_budget_variables(df, base)


def geometry_audit(frame: pd.DataFrame) -> Dict[str, Any]:
    if frame.empty:
        return {"events": 0}
    err = np.abs(frame["geometry_identity_error"].to_numpy(dtype=float))
    total_errors = []
    for h in HORIZONS_MINUTES:
        col = f"total_reversion_identity_error_{h}m"
        if col in frame:
            x = np.abs(frame[col].dropna().to_numpy(dtype=float))
            if len(x):
                total_errors.append(float(np.max(x)))
    exact5 = frame["exact_5m_available"].to_numpy(dtype=bool)
    years = sorted(int(x) for x in pd.Series(frame["year"]).dropna().unique())
    return {
        "events": int(len(frame)),
        "years": years,
        "max_abs_geometry_identity_error": float(np.nanmax(err)),
        "max_abs_total_identity_error": float(max(total_errors)) if total_errors else np.nan,
        "negative_excursion_count": int((frame["breach_excursion_atr"] < -IDENTITY_TOLERANCE).sum()),
        "negative_in_candle_reversion_count": int((frame["in_candle_reversion_atr"] < -IDENTITY_TOLERANCE).sum()),
        "exact_5m_available": int(exact5.sum()),
        "exact_5m_coverage_pct": float(exact5.mean() * 100.0),
    }


def _summary_stats(values: pd.Series) -> Dict[str, float]:
    x = values.dropna().to_numpy(dtype=float)
    if len(x) == 0:
        return {"n": 0}
    return {
        "n": int(len(x)),
        "mean": float(np.mean(x)),
        "median": float(np.median(x)),
        "p10": float(np.quantile(x, 0.10)),
        "p25": float(np.quantile(x, 0.25)),
        "p75": float(np.quantile(x, 0.75)),
        "p90": float(np.quantile(x, 0.90)),
    }


def build_horizon_summary(frame: pd.DataFrame) -> pd.DataFrame:
    rows: List[Dict[str, Any]] = []
    rin = frame["in_candle_reversion_atr"]
    for h in HORIZONS_MINUTES:
        exact = frame[f"exact_{h}m_available"].astype(bool)
        sub = frame[exact]
        post = _summary_stats(sub[f"post_close_reversion_atr_{h}m"])
        total = _summary_stats(sub[f"total_reversion_atr_{h}m"])
        cons = _summary_stats(sub[f"consumption_ratio_{h}m"])
        rows.append({
            "horizon_min": int(h),
            "events_total": int(len(frame)),
            "exact_events": int(exact.sum()),
            "exact_pct": float(exact.mean() * 100.0),
            "mean_in_candle_reversion_atr": float(rin.mean()),
            "median_in_candle_reversion_atr": float(rin.median()),
            "mean_post_close_reversion_atr": post.get("mean", np.nan),
            "median_post_close_reversion_atr": post.get("median", np.nan),
            "mean_total_reversion_atr": total.get("mean", np.nan),
            "median_total_reversion_atr": total.get("median", np.nan),
            "p90_total_reversion_atr": total.get("p90", np.nan),
            "consumption_defined_n": int(cons.get("n", 0)),
            "median_consumption_ratio": cons.get("median", np.nan),
        })
    return pd.DataFrame(rows)


def build_fixed_reclaim_bins(frame: pd.DataFrame) -> pd.DataFrame:
    rows: List[Dict[str, Any]] = []
    for h in HORIZONS_MINUTES:
        for bucket in RECLAIM_LABELS:
            sub = frame[(frame["in_candle_reversion_bin"] == bucket) & frame[f"exact_{h}m_available"].astype(bool)]
            post = sub[f"post_close_reversion_atr_{h}m"]
            total = sub[f"total_reversion_atr_{h}m"]
            cons = sub[f"consumption_ratio_{h}m"]
            rows.append({
                "horizon_min": int(h),
                "reclaim_bin": bucket,
                "n": int(len(sub)),
                "mean_in_candle_reversion_atr": float(sub["in_candle_reversion_atr"].mean()) if len(sub) else np.nan,
                "mean_post_close_reversion_atr": float(post.mean()) if len(sub) else np.nan,
                "median_post_close_reversion_atr": float(post.median()) if len(sub) else np.nan,
                "post_close_positive_pct": float((post > 0).mean() * 100.0) if len(sub) else np.nan,
                "mean_total_reversion_atr": float(total.mean()) if len(sub) else np.nan,
                "median_total_reversion_atr": float(total.median()) if len(sub) else np.nan,
                "median_consumption_ratio": float(cons.median()) if cons.notna().any() else np.nan,
            })
    return pd.DataFrame(rows)


def build_event_class_summary(frame: pd.DataFrame) -> pd.DataFrame:
    rows: List[Dict[str, Any]] = []
    for h in HORIZONS_MINUTES:
        for event_class, sub0 in frame.groupby("event_class", sort=True):
            sub = sub0[sub0[f"exact_{h}m_available"].astype(bool)]
            rows.append({
                "horizon_min": int(h), "event_class": str(event_class), "n": int(len(sub)),
                "mean_in_candle_reversion_atr": float(sub["in_candle_reversion_atr"].mean()) if len(sub) else np.nan,
                "median_in_candle_reversion_atr": float(sub["in_candle_reversion_atr"].median()) if len(sub) else np.nan,
                "mean_post_close_reversion_atr": float(sub[f"post_close_reversion_atr_{h}m"].mean()) if len(sub) else np.nan,
                "median_post_close_reversion_atr": float(sub[f"post_close_reversion_atr_{h}m"].median()) if len(sub) else np.nan,
                "mean_total_reversion_atr": float(sub[f"total_reversion_atr_{h}m"].mean()) if len(sub) else np.nan,
                "median_total_reversion_atr": float(sub[f"total_reversion_atr_{h}m"].median()) if len(sub) else np.nan,
            })
    return pd.DataFrame(rows)


def build_energy_location_budget(frame: pd.DataFrame, horizon: int = 5) -> pd.DataFrame:
    rows: List[Dict[str, Any]] = []
    valid = frame[frame[f"exact_{horizon}m_available"].astype(bool)]
    for (energy, location), sub in valid.groupby(["energy_count", "location_count"], sort=True):
        total = sub[f"total_reversion_atr_{horizon}m"].dropna()
        post = sub[f"post_close_reversion_atr_{horizon}m"].dropna()
        rows.append({
            "horizon_min": int(horizon), "energy_count": int(energy), "location_count": int(location), "n": int(len(sub)),
            "mean_in_candle_reversion_atr": float(sub["in_candle_reversion_atr"].mean()),
            "mean_post_close_reversion_atr": float(post.mean()) if len(post) else np.nan,
            "median_post_close_reversion_atr": float(post.median()) if len(post) else np.nan,
            "mean_total_reversion_atr": float(total.mean()) if len(total) else np.nan,
            "median_total_reversion_atr": float(total.median()) if len(total) else np.nan,
            "p90_total_reversion_atr": float(total.quantile(0.90)) if len(total) else np.nan,
        })
    return pd.DataFrame(rows)


def _control_matrix(frame: pd.DataFrame, include_year_effects: bool = True) -> Tuple[np.ndarray, List[str]]:
    """Frozen nuisance controls; event_class intentionally excluded."""
    n = len(frame)
    hour = frame["hour"].to_numpy(dtype=float)
    cols = [
        np.ones(n, dtype=float),
        frame["breach_excursion_atr"].to_numpy(dtype=float),
        frame["atr_percentile"].to_numpy(dtype=float) / 100.0,
        frame["path_efficiency"].to_numpy(dtype=float),
        frame["stretch_abs"].to_numpy(dtype=float),
        frame["location_count"].to_numpy(dtype=float),
        (frame["side"].to_numpy(dtype=object) == "LONG").astype(float),
        np.sin(2.0 * np.pi * hour / 24.0),
        np.cos(2.0 * np.pi * hour / 24.0),
    ]
    names = ["intercept", "breach_excursion_atr", "atr_percentile_scaled", "path_efficiency", "stretch_abs", "location_count", "side_LONG", "hour_sin", "hour_cos"]
    if include_year_effects:
        year = frame["year"].to_numpy(dtype=int)
        for y in range(2019, 2026):
            cols.append((year == y).astype(float))
            names.append(f"year_{y}")
    return np.column_stack(cols), names


def _valid_regression_frame(frame: pd.DataFrame, horizon: int) -> pd.DataFrame:
    needed = [
        "in_candle_reversion_atr", f"total_reversion_atr_{horizon}m", f"exact_{horizon}m_available",
        "breach_excursion_atr", "atr_percentile", "path_efficiency", "stretch_abs",
        "location_count", "side", "hour", "year", "datetime",
    ]
    sub = frame.loc[frame[f"exact_{horizon}m_available"].astype(bool), needed].copy()
    numeric = ["in_candle_reversion_atr", f"total_reversion_atr_{horizon}m", "breach_excursion_atr", "atr_percentile", "path_efficiency", "stretch_abs", "location_count", "hour", "year"]
    mask = np.ones(len(sub), dtype=bool)
    for c in numeric:
        mask &= np.isfinite(sub[c].to_numpy(dtype=float))
    return sub.loc[mask].copy()


def fit_persistence_regression(
    frame: pd.DataFrame,
    horizon: int,
    *,
    include_year_effects: bool = True,
    return_residuals: bool = False,
) -> Dict[str, Any]:
    """FWL slope rho in R_total(h) ~ rho*R_in + frozen controls."""
    sub = _valid_regression_frame(frame, horizon)
    if len(sub) < 50:
        return {"horizon_min": int(horizon), "n": int(len(sub)), "rho_total_on_in": np.nan}

    x = sub["in_candle_reversion_atr"].to_numpy(dtype=float)
    y = sub[f"total_reversion_atr_{horizon}m"].to_numpy(dtype=float)
    z, control_names = _control_matrix(sub, include_year_effects=include_year_effects)
    bx = np.linalg.lstsq(z, x, rcond=None)[0]
    by = np.linalg.lstsq(z, y, rcond=None)[0]
    rx = x - z @ bx
    ry = y - z @ by
    den = float(np.dot(rx, rx))
    rho = np.nan if den <= 1e-15 else float(np.dot(rx, ry) / den)
    result: Dict[str, Any] = {
        "horizon_min": int(horizon), "n": int(len(sub)), "rho_total_on_in": rho,
        "compensation_fraction": float(1.0 - rho) if np.isfinite(rho) else np.nan,
        "controls": "|".join(control_names), "r_in_mean": float(np.mean(x)), "r_total_mean": float(np.mean(y)),
    }
    if return_residuals:
        result["_rx"] = rx
        result["_ry"] = ry
        result["_datetime"] = pd.to_datetime(sub["datetime"], utc=True).to_numpy()
    return result


def build_regression_table(frame: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame([{k: v for k, v in fit_persistence_regression(frame, h, include_year_effects=True).items() if not k.startswith("_")} for h in HORIZONS_MINUTES])


def build_yearly_5m_slopes(frame: pd.DataFrame) -> pd.DataFrame:
    rows: List[Dict[str, Any]] = []
    for year in range(2018, 2026):
        r = fit_persistence_regression(frame[frame["year"] == year], PRIMARY_HORIZON_MINUTES, include_year_effects=False)
        rho = float(r.get("rho_total_on_in", np.nan))
        rows.append({"year": int(year), "n": int(r.get("n", 0)), "rho_total_on_in_5m": rho, "compensation_fraction_5m": float(1.0-rho) if np.isfinite(rho) else np.nan})
    return pd.DataFrame(rows)


def fixed_residual_day_block_bootstrap(
    frame: pd.DataFrame,
    *,
    iterations: int = BOOTSTRAP_ITERATIONS,
    seed: int = BOOTSTRAP_SEED,
) -> Dict[str, Any]:
    """UTC-day bootstrap of FWL residual cross-products with nuisance fit fixed."""
    fit = fit_persistence_regression(frame, PRIMARY_HORIZON_MINUTES, include_year_effects=True, return_residuals=True)
    rx = np.asarray(fit.get("_rx", []), dtype=float)
    ry = np.asarray(fit.get("_ry", []), dtype=float)
    dts = pd.to_datetime(fit.get("_datetime", []), utc=True)
    if len(rx) == 0:
        return {"iterations": int(iterations), "valid_iterations": 0}
    work = pd.DataFrame({"utc_date": pd.DatetimeIndex(dts).date, "xy": rx*ry, "xx": rx*rx})
    stats = work.groupby("utc_date", sort=True)[["xy", "xx"]].sum().to_numpy(dtype=float)
    n_days = len(stats)
    rng = np.random.default_rng(seed)
    estimates: List[float] = []
    for _ in range(int(iterations)):
        sampled = stats[rng.integers(0, n_days, size=n_days)].sum(axis=0)
        if sampled[1] > 1e-15:
            estimates.append(float(sampled[0]/sampled[1]))
    arr = np.asarray(estimates, dtype=float)
    return {
        "method": "FIXED_RESIDUAL_FWL_UTC_DAY_BLOCK_BOOTSTRAP",
        "iterations": int(iterations), "seed": int(seed), "unique_utc_days": int(n_days), "valid_iterations": int(len(arr)),
        "point_rho": float(fit.get("rho_total_on_in", np.nan)),
        "mean_rho": float(np.mean(arr)) if len(arr) else np.nan,
        "ci95_lower": float(np.quantile(arr, 0.025)) if len(arr) else np.nan,
        "ci95_upper": float(np.quantile(arr, 0.975)) if len(arr) else np.nan,
    }


def evaluate_gates(
    audit: Dict[str, Any],
    regressions: pd.DataFrame,
    yearly: pd.DataFrame,
    bootstrap: Dict[str, Any],
) -> Dict[str, Any]:
    years = set(int(x) for x in audit.get("years", []))
    rho = {int(r["horizon_min"]): float(r["rho_total_on_in"]) for _, r in regressions.iterrows() if np.isfinite(float(r["rho_total_on_in"]))}
    yearly_rho = yearly["rho_total_on_in_5m"].to_numpy(dtype=float)
    valid_years = int(np.isfinite(yearly_rho).sum())
    attenuated_years = int(np.sum(np.isfinite(yearly_rho) & (yearly_rho < 1.0)))
    g0 = years == set(range(2018, 2026))
    g1 = (
        float(audit.get("max_abs_geometry_identity_error", np.inf)) <= IDENTITY_TOLERANCE
        and float(audit.get("max_abs_total_identity_error", np.inf)) <= IDENTITY_TOLERANCE
        and int(audit.get("negative_excursion_count", 1)) == 0
        and int(audit.get("negative_in_candle_reversion_count", 1)) == 0
        and float(audit.get("exact_5m_coverage_pct", 0.0)) >= MIN_EXACT_5M_COVERAGE_PCT
    )
    g2 = bool(rho.get(5, np.nan) < 1.0)
    g3 = bool(float(bootstrap.get("ci95_upper", np.nan)) < 1.0)
    g4 = bool(rho.get(3, np.nan) < 1.0 and rho.get(10, np.nan) < 1.0)
    g5 = bool(valid_years == 8 and attenuated_years >= MIN_ATTENUATED_YEARS)
    passed = all((g0, g1, g2, g3, g4, g5))
    return {
        "G0_dataset_and_years": g0,
        "G1_geometry_and_exact_clock": g1,
        "G2_primary_rho_5m_below_one": g2,
        "G3_day_block_ci_upper_below_one": g3,
        "G4_3m_and_10m_rho_below_one": g4,
        "G5_temporal_stability": g5,
        "valid_years": valid_years,
        "attenuated_years": attenuated_years,
        "verdict": "REVERSION_COMPENSATION_SUPPORTED_IN_DEVELOPMENT" if passed else "REVERSION_COMPENSATION_NOT_CONFIRMED",
    }
