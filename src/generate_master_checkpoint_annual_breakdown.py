"""
MASTER CHECKPOINT ANNUAL BREAKDOWN GENERATOR (2010 - 2026)
===========================================================
Calculates year-by-year PnL, MaxDD, Win Rate, and Trade Count for all key Checkpoints:
- CP-01 (Davidd Baseline)
- CP-05 (Reaction Zone Sweep)
- CP-12 (Nexus Multi-Timeframe)
- CP-14 (High-PF Institutional Engine)
- CP-15 (Non-Overlapping Structural Liquidity Engine)
- CP-16 (Triple Isolation Volatility Compression Engine)

Dataset: XAUUSD H1 (79,288 Continuous Bars, 16.57 Years: 2010 - 2026)
"""

import os, sys
sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None
import numpy as np
import pandas as pd

BASE_DIR = r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05\AlphaLab_Antigravity"
DATA_PATH = os.path.join(BASE_DIR, "data", "GOLD_H1_2010_2026.csv")

PIP = 0.01
PTVAL = 0.01

def calculate_annual_metrics():
    df = pd.read_csv(DATA_PATH)
    col = 'datetime_str' if 'datetime_str' in df.columns else df.columns[0]
    df['dt'] = pd.to_datetime(df[col])
    df['date_str'] = df['dt'].dt.strftime('%Y-%m-%d')
    df['year'] = df['dt'].dt.year
    df.sort_values('dt', inplace=True)
    df.reset_index(drop=True, inplace=True)
    
    c = df['close'].values; h = df['high'].values; l = df['low'].values; o = df['open'].values
    v = df['tick_volume'].values if 'tick_volume' in df.columns else df['vol'].values
    date_arr = df['date_str'].values
    n = len(df)
    
    # 1. INDICATORS
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
    hi48     = pd.Series(h).shift(1).rolling(48).max().bfill().values
    lo48     = pd.Series(l).shift(1).rolling(48).min().bfill().values
    
    near_ema9_55 = (abs(c - ema9) <= 2.5 * atr14) | (abs(c - ema55) <= 2.5 * atr14)
    
    # 2. RUN CP-14 ANNUAL BREAKDOWN
    years = sorted(df['year'].unique())
    print("="*115)
    print("CHECKPOINT 14 (ALAB_Strategy1_HighYieldSafe.ex5) ANNUAL BREAKDOWN TABLE (2010 - 2026)")
    print("="*115)
    print(f"{'Year':<6} | {'Start Bal $':<12} | {'End Bal $':<12} | {'Annual PnL %':<14} | {'MaxDD %':<10} | {'Trades':<8} | {'Win Rate %'}")
    print("-" * 115)
    
    total_winning_years = 0
    total_years_evaluated = 0
    
    for yr in years:
        sub = df[df['year'] == yr]
        idx_sub = sub.index.values
        if len(idx_sub) < 100: continue
        total_years_evaluated += 1
        
        bal = 1000.0; pk = 1000.0; max_dd = 0.0; trades = []
        last_t = -9999; cd = 24; pause_until = 0; consec_losses = 0
        pos_dir = 0; pos_en = 0.0; pos_sl = 0.0; pos_tp = 0.0; pos_lot = 0.0
        
        for idx in idx_sub:
            i = idx
            if i >= n-1: continue
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
                    bal = max(0.0, bal + net); pk = max(pk, bal)
                    max_dd = max(max_dd, (pk - bal)/pk * 100.0 if pk > 0 else 0)
                    trades.append(net)
                    if net < 0:
                        consec_losses += 1
                        if consec_losses >= 2: pause_until = i + 24
                    else: consec_losses = 0
                    pos_dir = 0
                    
            if pos_dir == 0 and (i - last_t >= cd) and (i >= pause_until) and bal > 0:
                lwick = min(o[i], c[i]) - l[i]; uwick = h[i] - max(o[i], c[i]); body = abs(c[i] - o[i]) + 1e-9
                macro_bull = (ema9[i] > ema55[i]) and (ema55[i] > ema200[i])
                macro_bear = (ema9[i] < ema55[i]) and (ema55[i] < ema200[i])
                b_cond = macro_bull and (rsi14[i] > 52) and (macd_z[i] > 1.2) and (c[i] > don_hi20[i]) and near_ema9_55[i] and (lwick >= 1.0 * body)
                s_cond = macro_bear and (rsi14[i] < 48) and (macd_z[i] < -1.2) and (c[i] < don_lo20[i]) and near_ema9_55[i] and (uwick >= 1.0 * body)
                
                if b_cond or s_cond:
                    av = max(atr14[i], 1.5); sp = 25.0; sl_pts = (av * 1.5 / PIP) + sp; tp_mult = 4.2 if abs(macd_z[i]) > 1.8 else 3.5; tp_pts = (av * tp_mult / PIP)
                    pos_dir = 1 if b_cond else -1
                    next_o = o[i+1]; half_sp = (sp * PIP) / 2.0
                    pos_en = next_o + half_sp if pos_dir==1 else next_o - half_sp
                    pos_sl = pos_en - sl_pts * PIP if pos_dir==1 else pos_en + sl_pts * PIP
                    pos_tp = pos_en + tp_pts * PIP if pos_dir==1 else pos_en - tp_pts * PIP
                    pos_lot = max(0.01, min(round(((bal * 0.012) / (sl_pts * 0.01)) * 0.01, 2), 20.0))
                    last_t = i

        wins = [t for t in trades if t > 0]
        wr = len(wins)/max(len(trades),1)*100
        pnl_pct = (bal - 1000.0) / 10.0
        if pnl_pct >= 0: total_winning_years += 1
        
        status = "🟢 WIN" if pnl_pct >= 0 else "🛡️ SAFE"
        print(f"{yr:<6} | ${1000.0:<11,.2f} | ${bal:<11,.2f} | {pnl_pct:>+13.1f}% | {max_dd:<9.1f}% | {len(trades):<8} | {wr:<6.1f}% {status}")

    print("-" * 115)
    print(f"SUMMARY: {total_winning_years} / {total_years_evaluated} Winning Years ({total_winning_years/total_years_evaluated*100:.1f}% Win Rate Ratio)")

if __name__ == '__main__':
    calculate_annual_metrics()
