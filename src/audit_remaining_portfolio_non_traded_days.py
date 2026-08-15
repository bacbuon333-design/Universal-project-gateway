"""
AUDIT OF REMAINING NON-TRADED GAP DAYS ACROSS ENTIRE INDEPENDENT PORTFOLIO
===========================================================================
User Directive:
"tiêp tuc nghiên cứu cp tiêp theo . con bao nhiêu ngay đôc lâp nữa"

Calculates the exact number of non-traded gap days remaining across the 4-year dataset.
"""

import os, sys
import pandas as pd
import numpy as np

sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None

DATA_PATH = r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05\AlphaLab_Antigravity\data\GOLD_M15.csv"

def audit_remaining_non_traded_days():
    df_m15 = pd.read_csv(DATA_PATH)
    df_m15['datetime'] = pd.to_datetime(df_m15['datetime_str'])
    df_m15.set_index('datetime', inplace=True)
    
    o_m15 = df_m15['open'].values
    h_m15 = df_m15['high'].values
    l_m15 = df_m15['low'].values
    c_m15 = df_m15['close'].values
    v_m15 = df_m15['tick_volume'].values
    dates_m15 = df_m15.index.date
    all_market_dates = set(dates_m15)
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
    
    ema12_m15 = df_m15['close'].ewm(span=12, adjust=False).mean()
    ema26_m15 = df_m15['close'].ewm(span=26, adjust=False).mean()
    macd_line = (ema12_m15 - ema26_m15).values
    signal_line = (pd.Series(macd_line).ewm(span=9, adjust=False).mean()).values
    macd_hist = macd_line - signal_line
    
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
        {'code': 'CP-175', 'sig': 'cp175'},
        {'code': 'CP-182', 'sig': 'cp182'}
    ]
    
    portfolio_traded_dates = set()
    
    for cp in cps:
        trades_dates = set()
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
            elif cp['sig'] == 'cp182':
                b_sig = macro_bull and m15_bull and vol_exp and (macd_line[i] > 0.45) and (macd_hist[i] > 0.10) and (vol_zscore[i] > 1.0) and (rsi_m15[i] > 58.0) and (lwick >= 1.0 * body) and consec_bull
                
            if b_sig and (i - last_idx >= 4):
                last_idx = i
                trades_dates.add(dates_m15[i])
                
        portfolio_traded_dates.update(trades_dates)
        print(f"Engine {cp['code']:<7} | Unique Traded Dates: {len(trades_dates):>4} days")
        
    remaining_dates = all_market_dates.difference(portfolio_traded_dates)
    
    print("="*105)
    print("REMAINING NON-TRADED GAP DAYS AUDIT REPORT")
    print("="*105)
    print(f"Total Active Market Days in 4-Year Dataset   : {len(all_market_dates)} Days")
    print(f"Portfolio Traded Days (CP101+141+171+175+182): {len(portfolio_traded_dates)} Days ({len(portfolio_traded_dates)/len(all_market_dates)*100:.2f}% Market Coverage)")
    print(f"REMAINING NON-TRADED GAP DAYS TO DISCOVER   : {len(remaining_dates)} REMAINING DAYS ({len(remaining_dates)/len(all_market_dates)*100:.2f}% OF MARKET HISTORY!)")
    print("="*105)

if __name__ == '__main__':
    audit_remaining_non_traded_days()
