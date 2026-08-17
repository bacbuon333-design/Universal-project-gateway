from __future__ import annotations

from typing import Any, Dict, List, Sequence, Tuple
import numpy as np
import pandas as pd

from m1_fusion.features import (
    ATR_PERCENTILE_THRESHOLD, EFFICIENCY_THRESHOLD, PATH_WINDOW,
    PRIOR_EXTREME_LOOKBACK, ROBUST_WINDOW, ROBUST_Z_THRESHOLD,
    compute_atr14, compute_atr_percentiles, compute_path_efficiency,
    compute_prior_extremes, compute_robust_stretch_z,
)
from m1_fusion.reaction_zones import REACTION_DISTANCE_ATR
from m1_mech_002.state_engine import (
    HORIZONS_MINUTES, M15_SWING_LOOKBACK, SESSION_LOOKBACK,
    _candle_intersects_any_zone, add_gap_aware_state_labels,
    build_completed_session_levels_clocktime, build_confirmed_m15_swing_zones,
    compute_previous_observed_day_levels,
)
from m1_mech_003.control_study import BreachEvent
from m1_mech_004.reversion_budget import add_reversion_budget_variables
from m1_mech_005.invariance_falsification import (
    REPRESENTATIONS, _representation_payload,
)

EXPERIMENT_ID = "ALAB-M1-FINAL-HOLDOUT-2015-2017"
HOLDOUT_START_UTC = pd.Timestamp("2015-01-01T00:00:00Z")
HOLDOUT_END_UTC = pd.Timestamp("2018-01-01T00:00:00Z")
HOLDOUT_YEARS: Tuple[int, ...] = (2015, 2016, 2017)
PRIMARY_HORIZON_MINUTES = 5
BOOTSTRAP_ITERATIONS = 2000
BOOTSTRAP_SEED = 20260820
MIN_HOLDOUT_ROWS = 750_000
MIN_YEAR_ROWS = 250_000
MIN_BREACH_EVENTS = 100_000
MIN_EXACT_5M_COVERAGE_PCT = 98.0
MIN_EXCURSION_RATIO_COVERAGE_PCT = 50.0


def validate_holdout_frame(df: pd.DataFrame, *, require_all_years: bool = True) -> None:
    req = {"datetime", "open", "high", "low", "close"}
    missing = req - set(df.columns)
    if missing or df.empty:
        raise ValueError(f"Invalid holdout frame; missing={sorted(missing)} empty={df.empty}")
    dt = pd.to_datetime(df["datetime"], utc=True)
    if not dt.is_monotonic_increasing or dt.duplicated().any():
        raise ValueError("Holdout timestamps must be unique and monotonic.")
    if dt.min() < HOLDOUT_START_UTC:
        raise RuntimeError("STOP_BLOCKED_PRE2015_DATA_ACCESS")
    if dt.max() >= HOLDOUT_END_UTC:
        raise RuntimeError("STOP_BLOCKED_DEVELOPMENT_OR_DISCOVERY_ACCESS")
    years = set(int(y) for y in dt.dt.year.unique())
    if not years.issubset(set(HOLDOUT_YEARS)):
        raise RuntimeError(f"STOP_BLOCKED_OUTSIDE_HOLDOUT_YEARS: {sorted(years)}")
    if require_all_years and years != set(HOLDOUT_YEARS):
        raise RuntimeError(f"STOP_BLOCKED_INCOMPLETE_HOLDOUT_YEARS: {sorted(years)}")


def audit_holdout_dataset(df: pd.DataFrame, *, dataset_sha256: str | None = None) -> Dict[str, Any]:
    validate_holdout_frame(df, require_all_years=True)
    dt = pd.to_datetime(df["datetime"], utc=True)
    o, h, l, c = (df[x].to_numpy(float) for x in ("open", "high", "low", "close"))
    finite = np.isfinite(np.column_stack([o, h, l, c])).all(axis=1)
    invalid = (~finite) | (h < l) | (h < np.maximum(o, c)) | (l > np.minimum(o, c))
    delta = dt.diff().dt.total_seconds().to_numpy(float)
    whole = (dt.dt.second.to_numpy() == 0) & (dt.dt.microsecond.to_numpy() == 0)
    per_year = dt.dt.year.value_counts().sort_index().to_dict()
    return {
        "dataset_sha256": dataset_sha256, "rows": int(len(df)),
        "start": str(dt.min()), "end": str(dt.max()),
        "years": sorted(int(y) for y in dt.dt.year.unique()),
        "per_year_rows": {str(int(k)): int(v) for k, v in per_year.items()},
        "unique_utc_days": int(dt.dt.date.nunique()),
        "duplicate_timestamps": int(dt.duplicated().sum()),
        "non_whole_minute_timestamps": int((~whole).sum()),
        "invalid_or_nonfinite_ohlc": int(invalid.sum()),
        "gaps_gt_60s": int(np.nansum(delta > 60.0)),
        "gaps_gt_1h": int(np.nansum(delta > 3600.0)),
        "max_gap_seconds": float(np.nanmax(delta[1:])) if len(delta) > 1 else 0.0,
        "row_sufficiency": bool(len(df) >= MIN_HOLDOUT_ROWS),
        "per_year_row_sufficiency": bool(all(int(per_year.get(y, 0)) >= MIN_YEAR_ROWS for y in HOLDOUT_YEARS)),
    }


def detect_holdout_breach_events(df: pd.DataFrame) -> List[BreachEvent]:
    validate_holdout_frame(df, require_all_years=False)
    n = len(df)
    if n < 550:
        return []
    atr = compute_atr14(df)
    ph, pl = compute_prior_extremes(df, PRIOR_EXTREME_LOOKBACK)
    eff, is_up, is_down = compute_path_efficiency(df, PATH_WINDOW)
    z = compute_robust_stretch_z(df, ROBUST_WINDOW)
    ap = compute_atr_percentiles(atr, 500)
    o, hi, lo, cl = (df[x].to_numpy(float) for x in ("open", "high", "low", "close"))
    av, phv, plv = atr.to_numpy(float), ph.to_numpy(float), pl.to_numpy(float)
    dts = pd.DatetimeIndex(df["datetime"])
    events, eid = [], 0
    for t in range(510, n - 35):
        a = av[t]
        if not np.isfinite(a) or a <= 0:
            continue
        upper = np.isfinite(phv[t]) and hi[t] > phv[t]
        lower = np.isfinite(plv[t]) and lo[t] < plv[t]
        if upper == lower:
            continue
        if upper:
            if cl[t] < phv[t]: ec = "FAILED_AUCTION"
            elif cl[t] > phv[t]: ec = "ACCEPTED_BREAKOUT"
            else: continue
            side, prior, aligned, zm = "SHORT", phv[t], bool(is_up[t]), bool(z[t] >= ROBUST_Z_THRESHOLD)
        else:
            if cl[t] > plv[t]: ec = "FAILED_AUCTION"
            elif cl[t] < plv[t]: ec = "ACCEPTED_BREAKOUT"
            else: continue
            side, prior, aligned, zm = "LONG", plv[t], bool(is_down[t]), bool(z[t] <= -ROBUST_Z_THRESHOLD)
        ev = float(eff[t]); pct = float(ap[t])
        events.append(BreachEvent(
            eid, t, pd.Timestamp(dts[t]), side, ec, float(prior), float(o[t]), float(hi[t]),
            float(lo[t]), float(cl[t]), ev, bool(aligned and ev >= EFFICIENCY_THRESHOLD),
            float(z[t]), zm, float(a), pct, bool(pct >= ATR_PERCENTILE_THRESHOLD),
        ))
        eid += 1
    return events


def build_holdout_mechanism_frame(df: pd.DataFrame, events: Sequence[BreachEvent]) -> pd.DataFrame:
    validate_holdout_frame(df, require_all_years=False)
    if not events:
        return pd.DataFrame()
    pdh, pdl = compute_previous_observed_day_levels(df)
    session_idx = build_completed_session_levels_clocktime(df)
    m15_idx = build_confirmed_m15_swing_zones(df)
    rows = []
    for ev in events:
        t, atr = int(ev.bar_index), float(ev.atr14)
        o, h, l, c = map(float, (ev.price_open, ev.price_high, ev.price_low, ev.price_close))
        if not np.isfinite(atr) or atr <= 0 or h <= l:
            continue
        if ev.side == "LONG": extreme, level, wanted = l, pdl[t], "LOW"
        else: extreme, level, wanted = h, pdh[t], "HIGH"
        tol = REACTION_DISTANCE_ATR * atr
        pd_match = bool(np.isfinite(level) and ((l <= level <= h) or abs(extreme - level) <= tol))
        sl, sw, _ = session_idx[wanted].recent_slice(ev.datetime, SESSION_LOOKBACK)
        session_match = _candle_intersects_any_zone(l, h, sl, sw)
        if not session_match and len(sl): session_match = bool(np.any(np.abs(extreme - sl) <= tol))
        ml, mw, _ = m15_idx[wanted].recent_slice(ev.datetime, M15_SWING_LOOKBACK)
        m15_match = _candle_intersects_any_zone(l, h, ml, mw)
        rows.append({
            "event_id": int(ev.event_id), "bar_index": t, "datetime": pd.Timestamp(ev.datetime),
            "year": int(pd.Timestamp(ev.datetime).year), "hour": int(pd.Timestamp(ev.datetime).hour),
            "side": ev.side, "event_class": ev.event_class, "prior_extreme": float(ev.prior_extreme),
            "event_close": c, "atr14": atr, "path_efficiency": float(ev.efficiency_ratio),
            "stretch_abs": abs(float(ev.stretch_z)), "atr_percentile": float(ev.atr_percentile),
            "location_count": int(pd_match) + int(session_match) + int(m15_match),
        })
    base = pd.DataFrame(rows)
    if base.empty: return base
    base = add_gap_aware_state_labels(df, base, horizons=HORIZONS_MINUTES)
    base = add_reversion_budget_variables(df, base, horizons=HORIZONS_MINUTES)
    atr_pre = compute_atr14(df).shift(1).to_numpy(float)
    base["pre_event_atr14"] = atr_pre[base["bar_index"].to_numpy(int)]
    return base


def build_holdout_frame(df: pd.DataFrame) -> pd.DataFrame:
    return build_holdout_mechanism_frame(df, detect_holdout_breach_events(df))


def _holdout_control_matrix(p: pd.DataFrame, include_year_effects: bool = True):
    hour = p["hour"].to_numpy(float); n = len(p)
    cols = [np.ones(n), p["_exc_control"].to_numpy(float), p["atr_percentile"].to_numpy(float)/100.0,
            p["path_efficiency"].to_numpy(float), p["stretch_abs"].to_numpy(float), p["location_count"].to_numpy(float),
            (p["side"].to_numpy(object)=="LONG").astype(float), np.sin(2*np.pi*hour/24), np.cos(2*np.pi*hour/24)]
    names = ["intercept","coordinate_excursion","atr_percentile_scaled","path_efficiency","stretch_abs","location_count","side_LONG","hour_sin","hour_cos"]
    if include_year_effects:
        year = p["year"].to_numpy(int)
        for y in (2016, 2017): cols.append((year==y).astype(float)); names.append(f"year_{y}")
    return np.column_stack(cols), names


def fit_holdout_payload(p: pd.DataFrame, *, include_year_effects=True, return_residuals=False):
    if len(p) < 50: return {"n": int(len(p)), "rho": np.nan}
    x, y = p["_x"].to_numpy(float), p["_y"].to_numpy(float)
    z, names = _holdout_control_matrix(p, include_year_effects)
    bx, by = np.linalg.lstsq(z, x, rcond=None)[0], np.linalg.lstsq(z, y, rcond=None)[0]
    rx, ry = x-z@bx, y-z@by; den = float(rx@rx)
    rho = np.nan if den <= 1e-15 else float((rx@ry)/den)
    out = {"n": int(len(p)), "rho": rho, "attenuation_fraction": float(1-rho) if np.isfinite(rho) else np.nan,
           "controls": "|".join(names), "x_mean": float(np.mean(x)), "y_mean": float(np.mean(y))}
    if return_residuals:
        out.update({"_rx": rx, "_ry": ry, "_datetime": pd.to_datetime(p["datetime"], utc=True).to_numpy()})
    return out


def fit_holdout_representation(frame, rep, *, year=None, return_residuals=False):
    p = _representation_payload(frame, rep, PRIMARY_HORIZON_MINUTES)
    if year is not None: p = p[p["year"] == int(year)].copy()
    out = fit_holdout_payload(p, include_year_effects=(year is None), return_residuals=return_residuals)
    out.update({"representation": rep, "horizon_min": 5, "coverage_events": int(len(p))})
    if year is not None: out["year"] = int(year)
    return out


def day_block_bootstrap(fit, *, iterations=BOOTSTRAP_ITERATIONS, seed=BOOTSTRAP_SEED):
    rx, ry = np.asarray(fit.get("_rx", []), float), np.asarray(fit.get("_ry", []), float)
    dts = pd.to_datetime(fit.get("_datetime", []), utc=True)
    if len(rx)==0: return {"iterations": int(iterations), "valid_iterations": 0}
    w = pd.DataFrame({"d": pd.DatetimeIndex(dts).date, "xy": rx*ry, "xx": rx*rx})
    stats = w.groupby("d", sort=True)[["xy","xx"]].sum().to_numpy(float); n=len(stats); rng=np.random.default_rng(seed); vals=[]
    for _ in range(iterations):
        s=stats[rng.integers(0,n,size=n)].sum(axis=0)
        if s[1]>1e-15: vals.append(float(s[0]/s[1]))
    a=np.asarray(vals,float)
    return {"iterations":iterations,"seed":seed,"unique_utc_days":n,"valid_iterations":len(a),"point_rho":float(fit.get("rho",np.nan)),
            "mean_rho":float(np.mean(a)) if len(a) else np.nan,"ci95_lower":float(np.quantile(a,.025)) if len(a) else np.nan,
            "ci95_upper":float(np.quantile(a,.975)) if len(a) else np.nan}


def build_confirmation_table(frame):
    rows=[]; boots={}; fits={}
    for rep in REPRESENTATIONS:
        fit=fit_holdout_representation(frame,rep,return_residuals=True); bs=day_block_bootstrap(fit)
        row={k:v for k,v in fit.items() if not k.startswith("_")}; row.update(ci95_lower=bs.get("ci95_lower",np.nan),ci95_upper=bs.get("ci95_upper",np.nan))
        rows.append(row); boots[rep]=bs; fits[rep]=fit
    return pd.DataFrame(rows), boots, fits


def joint_max_rho_day_block_bootstrap(fits, *, iterations=BOOTSTRAP_ITERATIONS, seed=BOOTSTRAP_SEED):
    daily={}; days=set(); observed={}
    for rep in REPRESENTATIONS:
        f=fits[rep]; rx=np.asarray(f.get("_rx",[]),float); ry=np.asarray(f.get("_ry",[]),float); dts=pd.to_datetime(f.get("_datetime",[]),utc=True)
        if len(rx)==0: return {"iterations":iterations,"valid_iterations":0,"error":f"missing residuals {rep}"}
        g=pd.DataFrame({"d":pd.DatetimeIndex(dts).date,"xy":rx*ry,"xx":rx*rx}).groupby("d",sort=True)[["xy","xx"]].sum()
        daily[rep]=g; days.update(g.index.tolist()); observed[rep]=float(f.get("rho",np.nan))
    days=sorted(days); aligned={r:g.reindex(days,fill_value=0.0)[["xy","xx"]].to_numpy(float) for r,g in daily.items()}
    rng=np.random.default_rng(seed); vals=[]; n=len(days)
    for _ in range(iterations):
        idx=rng.integers(0,n,size=n); rs=[]; ok=True
        for r in REPRESENTATIONS:
            s=aligned[r][idx].sum(axis=0)
            if s[1]<=1e-15: ok=False; break
            rs.append(float(s[0]/s[1]))
        if ok: vals.append(max(rs))
    a=np.asarray(vals,float)
    return {"method":"SHARED_UTC_DAY_RESAMPLE_MAX_RHO","iterations":iterations,"seed":seed,"unique_utc_days":n,"valid_iterations":len(a),
            "observed_rho_by_representation":observed,"observed_max_rho":float(max(observed.values())),
            "bootstrap_mean_max_rho":float(np.mean(a)) if len(a) else np.nan,
            "bootstrap_ci95_upper_max_rho":float(np.quantile(a,.975)) if len(a) else np.nan}


def build_yearly_descriptive_table(frame):
    return pd.DataFrame([{"representation":r,"year":y,"n":int((f:=fit_holdout_representation(frame,r,year=y)).get("n",0)),"rho_5m":float(f.get("rho",np.nan))}
                         for r in REPRESENTATIONS for y in HOLDOUT_YEARS])


def evaluate_final_holdout_gates(audit, frame, confirmation, boots, joint):
    exact_n=int(frame["exact_5m_available"].sum()) if len(frame) else 0
    exact_pct=float(frame["exact_5m_available"].mean()*100) if len(frame) else 0.0
    dp=_representation_payload(frame,"EXCURSION_RATIO",5) if len(frame) else pd.DataFrame(); d_cov=float(len(dp)/exact_n*100) if exact_n else 0.0
    g0=(int(audit.get("rows",0))>=MIN_HOLDOUT_ROWS and bool(audit.get("per_year_row_sufficiency",False)) and set(audit.get("years",[]))==set(HOLDOUT_YEARS)
        and int(audit.get("duplicate_timestamps",1))==0 and int(audit.get("non_whole_minute_timestamps",1))==0 and int(audit.get("invalid_or_nonfinite_ohlc",1))==0
        and len(frame)>=MIN_BREACH_EVENTS and exact_pct>=MIN_EXACT_5M_COVERAGE_PCT and d_cov>=MIN_EXCURSION_RATIO_COVERAGE_PCT
        and all(int(boots.get(r,{}).get("valid_iterations",0))==BOOTSTRAP_ITERATIONS for r in REPRESENTATIONS)
        and int(joint.get("valid_iterations",0))==BOOTSTRAP_ITERATIONS)
    primary=confirmation[confirmation["horizon_min"]==5]
    rm={str(x["representation"]):float(x["rho"]) for _,x in primary.iterrows()}; um={str(x["representation"]):float(x["ci95_upper"]) for _,x in primary.iterrows()}
    g1=len(rm)==4 and all(np.isfinite(rm.get(r,np.nan)) and rm[r]<1 for r in REPRESENTATIONS)
    g2=len(um)==4 and all(np.isfinite(um.get(r,np.nan)) and um[r]<1 for r in REPRESENTATIONS)
    ju=float(joint.get("bootstrap_ci95_upper_max_rho",np.nan)); g3=bool(np.isfinite(ju) and ju<1)
    if not g0: verdict,status="FINAL_HOLDOUT_BLOCKED_DATA_INSUFFICIENT_OR_INVALID","CLOSED_WITHOUT_SCIENTIFIC_VERDICT_DATA_BLOCKED"
    elif g1 and g2 and g3: verdict,status="FINAL_HOLDOUT_CONFIRMED","CLOSE_CONFIRMED_PHENOMENON"
    else: verdict,status="FINAL_HOLDOUT_REJECTED","CLOSE_REJECTED_MECHANISM_FAMILY"
    return {"G0_holdout_data_quality_and_coverage":bool(g0),"G1_all_four_point_rho_5m_below_one":bool(g1),"G2_all_four_individual_ci_upper_below_one":bool(g2),
            "G3_joint_max_rho_bootstrap_upper_below_one":bool(g3),"breach_events":int(len(frame)),"exact_5m_coverage_pct":exact_pct,
            "excursion_ratio_5m_coverage_pct":d_cov,"rho_5m_by_representation":rm,"ci95_upper_by_representation":um,
            "joint_ci95_upper_max_rho":ju,"verdict":verdict,"research_program_status":status}
