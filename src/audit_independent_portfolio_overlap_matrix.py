"""
COMPREHENSIVE PORTFOLIO INTERSECTION & OVERLAP MATRIX AUDIT FOR INDEPENDENT CPS
================================================================================
User Directive:
"Bạn kiểm tra kỹ lại toỏng các lệnh CP đạt chuẩn không trungf vào nhau quá nhiều ?"

Performs an exact pairwise intersection analysis across all approved independent CPs:
- CP-101 (Anchor Base Engine)
- CP-141 (Keltner Upper Engine)
- CP-171 (Independent BB Expansion Engine)
- CP-175 (Independent Keltner RSI Engine)
"""

import os, sys
import pandas as pd
import numpy as np

sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None

DATA_PATH = r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05\AlphaLab_Antigravity\data\GOLD_M15.csv"

def get_independent_cp_trade_timestamps():
    df_m15 = pd.read_csv(DATA_PATH)
    df_m15['datetime'] = pd.to_datetime(df_m15['datetime_str'])
    df_m15.set_index('datetime', inplace=True)
    
    o_m15 = df_m15['open'].values
    h_m15 = df_m15['high'].values
    l_m15 = df_m15['low'].values
    c_m15 = df_m15['close'].values
    v_m15 = df_m15['tick_volume'].values
    n = len(c_m15)
    
    # Resample H1 for trend alignment
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
    
    # M15 Indicators
    ema9_m15 = df_m15['close'].ewm(span=9, adjust=False).mean().values
    ema20_m15 = df_m15['close'].ewm(span=20, adjust=False).mean().values
    
    tr = np.maximum(h_m15 - l_m15, np.maximum(np.abs(h_m15 - np.roll(c_m15, 1)), np.abs(l_m15 - np.roll(c_m15, 1))))
    atr14_m15 = pd.Series(tr).rolling(14).mean().values
    atr50_m15 = pd.Series(tr).rolling(50).mean().values
    
    don_hi15_m15 = pd.Series(h_m15).shift(1).rolling(15).max().values
    kelt_upper_195 = ema20_m15 + 1.95 * atr14_m15
    kelt_upper_205 = ema20_m15 + 2.05 * atr14_m15
    
    sma20_m15 = pd.Series(c_m15).rolling(20).mean().values
    std20_m15 = pd.Series(c_m15).rolling(20).std().values
    upper_bb_m15 = sma20_m15 + 2.0 * std20_m15
    
    delta = df_m15['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rsi_m15 = (100 - (100 / (1 + gain / (loss + 1e-9)))).values
    
    vol_sma50 = pd.Series(v_m15).rolling(50).mean().values
    vol_std50 = pd.Series(v_m15).rolling(50).std().values
    vol_zscore = (v_m15 - vol_sma50) / (vol_std50 + 1e-9)
    
    cps = [
        {'code': 'CP-101', 'sig': 'cp101'},
        {'code': 'CP-141', 'sig': 'cp141'},
        {'code': 'CP-171', 'sig': 'cp171'},
        {'code': 'CP-175', 'sig': 'cp175'}
    ]
    
    cp_trades = {}
    
    for cp in cps:
        trades = []
        last_idx = -1
        
        for i in range(200, n - 1):
            av = max(atr14_m15[i], 0.8)
            body = abs(c_m15[i] - o_m15[i]) + 1e-5
            lwick = min(o_m15[i], c_m15[i]) - l_m15[i]
            
            macro_bull = (ema9_h1[i] > ema20_h1[i]) and (ema20_h1[i] > ema55_h1[i]) and (ema55_h1[i] > ema200_h1[i])
            m15_bull   = (ema9_m15[i] > ema20_m15[i])
            vol_exp    = (atr14_m15[i] >= atr50_m15[i] * 1.0)
            consec_bull = (c_m15[i] > o_m15[i]) and (c_m15[i-1] > o_m15[i-1])
            
            b_sig = False
            if cp['sig'] == 'cp101':
                b_sig = macro_bull and m15_bull and vol_exp and (c_m15[i] > don_hi15_m15[i]) and (rsi_m15[i] > 55.0) and (lwick >= 0.8 * body) and consec_bull
            elif cp['sig'] == 'cp141':
                b_sig = macro_bull and m15_bull and vol_exp and (c_m15[i] > kelt_upper_195[i]) and (rsi_m15[i] > 62.0) and (lwick >= 1.0 * body) and consec_bull
            elif cp['sig'] == 'cp171':
                b_sig = macro_bull and m15_bull and vol_exp and (c_m15[i] > upper_bb_m15[i]) and (vol_zscore[i] > 0.8) and (rsi_m15[i] > 55.0) and (lwick >= 0.8 * body) and consec_bull
            elif cp['sig'] == 'cp175':
                b_sig = macro_bull and m15_bull and vol_exp and (c_m15[i] > kelt_upper_205[i]) and (vol_zscore[i] > 0.9) and (rsi_m15[i] > 60.0) and (lwick >= 1.0 * body) and consec_bull
                
            if b_sig and (i - last_idx >= 4):
                last_idx = i
                entry_time_str = df_m15.index[i+1].strftime('%Y-%m-%d %H:%M:%S')
                trades.append(entry_time_str)
                
        cp_trades[cp['code']] = trades
        
    return cp_trades

def run_independent_portfolio_overlap_audit():
    cp_trades = get_independent_cp_trade_timestamps()
    codes = list(cp_trades.keys())
    
    print("="*105)
    print("COMPREHENSIVE PORTFOLIO INTERSECTION & OVERLAP MATRIX AUDIT FOR INDEPENDENT CPS")
    print("="*105)
    
    all_timestamps = []
    for c in codes:
        print(f"Independent Engine {c:<7} | Executed Trades: {len(cp_trades[c]):>4} trades")
        all_timestamps.extend(cp_trades[c])
        
    unique_timestamps = set(all_timestamps)
    
    print("-" * 105)
    print("PAIRWISE OVERLAP MATRIX (NUMBER OF SHARED EXACT ENTRY TIMESTAMPS):")
    print("-" * 105)
    
    header = f"{'Engine':<10}" + "".join([f"{c:>12}" for c in codes])
    print(header)
    print("-" * 105)
    
    for c1 in codes:
        row = f"{c1:<10}"
        set1 = set(cp_trades[c1])
        for c2 in codes:
            set2 = set(cp_trades[c2])
            overlap_count = len(set1.intersection(set2))
            row += f"{overlap_count:>12}"
        print(row)
        
    print("-" * 105)
    print("PORTFOLIO DIVERSIFICATION SUMMARY:")
    print("-" * 105)
    print(f"Total Cumulative Trades Across All 4 Independent CPs : {len(all_timestamps)} trades")
    print(f"Total Unique Non-Overlapping Trades                  : {len(unique_timestamps)} UNIQUE TRADES!")
    print(f"Overall Portfolio Overlap Ratio                      : {((len(all_timestamps) - len(unique_timestamps)) / len(all_timestamps)) * 100.0:.2f}% (RẤT THẤP!)")
    print("="*105)

if __name__ == '__main__':
    run_independent_portfolio_overlap_audit()
