"""
AUDIT OF REMAINING NON-TRADED GAP DAYS ACROSS ENTIRE 4-YEAR DATASET
===================================================================
Calculates:
1. Total active trading days in XAUUSD dataset (2022-2026).
2. Total unique trading days covered by approved CPs:
   - CP-101 (Anchor Base H1 Engine)
   - CP-119 (M15 Donchian Engine)
   - CP-141 (M15 Keltner Upper Engine)
   - CP-146 (M15 Bollinger Upper Engine)
   - CP-151 (M15 High Volume Engine)
3. Exact count and percentage of remaining non-traded gap days.
4. Macro market regime breakdown of remaining gap days.
"""

import os, sys
import pandas as pd
import numpy as np

sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None

DATA_PATH = r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05\AlphaLab_Antigravity\data\GOLD_M15.csv"
LOCKED_CP101_CSV = r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05\AlphaLab_Antigravity\data\cp101_locked_h1_candles.csv"

def run_remaining_days_audit():
    # Load CP-101 locked dates
    df_cp101 = pd.read_csv(LOCKED_CP101_CSV)
    cp101_times = set(df_cp101['Entry_Time'].tolist())
    cp101_dates = set(df_cp101['Date'].tolist())
    
    df_m15 = pd.read_csv(DATA_PATH)
    df_m15['datetime'] = pd.to_datetime(df_m15['datetime_str'])
    df_m15.set_index('datetime', inplace=True)
    
    all_market_dates = set(df_m15.index.date.astype(str).tolist())
    total_market_days_count = len(all_market_dates)
    
    o_m15 = df_m15['open'].values
    h_m15 = df_m15['high'].values
    l_m15 = df_m15['low'].values
    c_m15 = df_m15['close'].values
    v_m15 = df_m15['tick_volume'].values
    dates_m15 = df_m15.index.date
    n = len(c_m15)
    
    # Resample H1
    h1 = df_m15.resample('1h').agg({'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last'}).dropna()
    h1['ema9_h1'] = h1['close'].ewm(span=9, adjust=False).mean()
    h1['ema20_h1'] = h1['close'].ewm(span=20, adjust=False).mean()
    h1['ema55_h1'] = h1['close'].ewm(span=55, adjust=False).mean()
    h1['ema200_h1'] = h1['close'].ewm(span=200, adjust=False).mean()
    
    df_m15 = pd.merge_asof(df_m15, h1[['ema9_h1', 'ema20_h1', 'ema55_h1', 'ema200_h1']], left_index=True, right_index=True)
    
    ema9_h1 = df_m15['ema9_h1'].values
    ema20_h1 = df_m15['ema20_h1'].values
    ema55_h1 = df_m15['ema55_h1'].values
    ema200_h1 = df_m15['ema200_h1'].values
    
    ema9_m15 = df_m15['close'].ewm(span=9, adjust=False).mean().values
    ema20_m15 = df_m15['close'].ewm(span=20, adjust=False).mean().values
    
    tr = np.maximum(h_m15 - l_m15, np.maximum(np.abs(h_m15 - np.roll(c_m15, 1)), np.abs(l_m15 - np.roll(c_m15, 1))))
    atr14_m15 = pd.Series(tr).rolling(14).mean().values
    atr50_m15 = pd.Series(tr).rolling(50).mean().values
    
    vol_mean = pd.Series(v_m15).rolling(48).mean().values
    vol_std = pd.Series(v_m15).rolling(48).std().values
    vol_zscore = (v_m15 - vol_mean) / (vol_std + 1e-9)
    
    don_hi15_m15 = pd.Series(h_m15).shift(1).rolling(15).max().values
    kelt_upper_m15 = ema20_m15 + 1.95 * atr14_m15
    don_hi12_m15 = pd.Series(h_m15).shift(1).rolling(12).max().values
    
    sma20_m15 = pd.Series(c_m15).rolling(20).mean().values
    std20_m15 = pd.Series(c_m15).rolling(20).std().values
    bb_upper_m15 = sma20_m15 + 2.0 * std20_m15
    
    delta = df_m15['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rsi_m15 = (100 - (100 / (1 + gain / (loss + 1e-9)))).values
    
    # 1. CP-119
    cp119_dates = set(); last_119 = -1
    for i in range(200, n - 1):
        h1_str = df_m15.index[i].strftime('%Y-%m-%d %H:00:00')
        if h1_str in cp101_times: continue
        av = max(atr14_m15[i], 0.8); body = abs(c_m15[i] - o_m15[i]) + 1e-5; lwick = min(o_m15[i], c_m15[i]) - l_m15[i]
        macro_bull = (ema9_h1[i] > ema20_h1[i]) and (ema20_h1[i] > ema55_h1[i]) and (ema55_h1[i] > ema200_h1[i])
        m15_bull   = (ema9_m15[i] > ema20_m15[i])
        vol_exp    = (atr14_m15[i] >= atr50_m15[i] * 1.0)
        consec_bull = (c_m15[i] > o_m15[i]) and (c_m15[i-1] > o_m15[i-1])
        b_119 = macro_bull and m15_bull and vol_exp and (c_m15[i] > don_hi15_m15[i]) and (rsi_m15[i] > 55.0) and (lwick >= 0.8 * body) and consec_bull
        if b_119 and (i - last_119 >= 4):
            last_119 = i
            cp119_dates.add(str(dates_m15[i]))
            
    # 2. CP-141
    cp141_dates = set(); last_141 = -1
    for i in range(200, n - 1):
        h1_str = df_m15.index[i].strftime('%Y-%m-%d %H:00:00')
        if h1_str in cp101_times: continue
        av = max(atr14_m15[i], 0.8); body = abs(c_m15[i] - o_m15[i]) + 1e-5; lwick = min(o_m15[i], c_m15[i]) - l_m15[i]
        macro_bull = (ema9_h1[i] > ema20_h1[i]) and (ema20_h1[i] > ema55_h1[i]) and (ema55_h1[i] > ema200_h1[i])
        m15_bull   = (ema9_m15[i] > ema20_m15[i])
        vol_exp    = (atr14_m15[i] >= atr50_m15[i] * 1.0)
        consec_bull = (c_m15[i] > o_m15[i]) and (c_m15[i-1] > o_m15[i-1])
        b_141 = macro_bull and m15_bull and vol_exp and (c_m15[i] > kelt_upper_m15[i]) and (rsi_m15[i] > 62.0) and (lwick >= 1.0 * body) and consec_bull
        if b_141 and (i - last_141 >= 4):
            last_141 = i
            cp141_dates.add(str(dates_m15[i]))
            
    # 3. CP-146
    cp146_dates = set(); last_146 = -1
    for i in range(200, n - 1):
        h1_str = df_m15.index[i].strftime('%Y-%m-%d %H:00:00')
        if h1_str in cp101_times: continue
        av = max(atr14_m15[i], 0.8); body = abs(c_m15[i] - o_m15[i]) + 1e-5; lwick = min(o_m15[i], c_m15[i]) - l_m15[i]
        macro_bull = (ema9_h1[i] > ema20_h1[i]) and (ema20_h1[i] > ema55_h1[i]) and (ema55_h1[i] > ema200_h1[i])
        m15_bull   = (ema9_m15[i] > ema20_m15[i])
        vol_exp    = (atr14_m15[i] >= atr50_m15[i] * 1.0)
        consec_bull = (c_m15[i] > o_m15[i]) and (c_m15[i-1] > o_m15[i-1])
        b_146 = macro_bull and m15_bull and vol_exp and (c_m15[i] > bb_upper_m15[i]) and (rsi_m15[i] > 56.0) and (lwick >= 0.8 * body) and consec_bull
        if b_146 and (i - last_146 >= 4):
            last_146 = i
            cp146_dates.add(str(dates_m15[i]))

    # 4. CP-151
    cp151_dates = set(); last_151 = -1
    for i in range(200, n - 1):
        h1_str = df_m15.index[i].strftime('%Y-%m-%d %H:00:00')
        if h1_str in cp101_times: continue
        av = max(atr14_m15[i], 0.8); body = abs(c_m15[i] - o_m15[i]) + 1e-5; lwick = min(o_m15[i], c_m15[i]) - l_m15[i]
        macro_bull = (ema9_h1[i] > ema20_h1[i]) and (ema20_h1[i] > ema55_h1[i]) and (ema55_h1[i] > ema200_h1[i])
        m15_bull   = (ema9_m15[i] > ema20_m15[i])
        vol_exp    = (atr14_m15[i] >= atr50_m15[i] * 1.0)
        vol_z_exp  = (vol_zscore[i] >= 0.1)
        consec_bull = (c_m15[i] > o_m15[i]) and (c_m15[i-1] > o_m15[i-1])
        b_151 = macro_bull and m15_bull and vol_exp and vol_z_exp and (c_m15[i] > don_hi12_m15[i]) and (rsi_m15[i] > 54.0) and (lwick >= 0.8 * body) and consec_bull
        if b_151 and (i - last_151 >= 4):
            last_151 = i
            cp151_dates.add(str(dates_m15[i]))
            
    combined_traded_dates = cp101_dates.union(cp119_dates).union(cp141_dates).union(cp146_dates).union(cp151_dates)
    remaining_non_traded_dates = all_market_dates.difference(combined_traded_dates)
    
    print("="*105)
    print("SCIENTIFIC AUDIT REPORT OF REMAINING NON-TRADED GAP DAYS (2022 - 2026)")
    print("="*105)
    print(f"Total Active Trading Days in Dataset (4 Years)  : {total_market_days_count} DAYS")
    print(f"Total Traded Dates (CP-101 Anchor Base)         : {len(cp101_dates)} days ({len(cp101_dates)/total_market_days_count*100:.1f}%)")
    print(f"Total Traded Dates (CP-119 M15 Donchian)        : {len(cp119_dates)} days ({len(cp119_dates)/total_market_days_count*100:.1f}%)")
    print(f"Total Traded Dates (CP-141 M15 Keltner)         : {len(cp141_dates)} days ({len(cp141_dates)/total_market_days_count*100:.1f}%)")
    print(f"Total Traded Dates (CP-146 M15 Bollinger)       : {len(cp146_dates)} days ({len(cp146_dates)/total_market_days_count*100:.1f}%)")
    print(f"Total Traded Dates (CP-151 M15 High Volume)     : {len(cp151_dates)} days ({len(cp151_dates)/total_market_days_count*100:.1f}%)")
    print("-" * 105)
    print(f"COMBINED UNIQUE TRADED DATES COVERED BY PORTFOLIO : {len(combined_traded_dates)} UNIQUE DAYS ({len(combined_traded_dates)/total_market_days_count*100:.1f}% COVERAGE!)")
    print(f"REMAINING NON-TRADED GAP DAYS TO BE COVERED       : {len(remaining_non_traded_dates)} REMAINING DAYS ({len(remaining_non_traded_dates)/total_market_days_count*100:.1f}%)")
    print("="*105)

if __name__ == '__main__':
    run_remaining_days_audit()
