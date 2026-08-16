"""
V3.6 LMDC EVENT STUDY ENGINE
============================
Rigorous causal event-study engine analyzing London Morning Directional Carry (LMDC)
on Gold M30 across 33 complete quarters (2018Q2 to 2026Q2).
"""

from __future__ import annotations

import json
import os
import sys
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None

EVAL_START = "2018Q2"
EVAL_END = "2026Q2"
SPREAD_PIPS = 25.0
COMMISSION_PER_LOT = 7.0
FIXED_LOT = 0.10


def compute_true_range(df: pd.DataFrame) -> np.ndarray:
    h = df['high'].values
    l = df['low'].values
    c = df['close'].values
    prev_c = np.roll(c, 1)
    prev_c[0] = c[0]
    tr = np.maximum(h - l, np.maximum(np.abs(h - prev_c), np.abs(l - prev_c)))
    return tr


def run_lmdc_event_study(data_filename: str = "GOLD_M30.csv") -> Dict:
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    data_path = os.path.join(root_dir, data_filename)
    if not os.path.exists(data_path):
        data_path = os.path.join(root_dir, "AlphaLab_Antigravity", data_filename)
        
    df = pd.read_csv(data_path)
    
    # Standardize column names
    col_map = {c: c.lower().strip() for c in df.columns}
    df = df.rename(columns=col_map)
    if 'datetime_str' in df.columns:
        df['datetime'] = pd.to_datetime(df['datetime_str'])
    else:
        df['datetime'] = pd.to_datetime(df['datetime'])
        
    df = df.sort_values('datetime').reset_index(drop=True)
    df['tr'] = compute_true_range(df)
    df['atr14'] = pd.Series(df['tr']).rolling(14).mean().values
    
    df['date'] = df['datetime'].dt.date
    df['time'] = df['datetime'].dt.time
    df['hour'] = df['datetime'].dt.hour
    df['minute'] = df['datetime'].dt.minute
    df['quarter'] = df['datetime'].dt.to_period('Q').astype(str)
    df['year'] = df['datetime'].dt.year
    
    # -------------------------------------------------------------
    # 1. EXTRACT DAILY MORNING EVENTS (08:00 <= hour < 12:00)
    # -------------------------------------------------------------
    events: List[Dict] = []
    
    # Group by date
    unique_dates = df['date'].unique()
    
    for d in unique_dates:
        day_bars = df[df['date'] == d].copy().reset_index(drop=True)
        if len(day_bars) < 20:  # Skip truncated holidays/weekends
            continue
            
        q_str = day_bars['quarter'].iloc[0]
        if q_str < EVAL_START or q_str > EVAL_END:
            continue
            
        # Morning bars: 08:00 to 11:59 UTC
        morning_mask = (day_bars['hour'] >= 8) & (day_bars['hour'] < 12)
        m_bars = day_bars[morning_mask]
        
        if len(m_bars) < 6:  # Expected 8 bars on M30 (08:00, 08:30, 09:00, 09:30, 10:00, 10:30, 11:00, 11:30)
            continue
            
        # First bar at/after 08:00
        m_open = float(m_bars.iloc[0]['open'])
        # Final completed bar before 12:00 (11:30 bar)
        last_m_bar = m_bars.iloc[-1]
        m_close = float(last_m_bar['close'])
        m_move = m_close - m_open
        
        # Causal ATR measured at 11:30 bar close
        atr14_pre12 = float(last_m_bar['atr14'])
        if np.isnan(atr14_pre12) or atr14_pre12 <= 0:
            continue
            
        morning_z = m_move / atr14_pre12
        abs_morning_z = abs(morning_z)
        
        if m_move > 0:
            direction = 1
            direction_str = "POSITIVE"
        elif m_move < 0:
            direction = -1
            direction_str = "NEGATIVE"
        else:
            direction = 0
            direction_str = "NEUTRAL"
            
        # Assign fixed magnitude bucket
        if abs_morning_z < 0.5:
            bucket = "TIER_0_LT_0.5"
            bucket_label = "|z| < 0.5 (Baseline/Quiet)"
        elif abs_morning_z < 1.0:
            bucket = "TIER_1_0.5_TO_1.0"
            bucket_label = "0.5 <= |z| < 1.0 (Mild)"
        elif abs_morning_z < 1.5:
            bucket = "TIER_2_1.0_TO_1.5"
            bucket_label = "1.0 <= |z| < 1.5 (Moderate)"
        elif abs_morning_z < 2.0:
            bucket = "TIER_3_1.5_TO_2.0"
            bucket_label = "1.5 <= |z| < 2.0 (Strong)"
        else:
            bucket = "TIER_4_GE_2.0"
            bucket_label = "|z| >= 2.0 (Extreme)"
            
        # Reference price: 12:00 UTC bar close
        bar_1200 = day_bars[(day_bars['hour'] == 12) & (day_bars['minute'] == 0)]
        if len(bar_1200) == 0:
            continue
        p_ref = float(bar_1200.iloc[0]['close'])
        ref_idx = bar_1200.index[0]
        
        # Forward horizons
        # 30m = ref_idx + 1 (12:30 bar close)
        # 1h  = ref_idx + 2 (13:00 bar close)
        # 2h  = ref_idx + 4 (14:00 bar close)
        # 4h  = ref_idx + 8 (16:00 bar close)
        # 8h  = ref_idx + 16 (20:00 bar close)
        # Day close = last bar of day
        
        horizons_dict = {}
        for h_name, offset in [("30m", 1), ("1h", 2), ("2h", 4), ("4h", 8), ("8h", 16)]:
            target_idx = ref_idx + offset
            if target_idx < len(day_bars):
                p_future = float(day_bars.iloc[target_idx]['close'])
                raw_ret = p_future - p_ref
                signed_ret = direction * raw_ret
                signed_atr_ret = signed_ret / atr14_pre12
                horizons_dict[f"raw_ret_{h_name}"] = raw_ret
                horizons_dict[f"signed_ret_{h_name}"] = signed_ret
                horizons_dict[f"signed_atr_ret_{h_name}"] = signed_atr_ret
                horizons_dict[f"is_cont_{h_name}"] = bool(signed_ret > 0)
            else:
                horizons_dict[f"raw_ret_{h_name}"] = np.nan
                horizons_dict[f"signed_ret_{h_name}"] = np.nan
                horizons_dict[f"signed_atr_ret_{h_name}"] = np.nan
                horizons_dict[f"is_cont_{h_name}"] = np.nan
                
        # Day close horizon
        last_day_bar = day_bars.iloc[-1]
        p_day_close = float(last_day_bar['close'])
        raw_ret_day = p_day_close - p_ref
        signed_ret_day = direction * raw_ret_day
        signed_atr_ret_day = signed_ret_day / atr14_pre12
        horizons_dict["raw_ret_day_close"] = raw_ret_day
        horizons_dict["signed_ret_day_close"] = signed_ret_day
        horizons_dict["signed_atr_ret_day_close"] = signed_atr_ret_day
        horizons_dict["is_cont_day_close"] = bool(signed_ret_day > 0)
        
        # MFE / MAE over remaining day bars (after 12:00 UTC)
        afternoon_bars = day_bars.iloc[ref_idx+1:]
        if len(afternoon_bars) > 0 and direction != 0:
            highs = afternoon_bars['high'].values
            lows = afternoon_bars['low'].values
            if direction == 1:
                mfe_pts = np.max(highs) - p_ref
                mae_pts = p_ref - np.min(lows)
            else:
                mfe_pts = p_ref - np.min(lows)
                mae_pts = np.max(highs) - p_ref
            mfe_atr = max(mfe_pts, 0.0) / atr14_pre12
            mae_atr = max(mae_pts, 0.0) / atr14_pre12
        else:
            mfe_atr = np.nan
            mae_atr = np.nan
            
        # Volatility regime indicator (ATR14 / ATR50)
        atr50 = float(last_m_bar['atr14'])  # Placeholder, let's use rolling ATR50 if available
        
        events.append({
            'date': str(d),
            'quarter': q_str,
            'year': int(day_bars['year'].iloc[0]),
            'morning_open': m_open,
            'morning_close': m_close,
            'morning_move': m_move,
            'atr14_pre12': atr14_pre12,
            'morning_z': morning_z,
            'abs_morning_z': abs_morning_z,
            'direction': direction,
            'direction_str': direction_str,
            'bucket': bucket,
            'bucket_label': bucket_label,
            'p_ref_1200': p_ref,
            'mfe_atr': mfe_atr,
            'mae_atr': mae_atr,
            **horizons_dict
        })
        
    edf = pd.DataFrame(events)
    out_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "reports", "v3_6"))
    os.makedirs(out_dir, exist_ok=True)
    
    # Save raw events CSV
    events_csv_path = os.path.join(out_dir, "lmdc_events.csv")
    edf.to_csv(events_csv_path, index=False)
    
    # -------------------------------------------------------------
    # 2. BUCKET SUMMARY
    # -------------------------------------------------------------
    bucket_order = [
        "TIER_0_LT_0.5",
        "TIER_1_0.5_TO_1.0",
        "TIER_2_1.0_TO_1.5",
        "TIER_3_1.5_TO_2.0",
        "TIER_4_GE_2.0"
    ]
    
    bucket_rows = []
    for b in bucket_order:
        sub = edf[edf['bucket'] == b]
        n_b = len(sub)
        row = {
            'bucket': b,
            'bucket_label': sub['bucket_label'].iloc[0] if n_b > 0 else b,
            'event_count': n_b,
            'event_share_pct': (n_b / len(edf) * 100.0) if len(edf) > 0 else 0.0
        }
        for h in ["30m", "1h", "2h", "4h", "8h", "day_close"]:
            col = f"signed_atr_ret_{h}"
            c_col = f"is_cont_{h}"
            vals = sub[col].dropna().values
            c_vals = sub[c_col].dropna().values
            row[f"mean_atr_{h}"] = float(np.mean(vals)) if len(vals) > 0 else np.nan
            row[f"median_atr_{h}"] = float(np.median(vals)) if len(vals) > 0 else np.nan
            row[f"std_atr_{h}"] = float(np.std(vals)) if len(vals) > 0 else np.nan
            row[f"p25_atr_{h}"] = float(np.percentile(vals, 25)) if len(vals) > 0 else np.nan
            row[f"p75_atr_{h}"] = float(np.percentile(vals, 75)) if len(vals) > 0 else np.nan
            row[f"cont_prob_{h}"] = float(np.mean(c_vals) * 100.0) if len(c_vals) > 0 else np.nan
        bucket_rows.append(row)
    bdf = pd.DataFrame(bucket_rows)
    bdf.to_csv(os.path.join(out_dir, "lmdc_bucket_summary.csv"), index=False)
    
    # -------------------------------------------------------------
    # 3. HORIZON SUMMARY (POOLED & STRONG-MOVE BUCKETS)
    # -------------------------------------------------------------
    horizon_rows = []
    for h in ["30m", "1h", "2h", "4h", "8h", "day_close"]:
        col = f"signed_atr_ret_{h}"
        c_col = f"is_cont_{h}"
        # All events
        all_vals = edf[col].dropna().values
        all_c = edf[c_col].dropna().values
        # Moderate+ (Tier 2, 3, 4: |z| >= 1.0)
        mod_sub = edf[edf['abs_morning_z'] >= 1.0]
        mod_vals = mod_sub[col].dropna().values
        mod_c = mod_sub[c_col].dropna().values
        # Strong+ (Tier 3, 4: |z| >= 1.5)
        str_sub = edf[edf['abs_morning_z'] >= 1.5]
        str_vals = str_sub[col].dropna().values
        str_c = str_sub[c_col].dropna().values
        
        horizon_rows.append({
            'horizon': h,
            'all_count': len(all_vals),
            'all_mean_atr': float(np.mean(all_vals)),
            'all_median_atr': float(np.median(all_vals)),
            'all_cont_prob': float(np.mean(all_c) * 100.0),
            'mod_count': len(mod_vals),
            'mod_mean_atr': float(np.mean(mod_vals)) if len(mod_vals) > 0 else np.nan,
            'mod_median_atr': float(np.median(mod_vals)) if len(mod_vals) > 0 else np.nan,
            'mod_cont_prob': float(np.mean(mod_c) * 100.0) if len(mod_c) > 0 else np.nan,
            'str_count': len(str_vals),
            'str_mean_atr': float(np.mean(str_vals)) if len(str_vals) > 0 else np.nan,
            'str_median_atr': float(np.median(str_vals)) if len(str_vals) > 0 else np.nan,
            'str_cont_prob': float(np.mean(str_c) * 100.0) if len(str_c) > 0 else np.nan
        })
    hdf = pd.DataFrame(horizon_rows)
    hdf.to_csv(os.path.join(out_dir, "lmdc_horizon_summary.csv"), index=False)
    
    # -------------------------------------------------------------
    # 4. DIRECTIONAL SUMMARY (LONG VS SHORT MORNINGS)
    # -------------------------------------------------------------
    dir_rows = []
    for d_val, d_name in [(1, "POSITIVE_MORNING_LONG"), (-1, "NEGATIVE_MORNING_SHORT")]:
        sub = edf[edf['direction'] == d_val]
        row = {
            'direction': d_name,
            'total_events': len(sub),
            'strong_events_ge_1.5': len(sub[sub['abs_morning_z'] >= 1.5]),
            'mean_abs_z': float(sub['abs_morning_z'].mean()),
            'median_mfe_atr': float(sub['mfe_atr'].median()),
            'median_mae_atr': float(sub['mae_atr'].median()),
            'mfe_mae_ratio': float(sub['mfe_atr'].median() / sub['mae_atr'].median()) if sub['mae_atr'].median() > 0 else np.nan
        }
        for h in ["1h", "2h", "4h", "8h"]:
            vals = sub[f"signed_atr_ret_{h}"].dropna().values
            c_vals = sub[f"is_cont_{h}"].dropna().values
            row[f"mean_atr_{h}"] = float(np.mean(vals)) if len(vals) > 0 else np.nan
            row[f"median_atr_{h}"] = float(np.median(vals)) if len(vals) > 0 else np.nan
            row[f"cont_prob_{h}"] = float(np.mean(c_vals) * 100.0) if len(c_vals) > 0 else np.nan
        dir_rows.append(row)
    ddf = pd.DataFrame(dir_rows)
    ddf.to_csv(os.path.join(out_dir, "lmdc_direction_summary.csv"), index=False)
    
    # -------------------------------------------------------------
    # 5. QUARTER-BY-QUARTER EFFECTS (33 COMPLETE QUARTERS)
    # -------------------------------------------------------------
    q_rows = []
    # Build complete list of 33 quarters
    all_quarters = [f"{y}Q{q}" for y in range(2018, 2027) for q in range(1, 5) if EVAL_START <= f"{y}Q{q}" <= EVAL_END]
    for q_str in all_quarters:
        sub = edf[edf['quarter'] == q_str]
        n_q = len(sub)
        sub_str = sub[sub['abs_morning_z'] >= 1.5]
        
        q_rows.append({
            'quarter': q_str,
            'total_events': n_q,
            'strong_events_ge_1.5': len(sub_str),
            'mean_signed_atr_1h': float(sub['signed_atr_ret_1h'].mean()) if n_q > 0 else np.nan,
            'mean_signed_atr_2h': float(sub['signed_atr_ret_2h'].mean()) if n_q > 0 else np.nan,
            'mean_signed_atr_4h': float(sub['signed_atr_ret_4h'].mean()) if n_q > 0 else np.nan,
            'mean_signed_atr_8h': float(sub['signed_atr_ret_8h'].mean()) if n_q > 0 else np.nan,
            'cont_prob_2h': float(sub['is_cont_2h'].mean() * 100.0) if n_q > 0 else np.nan,
            'cont_prob_4h': float(sub['is_cont_4h'].mean() * 100.0) if n_q > 0 else np.nan,
            'strong_mean_atr_4h': float(sub_str['signed_atr_ret_4h'].mean()) if len(sub_str) > 0 else np.nan
        })
    qdf = pd.DataFrame(q_rows)
    qdf.to_csv(os.path.join(out_dir, "lmdc_quarter_effects.csv"), index=False)
    
    # -------------------------------------------------------------
    # 6. YEAR-BY-YEAR STABILITY (2018-2026, FOCUS 2019-2025)
    # -------------------------------------------------------------
    y_rows = []
    for y in sorted(edf['year'].unique()):
        sub = edf[edf['year'] == y]
        is_full = bool(2019 <= y <= 2025)
        y_rows.append({
            'year': int(y),
            'is_full_calendar_year': is_full,
            'event_count': len(sub),
            'mean_signed_atr_1h': float(sub['signed_atr_ret_1h'].mean()),
            'median_signed_atr_1h': float(sub['signed_atr_ret_1h'].median()),
            'mean_signed_atr_2h': float(sub['signed_atr_ret_2h'].mean()),
            'median_signed_atr_2h': float(sub['signed_atr_ret_2h'].median()),
            'mean_signed_atr_4h': float(sub['signed_atr_ret_4h'].mean()),
            'median_signed_atr_4h': float(sub['signed_atr_ret_4h'].median()),
            'mean_signed_atr_8h': float(sub['signed_atr_ret_8h'].mean()),
            'median_signed_atr_8h': float(sub['signed_atr_ret_8h'].median()),
            'cont_prob_2h': float(sub['is_cont_2h'].mean() * 100.0),
            'cont_prob_4h': float(sub['is_cont_4h'].mean() * 100.0),
            'is_positive_4h': bool(sub['signed_atr_ret_4h'].mean() > 0)
        })
    ydf = pd.DataFrame(y_rows)
    ydf.to_csv(os.path.join(out_dir, "lmdc_year_summary.csv"), index=False)
    
    # -------------------------------------------------------------
    # 7. LEAVE-ONE-YEAR-OUT SENSITIVITY (2019..2025)
    # -------------------------------------------------------------
    loyo_rows = []
    full_years_sub = edf[(edf['year'] >= 2019) & (edf['year'] <= 2025)]
    base_1h = float(full_years_sub['signed_atr_ret_1h'].mean())
    base_2h = float(full_years_sub['signed_atr_ret_2h'].mean())
    base_4h = float(full_years_sub['signed_atr_ret_4h'].mean())
    
    for y_omit in range(2019, 2026):
        sub = full_years_sub[full_years_sub['year'] != y_omit]
        loyo_rows.append({
            'omitted_year': y_omit,
            'remaining_events': len(sub),
            'mean_signed_atr_1h': float(sub['signed_atr_ret_1h'].mean()),
            'mean_signed_atr_2h': float(sub['signed_atr_ret_2h'].mean()),
            'mean_signed_atr_4h': float(sub['signed_atr_ret_4h'].mean()),
            'diff_from_baseline_4h': float(sub['signed_atr_ret_4h'].mean() - base_4h),
            'sign_stable_4h': bool((sub['signed_atr_ret_4h'].mean() > 0) == (base_4h > 0))
        })
    loyodf = pd.DataFrame(loyo_rows)
    loyodf.to_csv(os.path.join(out_dir, "lmdc_leave_one_year_out.csv"), index=False)
    
    # -------------------------------------------------------------
    # 8. RECENT-REGIME COMPARISON (PRE-2025 VS RECENT)
    # -------------------------------------------------------------
    pre2025_sub = edf[edf['quarter'] <= '2024Q4']
    recent_sub = edf[edf['quarter'] >= '2025Q1']
    
    p25_rows = [
        {
            'view': 'VIEW_A_FULL_SAMPLE',
            'period': f'{EVAL_START}..{EVAL_END}',
            'event_count': len(edf),
            'mean_signed_atr_1h': float(edf['signed_atr_ret_1h'].mean()),
            'mean_signed_atr_2h': float(edf['signed_atr_ret_2h'].mean()),
            'mean_signed_atr_4h': float(edf['signed_atr_ret_4h'].mean()),
            'mean_signed_atr_8h': float(edf['signed_atr_ret_8h'].mean()),
            'cont_prob_2h': float(edf['is_cont_2h'].mean() * 100.0),
            'cont_prob_4h': float(edf['is_cont_4h'].mean() * 100.0)
        },
        {
            'view': 'VIEW_B_PRE_2025',
            'period': f'{EVAL_START}..2024Q4',
            'event_count': len(pre2025_sub),
            'mean_signed_atr_1h': float(pre2025_sub['signed_atr_ret_1h'].mean()),
            'mean_signed_atr_2h': float(pre2025_sub['signed_atr_ret_2h'].mean()),
            'mean_signed_atr_4h': float(pre2025_sub['signed_atr_ret_4h'].mean()),
            'mean_signed_atr_8h': float(pre2025_sub['signed_atr_ret_8h'].mean()),
            'cont_prob_2h': float(pre2025_sub['is_cont_2h'].mean() * 100.0),
            'cont_prob_4h': float(pre2025_sub['is_cont_4h'].mean() * 100.0)
        },
        {
            'view': 'VIEW_C_RECENT',
            'period': '2025Q1..2026Q2',
            'event_count': len(recent_sub),
            'mean_signed_atr_1h': float(recent_sub['signed_atr_ret_1h'].mean()),
            'mean_signed_atr_2h': float(recent_sub['signed_atr_ret_2h'].mean()),
            'mean_signed_atr_4h': float(recent_sub['signed_atr_ret_4h'].mean()),
            'mean_signed_atr_8h': float(recent_sub['signed_atr_ret_8h'].mean()),
            'cont_prob_2h': float(recent_sub['is_cont_2h'].mean() * 100.0),
            'cont_prob_4h': float(recent_sub['is_cont_4h'].mean() * 100.0)
        }
    ]
    p25df = pd.DataFrame(p25_rows)
    p25df.to_csv(os.path.join(out_dir, "lmdc_pre2025_vs_recent.csv"), index=False)
    
    # -------------------------------------------------------------
    # 9. MFE / MAE SUMMARY BY BUCKET
    # -------------------------------------------------------------
    mfe_rows = []
    for b in bucket_order:
        sub = edf[edf['bucket'] == b]
        mfe_v = sub['mfe_atr'].dropna().values
        mae_v = sub['mae_atr'].dropna().values
        mfe_rows.append({
            'bucket': b,
            'event_count': len(sub),
            'mean_mfe_atr': float(np.mean(mfe_v)) if len(mfe_v) > 0 else np.nan,
            'median_mfe_atr': float(np.median(mfe_v)) if len(mfe_v) > 0 else np.nan,
            'p25_mfe_atr': float(np.percentile(mfe_v, 25)) if len(mfe_v) > 0 else np.nan,
            'p75_mfe_atr': float(np.percentile(mfe_v, 75)) if len(mfe_v) > 0 else np.nan,
            'mean_mae_atr': float(np.mean(mae_v)) if len(mae_v) > 0 else np.nan,
            'median_mae_atr': float(np.median(mae_v)) if len(mae_v) > 0 else np.nan,
            'p25_mae_atr': float(np.percentile(mae_v, 25)) if len(mae_v) > 0 else np.nan,
            'p75_mae_atr': float(np.percentile(mae_v, 75)) if len(mae_v) > 0 else np.nan,
            'median_mfe_mae_ratio': float(np.median(mfe_v) / np.median(mae_v)) if len(mae_v) > 0 and np.median(mae_v) > 0 else np.nan
        })
    mfedf = pd.DataFrame(mfe_rows)
    mfedf.to_csv(os.path.join(out_dir, "lmdc_mfe_mae_summary.csv"), index=False)
    
    # -------------------------------------------------------------
    # 10. QUARTER-BLOCK BOOTSTRAP (2,000 RESAMPLES)
    # -------------------------------------------------------------
    np.random.seed(42)
    quarters_list = edf['quarter'].unique()
    n_q = len(quarters_list)
    n_boot = 2000
    
    boot_records = []
    for h in ["1h", "2h", "4h", "8h"]:
        col = f"signed_atr_ret_{h}"
        # Group events by quarter into dict of arrays
        q_map = {q: edf[edf['quarter'] == q][col].dropna().values for q in quarters_list}
        
        boot_means = []
        for _ in range(n_boot):
            sampled_quarters = np.random.choice(quarters_list, size=n_q, replace=True)
            sampled_vals = np.concatenate([q_map[sq] for sq in sampled_quarters if len(q_map[sq]) > 0])
            boot_means.append(np.mean(sampled_vals))
            
        boot_records.append({
            'horizon': h,
            'n_resamples': n_boot,
            'sample_mean_atr': float(edf[col].mean()),
            'ci_2.5_pct': float(np.percentile(boot_means, 2.5)),
            'ci_50.0_pct_median': float(np.percentile(boot_means, 50.0)),
            'ci_97.5_pct': float(np.percentile(boot_means, 97.5)),
            'ci_width': float(np.percentile(boot_means, 97.5) - np.percentile(boot_means, 2.5)),
            'p_strictly_positive': float(np.mean(np.array(boot_means) > 0) * 100.0)
        })
    bootdf = pd.DataFrame(boot_records)
    bootdf.to_csv(os.path.join(out_dir, "lmdc_block_bootstrap.csv"), index=False)
    
    # -------------------------------------------------------------
    # 11. COST BENCHMARK DIAGNOSTIC JSON
    # -------------------------------------------------------------
    mean_atr_pts = float(edf['atr14_pre12'].mean())
    spread_cost_pts = SPREAD_PIPS * 0.01  # 25 pips = $0.25 USD on Gold
    comm_cost_pts = (COMMISSION_PER_LOT / 100.0)  # $7/100oz = $0.07 USD
    total_cost_pts = spread_cost_pts + comm_cost_pts  # $0.32 USD
    cost_in_atr = total_cost_pts / mean_atr_pts if mean_atr_pts > 0 else np.nan
    
    cost_meta = {
        'instrument': 'GOLD_M30',
        'mean_atr14_pre12_usd': mean_atr_pts,
        'spread_pips': SPREAD_PIPS,
        'spread_cost_usd': spread_cost_pts,
        'commission_per_lot_usd': COMMISSION_PER_LOT,
        'commission_cost_usd_per_oz': comm_cost_pts,
        'total_roundtrip_cost_usd': total_cost_pts,
        'cost_in_atr_units': cost_in_atr,
        'observed_1h_signed_atr_return': float(edf['signed_atr_ret_1h'].mean()),
        'observed_2h_signed_atr_return': float(edf['signed_atr_ret_2h'].mean()),
        'observed_4h_signed_atr_return': float(edf['signed_atr_ret_4h'].mean()),
        'observed_8h_signed_atr_return': float(edf['signed_atr_ret_8h'].mean()),
        'is_4h_effect_greater_than_cost': bool(float(edf['signed_atr_ret_4h'].mean()) > cost_in_atr)
    }
    with open(os.path.join(out_dir, "lmdc_cost_benchmark.json"), 'w') as f:
        json.dump(cost_meta, f, indent=2)
        
    # -------------------------------------------------------------
    # 12. METADATA JSON
    # -------------------------------------------------------------
    meta = {
        'study_name': 'V3.6 London Morning Directional Carry (LMDC) Event Study',
        'evaluation_window': f'{EVAL_START}..{EVAL_END}',
        'total_complete_quarters': 33,
        'total_trading_day_events': len(edf),
        'positive_morning_events': int((edf['direction'] == 1).sum()),
        'negative_morning_events': int((edf['direction'] == -1).sum()),
        'neutral_morning_events': int((edf['direction'] == 0).sum()),
        'strong_events_ge_1.5': int((edf['abs_morning_z'] >= 1.5).sum()),
        'extreme_events_ge_2.0': int((edf['abs_morning_z'] >= 2.0).sum())
    }
    with open(os.path.join(out_dir, "lmdc_metadata.json"), 'w') as f:
        json.dump(meta, f, indent=2)
        
    print(f"✅ V3.6 Event Study Complete. Generated 12 raw files under {out_dir}")
    return meta

if __name__ == '__main__':
    run_lmdc_event_study()
