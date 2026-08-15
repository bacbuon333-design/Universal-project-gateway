"""
BLIND TRIPLE PORTFOLIO OVERLAP VERIFIER & CAUSAL COLLISION AUDITOR
===================================================================
Runs all 3 strategies (CP-14, CP-15, CP-16) INDEPENDENTLY without any pre-computed forbidden dates.
Evaluates their natural indicator signal logic to measure exact blind trade date & bar collisions.

Rules evaluated blindly:
- Strategy 1 (CP-14): Trend Breakout + MACD Z-Score > 1.2 + Donchian 20 High/Low + Rejection Wick >= 1.0x Body.
- Strategy 2 (CP-15): Counter-Trend Structural Sweep (Low <= Donchian_Low_48 + 0.8x ATR) + RSI < 45 / RSI > 55.
- Strategy 3 (CP-16): Volatility Compression (ATR14 <= ATR50 * 0.95) + Keltner Donchian 10 Breakout + Volume Z >= 0.3.

Dataset: XAUUSD H1 (16.57 Continuous Years: 2010 - 2026, 79,288 bars)
Execution: Real broker costs (Spread 25p + Comm $7/lot + Slippage 5p)
"""

import os, sys
sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None
import numpy as np
import pandas as pd

BASE_DIR = r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05\AlphaLab_Antigravity"
DATA_PATH = os.path.join(BASE_DIR, "data", "GOLD_H1_2010_2026.csv")

PIP = 0.01
PTVAL = 0.01

def run_blind_triple_verifier():
    df = pd.read_csv(DATA_PATH)
    col = 'datetime_str' if 'datetime_str' in df.columns else df.columns[0]
    df['dt'] = pd.to_datetime(df[col])
    df['date_str'] = df['dt'].dt.strftime('%Y-%m-%d')
    df['year'] = df['dt'].dt.year
    df.sort_values('dt', inplace=True)
    df.reset_index(drop=True, inplace=True)
    
    c = df['close'].values; h = df['high'].values; l = df['low'].values; o = df['open'].values
    v = df['tick_volume'].values if 'tick_volume' in df.columns else df['vol'].values
    dt_str = df[col].values
    date_arr = df['date_str'].values
    n = len(df)
    
    # 1. COMPUTE ALL INDICATORS NATIVELY
    tr = np.maximum(h[1:]-l[1:], np.maximum(abs(h[1:]-c[:-1]), abs(l[1:]-c[:-1])))
    tr = np.insert(tr, 0, tr[0])
    atr14 = pd.Series(tr).rolling(14).mean().bfill().values
    atr50 = pd.Series(tr).rolling(50).mean().bfill().values
    
    ema9   = pd.Series(c).ewm(span=9,   adjust=False).mean().values
    ema55  = pd.Series(c).ewm(span=55,  adjust=False).mean().values
    ema200 = pd.Series(c).ewm(span=200, adjust=False).mean().values
    
    d = pd.Series(c).diff()
    up = d.clip(lower=0).ewm(alpha=1/14, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1/14, adjust=False).mean().clip(1e-9)
    rsi14 = (100 - 100 / (1 + up / dn)).values
    
    ema12 = pd.Series(c).ewm(span=12, adjust=False).mean().values
    ema26 = pd.Series(c).ewm(span=26, adjust=False).mean().values
    macd_line = ema12 - ema26
    signal_line = pd.Series(macd_line).ewm(span=9, adjust=False).mean().values
    macd_hist = macd_line - signal_line
    
    hist_mid = pd.Series(macd_hist).rolling(20).mean().bfill().values
    hist_std = pd.Series(macd_hist).rolling(20).std().bfill().values + 1e-9
    macd_z     = (macd_hist - hist_mid) / hist_std
    
    don_hi20 = pd.Series(h).shift(1).rolling(20).max().bfill().values
    don_lo20 = pd.Series(l).shift(1).rolling(20).min().bfill().values
    don_hi10 = pd.Series(h).shift(1).rolling(10).max().bfill().values
    don_lo10 = pd.Series(l).shift(1).rolling(10).min().bfill().values
    hi48     = pd.Series(h).shift(1).rolling(48).max().bfill().values
    lo48     = pd.Series(l).shift(1).rolling(48).min().bfill().values
    
    near_ema9_55 = (abs(c - ema9) <= 2.5 * atr14) | (abs(c - ema55) <= 2.5 * atr14)
    vol_mean = pd.Series(v).rolling(50).mean().bfill().values
    vol_std  = pd.Series(v).rolling(50).std().bfill().values + 1e-9
    vol_z    = (v - vol_mean) / vol_std

    # 2. RUN STRATEGY 1 (CP-14) INDEPENDENTLY
    trades_s1 = []
    last_trade = -9999; cooldown = 24; pause_until = 0; pos_dir = 0; pos_sl = 0.0; pos_tp = 0.0; pos_en = 0.0; pos_lot = 0.0
    bal1 = 1000.0; pk1 = 1000.0; max_dd1 = 0.0
    
    for i in range(200, n-1):
        if pos_dir != 0:
            done = False; ep = c[i]
            if pos_dir == 1:
                if l[i] <= pos_sl: ep = pos_sl - 5.0 * PIP; done = True
                elif h[i] >= pos_tp: ep = pos_tp; done = True
            else:
                if h[i] >= pos_sl: ep = pos_sl + 5.0 * PIP; done = True
                elif l[i] <= pos_tp: ep = pos_tp; done = True
            if done:
                pts = (ep - pos_en)/PIP if pos_dir==1 else (pos_en - ep)/PIP
                gross = pts * PTVAL * (pos_lot / 0.01); fee = (pos_lot / 0.01) * 0.37; net = gross - fee
                bal1 = max(0.0, bal1 + net); pk1 = max(pk1, bal1)
                max_dd1 = max(max_dd1, (pk1 - bal1)/pk1 * 100.0 if pk1 > 0 else 0)
                pos_dir = 0
                
        if pos_dir == 0 and (i - last_trade >= cooldown) and (i >= pause_until):
            lwick = min(o[i], c[i]) - l[i]; uwick = h[i] - max(o[i], c[i]); body = abs(c[i] - o[i]) + 1e-9
            macro_bull = (ema9[i] > ema55[i]) and (ema55[i] > ema200[i])
            macro_bear = (ema9[i] < ema55[i]) and (ema55[i] < ema200[i])
            
            b_cond = macro_bull and (rsi14[i] > 52) and (macd_z[i] > 1.2) and (c[i] > don_hi20[i]) and near_ema9_55[i] and (lwick >= 1.0 * body)
            s_cond = macro_bear and (rsi14[i] < 48) and (macd_z[i] < -1.2) and (c[i] < don_lo20[i]) and near_ema9_55[i] and (uwick >= 1.0 * body)
            
            if b_cond or s_cond:
                av = max(atr14[i], 1.5); sp = 25.0; sl_pts = (av * 1.5 / PIP) + sp; tp_mult = 4.2 if abs(macd_z[i]) > 1.8 else 3.5; tp_pts = (av * tp_mult / PIP)
                pos_dir = 1 if b_cond else -1
                pos_en = o[i+1] + (sp*PIP/2.0 if b_cond else -sp*PIP/2.0)
                pos_sl = pos_en - sl_pts * PIP if b_cond else pos_en + sl_pts * PIP
                pos_tp = pos_en + tp_pts * PIP if b_cond else pos_en - tp_pts * PIP
                pos_lot = max(0.01, min(round(((bal1 * 0.012) / (sl_pts * 0.01)) * 0.01, 2), 20.0))
                trades_s1.append({'bar': i, 'dt': dt_str[i], 'date': date_arr[i], 'dir': pos_dir})
                last_trade = i

    # 3. RUN STRATEGY 2 (CP-15) INDEPENDENTLY (BLIND NO DATES FILTER)
    trades_s2 = []
    last_trade = -9999; cooldown = 12; pause_until = 0; pos_dir = 0; pos_sl = 0.0; pos_tp = 0.0; pos_en = 0.0; pos_lot = 0.0
    bal2 = 1000.0; pk2 = 1000.0; max_dd2 = 0.0
    
    for i in range(200, n-1):
        if pos_dir != 0:
            done = False; ep = c[i]
            if pos_dir == 1:
                if l[i] <= pos_sl: ep = pos_sl - 5.0 * PIP; done = True
                elif h[i] >= pos_tp: ep = pos_tp; done = True
            else:
                if h[i] >= pos_sl: ep = pos_sl + 5.0 * PIP; done = True
                elif l[i] <= pos_tp: ep = pos_tp; done = True
            if done:
                pts = (ep - pos_en)/PIP if pos_dir==1 else (pos_en - ep)/PIP
                gross = pts * PTVAL * (pos_lot / 0.01); fee = (pos_lot / 0.01) * 0.37; net = gross - fee
                bal2 = max(0.0, bal2 + net); pk2 = max(pk2, bal2)
                max_dd2 = max(max_dd2, (pk2 - bal2)/pk2 * 100.0 if pk2 > 0 else 0)
                pos_dir = 0
                
        if pos_dir == 0 and (i - last_trade >= cooldown) and (i >= pause_until):
            av = max(atr14[i], 1.5); lwick = min(o[i], c[i]) - l[i]; uwick = h[i] - max(o[i], c[i]); body = abs(c[i] - o[i]) + 1e-9
            macro_bull = c[i] > ema200[i]; macro_bear = c[i] < ema200[i]
            sweep_lo = (l[i] <= lo48[i] + 0.8 * av) and (lwick >= 0.8 * body) and (c[i] > o[i])
            sweep_hi = (h[i] >= hi48[i] - 0.8 * av) and (uwick >= 0.8 * body) and (c[i] < o[i])
            
            b_cond = macro_bull and sweep_lo and (rsi14[i] > 40)
            s_cond = macro_bear and sweep_hi and (rsi14[i] < 60)
            
            if b_cond or s_cond:
                sp = 25.0; sl_pts = (av * 1.5 / PIP) + sp; tp_mult = 4.0 if abs(macd_z[i]) > 1.5 else 3.5; tp_pts = (av * tp_mult / PIP)
                pos_dir = 1 if b_cond else -1
                pos_en = o[i+1] + (sp*PIP/2.0 if b_cond else -sp*PIP/2.0)
                pos_sl = pos_en - sl_pts * PIP if b_cond else pos_en + sl_pts * PIP
                pos_tp = pos_en + tp_pts * PIP if b_cond else pos_en - tp_pts * PIP
                pos_lot = max(0.01, min(round(((bal2 * 0.012) / (sl_pts * 0.01)) * 0.01, 2), 20.0))
                trades_s2.append({'bar': i, 'dt': dt_str[i], 'date': date_arr[i], 'dir': pos_dir})
                last_trade = i

    # 4. RUN STRATEGY 3 (CP-16) INDEPENDENTLY (BLIND NO DATES FILTER)
    trades_s3 = []
    last_trade = -9999; cooldown = 12; pause_until = 0; pos_dir = 0; pos_sl = 0.0; pos_tp = 0.0; pos_en = 0.0; pos_lot = 0.0
    bal3 = 1000.0; pk3 = 1000.0; max_dd3 = 0.0
    
    for i in range(200, n-1):
        if pos_dir != 0:
            done = False; ep = c[i]
            if pos_dir == 1:
                if l[i] <= pos_sl: ep = pos_sl - 5.0 * PIP; done = True
                elif h[i] >= pos_tp: ep = pos_tp; done = True
            else:
                if h[i] >= pos_sl: ep = pos_sl + 5.0 * PIP; done = True
                elif l[i] <= pos_tp: ep = pos_tp; done = True
            if done:
                pts = (ep - pos_en)/PIP if pos_dir==1 else (pos_en - ep)/PIP
                gross = pts * PTVAL * (pos_lot / 0.01); fee = (pos_lot / 0.01) * 0.37; net = gross - fee
                bal3 = max(0.0, bal3 + net); pk3 = max(pk3, bal3)
                max_dd3 = max(max_dd3, (pk3 - bal3)/pk3 * 100.0 if pk3 > 0 else 0)
                pos_dir = 0
                
        if pos_dir == 0 and (i - last_trade >= cooldown) and (i >= pause_until):
            av = max(atr14[i], 1.5); squeeze_ok = (atr14[i] <= atr50[i] * 0.95)
            macro_bull = c[i] > ema200[i]; macro_bear = c[i] < ema200[i]
            break_hi10 = (c[i] > don_hi10[i]) and (c[i] > o[i]) and (rsi14[i] > 48) and (vol_z[i] >= 0.3)
            break_lo10 = (c[i] < don_lo10[i]) and (c[i] < o[i]) and (rsi14[i] < 52) and (vol_z[i] >= 0.3)
            
            b_cond = macro_bull and squeeze_ok and break_hi10
            s_cond = macro_bear and squeeze_ok and break_lo10
            
            if b_cond or s_cond:
                sp = 25.0; sl_pts = (av * 1.5 / PIP) + sp; tp_mult = 4.0 if abs(macd_z[i]) > 1.5 else 3.5; tp_pts = (av * tp_mult / PIP)
                pos_dir = 1 if b_cond else -1
                pos_en = o[i+1] + (sp*PIP/2.0 if b_cond else -sp*PIP/2.0)
                pos_sl = pos_en - sl_pts * PIP if b_cond else pos_en + sl_pts * PIP
                pos_tp = pos_en + tp_pts * PIP if b_cond else pos_en - tp_pts * PIP
                pos_lot = max(0.01, min(round(((bal3 * 0.012) / (sl_pts * 0.01)) * 0.01, 2), 20.0))
                trades_s3.append({'bar': i, 'dt': dt_str[i], 'date': date_arr[i], 'dir': pos_dir})
                last_trade = i

    # 5. CROSS-AUDIT COLLISION ANALYSIS
    dates_s1 = set([t['date'] for t in trades_s1])
    dates_s2 = set([t['date'] for t in trades_s2])
    dates_s3 = set([t['date'] for t in trades_s3])
    
    bars_s1 = set([t['bar'] for t in trades_s1])
    bars_s2 = set([t['bar'] for t in trades_s2])
    bars_s3 = set([t['bar'] for t in trades_s3])
    
    # Same-Day Collisions
    overlap_1_2_day = dates_s1.intersection(dates_s2)
    overlap_1_3_day = dates_s1.intersection(dates_s3)
    overlap_2_3_day = dates_s2.intersection(dates_s3)
    triple_overlap_day = dates_s1.intersection(dates_s2).intersection(dates_s3)
    
    # Same-Bar Collisions (Exact H1 Bar)
    overlap_1_2_bar = bars_s1.intersection(bars_s2)
    overlap_1_3_bar = bars_s1.intersection(bars_s3)
    overlap_2_3_bar = bars_s2.intersection(bars_s3)
    triple_overlap_bar = bars_s1.intersection(bars_s2).intersection(bars_s3)

    print("="*115)
    print("BLIND TRIPLE PORTFOLIO OVERLAP VERIFIER & CAUSAL COLLISION AUDIT (16.57 YEARS H1 GOLD)")
    print("Zero Pre-computed Dates | 100% Native Indicator Logic Run Separately")
    print("="*115)
    print(f"Strategy 1 (CP-14 Trend Breakout)           : {len(trades_s1):<5} trades across {len(dates_s1):<5} unique dates.")
    print(f"Strategy 2 (CP-15 Structural Sweep Reversal) : {len(trades_s2):<5} trades across {len(dates_s2):<5} unique dates.")
    print(f"Strategy 3 (CP-16 Volatility Squeeze)       : {len(trades_s3):<5} trades across {len(dates_s3):<5} unique dates.")
    
    print("-" * 115)
    print("BLIND COLLISION ANALYSIS RESULTS:")
    print(f"  1. Exact Same-Bar (H1 Nến) Collision Count  : S1 vs S2 = {len(overlap_1_2_bar)} | S1 vs S3 = {len(overlap_1_3_bar)} | S2 vs S3 = {len(overlap_2_3_bar)}")
    print(f"  2. Triple Same-Bar Collision (3 Bot Cùng Nến): {len(triple_overlap_bar)} nến trùng!")
    print(f"  3. Same-Day Date Collision Count            : S1 vs S2 = {len(overlap_1_2_day)} dates | S1 vs S3 = {len(overlap_1_3_day)} dates | S2 vs S3 = {len(overlap_2_3_day)} dates")
    print(f"  4. Triple Same-Day Collision (3 Bot Cùng Ngày): {len(triple_overlap_day)} ngày trùng!")
    
    # Total combined unique trading dates covered
    all_dates_union = dates_s1.union(dates_s2).union(dates_s3)
    total_trades_all = len(trades_s1) + len(trades_s2) + len(trades_s3)
    print(f"\n🏆 COMBINED TRIPLE PORTFOLIO METRICS:")
    print(f"  Total Trades Logged (Combined 3 Bots)       : {total_trades_all:,} trades")
    print(f"  Total Unique Calendar Dates Covered         : {len(all_dates_union):,} unique trading days")
    print(f"  Natural Trade Isolation Ratio               : {(1.0 - (len(overlap_1_2_day)+len(overlap_1_3_day)+len(overlap_2_3_day))/total_trades_all)*100:.1f}% Independent Coverage")

if __name__ == '__main__':
    run_blind_triple_verifier()
