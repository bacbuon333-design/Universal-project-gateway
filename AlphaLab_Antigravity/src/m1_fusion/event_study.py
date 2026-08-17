from __future__ import annotations

"""Event study engine and statistical evaluation for ALAB-M1-FUSION-001."""

from typing import Any, Dict, List, Tuple
import numpy as np
import pandas as pd

from .failed_auction import FailedAuctionEvent

HORIZONS = [1, 3, 5, 10, 15, 30]
BOOTSTRAP_SIMULATIONS = 2000
RANDOM_SEED = 20260817


def run_event_study(
    df: pd.DataFrame, events: List[FailedAuctionEvent]
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """Compute forward outcomes and statistical metrics across horizons and breakdowns."""
    if not events:
        return pd.DataFrame(), {
            "verdict": "INSUFFICIENT_EVIDENCE",
            "reason": "No events found.",
            "total_events": 0,
        }

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
            "datetime": ev.datetime,
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

        # Compute forward returns and excursions for each horizon
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
                # Long snapback: profit if price moves up
                ret = (c_future - c_t) / c_t
                mfe = (np.max(sub_highs) - c_t) / c_t if len(sub_highs) > 0 else 0.0
                mae = (c_t - np.min(sub_lows)) / c_t if len(sub_lows) > 0 else 0.0
            else:
                # Short snapback: profit if price moves down
                ret = (c_t - c_future) / c_t
                mfe = (c_t - np.min(sub_lows)) / c_t if len(sub_lows) > 0 else 0.0
                mae = (np.max(sub_highs) - c_t) / c_t if len(sub_highs) > 0 else 0.0

            row[f"fwd_ret_{h}m"] = ret
            row[f"mfe_{h}m"] = mfe
            row[f"mae_{h}m"] = mae

        event_rows.append(row)

    df_events = pd.DataFrame(event_rows)

    # Statistical Evaluation & Bootstrapping
    summary_stats = compute_summary_statistics(df_events)
    gate_decision = evaluate_discovery_gates(df_events, summary_stats)

    return df_events, gate_decision


def compute_summary_statistics(df_events: pd.DataFrame) -> Dict[str, Any]:
    """Compute mean, median, std, win rate, MFE, MAE and bootstrap 95% CI."""
    stats: Dict[str, Any] = {}
    rng = np.random.default_rng(RANDOM_SEED)

    for h in HORIZONS:
        col = f"fwd_ret_{h}m"
        valid_rets = df_events[col].dropna().to_numpy(dtype=float)
        mfe_col = f"mfe_{h}m"
        valid_mfe = df_events[mfe_col].dropna().to_numpy(dtype=float)
        mae_col = f"mae_{h}m"
        valid_mae = df_events[mae_col].dropna().to_numpy(dtype=float)

        n_obs = len(valid_rets)
        if n_obs == 0:
            continue

        mean_ret = float(np.mean(valid_rets))
        median_ret = float(np.median(valid_rets))
        std_ret = float(np.std(valid_rets, ddof=1)) if n_obs > 1 else 0.0
        win_rate = float(np.mean(valid_rets > 0))

        # Bootstrap 95% CI for mean return
        if n_obs >= 10:
            boot_means = np.empty(BOOTSTRAP_SIMULATIONS)
            for b in range(BOOTSTRAP_SIMULATIONS):
                sample = rng.choice(valid_rets, size=n_obs, replace=True)
                boot_means[b] = np.mean(sample)
            ci_lower = float(np.percentile(boot_means, 2.5))
            ci_upper = float(np.percentile(boot_means, 97.5))
        else:
            ci_lower = mean_ret
            ci_upper = mean_ret

        stats[f"h{h}m"] = {
            "n": n_obs,
            "mean_return_bps": mean_ret * 10000.0,
            "median_return_bps": median_ret * 10000.0,
            "std_return_bps": std_ret * 10000.0,
            "win_proportion": win_rate,
            "ci_95_lower_bps": ci_lower * 10000.0,
            "ci_95_upper_bps": ci_upper * 10000.0,
            "mean_mfe_bps": float(np.mean(valid_mfe)) * 10000.0 if len(valid_mfe) > 0 else 0.0,
            "median_mfe_bps": float(np.median(valid_mfe)) * 10000.0 if len(valid_mfe) > 0 else 0.0,
            "mean_mae_bps": float(np.mean(valid_mae)) * 10000.0 if len(valid_mae) > 0 else 0.0,
            "median_mae_bps": float(np.median(valid_mae)) * 10000.0 if len(valid_mae) > 0 else 0.0,
        }

    return stats


def evaluate_discovery_gates(
    df_events: pd.DataFrame, summary_stats: Dict[str, Any]
) -> Dict[str, Any]:
    """Evaluate the 6 discovery gates from Section 18."""
    total_events = len(df_events)
    long_events = int((df_events["side"] == "LONG").sum())
    short_events = int((df_events["side"] == "SHORT").sum())

    # Gate 1: Sample size
    gate1_sample = (total_events >= 500) and (long_events >= 150) and (short_events >= 150)

    # Gate 2 & 3: Primary 5m horizon mean and bootstrap CI lower bound
    h5_stats = summary_stats.get("h5m", {})
    mean_5m = h5_stats.get("mean_return_bps", -999.0)
    ci_lower_5m = h5_stats.get("ci_95_lower_bps", -999.0)

    gate2_mean_5m_pos = mean_5m > 0.0
    gate3_ci_lower_pos = ci_lower_5m > 0.0

    # Gate 4: Adjacent horizon (3m or 10m) mean > 0
    mean_3m = summary_stats.get("h3m", {}).get("mean_return_bps", -999.0)
    mean_10m = summary_stats.get("h10m", {}).get("mean_return_bps", -999.0)
    gate4_adjacent_pos = (mean_3m > 0.0) or (mean_10m > 0.0)

    # Gate 5: Year stability (not driven by single year)
    years = sorted(df_events["year"].unique())
    year_means = {}
    pos_years = 0
    for y in years:
        sub_y = df_events[df_events["year"] == y]["fwd_ret_5m"].dropna()
        if len(sub_y) >= 20:
            y_mean = float(np.mean(sub_y)) * 10000.0
            year_means[int(y)] = y_mean
            if y_mean > 0.0:
                pos_years += 1

    total_valid_years = len(year_means)
    gate5_year_stability = (pos_years >= 2) if total_valid_years >= 2 else (pos_years == 1)

    # Gate 6: Score gradient check (high scores do not systematically collapse below low scores)
    score_bins = ["3-4", "5-6", "7-8", "9-10"]
    score_bin_means = {}
    for sb in score_bins:
        sub_sb = df_events[df_events["score_bin"] == sb]["fwd_ret_5m"].dropna()
        if len(sub_sb) >= 10:
            score_bin_means[sb] = float(np.mean(sub_sb)) * 10000.0

    # Check that high score (7-8 or 9-10) is not severely worse than low score (3-4)
    gate6_score_gradient = True
    if "7-8" in score_bin_means and "3-4" in score_bin_means:
        if score_bin_means["7-8"] < score_bin_means["3-4"] - 5.0 and score_bin_means.get("9-10", -999.0) < score_bin_means["3-4"]:
            gate6_score_gradient = False

    all_gates_pass = (
        gate1_sample
        and gate2_mean_5m_pos
        and gate3_ci_lower_pos
        and gate4_adjacent_pos
        and gate5_year_stability
        and gate6_score_gradient
    )

    if not gate1_sample:
        verdict = "INSUFFICIENT_EVIDENCE"
    elif all_gates_pass:
        verdict = "MECHANISM_CLUE"
    else:
        verdict = "NO_MECHANISM_EVIDENCE"

    return {
        "verdict": verdict,
        "total_events": total_events,
        "long_events": long_events,
        "short_events": short_events,
        "summary_stats": summary_stats,
        "year_means_5m": year_means,
        "score_bin_means_5m": score_bin_means,
        "gate1_sample": gate1_sample,
        "gate2_mean_5m_pos": gate2_mean_5m_pos,
        "gate3_ci_lower_pos": gate3_ci_lower_pos,
        "gate4_adjacent_pos": gate4_adjacent_pos,
        "gate5_year_stability": gate5_year_stability,
        "gate6_score_gradient": gate6_score_gradient,
        "all_gates_pass": all_gates_pass,
    }
