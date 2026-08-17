from __future__ import annotations

"""Event study, day-block bootstrap, and discovery gate evaluation for ALAB-M1-FUSION-001R."""

from typing import Any, Dict, List, Tuple
import numpy as np
import pandas as pd

from .failed_auction import FailedAuctionEvent

HORIZONS = [1, 3, 5, 10, 15, 30]
BOOTSTRAP_SIMULATIONS = 2000
RANDOM_SEED = 20260817
MIN_VALID_YEAR_EVENTS = 200


def run_event_study(
    df: pd.DataFrame,
    events: List[FailedAuctionEvent],
    data_audit_meta: Dict[str, Any],
) -> Tuple[pd.DataFrame, Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
    """Compute forward outcomes, day-block bootstrap, overlap statistics, and gate evaluations.
    
    Returns:
        df_events: DataFrame of all detected events and forward outcomes
        event_decision: Full gate evaluation and summary
        overlap_audit: Serial dependence and overlap metrics
        block_bootstrap_info: Day-level block bootstrap details
    """
    if not events:
        empty_res = {
            "verdict": "STOP_BLOCKED_INSUFFICIENT_DATA",
            "total_events": 0,
            "all_gates_pass": False,
        }
        return pd.DataFrame(), empty_res, {}, {}

    closes = df["close"].to_numpy(dtype=float)
    highs = df["high"].to_numpy(dtype=float)
    lows = df["low"].to_numpy(dtype=float)
    n = len(df)

    event_rows = []
    for ev in events:
        t = ev.bar_index
        side = ev.side
        c_t = closes[t]

        row: Dict[str, Any] = {
            "event_id": ev.event_id,
            "bar_index": t,
            "datetime": ev.datetime,
            "date": ev.datetime.date(),
            "year": ev.datetime.year,
            "hour": ev.datetime.hour,
            "side": side,
            "reaction_score": ev.reaction_score,
            "score_bin": ev.score_bin,
            "efficiency_ratio": ev.efficiency_ratio,
            "stretch_z": ev.stretch_z,
            "atr14": ev.atr14,
            "atr_percentile": ev.atr_percentile,
            "pdh_pdl_match": ev.pdh_pdl_match,
            "session_level_match": ev.session_level_match,
            "m15_swing_match": ev.m15_swing_match,
        }

        # Volatility state
        if ev.atr_percentile < 50:
            row["vol_state"] = "0-49"
        elif ev.atr_percentile < 80:
            row["vol_state"] = "50-79"
        elif ev.atr_percentile < 95:
            row["vol_state"] = "80-94"
        else:
            row["vol_state"] = "95-100"

        # Session
        h_val = ev.datetime.hour
        if 0 <= h_val < 8:
            row["session"] = "ASIA"
        elif 8 <= h_val < 13:
            row["session"] = "LONDON_RESEARCH"
        elif 13 <= h_val < 18:
            row["session"] = "NEW_YORK_RESEARCH"
        else:
            row["session"] = "OTHER"

        # Forward returns & excursions
        for h in HORIZONS:
            end_idx = t + h
            if end_idx >= n:
                row[f"fwd_ret_{h}m"] = np.nan
                row[f"mfe_{h}m"] = np.nan
                row[f"mae_{h}m"] = np.nan
                continue

            c_future = closes[end_idx]
            sub_highs = highs[t + 1 : end_idx + 1]
            sub_lows = lows[t + 1 : end_idx + 1]

            if side == "LONG":
                ret = (c_future - c_t) / c_t
                mfe = (np.max(sub_highs) - c_t) / c_t if len(sub_highs) > 0 else 0.0
                mae = (c_t - np.min(sub_lows)) / c_t if len(sub_lows) > 0 else 0.0
            else:
                ret = (c_t - c_future) / c_t
                mfe = (c_t - np.min(sub_lows)) / c_t if len(sub_lows) > 0 else 0.0
                mae = (np.max(sub_highs) - c_t) / c_t if len(sub_highs) > 0 else 0.0

            row[f"fwd_ret_{h}m"] = ret
            row[f"mfe_{h}m"] = mfe
            row[f"mae_{h}m"] = mae

        event_rows.append(row)

    df_events = pd.DataFrame(event_rows)

    # 1. Overlap Audit
    overlap_audit = compute_overlap_audit(df_events)

    # 2. Block Bootstrap (Day-Level)
    block_bootstrap_info = compute_day_block_bootstrap(df_events)

    # 3. Summary Statistics
    summary_stats = compute_summary_statistics(df_events, block_bootstrap_info)

    # 4. Discovery Gate Evaluation
    event_decision = evaluate_replication_gates(
        df_events, summary_stats, block_bootstrap_info, data_audit_meta
    )

    return df_events, event_decision, overlap_audit, block_bootstrap_info


def compute_overlap_audit(df_events: pd.DataFrame) -> Dict[str, Any]:
    """Calculate event density and forward window overlap percentages."""
    if len(df_events) < 2:
        return {}

    bar_indices = df_events["bar_index"].to_numpy()
    gaps = np.diff(bar_indices)
    events_per_day = df_events.groupby("date")["event_id"].count()

    overlap_5m = float(np.mean(gaps <= 5) * 100.0) if len(gaps) > 0 else 0.0
    overlap_10m = float(np.mean(gaps <= 10) * 100.0) if len(gaps) > 0 else 0.0
    overlap_30m = float(np.mean(gaps <= 30) * 100.0) if len(gaps) > 0 else 0.0

    return {
        "total_events": len(df_events),
        "total_days": len(events_per_day),
        "mean_events_per_day": float(events_per_day.mean()),
        "median_events_per_day": float(events_per_day.median()),
        "p90_events_per_day": float(events_per_day.quantile(0.90)),
        "median_gap_bars": float(np.median(gaps)) if len(gaps) > 0 else 0.0,
        "overlap_pct_5m": overlap_5m,
        "overlap_pct_10m": overlap_10m,
        "overlap_pct_30m": overlap_30m,
    }


def compute_day_block_bootstrap(
    df_events: pd.DataFrame, n_boot: int = BOOTSTRAP_SIMULATIONS, seed: int = RANDOM_SEED
) -> Dict[str, Any]:
    """Perform non-overlapping UTC Day-Level Block Bootstrap."""
    dates = df_events["date"].unique()
    n_days = len(dates)
    if n_days == 0:
        return {}

    # Pre-group event returns by day for fast lookup
    day_returns: Dict[int, Dict[str, np.ndarray]] = {}
    for d_idx, d in enumerate(dates):
        sub = df_events[df_events["date"] == d]
        day_returns[d_idx] = {
            f"h{h}m": sub[f"fwd_ret_{h}m"].dropna().to_numpy(dtype=float) for h in HORIZONS
        }

    rng = np.random.default_rng(seed)
    block_results: Dict[str, Any] = {}

    for h in HORIZONS:
        h_key = f"h{h}m"
        boot_means = np.empty(n_boot, dtype=float)

        for b in range(n_boot):
            sampled_day_indices = rng.choice(n_days, size=n_days, replace=True)
            # Combine all event returns from sampled days
            sampled_rets = []
            for s_idx in sampled_day_indices:
                r_arr = day_returns[s_idx][h_key]
                if len(r_arr) > 0:
                    sampled_rets.append(r_arr)

            if sampled_rets:
                concat_arr = np.concatenate(sampled_rets)
                boot_means[b] = np.mean(concat_arr)
            else:
                boot_means[b] = 0.0

        ci_lower = float(np.percentile(boot_means, 2.5))
        ci_upper = float(np.percentile(boot_means, 97.5))
        mean_val = float(np.mean(boot_means))

        block_results[h_key] = {
            "mean_bps": mean_val * 10000.0,
            "ci_95_lower_bps": ci_lower * 10000.0,
            "ci_95_upper_bps": ci_upper * 10000.0,
            "boot_simulations": n_boot,
            "unique_days_sampled": n_days,
        }

    return block_results


def compute_summary_statistics(
    df_events: pd.DataFrame, block_bootstrap: Dict[str, Any]
) -> Dict[str, Any]:
    stats: Dict[str, Any] = {}
    for h in HORIZONS:
        col = f"fwd_ret_{h}m"
        valid_rets = df_events[col].dropna().to_numpy(dtype=float)
        valid_mfe = df_events[f"mfe_{h}m"].dropna().to_numpy(dtype=float)
        valid_mae = df_events[f"mae_{h}m"].dropna().to_numpy(dtype=float)
        n_obs = len(valid_rets)
        if n_obs == 0:
            continue

        mean_ret = float(np.mean(valid_rets))
        median_ret = float(np.median(valid_rets))
        std_ret = float(np.std(valid_rets, ddof=1)) if n_obs > 1 else 0.0
        win_rate = float(np.mean(valid_rets > 0))

        # Day-block bootstrap stats
        bb = block_bootstrap.get(f"h{h}m", {})

        stats[f"h{h}m"] = {
            "n": n_obs,
            "mean_return_bps": mean_ret * 10000.0,
            "median_return_bps": median_ret * 10000.0,
            "std_return_bps": std_ret * 10000.0,
            "win_proportion": win_rate,
            "day_block_ci_95_lower_bps": bb.get("ci_95_lower_bps", mean_ret * 10000.0),
            "day_block_ci_95_upper_bps": bb.get("ci_95_upper_bps", mean_ret * 10000.0),
            "mean_mfe_bps": float(np.mean(valid_mfe)) * 10000.0 if len(valid_mfe) > 0 else 0.0,
            "median_mfe_bps": float(np.median(valid_mfe)) * 10000.0 if len(valid_mfe) > 0 else 0.0,
            "mean_mae_bps": float(np.mean(valid_mae)) * 10000.0 if len(valid_mae) > 0 else 0.0,
            "median_mae_bps": float(np.median(valid_mae)) * 10000.0 if len(valid_mae) > 0 else 0.0,
        }
    return stats


def evaluate_replication_gates(
    df_events: pd.DataFrame,
    summary_stats: Dict[str, Any],
    block_bootstrap: Dict[str, Any],
    data_audit_meta: Dict[str, Any],
) -> Dict[str, Any]:
    """Evaluate full replication gates (Gate 0 through 5 + descriptive Gate 6)."""
    total_events = len(df_events)
    if "side" in df_events.columns:
        long_events = int((df_events["side"] == "LONG").sum())
        short_events = int((df_events["side"] == "SHORT").sum())
    else:
        long_events = total_events // 2
        short_events = total_events - long_events

    # Gate 0: Data requirements (>=1,000,000 rows, >=3 calendar years)
    is_suff_hist = bool(data_audit_meta.get("is_sufficient_history", False))
    is_suff_temp = bool(data_audit_meta.get("is_sufficient_temporal_coverage", False))
    gate0_data = is_suff_hist and is_suff_temp

    # Gate 1: Event sample (>=500 total, >=150 long, >=150 short)
    gate1_sample = (total_events >= 500) and (long_events >= 150) and (short_events >= 150)

    # Gate 2: Primary 5m mean return > 0
    h5_stats = summary_stats.get("h5m", {})
    mean_5m = h5_stats.get("mean_return_bps", -999.0)
    gate2_mean_5m_pos = mean_5m > 0.0

    # Gate 3: DAY-BLOCK bootstrap 95% CI lower bound > 0
    ci_lower_5m = h5_stats.get("day_block_ci_95_lower_bps", -999.0)
    gate3_day_block_ci_pos = ci_lower_5m > 0.0

    # Gate 4: Adjacent horizon (3m or 10m) mean > 0
    mean_3m = summary_stats.get("h3m", {}).get("mean_return_bps", -999.0)
    mean_10m = summary_stats.get("h10m", {}).get("mean_return_bps", -999.0)
    gate4_adjacent_pos = (mean_3m > 0.0) or (mean_10m > 0.0)

    # Gate 5: Temporal stability (>=3 valid calendar years with >=200 events, >=70% positive)
    years = sorted(df_events["year"].unique())
    valid_years_count = 0
    pos_valid_years_count = 0
    year_details = {}

    for y in years:
        sub_y = df_events[df_events["year"] == y]["fwd_ret_5m"].dropna()
        n_y = len(sub_y)
        if n_y >= MIN_VALID_YEAR_EVENTS:
            valid_years_count += 1
            y_mean = float(np.mean(sub_y)) * 10000.0
            year_details[int(y)] = {"n_events": n_y, "mean_5m_bps": y_mean, "is_valid": True}
            if y_mean > 0.0:
                pos_valid_years_count += 1
        else:
            y_mean = float(np.mean(sub_y)) * 10000.0 if n_y > 0 else 0.0
            year_details[int(y)] = {"n_events": n_y, "mean_5m_bps": y_mean, "is_valid": False}

    gate5_year_stability = (
        (valid_years_count >= 3)
        and (pos_valid_years_count / valid_years_count >= 0.70)
    )

    # Gate 6: Descriptive score consistency check
    score_bins = ["3-4", "5-6", "7-8", "9-10"]
    score_bin_means = {}
    score_bin_counts = {}
    for sb in score_bins:
        sub_sb = df_events[df_events["score_bin"] == sb]["fwd_ret_5m"].dropna()
        score_bin_counts[sb] = len(sub_sb)
        if len(sub_sb) > 0:
            score_bin_means[sb] = float(np.mean(sub_sb)) * 10000.0
        else:
            score_bin_means[sb] = 0.0

    # Descriptive classification
    m34 = score_bin_means.get("3-4", 0.0)
    m56 = score_bin_means.get("5-6", 0.0)
    m78 = score_bin_means.get("7-8", 0.0)
    m910 = score_bin_means.get("9-10", 0.0)
    n910 = score_bin_counts.get("9-10", 0)

    if m34 <= m56 <= m78 <= m910 and n910 >= 30:
        score_consistency = "MONOTONIC"
    elif n910 < 30 and m78 > m34:
        score_consistency = "INSUFFICIENT_HIGH_SCORE_SAMPLE"
    elif m78 > m34:
        score_consistency = "PARTIAL"
    else:
        score_consistency = "INVERTED"

    # Overall Verdict
    all_gates_pass = (
        gate0_data
        and gate1_sample
        and gate2_mean_5m_pos
        and gate3_day_block_ci_pos
        and gate4_adjacent_pos
        and gate5_year_stability
    )

    if not gate0_data:
        verdict = "STOP_BLOCKED_INSUFFICIENT_HISTORY"
    elif not gate1_sample:
        verdict = "INSUFFICIENT_REPLICATION_DATA"
    elif all_gates_pass:
        verdict = "REPLICATION_CONFIRMED"
    else:
        verdict = "REPLICATION_NOT_CONFIRMED"

    return {
        "verdict": verdict,
        "total_events": total_events,
        "long_events": long_events,
        "short_events": short_events,
        "summary_stats": summary_stats,
        "valid_calendar_years_count": valid_years_count,
        "positive_valid_years_count": pos_valid_years_count,
        "year_details": year_details,
        "score_bin_means_5m": score_bin_means,
        "score_bin_counts": score_bin_counts,
        "score_consistency_status": score_consistency,
        "gate0_data": gate0_data,
        "gate1_sample": gate1_sample,
        "gate2_mean_5m_pos": gate2_mean_5m_pos,
        "gate3_day_block_ci_pos": gate3_day_block_ci_pos,
        "gate4_adjacent_pos": gate4_adjacent_pos,
        "gate5_year_stability": gate5_year_stability,
        "all_gates_pass": all_gates_pass,
    }
