"""
EXPERIMENT H-100: STATISTICAL EVENT STUDY OF VOLATILITY COMPRESSION
====================================================================
Pure econometric event study measuring forward volatility, returns, MFE, and MAE
following compression events versus unconditional baselines.

Evaluates 4 compression definitions across horizons: k in [1, 3, 6, 12, 24, 48] bars.
1. Definition A: Bollinger Bands inside Keltner Channels (Squeeze >= 4 bars)
2. Definition B: ATR(14) <= 20th Percentile (rolling 100 bars)
3. Definition C: Normalized True Range (NTR) <= 20th Percentile
4. Definition D: Normalized Bar Range (High - Low) <= 20th Percentile
"""

import os
import sys
import numpy as np
import pandas as pd
from scipy import stats
from deep_quant_engine import DeepQuantEngine

sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None

def run_compression_event_study():
    print("=" * 95)
    print("📊 EXPERIMENT H-100: COMPRESSION EVENT STUDY (GOLD H1 2001-2026)")
    print("=" * 95)
    
    engine = DeepQuantEngine("GOLD_H1_2001_2026.csv")
    df = engine.df.copy()
    
    c = df['close'].values
    h = df['high'].values
    l = df['low'].values
    o = df['open'].values
    n = len(c)
    
    # -------------------------------------------------------------
    # 1. COMPUTE COMPRESSION EVENT MASKS
    # -------------------------------------------------------------
    c_s = pd.Series(c)
    
    # Def A: Bollinger inside Keltner
    mid = c_s.rolling(20).mean().values
    std = c_s.rolling(20).std().values
    bb_u = mid + 2.0 * std
    bb_l = mid - 2.0 * std
    
    tr = np.maximum(h - l, np.maximum(np.abs(h - np.roll(c, 1)), np.abs(l - np.roll(c, 1))))
    atr20 = pd.Series(tr).rolling(20).mean().values
    atr14 = pd.Series(tr).rolling(14).mean().values
    kelt_mid = c_s.ewm(span=20, adjust=False).mean().values
    kelt_u = kelt_mid + 1.2 * atr20
    kelt_l = kelt_mid - 1.2 * atr20
    
    is_sqz = (bb_u < kelt_u) & (bb_l > kelt_l)
    sqz_cnt = pd.Series(is_sqz.astype(int)).rolling(5).sum().values
    # Episode trigger: was squeezing for >= 4 bars, now bar triggers
    event_sqz = (sqz_cnt >= 4)
    
    # Def B: ATR14 <= 20th percentile over rolling 100 bars
    atr_p20 = pd.Series(atr14).rolling(100).quantile(0.20).values
    event_atr_p20 = (atr14 <= atr_p20)
    
    # Def C: NTR <= 20th percentile
    ntr = tr / c
    ntr_p20 = pd.Series(ntr).rolling(100).quantile(0.20).values
    event_ntr_p20 = (ntr <= ntr_p20)
    
    # Def D: Range (High - Low) / Close <= 20th percentile
    bar_range = (h - l) / c
    range_p20 = pd.Series(bar_range).rolling(100).quantile(0.20).values
    event_range_p20 = (bar_range <= range_p20)
    
    events = {
        'Unconditional Baseline (All Bars)': np.ones(n, dtype=bool),
        'Def A: Bollinger Squeeze (>=4 bars)': event_sqz,
        'Def B: ATR14 <= 20th Percentile': event_atr_p20,
        'Def C: NTR <= 20th Percentile': event_ntr_p20,
        'Def D: Bar Range <= 20th Percentile': event_range_p20
    }
    
    horizons = [1, 3, 6, 12, 24, 48]
    
    # -------------------------------------------------------------
    # 2. MEASURE FORWARD EXPANSION METRICS
    # -------------------------------------------------------------
    results = []
    
    for ev_name, ev_mask in events.items():
        # Clean mask: avoid first 200 bars and last 50 bars
        valid_idx = np.where(ev_mask & (np.arange(n) >= 200) & (np.arange(n) < n - 48))[0]
        n_events = len(valid_idx)
        
        for k in horizons:
            abs_returns = []
            max_ranges = []
            dir_returns = []
            
            for idx in valid_idx:
                p0 = c[idx]
                pk = c[idx + k]
                # Absolute return
                abs_ret = abs(pk - p0) / p0 * 100.0
                abs_returns.append(abs_ret)
                
                # Max Range over forward window
                win_h = np.max(h[idx+1 : idx+k+1])
                win_l = np.min(l[idx+1 : idx+k+1])
                max_rng = (win_h - win_l) / p0 * 100.0
                max_ranges.append(max_rng)
                
                # Directional return
                dir_ret = (pk - p0) / p0 * 100.0
                dir_returns.append(dir_ret)
                
            mean_abs_ret = np.mean(abs_returns)
            mean_max_rng = np.mean(max_ranges)
            mean_dir_ret = np.mean(dir_returns)
            std_dir_ret = np.std(dir_returns)
            
            results.append({
                'Event Definition': ev_name,
                'Horizon (k bars)': f"{k}h",
                'Event Count': n_events,
                'Mean Abs Ret (%)': mean_abs_ret,
                'Mean Max Range (%)': mean_max_rng,
                'Directional Mean (%)': mean_dir_ret,
                'Directional Std (%)': std_dir_ret
            })
            
    res_df = pd.DataFrame(results)
    
    # Print comparison table for 24h and 48h
    print("\n--- FORWARD EXPANSION MAGNITUDE BY HORIZON ---")
    summary_pivot = res_df.pivot(index='Event Definition', columns='Horizon (k bars)', values='Mean Max Range (%)')
    print(summary_pivot.to_string())
    
    # Statistical significance test (t-test of Def A vs Baseline for 24h and 48h range)
    baseline_24 = [ (np.max(h[i+1:i+25]) - np.min(l[i+1:i+25])) / c[i] * 100.0 for i in range(200, n-48) ]
    sqz_idx = np.where(event_sqz & (np.arange(n) >= 200) & (np.arange(n) < n - 48))[0]
    sqz_24 = [ (np.max(h[i+1:i+25]) - np.min(l[i+1:i+25])) / c[i] * 100.0 for i in sqz_idx ]
    
    t_stat, p_val = stats.ttest_ind(sqz_24, baseline_24, equal_var=False)
    print(f"\nStatistical Significance (24-Hour Forward Max Range):")
    print(f"  Baseline Mean Range: {np.mean(baseline_24):.3f}% | Squeeze Mean Range: {np.mean(sqz_24):.3f}%")
    print(f"  Welch's t-statistic : {t_stat:.3f} (p-value = {p_val:.4e})")
    
    # Save machine-readable output
    os.makedirs(os.path.join(os.path.dirname(__file__), '..', 'reports', 'v3'), exist_ok=True)
    res_df.to_csv(os.path.join(os.path.dirname(__file__), '..', 'reports', 'v3', 'h100_compression_event_study.csv'), index=False)
    print("\nSaved H-100 event study to AlphaLab_Antigravity/reports/v3/h100_compression_event_study.csv")
    return res_df

if __name__ == '__main__':
    run_compression_event_study()
