"""
EXPERIMENT H-101: DIRECTIONALITY & TRIGGER EVENT STUDY
======================================================
Investigates whether the transition from compression to expansion provides:
1. Magnitude expansion beyond baseline when breakout occurs.
2. Directional persistence (Upward breakout -> Positive forward return, Downward breakout -> Negative forward return).
3. The incremental predictive power of Macro Trend Alignment (EMA 200) and Noise Rejection (ER).
"""

import os
import sys
import numpy as np
import pandas as pd
from scipy import stats
from deep_quant_engine import DeepQuantEngine

sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None

def run_directionality_study():
    print("=" * 95)
    print("📊 EXPERIMENT H-101: DIRECTIONALITY & TRIGGER STUDY (GOLD H1 2001-2026)")
    print("=" * 95)
    
    engine = DeepQuantEngine("GOLD_H1_2001_2026.csv")
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
    sqz_cnt = pd.Series(is_sqz.astype(int)).rolling(5).sum().values
    was_sqz = (pd.Series(sqz_cnt).shift(1).values >= 4)
    
    # Macro EMA 200
    macro_ema = c_s.ewm(span=200, adjust=False).mean().values
    macro_bull = (c > macro_ema) & (macro_ema > pd.Series(macro_ema).shift(5).values)
    macro_bear = (c < macro_ema) & (macro_ema < pd.Series(macro_ema).shift(5).values)
    
    # Kaufman ER
    net_chg = c_s.diff(10).abs()
    sum_chg = c_s.diff(1).abs().rolling(10).sum()
    er = (net_chg / (sum_chg + 1e-9)).values
    er_ok = (er >= 0.20)
    
    # Trigger Events
    break_up = (c > bb_u)
    break_down = (c < bb_l)
    
    triggers = {
        '1. Unconditional Baseline (Random Bars)': np.ones(n, dtype=bool),
        '2. Pure BB Upper Break (No Squeeze)': break_up,
        '3. Squeeze + Upper Break (Squeeze Expansion Long)': was_sqz & break_up,
        '4. Squeeze + Upper Break + Macro Trend Bullish': was_sqz & break_up & macro_bull,
        '5. Squeeze + Upper Break + Macro Trend + ER >= 0.20': was_sqz & break_up & macro_bull & er_ok,
        '6. Pure BB Lower Break (No Squeeze)': break_down,
        '7. Squeeze + Lower Break (Squeeze Expansion Short)': was_sqz & break_down,
        '8. Squeeze + Lower Break + Macro Trend Bearish': was_sqz & break_down & macro_bear,
        '9. Squeeze + Lower Break + Macro Trend + ER >= 0.20': was_sqz & break_down & macro_bear & er_ok,
    }
    
    horizons = [6, 12, 24, 48, 72]
    records = []
    
    for t_name, mask in triggers.items():
        valid_idx = np.where(mask & (np.arange(n) >= 200) & (np.arange(n) < n - 72))[0]
        n_ev = len(valid_idx)
        
        # Deduplicate consecutive trigger bars (keep only episode entry)
        dedup_idx = []
        last_i = -999
        for i in valid_idx:
            if i - last_i >= 5: # At least 5 bars separation
                dedup_idx.append(i)
                last_i = i
        n_dedup = len(dedup_idx)
        
        for k in horizons:
            dir_rets = []
            max_mfe = []
            max_mae = []
            
            for idx in dedup_idx:
                p0 = c[idx]
                pk = c[idx + k]
                # Forward directional return (adjusted: positive if long, inverted if short)
                is_short_test = ('Lower' in t_name)
                d_ret = ((p0 - pk) if is_short_test else (pk - p0)) / p0 * 100.0
                dir_rets.append(d_ret)
                
                # MFE / MAE
                win_h = np.max(h[idx+1 : idx+k+1])
                win_l = np.min(l[idx+1 : idx+k+1])
                if is_short_test:
                    mfe = (p0 - win_l) / p0 * 100.0
                    mae = (win_h - p0) / p0 * 100.0
                else:
                    mfe = (win_h - p0) / p0 * 100.0
                    mae = (p0 - win_l) / p0 * 100.0
                max_mfe.append(mfe)
                max_mae.append(mae)
                
            mean_ret = np.mean(dir_rets) if n_dedup > 0 else 0.0
            win_pct = np.mean(np.array(dir_rets) > 0) * 100.0 if n_dedup > 0 else 0.0
            mean_mfe = np.mean(max_mfe) if n_dedup > 0 else 0.0
            mean_mae = np.mean(max_mae) if n_dedup > 0 else 0.0
            mfe_mae_ratio = (mean_mfe / mean_mae) if mean_mae > 0 else 0.0
            
            records.append({
                'Trigger Architecture': t_name,
                'Events': n_dedup,
                'Horizon': f"{k}h",
                'Mean Trade Return (%)': mean_ret,
                'Win Rate (%)': win_pct,
                'Mean MFE (%)': mean_mfe,
                'Mean MAE (%)': mean_mae,
                'MFE/MAE Ratio': mfe_mae_ratio
            })
            
    res_df = pd.DataFrame(records)
    
    print("\n--- 24-HOUR AND 48-HOUR DIRECTIONAL FORWARD PERFORMANCE ---")
    piv_24 = res_df[res_df['Horizon'] == '24h'][['Trigger Architecture', 'Events', 'Mean Trade Return (%)', 'Win Rate (%)', 'MFE/MAE Ratio']]
    print(piv_24.to_string(index=False))
    
    piv_48 = res_df[res_df['Horizon'] == '48h'][['Trigger Architecture', 'Events', 'Mean Trade Return (%)', 'Win Rate (%)', 'MFE/MAE Ratio']]
    print("\n--- 48-HOUR HORIZON ---")
    print(piv_48.to_string(index=False))
    
    # Save machine-readable output
    os.makedirs(os.path.join(os.path.dirname(__file__), '..', 'reports', 'v3'), exist_ok=True)
    res_df.to_csv(os.path.join(os.path.dirname(__file__), '..', 'reports', 'v3', 'h101_directionality_study.csv'), index=False)
    print("\nSaved H-101 results to AlphaLab_Antigravity/reports/v3/h101_directionality_study.csv")
    return res_df

if __name__ == '__main__':
    run_directionality_study()
