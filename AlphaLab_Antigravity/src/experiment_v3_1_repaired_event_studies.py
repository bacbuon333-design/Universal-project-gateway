"""
V3.1 REPAIRED EVENT STUDIES: H-100 (EPISODE-DECOUPLED) & H-101 (IDENTICAL HORIZONS)
===================================================================================
Repairs:
1. Distinct event families:
   - Family A: Compression State (all active bars)
   - Family B: Compression Episode Start (first bar of squeeze)
   - Family C: Compression Episode End (last bar of squeeze)
   - Family D: Compression -> Upper Breakout Release (Deduplicated first break)
   - Family E: Compression -> Lower Breakout Release (Deduplicated first break)
   - Family F: Non-compression BB Upper Break Baseline
   - Family G: Non-compression BB Lower Break Baseline
   - Family H: Unconditional All Bars Baseline
2. Deduplication & Episode ID assignment (zero overlapping pseudo-observations).
3. Identical Horizon directional evaluation for Long & Short at 6h, 12h, 24h, 48h, 72h.
"""

import os
import sys
import numpy as np
import pandas as pd
from scipy import stats
from deep_quant_engine import DeepQuantEngine

sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None

def run_repaired_event_studies():
    print("=" * 95)
    print("🔬 V3.1 REPAIRED EVENT STUDIES: H-100 (EPISODE DECOUPLED) & H-101 (IDENTICAL HORIZONS)")
    print("=" * 95)
    
    engine = DeepQuantEngine("GOLD_H1_2001_2026.csv", pip_size=0.01, point_val=0.01)
    df = engine.df.copy()
    
    c = df['close'].values
    h = df['high'].values
    l = df['low'].values
    n = len(c)
    
    c_s = pd.Series(c)
    mid = c_s.rolling(20).mean().values
    std = c_s.rolling(20).std().values
    bb_u = mid + 2.0 * std
    bb_l = mid - 2.0 * std
    
    tr = np.maximum(h - l, np.maximum(np.abs(h - np.roll(c, 1)), np.abs(l - np.roll(c, 1))))
    atr20 = pd.Series(tr).rolling(20).mean().values
    kelt_mid = c_s.ewm(span=20, adjust=False).mean().values
    kelt_u = kelt_mid + 1.2 * atr20
    kelt_l = kelt_mid - 1.2 * atr20
    
    is_sqz = (bb_u < kelt_u) & (bb_l > kelt_l)
    
    # -------------------------------------------------------------
    # 1. IDENTIFY UNIQUE COMPRESSION EPISODES & EPISODE TRANSITIONS
    # -------------------------------------------------------------
    episode_id = np.zeros(n, dtype=int)
    ep_count = 0
    in_ep = False
    ep_starts = []
    ep_ends = []
    
    # Track episodes where squeeze lasts >= 4 consecutive bars
    sqz_len = 0
    cur_ep_indices = []
    
    for i in range(n):
        if is_sqz[i]:
            sqz_len += 1
            cur_ep_indices.append(i)
        else:
            if sqz_len >= 4:
                ep_count += 1
                ep_starts.append(cur_ep_indices[0])
                ep_ends.append(cur_ep_indices[-1])
                for idx in cur_ep_indices:
                    episode_id[idx] = ep_count
            sqz_len = 0
            cur_ep_indices = []
            
    print(f"Total Discrete Squeeze Episodes (>= 4 bars): {ep_count}")
    
    # Event Family Masks
    mask_state = (episode_id > 0)
    mask_start = np.zeros(n, dtype=bool)
    mask_start[ep_starts] = True
    mask_end = np.zeros(n, dtype=bool)
    mask_end[ep_ends] = True
    
    # Deduplicated Breakout Releases: first bar within 10 bars after episode end that crosses BB
    ep_upper_release = []
    ep_lower_release = []
    
    for end_i in ep_ends:
        for f_i in range(end_i + 1, min(n, end_i + 10)):
            if c[f_i] > bb_u[f_i]:
                ep_upper_release.append(f_i)
                break
            elif c[f_i] < bb_l[f_i]:
                ep_lower_release.append(f_i)
                break
                
    mask_up_rel = np.zeros(n, dtype=bool)
    mask_up_rel[ep_upper_release] = True
    mask_dn_rel = np.zeros(n, dtype=bool)
    mask_dn_rel[ep_lower_release] = True
    
    # Non-compression BB breakout baseline (crosses BB when no squeeze in past 20 bars)
    recent_sqz_20 = pd.Series(is_sqz.astype(int)).rolling(20).sum().values
    mask_non_sqz_up = (c > bb_u) & (recent_sqz_20 == 0)
    mask_non_sqz_dn = (c < bb_l) & (recent_sqz_20 == 0)
    
    # Deduplicate non-sqz breakouts
    def dedup(m, min_dist=10):
        idx = np.where(m & (np.arange(n) >= 200) & (np.arange(n) < n - 72))[0]
        res = []
        last_i = -999
        for i in idx:
            if i - last_i >= min_dist:
                res.append(i)
                last_i = i
        return res
        
    non_sqz_up_idx = dedup(mask_non_sqz_up)
    non_sqz_dn_idx = dedup(mask_non_sqz_dn)
    
    # Macro EMA 200
    macro_ema = c_s.ewm(span=200, adjust=False).mean().values
    macro_bull = (c > macro_ema) & (macro_ema > pd.Series(macro_ema).shift(5).values)
    macro_bear = (c < macro_ema) & (macro_ema < pd.Series(macro_ema).shift(5).values)
    
    # -------------------------------------------------------------
    # 2. H-100 REPAIRED FORWARD VOLATILITY EXPANSION EVENT STUDY
    # -------------------------------------------------------------
    print("\n--- H-100 REPAIRED: FORWARD VOLATILITY EXPANSION BY EVENT FAMILY ---")
    families = {
        'Family A: Compression State Bars': np.where(mask_state & (np.arange(n) >= 200) & (np.arange(n) < n - 72))[0],
        'Family B: Compression Episode Start': np.where(mask_start & (np.arange(n) >= 200) & (np.arange(n) < n - 72))[0],
        'Family C: Compression Episode End': np.where(mask_end & (np.arange(n) >= 200) & (np.arange(n) < n - 72))[0],
        'Family D: Squeeze -> Upper Breakout Release': np.where(mask_up_rel & (np.arange(n) >= 200) & (np.arange(n) < n - 72))[0],
        'Family E: Squeeze -> Lower Breakout Release': np.where(mask_dn_rel & (np.arange(n) >= 200) & (np.arange(n) < n - 72))[0],
        'Family F: Non-Compression BB Upper Break Baseline': non_sqz_up_idx,
        'Family G: Non-Compression BB Lower Break Baseline': non_sqz_dn_idx,
        'Family H: Unconditional Baseline (Random Bars)': np.arange(200, n - 72, 5) # Subsampled to avoid overlap
    }
    
    h100_records = []
    horizons = [6, 12, 24, 48, 72]
    
    for f_name, indices in families.items():
        n_ev = len(indices)
        for k in horizons:
            ranges = []
            abs_rets = []
            for idx in indices:
                p0 = c[idx]
                pk = c[idx + k]
                abs_rets.append(abs(pk - p0) / p0 * 100.0)
                win_h = np.max(h[idx+1 : idx+k+1])
                win_l = np.min(l[idx+1 : idx+k+1])
                ranges.append((win_h - win_l) / p0 * 100.0)
            h100_records.append({
                'Event Family': f_name,
                'Events': n_ev,
                'Horizon': f"{k}h",
                'Mean Max Range (%)': np.mean(ranges) if n_ev > 0 else 0.0,
                'Mean Abs Return (%)': np.mean(abs_rets) if n_ev > 0 else 0.0
            })
            
    h100_df = pd.DataFrame(h100_records)
    piv_h100 = h100_df.pivot(index='Event Family', columns='Horizon', values='Mean Max Range (%)')
    print(piv_h100[['6h', '12h', '24h', '48h', '72h']].to_string())
    
    # -------------------------------------------------------------
    # 3. H-101 REPAIRED: DIRECTIONALITY AT IDENTICAL HORIZONS
    # -------------------------------------------------------------
    print("\n--- H-101 REPAIRED: DIRECTIONAL PREDICTABILITY AT IDENTICAL HORIZONS ---")
    
    dir_test_groups = [
        # Long tests
        ("LONG: Non-Squeeze Upper Break (Baseline)", non_sqz_up_idx, False, False),
        ("LONG: Squeeze Upper Breakout Release", np.where(mask_up_rel & (np.arange(n) >= 200) & (np.arange(n) < n - 72))[0], False, False),
        ("LONG: Squeeze Upper Break + Macro Bullish Trend", np.where(mask_up_rel & macro_bull & (np.arange(n) >= 200) & (np.arange(n) < n - 72))[0], False, False),
        
        # Short tests
        ("SHORT: Non-Squeeze Lower Break (Baseline)", non_sqz_dn_idx, True, False),
        ("SHORT: Squeeze Lower Breakout Release", np.where(mask_dn_rel & (np.arange(n) >= 200) & (np.arange(n) < n - 72))[0], True, False),
        ("SHORT: Squeeze Lower Break + Macro Bearish Trend", np.where(mask_dn_rel & macro_bear & (np.arange(n) >= 200) & (np.arange(n) < n - 72))[0], True, False),
    ]
    
    h101_records = []
    for g_name, indices, is_short, _ in dir_test_groups:
        n_ev = len(indices)
        for k in horizons:
            dir_rets = []
            mfes = []
            maes = []
            for idx in indices:
                p0 = c[idx]
                pk = c[idx + k]
                d_ret = ((p0 - pk) if is_short else (pk - p0)) / p0 * 100.0
                dir_rets.append(d_ret)
                
                win_h = np.max(h[idx+1 : idx+k+1])
                win_l = np.min(l[idx+1 : idx+k+1])
                if is_short:
                    mfe = (p0 - win_l) / p0 * 100.0
                    mae = (win_h - p0) / p0 * 100.0
                else:
                    mfe = (win_h - p0) / p0 * 100.0
                    mae = (p0 - win_l) / p0 * 100.0
                mfes.append(mfe)
                maes.append(mae)
                
            mean_ret = np.mean(dir_rets) if n_ev > 0 else 0.0
            med_ret = np.median(dir_rets) if n_ev > 0 else 0.0
            wr = np.mean(np.array(dir_rets) > 0) * 100.0 if n_ev > 0 else 0.0
            mean_mfe = np.mean(mfes) if n_ev > 0 else 0.0
            mean_mae = np.mean(maes) if n_ev > 0 else 0.0
            mfe_mae_ratio = (mean_mfe / mean_mae) if mean_mae > 0 else 0.0
            
            # 95% Confidence Interval for mean return
            ci_half = 1.96 * (np.std(dir_rets) / np.sqrt(n_ev)) if n_ev > 1 else 0.0
            ci_str = f"[{mean_ret - ci_half:+.2f}%, {mean_ret + ci_half:+.2f}%]"
            
            h101_records.append({
                'Architecture': g_name,
                'Events': n_ev,
                'Horizon': f"{k}h",
                'Mean Return (%)': mean_ret,
                'Median Return (%)': med_ret,
                'Win Rate (%)': wr,
                'Mean MFE (%)': mean_mfe,
                'Mean MAE (%)': mean_mae,
                'MFE/MAE Ratio': mfe_mae_ratio,
                '95% CI': ci_str
            })
            
    h101_df = pd.DataFrame(h101_records)
    
    # Print comparison at 24h and 48h
    print("\n--- 24-HOUR HORIZON DIRECTIONALITY ---")
    print(h101_df[h101_df['Horizon'] == '24h'][['Architecture', 'Events', 'Mean Return (%)', 'Win Rate (%)', 'MFE/MAE Ratio', '95% CI']].to_string(index=False))
    
    print("\n--- 48-HOUR HORIZON DIRECTIONALITY ---")
    print(h101_df[h101_df['Horizon'] == '48h'][['Architecture', 'Events', 'Mean Return (%)', 'Win Rate (%)', 'MFE/MAE Ratio', '95% CI']].to_string(index=False))
    
    # Save machine-readable outputs
    os.makedirs(os.path.join(os.path.dirname(__file__), '..', 'reports', 'v3_1'), exist_ok=True)
    h100_df.to_csv(os.path.join(os.path.dirname(__file__), '..', 'reports', 'v3_1', 'h100_repaired_event_study.csv'), index=False)
    h101_df.to_csv(os.path.join(os.path.dirname(__file__), '..', 'reports', 'v3_1', 'h101_repaired_directionality.csv'), index=False)
    print("\nSaved repaired event study reports to AlphaLab_Antigravity/reports/v3_1/.")

if __name__ == '__main__':
    run_repaired_event_studies()
