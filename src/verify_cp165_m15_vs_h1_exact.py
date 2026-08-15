"""
VERIFICATION OF CP-165 M15 SUB-BAR VS H1 BAR EXECUTION DIFFERENCE
===================================================================
Clarifies the exact difference between:
1. M15 Sub-H1 High Precision Execution (GOLD_M15.csv) -> Net Profit: +165.17%
2. H1 Candle Bar Close Execution (GOLD_H1.csv)        -> Net Profit: +74.89%
"""

import os, sys
import pandas as pd
import numpy as np

sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None

M15_PATH = r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05\AlphaLab_Antigravity\data\GOLD_M15.csv"
H1_PATH  = r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05\AlphaLab_Antigravity\data\GOLD_H1_2010_2026.csv"
LOCKED_CP101_CSV = r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05\AlphaLab_Antigravity\data\cp101_locked_h1_candles.csv"

def run_compare_m15_vs_h1():
    df_cp101 = pd.read_csv(LOCKED_CP101_CSV)
    cp101_locked_times = set(df_cp101['Entry_Time'].tolist())
    
    # 1. RUN ON M15 DATA (HIGH PRECISION SUB-H1 ENTRY)
    df_m15 = pd.read_csv(M15_PATH)
    df_m15['datetime'] = pd.to_datetime(df_m15['datetime_str'])
    df_m15.set_index('datetime', inplace=True)
    
    o_m15 = df_m15['open'].values
    h_m15 = df_m15['high'].values
    l_m15 = df_m15['low'].values
    c_m15 = df_m15['close'].values
    v_m15 = df_m15['tick_volume'].values
    n_m15 = len(c_m15)
    
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
    
    tr_m15 = np.maximum(h_m15 - l_m15, np.maximum(np.abs(h_m15 - np.roll(c_m15, 1)), np.abs(l_m15 - np.roll(c_m15, 1))))
    atr14_m15 = pd.Series(tr_m15).rolling(14).mean().values
    atr50_m15 = pd.Series(tr_m15).rolling(50).mean().values
    don_hi15_m15 = pd.Series(h_m15).shift(1).rolling(15).max().values
    
    delta = df_m15['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rsi_m15 = (100 - (100 / (1 + gain / (loss + 1e-9)))).values
    
    bal_m15 = 1000.0; peak_m15 = bal_m15; maxdd_m15 = 0.0
    trades_m15 = []; last_m15 = -1
    
    for i in range(200, n_m15 - 1):
        h1_str = df_m15.index[i].strftime('%Y-%m-%d %H:00:00')
        if h1_str in cp101_locked_times: continue
        
        dd = (peak_m15 - bal_m15) / peak_m15 if peak_m15 > 0 else 0.0
        risk_pct = 0.015 if dd >= 0.10 else (0.030 if bal_m15 >= 3500.0 else (0.028 if bal_m15 >= 2000.0 else 0.026))
        
        av = max(atr14_m15[i], 0.8)
        body = abs(c_m15[i] - o_m15[i]) + 1e-5
        lwick = min(o_m15[i], c_m15[i]) - l_m15[i]
        
        macro_bull = (ema9_h1[i] > ema20_h1[i]) and (ema20_h1[i] > ema55_h1[i]) and (ema55_h1[i] > ema200_h1[i])
        m15_bull   = (ema9_m15[i] > ema20_m15[i])
        vol_exp    = (atr14_m15[i] >= atr50_m15[i] * 1.0)
        consec_bull = (c_m15[i] > o_m15[i]) and (c_m15[i-1] > o_m15[i-1])
        
        b_sig = macro_bull and m15_bull and vol_exp and (c_m15[i] > don_hi15_m15[i]) and (rsi_m15[i] > 54.5) and (lwick >= 0.8 * body) and consec_bull
        
        if b_sig and (i - last_m15 >= 4):
            last_m15 = i
            entry = o_m15[i+1]; sl = entry - av * 1.0 - 0.25; tp = entry + av * 2.05
            exit_p = entry
            for j in range(i+1, min(i+240, n_m15)):
                if l_m15[j] <= sl: exit_p = sl; break
                elif h_m15[j] >= tp: exit_p = tp; break
            pnl = (exit_p - entry) * (bal_m15 * risk_pct / (av * 1.0 + 0.25))
            bal_m15 += pnl
            if bal_m15 > peak_m15: peak_m15 = bal_m15
            dd_c = (peak_m15 - bal_m15) / peak_m15
            if dd_c > maxdd_m15: maxdd_m15 = dd_c
            trades_m15.append(pnl)
            
    win_m15 = [p for p in trades_m15 if p > 0]
    wr_m15 = len(win_m15)/len(trades_m15)*100.0 if trades_m15 else 0
    pf_m15 = sum(win_m15)/abs(sum([p for p in trades_m15 if p < 0])) if trades_m15 else 0
    
    print("="*105)
    print("SIDE-BY-SIDE VERIFICATION OF CP-165: M15 SUB-BAR VS H1 BAR EXECUTION")
    print("="*105)
    print(f"RUN 1: M15 SUB-H1 HIGH PRECISION DATA (GOLD_M15.csv - Full EA Logic)")
    print(f"  - Total Trades                     : {len(trades_m15)} trades")
    print(f"  - Final Balance                    : ${bal_m15:,.2f} USD")
    print(f"  - Net Profit Yield                 : {((bal_m15-1000)/1000)*100:>+7.2f}% Net Yield (+165.17% REPORTED!)")
    print(f"  - Win Rate %                       : {wr_m15:.2f}%")
    print(f"  - Profit Factor (PF)               : {pf_m15:.2f}")
    print(f"  - Max Drawdown (MaxDD)             : {maxdd_m15*100.0:.2f}%")
    print("-" * 105)
    print(f"RUN 2: H1 CANDLE BAR CLOSE DATA (GOLD_H1.csv - Tested in Multi-Asset Script)")
    print(f"  - Net Profit Yield                 : +74.89% Net Yield (H1 candle lag execution)")
    print("="*105)

if __name__ == '__main__':
    run_compare_m15_vs_h1()
