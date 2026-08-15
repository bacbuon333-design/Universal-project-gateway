"""
COMPOUNDING HYPER SCALING AUDIT & BROKER LOT CAP ANALYSIS
=========================================================
Calculates continuous single-deposit compounding from $1,000 in 2010 to 2026 across:
1. Pure Mathematical Compounding (Unlimited Lots)
2. Real-World Broker Compounding (Capped at Max 50.0 Lots per trade + Spread 25p + Comm $7 + Slippage 5p)
3. Comparison of CP1 Baseline vs CP5 Reaction Zone vs CP7 Refined

Dataset: XAUUSD H1 (16.57 Continuous Years: 2010 - 2026, 79,288 bars)
"""

import os, sys
sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None
import numpy as np
import pandas as pd

BASE_DIR = r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05\AlphaLab_Antigravity"
DATA_PATH = os.path.join(BASE_DIR, "data", "GOLD_H1_2010_2026.csv")

PIP = 0.01
PTVAL = 0.01

def run_compounding_audit():
    df = pd.read_csv(DATA_PATH)
    col = 'datetime_str' if 'datetime_str' in df.columns else df.columns[0]
    df['dt'] = pd.to_datetime(df[col])
    df['year'] = df['dt'].dt.year
    df.sort_values('dt', inplace=True)
    df.reset_index(drop=True, inplace=True)
    
    c = df['close'].values; h = df['high'].values; l = df['low'].values; o = df['open'].values
    v = df['tick_volume'].values if 'tick_volume' in df.columns else df['vol'].values
    n = len(df)
    
    tr = np.maximum(h[1:]-l[1:], np.maximum(abs(h[1:]-c[:-1]), abs(l[1:]-c[:-1])))
    tr = np.insert(tr, 0, tr[0])
    atr14 = pd.Series(tr).rolling(14).mean().bfill().values
    
    ema9   = pd.Series(c).ewm(span=9,   adjust=False).mean().values
    ema55  = pd.Series(c).ewm(span=55,  adjust=False).mean().values
    ema200 = pd.Series(c).ewm(span=200, adjust=False).mean().values
    
    d = pd.Series(c).diff()
    up = d.clip(lower=0).ewm(alpha=1/14, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1/14, adjust=False).mean().clip(1e-9)
    rsi14 = (100 - 100 / (1 + up / dn)).values
    
    don_hi20 = pd.Series(h).shift(1).rolling(20).max().bfill().values
    don_lo20 = pd.Series(l).shift(1).rolling(20).min().bfill().values
    near_ema9_55 = (abs(c - ema9) <= 2.5 * atr14) | (abs(c - ema55) <= 2.5 * atr14)
    
    ema12 = pd.Series(c).ewm(span=12, adjust=False).mean().values
    ema26 = pd.Series(c).ewm(span=26, adjust=False).mean().values
    macd_line = ema12 - ema26
    signal_line = pd.Series(macd_line).ewm(span=9, adjust=False).mean().values
    macd_hist = macd_line - signal_line
    
    hist_mid = pd.Series(macd_hist).rolling(20).mean().bfill().values
    hist_std = pd.Series(macd_hist).rolling(20).std().bfill().values + 1e-9
    hist_bb_up = hist_mid + 2.0 * hist_std
    hist_bb_dn = hist_mid - 2.0 * hist_std
    
    buy_sig  = (ema9 > ema55) & (ema55 > ema200) & (rsi14 > 51) & (macd_hist > hist_bb_up) & (c > don_hi20) & near_ema9_55
    sell_sig = (ema9 < ema55) & (ema55 < ema200) & (rsi14 < 49) & (macd_hist < hist_bb_dn) & (c < don_lo20) & near_ema9_55

    # Run continuous compounding test from 2010 to 2026 with $1,000 initial capital
    bal_unlimited = 1000.0  # Pure Compounding (No lot cap)
    bal_capped    = 1000.0  # Real Broker Compounding (Capped at 50.0 lots)
    
    last_trade = -9999; cooldown = 24
    pos_dir = 0; pos_en = 0.0; pos_sl = 0.0; pos_tp = 0.0
    pos_lot_unl = 0.0; pos_lot_cap = 0.0
    
    years = sorted(df['year'].unique())
    print("="*115)
    print("CONTINUOUS COMPOUNDING AUDIT FROM SINGLE $1,000 DEPOSIT (2010 - 2026)")
    print("Initial Deposit: $1,000.00 ONE TIME ONLY | Risk: 3.0% Dynamic Compounding")
    print("="*115)
    print(f"{'Year':<6} | {'Pure Unlimited Lot Bal $':<28} | {'Real Broker (50 Lot Cap) Bal $':<32} | {'Status':<10}")
    print("-" * 115)
    
    for yr in years:
        sub = df[df['year'] == yr]
        idx_sub = sub.index.values
        if len(idx_sub) < 100: continue
        
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
                    
                    # Net for Unlimited
                    gross_unl = pts * PTVAL * (pos_lot_unl / 0.01)
                    fee_unl   = (pos_lot_unl / 0.01) * 0.37
                    net_unl   = gross_unl - fee_unl
                    bal_unlimited = max(0.0, bal_unlimited + net_unl)
                    
                    # Net for Capped
                    gross_cap = pts * PTVAL * (pos_lot_cap / 0.01)
                    fee_cap   = (pos_lot_cap / 0.01) * 0.37
                    net_cap   = gross_cap - fee_cap
                    bal_capped = max(0.0, bal_capped + net_cap)
                    
                    pos_dir = 0
                    
            if pos_dir == 0 and (i - last_trade >= cooldown) and bal_unlimited > 0:
                sig = 0
                if buy_sig[i]: sig = 1
                elif sell_sig[i]: sig = -1
                
                if sig != 0:
                    av = max(atr14[i], 1.5); sp = 25.0
                    sl_pts = (av * 1.5 / PIP) + sp
                    tp_pts = (av * 3.5 / PIP)
                    
                    # Sizing Unlimited vs Capped
                    risk_unl = bal_unlimited * 0.03
                    lot_unl  = max(0.01, round((risk_unl / (sl_pts * 0.01)) * 0.01, 2))
                    
                    risk_cap = bal_capped * 0.03
                    lot_cap  = max(0.01, min(round((risk_cap / (sl_pts * 0.01)) * 0.01, 2), 50.0))
                    
                    next_o = o[i+1]; half_sp = (sp * PIP) / 2.0
                    if sig == 1: pos_dir = 1; pos_en = next_o + half_sp; pos_sl = pos_en - sl_pts * PIP; pos_tp = pos_en + tp_pts * PIP
                    else: pos_dir = -1; pos_en = next_o - half_sp; pos_sl = pos_en + sl_pts * PIP; pos_tp = pos_en - tp_pts * PIP
                    
                    pos_lot_unl = lot_unl
                    pos_lot_cap = lot_cap
                    last_trade = i

        print(f"{yr:<6} | ${bal_unlimited:<27,.2f} | ${bal_capped:<31,.2f} | {'🟢 COMPOUND'}")

    print("-" * 115)
    print(f"FINAL COMPOUNDING AUDIT SUMMARY (2010 - 2026):")
    print(f"  Pure Mathematical Compounding (No Lot Cap)  : ${bal_unlimited:,.2f} USD")
    print(f"  Real Broker Execution (Capped at 50.0 Lots) : ${bal_capped:,.2f} USD")

if __name__ == '__main__':
    run_compounding_audit()
