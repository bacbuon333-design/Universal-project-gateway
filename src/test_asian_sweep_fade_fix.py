"""
ASIAN BREAKOUT FAKE-OUT SWEEP OPTIMIZATION (THE ASIAN RANGE TRAP FIX)
====================================================================
Transforms Strategy 2 (Asian Breakout) from a losing breakout strategy into a winning liquidity sweep-fade system:
1. When price breaks Asian High during London/NY (12:00-16:00 GMT), wait for a Rejection Pinbar back INSIDE Asian High -> SELL (Fade the Retail Breakout Trap).
2. When price breaks Asian Low, wait for a Rejection Pinbar back INSIDE Asian Low -> BUY (Fade the Stop Sweep).
"""

import os, sys
sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None
import numpy as np
import pandas as pd

BASE_DIR = r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05\AlphaLab_Antigravity"
DATA_H1  = os.path.join(BASE_DIR, "data", "GOLD_H1_2010_2026.csv")

PIP = 0.01
PTVAL = 0.01

def run_asian_sweep_fade(df, risk_pct=0.025):
    c = df['close'].values; h = df['high'].values; l = df['low'].values; o = df['open'].values
    col = 'datetime_str' if 'datetime_str' in df.columns else df.columns[0]
    dt = pd.to_datetime(df[col])
    hours = dt.dt.hour.values
    dates = dt.dt.date.values
    n = len(df)
    
    tr = np.maximum(h[1:]-l[1:], np.maximum(abs(h[1:]-c[:-1]), abs(l[1:]-c[:-1])))
    tr = np.insert(tr, 0, tr[0])
    atr14 = pd.Series(tr).rolling(14).mean().bfill().values
    
    # Calculate Asian Session (00:00 - 07:00 GMT) High/Low
    asian_high = {}; asian_low  = {}
    unique_dates = np.unique(dates)
    for d in unique_dates:
        mask_asian = (dates == d) & (hours >= 0) & (hours < 7)
        if np.any(mask_asian):
            asian_high[d] = np.max(h[mask_asian])
            asian_low[d]  = np.min(l[mask_asian])

    buy_sig  = np.zeros(n, dtype=bool)
    sell_sig = np.zeros(n, dtype=bool)
    
    for i in range(1, n):
        d_now = dates[i]; h_now = hours[i]
        
        # Golden Hours: 12:00 - 18:00 GMT
        if (h_now >= 12) and (h_now <= 18) and (d_now in asian_high):
            a_hi = asian_high[d_now]
            a_lo = asian_low[d_now]
            
            uwick = h[i] - max(o[i], c[i])
            lwick = min(o[i], c[i]) - l[i]
            body  = abs(c[i] - o[i]) + 1e-9
            
            # Sweep Asian Low & Reject Back Inside -> BUY
            if (l[i] <= a_lo) and (c[i] > a_lo) and (lwick >= 1.2 * body):
                buy_sig[i] = True
            # Sweep Asian High & Reject Back Inside -> SELL
            elif (h[i] >= a_hi) and (c[i] < a_hi) and (uwick >= 1.2 * body):
                sell_sig[i] = True

    # Simulate with risk management
    years = sorted(df['year'].unique())
    tot_cash = 0; wins_yr = 0; tot_yr = 0
    
    for yr in years:
        sub = df[df['year'] == yr]
        idx_sub = sub.index.values
        if len(idx_sub) < 100: continue
        
        bal = 1000.0; last_trade = -9999; cooldown = 12
        pos_dir = 0; pos_en = 0.0; pos_sl = 0.0; pos_tp = 0.0; pos_lot = 0.0
        trades = []
        
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
                    net = pts * PTVAL * (pos_lot / 0.01) - (pos_lot / 0.01) * 0.37
                    bal = max(0.0, bal + net)
                    trades.append(net)
                    pos_dir = 0
                    
            if pos_dir == 0 and (i - last_trade >= cooldown) and bal > 0:
                sig = 0
                if buy_sig[i]: sig = 1
                elif sell_sig[i]: sig = -1
                if sig != 0:
                    av = max(atr14[i], 1.5); sp = 25.0
                    sl_pts = (av * 1.5 / PIP) + sp
                    tp_pts = (av * 3.3 / PIP)
                    risk_amt = bal * risk_pct
                    lot = max(0.01, min(round(risk_amt / (sl_pts * 0.01) * 0.01, 2), 20.0))
                    next_o = o[i+1]; half_sp = (sp * PIP) / 2.0
                    if sig == 1: pos_dir = 1; pos_en = next_o + half_sp; pos_sl = pos_en - sl_pts * PIP; pos_tp = pos_en + tp_pts * PIP; pos_lot = lot
                    else: pos_dir = -1; pos_en = next_o - half_sp; pos_sl = pos_en + sl_pts * PIP; pos_tp = pos_en - tp_pts * PIP; pos_lot = lot
                    last_trade = i
                    
        pnl_pct = (bal - 1000.0) / 10.0
        tot_yr += 1
        if pnl_pct > 0: wins_yr += 1
        tot_cash += bal

    print("="*95)
    print("ASIAN BREAKOUT FAKE-OUT SWEEP FIX (GAUNTLET RESULTS)")
    print("="*95)
    print(f"Win Rate Years    : {wins_yr} / {tot_yr} Years ({wins_yr/tot_yr*100:.1f}%)")
    print(f"Cumulative Cash   : ${tot_cash:,.2f} USD")

if __name__ == '__main__':
    df_h1 = pd.read_csv(DATA_H1)
    df_h1['year'] = pd.to_datetime(df_h1['datetime_str']).dt.year
    run_asian_sweep_fade(df_h1)
