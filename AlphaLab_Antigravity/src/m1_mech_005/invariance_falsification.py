from __future__ import annotations

"""ALAB-M1-MECH-005 — compensation invariance and falsification audit.

Research-only. No strategy, PnL, order, broker, paper-trading, or live-trading logic.
The study intentionally tries to falsify the MECH-004 attenuation relationship by
changing the coordinate system and by destroying the event-to-future linkage with
pre-registered placebo transforms.
"""

from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd

from m1_fusion.features import compute_atr14
from m1_mech_002.state_engine import HORIZONS_MINUTES
from m1_mech_003.control_study import detect_breach_events
from m1_mech_004.reversion_budget import build_counterfactual_reversion_frame

EXPERIMENT_ID = "ALAB-M1-MECH-005"
PRIMARY_HORIZON_MINUTES = 5
BOOTSTRAP_ITERATIONS = 2000
BOOTSTRAP_SEED = 20260817
PLACEBO_LOCAL_SEED = 20260818
PLACEBO_SIGN_SEED = 20260819

REPRESENTATIONS: Tuple[str, ...] = (
    "ATR_T",
    "ATR_PRE",
    "PRICE_BPS",
    "EXCURSION_RATIO",
)
EXCURSION_RATIO_MIN_ATR = 0.10
MIN_EXACT_5M_COVERAGE_PCT = 98.0
MIN_EXCURSION_RATIO_COVERAGE_PCT = 50.0
KNOWN_MECH004_RHO_5M = 0.94191764717577
KNOWN_MECH004_RHO_TOLERANCE = 1e-10
GRADIENT_BINS = 5


def build_falsification_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Rebuild the frozen breach universe and add only pre-registered scale fields."""
    events = detect_breach_events(df)
    frame = build_counterfactual_reversion_frame(df, events)
    if frame.empty:
        return frame
    atr_pre = compute_atr14(df).shift(1).to_numpy(dtype=float)
    idx = frame["bar_index"].to_numpy(dtype=int)
    frame = frame.copy()
    frame["pre_event_atr14"] = atr_pre[idx]
    return frame


def _representation_payload(frame: pd.DataFrame, representation: str, horizon: int) -> pd.DataFrame:
    """Common x/y payload under one frozen coordinate system.

    x = in-candle reversion; y = total future reversion; post = y-x.
    EXCURSION_RATIO excludes breaches below 0.10 ATR_t to avoid near-zero ratios.
    """
    if representation not in REPRESENTATIONS:
        raise ValueError(f"Unknown representation: {representation}")
    exact_col = f"exact_{horizon}m_available"
    total_col = f"total_reversion_atr_{horizon}m"
    needed = [
        exact_col, total_col, "in_candle_reversion_atr", "breach_excursion_atr",
        "atr14", "pre_event_atr14", "prior_extreme", "atr_percentile",
        "path_efficiency", "stretch_abs", "location_count", "side", "hour",
        "year", "datetime",
    ]
    missing = [c for c in needed if c not in frame.columns]
    if missing:
        raise ValueError(f"Missing MECH-005 columns: {missing}")
    sub = frame.loc[frame[exact_col].astype(bool), needed].copy()
    if sub.empty:
        return sub.assign(_x=np.nan, _y=np.nan, _post=np.nan, _exc_control=np.nan)

    atr_t = sub["atr14"].to_numpy(dtype=float)
    atr_pre = sub["pre_event_atr14"].to_numpy(dtype=float)
    prior = sub["prior_extreme"].to_numpy(dtype=float)
    rin_atr = sub["in_candle_reversion_atr"].to_numpy(dtype=float)
    rtotal_atr = sub[total_col].to_numpy(dtype=float)
    exc_atr = sub["breach_excursion_atr"].to_numpy(dtype=float)
    raw_in = rin_atr * atr_t
    raw_total = rtotal_atr * atr_t
    raw_exc = exc_atr * atr_t

    if representation == "ATR_T":
        x, y, exc_control = rin_atr, rtotal_atr, exc_atr
        valid = np.ones(len(sub), dtype=bool)
    elif representation == "ATR_PRE":
        x, y, exc_control = raw_in / atr_pre, raw_total / atr_pre, raw_exc / atr_pre
        valid = np.isfinite(atr_pre) & (atr_pre > 0.0)
    elif representation == "PRICE_BPS":
        x = raw_in / prior * 10000.0
        y = raw_total / prior * 10000.0
        exc_control = raw_exc / prior * 10000.0
        valid = np.isfinite(prior) & (prior > 0.0)
    else:
        x, y = raw_in / raw_exc, raw_total / raw_exc
        exc_control = exc_atr
        valid = (
            np.isfinite(raw_exc) & (raw_exc > 0.0) & np.isfinite(exc_atr)
            & (exc_atr >= EXCURSION_RATIO_MIN_ATR)
        )

    numeric = np.column_stack([
        x, y, exc_control,
        sub["atr_percentile"].to_numpy(dtype=float),
        sub["path_efficiency"].to_numpy(dtype=float),
        sub["stretch_abs"].to_numpy(dtype=float),
        sub["location_count"].to_numpy(dtype=float),
        sub["hour"].to_numpy(dtype=float),
        sub["year"].to_numpy(dtype=float),
    ])
    valid &= np.all(np.isfinite(numeric), axis=1)
    sub = sub.loc[valid].copy()
    sub["_x"] = x[valid]
    sub["_y"] = y[valid]
    sub["_post"] = y[valid] - x[valid]
    sub["_exc_control"] = exc_control[valid]
    sub["_representation"] = representation
    return sub


def _control_matrix(frame: pd.DataFrame, include_year_effects: bool = True) -> Tuple[np.ndarray, List[str]]:
    n = len(frame)
    hour = frame["hour"].to_numpy(dtype=float)
    cols = [
        np.ones(n, dtype=float),
        frame["_exc_control"].to_numpy(dtype=float),
        frame["atr_percentile"].to_numpy(dtype=float) / 100.0,
        frame["path_efficiency"].to_numpy(dtype=float),
        frame["stretch_abs"].to_numpy(dtype=float),
        frame["location_count"].to_numpy(dtype=float),
        (frame["side"].to_numpy(dtype=object) == "LONG").astype(float),
        np.sin(2.0 * np.pi * hour / 24.0),
        np.cos(2.0 * np.pi * hour / 24.0),
    ]
    names = [
        "intercept", "coordinate_excursion", "atr_percentile_scaled",
        "path_efficiency", "stretch_abs", "location_count", "side_LONG",
        "hour_sin", "hour_cos",
    ]
    if include_year_effects:
        year = frame["year"].to_numpy(dtype=int)
        for y in range(2019, 2026):
            cols.append((year == y).astype(float))
            names.append(f"year_{y}")
    return np.column_stack(cols), names


def _fit_payload(
    payload: pd.DataFrame,
    *,
    y_override: np.ndarray | None = None,
    include_year_effects: bool = True,
    return_residuals: bool = False,
) -> Dict[str, Any]:
    if len(payload) < 50:
        return {"n": int(len(payload)), "rho": np.nan}
    x = payload["_x"].to_numpy(dtype=float)
    y = payload["_y"].to_numpy(dtype=float) if y_override is None else np.asarray(y_override, dtype=float)
    if len(y) != len(payload):
        raise ValueError("y_override length mismatch")
    valid = np.isfinite(x) & np.isfinite(y)
    if not np.all(valid):
        payload = payload.loc[valid].copy()
        x, y = x[valid], y[valid]
    if len(payload) < 50:
        return {"n": int(len(payload)), "rho": np.nan}
    z, names = _control_matrix(payload, include_year_effects=include_year_effects)
    bx = np.linalg.lstsq(z, x, rcond=None)[0]
    by = np.linalg.lstsq(z, y, rcond=None)[0]
    rx, ry = x - z @ bx, y - z @ by
    den = float(np.dot(rx, rx))
    rho = np.nan if den <= 1e-15 else float(np.dot(rx, ry) / den)
    out: Dict[str, Any] = {
        "n": int(len(payload)), "rho": rho,
        "attenuation_fraction": float(1.0-rho) if np.isfinite(rho) else np.nan,
        "controls": "|".join(names), "x_mean": float(np.mean(x)), "y_mean": float(np.mean(y)),
    }
    if return_residuals:
        out["_rx"], out["_ry"] = rx, ry
        out["_datetime"] = pd.to_datetime(payload["datetime"], utc=True).to_numpy()
    return out


def fit_representation(
    frame: pd.DataFrame,
    representation: str,
    horizon: int,
    *,
    include_year_effects: bool = True,
    return_residuals: bool = False,
) -> Dict[str, Any]:
    payload = _representation_payload(frame, representation, horizon)
    out = _fit_payload(payload, include_year_effects=include_year_effects, return_residuals=return_residuals)
    out.update({"representation": representation, "horizon_min": int(horizon), "coverage_events": int(len(payload))})
    return out


def _day_block_bootstrap_from_fit(fit: Dict[str, Any], *, iterations: int, seed: int) -> Dict[str, Any]:
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
        "iterations": int(iterations), "seed": int(seed), "unique_utc_days": int(n_days),
        "valid_iterations": int(len(arr)), "point_rho": float(fit.get("rho", np.nan)),
        "mean_rho": float(np.mean(arr)) if len(arr) else np.nan,
        "ci95_lower": float(np.quantile(arr, 0.025)) if len(arr) else np.nan,
        "ci95_upper": float(np.quantile(arr, 0.975)) if len(arr) else np.nan,
    }


def build_invariance_regression_table(frame: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    bootstraps: Dict[str, Any] = {}
    for rep in REPRESENTATIONS:
        for h in HORIZONS_MINUTES:
            fit = fit_representation(frame, rep, h, return_residuals=(h == PRIMARY_HORIZON_MINUTES))
            row = {k: v for k, v in fit.items() if not k.startswith("_")}
            if h == PRIMARY_HORIZON_MINUTES and np.isfinite(float(fit.get("rho", np.nan))):
                bs = _day_block_bootstrap_from_fit(fit, iterations=BOOTSTRAP_ITERATIONS, seed=BOOTSTRAP_SEED)
                row["ci95_lower"], row["ci95_upper"] = bs.get("ci95_lower", np.nan), bs.get("ci95_upper", np.nan)
                bootstraps[rep] = bs
            else:
                row["ci95_lower"], row["ci95_upper"] = np.nan, np.nan
            rows.append(row)
    return pd.DataFrame(rows), bootstraps


def build_gradient_table(frame: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """Predictor-only equal-count bins; no outcome-informed threshold search."""
    rows: List[Dict[str, Any]] = []
    audit: Dict[str, Any] = {}
    labels = [f"G{i}" for i in range(1, GRADIENT_BINS+1)]
    for rep in REPRESENTATIONS:
        payload = _representation_payload(frame, rep, PRIMARY_HORIZON_MINUTES)
        if payload.empty:
            audit[rep] = {"bins": 0, "monotonic_nonincreasing": False}
            continue
        try:
            bins = pd.qcut(payload["_x"], q=GRADIENT_BINS, labels=labels, duplicates="drop")
        except ValueError:
            audit[rep] = {"bins": 0, "monotonic_nonincreasing": False}
            continue
        work = payload.copy(); work["_gradient_bin"] = bins.astype(object)
        means: List[float] = []
        for label in labels:
            sub = work[work["_gradient_bin"] == label]
            if sub.empty:
                continue
            mpost = float(sub["_post"].mean()); means.append(mpost)
            rows.append({
                "representation": rep, "gradient_bin": label, "n": int(len(sub)),
                "mean_x": float(sub["_x"].mean()), "mean_post": mpost,
                "median_post": float(sub["_post"].median()),
            })
        monotonic = len(means) == GRADIENT_BINS and bool(np.all(np.diff(np.asarray(means)) <= 0.0))
        audit[rep] = {"bins": int(len(means)), "monotonic_nonincreasing": monotonic, "mean_post_by_bin": means}
    return pd.DataFrame(rows), audit


def _within_day_side_cyclic_shift(payload: pd.DataFrame, values: np.ndarray, *, seed: int) -> np.ndarray:
    """Distribution-preserving local placebo; no self-donor for groups n>1."""
    out = np.full(len(payload), np.nan, dtype=float)
    work = payload.reset_index(drop=True).copy(); work["_date"] = pd.to_datetime(work["datetime"], utc=True).dt.date
    rng = np.random.default_rng(seed); vals = np.asarray(values, dtype=float)
    for _, idx_like in work.groupby(["_date", "side"], sort=True).indices.items():
        idx = np.asarray(idx_like, dtype=int); n = len(idx)
        if n < 2:
            continue
        out[idx] = np.roll(vals[idx], int(rng.integers(1, n)))
    return out


def _within_day_side_balanced_signs(payload: pd.DataFrame, *, seed: int) -> np.ndarray:
    """Directional-information placebo with approximately balanced signs per local group."""
    signs = np.full(len(payload), np.nan, dtype=float)
    work = payload.reset_index(drop=True).copy(); work["_date"] = pd.to_datetime(work["datetime"], utc=True).dt.date
    rng = np.random.default_rng(seed)
    for _, idx_like in work.groupby(["_date", "side"], sort=True).indices.items():
        idx = np.asarray(idx_like, dtype=int); n = len(idx)
        if n < 2:
            continue
        base = np.ones(n, dtype=float); base[:n//2] = -1.0
        if n % 2 == 1:
            base[-1] = float(rng.choice([-1.0, 1.0]))
        rng.shuffle(base); signs[idx] = base
    return signs


def _fit_placebo(payload: pd.DataFrame, placebo_y: np.ndarray, *, seed: int) -> Dict[str, Any]:
    valid = np.isfinite(placebo_y); sub = payload.loc[valid].copy(); y = np.asarray(placebo_y, dtype=float)[valid]
    fit = _fit_payload(sub, y_override=y, include_year_effects=True, return_residuals=True)
    bs = _day_block_bootstrap_from_fit(fit, iterations=BOOTSTRAP_ITERATIONS, seed=seed)
    out = {k: v for k, v in fit.items() if not k.startswith("_")}
    out.update({
        "ci95_lower": bs.get("ci95_lower", np.nan), "ci95_upper": bs.get("ci95_upper", np.nan),
        "bootstrap_valid_iterations": int(bs.get("valid_iterations", 0)),
    })
    return out


def build_placebo_table(frame: pd.DataFrame) -> pd.DataFrame:
    payload = _representation_payload(frame, "ATR_T", PRIMARY_HORIZON_MINUTES).reset_index(drop=True)
    x, post = payload["_x"].to_numpy(dtype=float), payload["_post"].to_numpy(dtype=float)
    shuffled_post = _within_day_side_cyclic_shift(payload, post, seed=PLACEBO_LOCAL_SEED)
    p1 = _fit_placebo(payload, x + shuffled_post, seed=PLACEBO_LOCAL_SEED)
    p1.update({
        "placebo": "WITHIN_DAY_SIDE_CYCLIC_POST_SHUFFLE", "null_rho": 1.0,
        "construction": "R_in + cyclic_shift(R_post within UTC-date x side)",
    })
    signs = _within_day_side_balanced_signs(payload, seed=PLACEBO_SIGN_SEED)
    p2 = _fit_placebo(payload, x + post*signs, seed=PLACEBO_SIGN_SEED)
    p2.update({
        "placebo": "WITHIN_DAY_SIDE_BALANCED_POST_SIGN", "null_rho": 1.0,
        "construction": "R_in + R_post * balanced_random_sign within UTC-date x side",
    })
    return pd.DataFrame([p1, p2])


def build_yearly_invariance_table(frame: pd.DataFrame) -> pd.DataFrame:
    rows: List[Dict[str, Any]] = []
    for rep in REPRESENTATIONS:
        for year in range(2018, 2026):
            fit = fit_representation(frame[frame["year"] == year], rep, PRIMARY_HORIZON_MINUTES, include_year_effects=False)
            rows.append({"representation": rep, "year": int(year), "n": int(fit.get("n", 0)), "rho_5m": float(fit.get("rho", np.nan))})
    return pd.DataFrame(rows)


def build_coordinate_audit(frame: pd.DataFrame) -> Dict[str, Any]:
    exact5 = frame["exact_5m_available"].astype(bool); total_exact = int(exact5.sum())
    d_payload = _representation_payload(frame, "EXCURSION_RATIO", PRIMARY_HORIZON_MINUTES)
    base_fit = fit_representation(frame, "ATR_T", PRIMARY_HORIZON_MINUTES)
    recomputed = float(base_fit.get("rho", np.nan))
    return {
        "events": int(len(frame)), "years": sorted(int(x) for x in pd.Series(frame["year"]).dropna().unique()),
        "exact_5m_events": total_exact, "exact_5m_coverage_pct": float(exact5.mean()*100.0),
        "pre_event_atr_finite_pct": float(np.isfinite(frame["pre_event_atr14"].to_numpy(dtype=float)).mean()*100.0),
        "excursion_ratio_min_excursion_atr": float(EXCURSION_RATIO_MIN_ATR),
        "excursion_ratio_5m_events": int(len(d_payload)),
        "excursion_ratio_5m_coverage_pct_of_exact": float(len(d_payload)/total_exact*100.0) if total_exact else 0.0,
        "known_mech004_rho_5m": float(KNOWN_MECH004_RHO_5M), "recomputed_atr_t_rho_5m": recomputed,
        "base_rho_abs_error": float(abs(recomputed-KNOWN_MECH004_RHO_5M)),
    }


def evaluate_falsification_gates(
    audit: Dict[str, Any], invariance: pd.DataFrame, gradient_audit: Dict[str, Any], placebo: pd.DataFrame,
) -> Dict[str, Any]:
    years = set(int(x) for x in audit.get("years", [])); primary = invariance[invariance["horizon_min"] == PRIMARY_HORIZON_MINUTES]
    rho_by_rep = {str(r["representation"]): float(r["rho"]) for _, r in primary.iterrows() if np.isfinite(float(r["rho"]))}
    upper_by_rep = {str(r["representation"]): float(r["ci95_upper"]) for _, r in primary.iterrows() if np.isfinite(float(r["ci95_upper"]))}
    g0 = bool(
        years == set(range(2018, 2026))
        and float(audit.get("exact_5m_coverage_pct", 0.0)) >= MIN_EXACT_5M_COVERAGE_PCT
        and float(audit.get("excursion_ratio_5m_coverage_pct_of_exact", 0.0)) >= MIN_EXCURSION_RATIO_COVERAGE_PCT
        and float(audit.get("base_rho_abs_error", np.inf)) <= KNOWN_MECH004_RHO_TOLERANCE
    )
    g1 = bool(all(rep in rho_by_rep and rho_by_rep[rep] < 1.0 for rep in REPRESENTATIONS))
    g2 = bool(all(rep in upper_by_rep and upper_by_rep[rep] < 1.0 for rep in REPRESENTATIONS))
    g3 = bool(all(bool(gradient_audit.get(rep, {}).get("monotonic_nonincreasing", False)) for rep in REPRESENTATIONS))
    p = {str(r["placebo"]): r for _, r in placebo.iterrows()}
    def ci_contains_one(row: Any) -> bool:
        if row is None: return False
        lo, hi = float(row["ci95_lower"]), float(row["ci95_upper"])
        return bool(np.isfinite(lo) and np.isfinite(hi) and lo <= 1.0 <= hi)
    g4 = ci_contains_one(p.get("WITHIN_DAY_SIDE_CYCLIC_POST_SHUFFLE"))
    g5 = ci_contains_one(p.get("WITHIN_DAY_SIDE_BALANCED_POST_SIGN"))
    passed = all((g0, g1, g2, g3, g4, g5))
    return {
        "G0_boundary_coverage_and_base_reproduction": g0,
        "G1_all_four_coordinate_rho_5m_below_one": g1,
        "G2_all_four_coordinate_ci_upper_below_one": g2,
        "G3_all_four_inverse_gradients_monotonic": g3,
        "G4_local_shuffle_placebo_ci_contains_one": g4,
        "G5_sign_placebo_ci_contains_one": g5,
        "verdict": "COMPENSATION_INVARIANCE_SURVIVES_FALSIFICATION" if passed else "COMPENSATION_FALSIFIED_OR_NOT_INVARIANT",
    }
