"""
MULTI-TIMEFRAME CASCADING ENGINE (M15 INTRA-BAR PRECISION TRIGGER WITHIN H1 STRUCTURE)
=====================================================================================
Solves the H1 OHLC limitation:
1. H1 Macro Structure Gate: Identifies when Gold is in a Macro Bull/Bear Trend (EMA200) AND inside a 48-bar Support/Resistance Zone.
2. M15 Intra-Bar Precision Trigger: Scans M15 bars inside the active H1 structure zone for:
   - M15 Micro-Pinbar Rejection (Wick >= 1.2x Body)
   - M15 EMA 9/21 Micro-Cross Confirmation

Dataset: Gold M15 (4.23 Continuous Years: 2022 - 2026, 99,999 nến)
Execution: Real broker costs (Spread 25p + Comm $7/lot + Slippage 5p)
"""

import os, sys
sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None
import numpy as np
import pandas as pd

BASE_DIR = r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05\AlphaLab_Antigravity"
DATA_M15 = os.path.join(BASE_DIR, "data", "GOLD_M15.csv")

PIP = 0.01
PTVAL = 0.01

def run_m15_cascading_engine(risk_pct=0.025):
    df = pd.read_csv(DATA_M15)
    col = 'datetime_str' if 'datetime_str' in df.columns else df.columns[0]
    df['dt'] = pd.to_datetime(df[col])
    df['year'] = df['dt'].dt.year
    df.sort_values('dt', inplace=True)
    df.reset_index(drop=True, inplace=True)
    
    c = df['close'].values; h = df['high'].values; l = df['low'].values; o = df['open'].values
    n = len(df)
    
    tr = np.maximum(h[1:]-l[1:], np.maximum(abs(h[1:]-c[:-1]), abs(l[1:]-c[:-1])))
    tr = np.insert(tr, 0, tr[0])
    atr14 = pd.Series(tr).rolling(14).mean().bfill().values
    
    # M15 Indicators
    ema9_m15  = pd.Series(c).ewm(span=9,  adjust=False).mean().values
    ema21_m15 = pd.Series(c).ewm(span=21, adjust=False).mean().values
    
    # H1 Equivalent Indicators on M15 (H1 = 4 x M15 bars)
    ema200_h1 = pd.Series(c).ewm(span=800, adjust=False).mean().values
    hi192_h1  = pd.Series(h).shift(1).rolling(192).max().bfill().values # 48 H1 bars = 192 M15 bars
    lo192_h1  = pd.Series(l).shift(1).rolling(192).min().bfill().values
    
    buy_sig  = np.zeros(n, dtype=bool)
    sell_sig = np.zeros(n, dtype=bool)
    
    for i in range(200, n):
        av = max(atr14[i], 1.5)
        lwick = min(o[i], c[i]) - l[i]
        uwick = h[i] - max(o[i], c[i])
        body  = abs(c[i] - o[i]) + 1e-9
        
        # 1. H1 Macro Structure Gate (Causal)
        macro_bull = c[i] > ema200_h1[i]
        macro_bear = c[i] < ema200_h1[i]
        
        near_lo48 = (c[i] - lo192_h1[i]) <= 2.0 * av
        near_hi48 = (hi192_h1[i] - c[i]) <= 2.0 * av
        
        # 2. M15 Micro Precision Trigger
        m15_pin_buy  = (lwick >= 1.2 * body) and (c[i] > o[i])
        m15_pin_sell = (uwick >= 1.2 * body) and (c[i] < o[i])
        m15_ema_cross_up = ema9_m15[i] >= ema21_m15[i]
        m15_ema_cross_dn = ema9_m15[i] <= ema21_m15[i]
        
        if macro_bull and near_lo48 and m15_pin_buy and m15_ema_cross_up:
            buy_sig[i] = True
        elif macro_bear and near_hi48 and m15_pin_sell and m15_ema_cross_dn:
            sell_sig[i] = True

    # Simulate
    years = sorted(df['year'].unique())
    tot_cash = 0; wins_yr = 0; tot_yr = 0
    
    print("="*95)
    print("MULTI-TIMEFRAME CASCADING ENGINE (M15 INTRA-BAR SCAN WITHIN H1 STRUCTURE)")
    print("Dataset: Gold M15 (4.23 Continuous Years: 2022 - 2026, 99,999 nến)")
    print("="*95)
    print(f"{'Year':<6} | {'PnL %':<8} {'Ending Balance ($)':<20} {'MaxDD %':<8} {'Trades':<6} {'PF':<5}")
    print("-" * 95)
    
    for yr in years:
        sub = df[df['year'] == yr]
        idx_sub = sub.index.values
        if len(idx_sub) < 100: continue
        
        bal = 1000.0; pk = 1000.0; max_dd = 0.0
        last_trade = -9999; cooldown = 16 # 4 hours cooldown
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
                    pk  = max(pk, bal)
                    dd  = (pk - bal) / pk * 100.0 if pk > 0 else 0
                    max_dd = max(max_dd, dd)
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
        
        wins = [t for t in trades if t > 0]
        loss = [t for t in trades if t < 0]
        pf = sum(wins)/abs(sum(loss)) if loss and sum(loss)!=0 else 0
        s = "✅" if pnl_pct > 0 else "❌"
        
        print(f"{yr:<6} | {pnl_pct:>+6.1f}%  ${bal:<19,.2f} {max_dd:<8.1f} {len(trades):<6} {pf:<5.2f} {s}")

    print("-" * 95)
    print(f"SUMMARY: Win Rate Years = {wins_yr} / {tot_yr} ({wins_yr/tot_yr*100:.1f}%) | Total Cumulative Cash = ${tot_cash:,.2f} USD")

if __name__ == '__main__':
    run_m15_cascading_engine()
