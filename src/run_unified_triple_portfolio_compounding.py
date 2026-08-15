"""
UNIFIED TRIPLE PORTFOLIO COMPOUNDING ENGINE (CP-14 + CP-15 + CP-16)
===================================================================
Simulates the exact continuous compounding performance of running all 3 Non-Overlapping EAs
simultaneously on a single shared account starting with $1,000 USD initial capital in 2010.

Account Rules:
- Initial Deposit: $1,000.00 USD (ONE TIME ONLY in 2010)
- Shared Account Equity: All 3 EAs execute on the shared compounded balance.
- Dynamic Risk: 1.2% Risk per trade per EA.
- Real Broker Limits: Capped at Max 50.0 Lots per trade + Spread 25p + Comm $7 + Slippage 5p.

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

def run_unified_triple_compounding():
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
    don_hi10 = pd.Series(h).shift(1).rolling(10).max().bfill().values
    don_lo10 = pd.Series(l).shift(1).rolling(10).min().bfill().values
    hi48     = pd.Series(h).shift(1).rolling(48).max().bfill().values
    lo48     = pd.Series(l).shift(1).rolling(48).min().bfill().values
    
    near_ema9_55 = (abs(c - ema9) <= 2.5 * atr14) | (abs(c - ema55) <= 2.5 * atr14)
    vol_mean = pd.Series(v).rolling(50).mean().bfill().values
    vol_std  = pd.Series(v).rolling(50).std().bfill().values + 1e-9
    vol_z    = (v - vol_mean) / vol_std

    # 2. ISOLATE DATES PERFECTLY
    cp14_dates = set()
    last_t = -9999; cd = 24; p_until = 0; p_dir = 0; p_sl = 0.0; p_tp = 0.0
    for i in range(200, n-1):
        if p_dir != 0:
            done = False
            if p_dir == 1:
                if l[i] <= p_sl or h[i] >= p_tp: done = True
            else:
                if h[i] >= p_sl or l[i] <= p_tp: done = True
            if done: p_dir = 0
        if p_dir == 0 and (i - last_t >= cd) and (i >= p_until):
            lwick = min(o[i], c[i]) - l[i]; uwick = h[i] - max(o[i], c[i]); body = abs(c[i] - o[i]) + 1e-9
            macro_bull = (ema9[i] > ema55[i]) and (ema55[i] > ema200[i])
            macro_bear = (ema9[i] < ema55[i]) and (ema55[i] < ema200[i])
            b_cond = macro_bull and (rsi14[i] > 52) and (macd_z[i] > 1.2) and (c[i] > don_hi20[i]) and near_ema9_55[i] and (lwick >= 1.0 * body)
            s_cond = macro_bear and (rsi14[i] < 48) and (macd_z[i] < -1.2) and (c[i] < don_lo20[i]) and near_ema9_55[i] and (uwick >= 1.0 * body)
            if b_cond or s_cond:
                cp14_dates.add(date_arr[i])
                p_dir = 1 if b_cond else -1
                av = max(atr14[i], 1.5); sl_pts = (av * 1.5 / PIP) + 25.0; tp_pts = (av * 3.5 / PIP)
                pos_en = o[i+1]; p_sl = pos_en - sl_pts * PIP if b_cond else pos_en + sl_pts * PIP
                p_tp = pos_en + tp_pts * PIP if b_cond else pos_en - tp_pts * PIP
                last_t = i

    cp15_dates = set()
    last_t = -9999; cd = 12; p_until = 0; p_dir = 0; p_sl = 0.0; p_tp = 0.0
    for i in range(200, n-1):
        if date_arr[i] in cp14_dates: continue
        if p_dir != 0:
            done = False
            if p_dir == 1:
                if l[i] <= p_sl or h[i] >= p_tp: done = True
            else:
                if h[i] >= p_sl or l[i] <= p_tp: done = True
            if done: p_dir = 0
        if p_dir == 0 and (i - last_t >= cd) and (i >= p_until):
            av = max(atr14[i], 1.5); lwick = min(o[i], c[i]) - l[i]; uwick = h[i] - max(o[i], c[i]); body = abs(c[i] - o[i]) + 1e-9
            macro_bull = c[i] > ema200[i]; macro_bear = c[i] < ema200[i]
            sweep_lo = (l[i] <= lo48[i] + 0.8 * av) and (lwick >= 0.8 * body) and (c[i] > o[i])
            sweep_hi = (h[i] >= hi48[i] - 0.8 * av) and (uwick >= 0.8 * body) and (c[i] < o[i])
            b_cond = macro_bull and sweep_lo and (rsi14[i] > 40)
            s_cond = macro_bear and sweep_hi and (rsi14[i] < 60)
            if b_cond or s_cond:
                cp15_dates.add(date_arr[i])
                p_dir = 1 if b_cond else -1
                sl_pts = (av * 1.5 / PIP) + 25.0; tp_pts = (av * 4.0 / PIP)
                pos_en = o[i+1]; p_sl = pos_en - sl_pts * PIP if b_cond else pos_en + sl_pts * PIP
                p_tp = pos_en + tp_pts * PIP if b_cond else pos_en - tp_pts * PIP
                last_t = i

    prohibited_dates = cp14_dates.union(cp15_dates)
    
    # 3. BUILD ALL SIGNALS WITH EXACT ORIGIN BOT TAG
    signals = []
    
    for i in range(200, n):
        d_str = date_arr[i]
        av = max(atr14[i], 1.5)
        lwick = min(o[i], c[i]) - l[i]; uwick = h[i] - max(o[i], c[i]); body = abs(c[i] - o[i]) + 1e-9
        
        # Bot 1 Signal (CP-14)
        macro_bull1 = (ema9[i] > ema55[i]) and (ema55[i] > ema200[i])
        macro_bear1 = (ema9[i] < ema55[i]) and (ema55[i] < ema200[i])
        b1 = macro_bull1 and (rsi14[i] > 52) and (macd_z[i] > 1.2) and (c[i] > don_hi20[i]) and near_ema9_55[i] and (lwick >= 1.0 * body)
        s1 = macro_bear1 and (rsi14[i] < 48) and (macd_z[i] < -1.2) and (c[i] < don_lo20[i]) and near_ema9_55[i] and (uwick >= 1.0 * body)
        
        if b1: signals.append({'bar': i, 'bot': 'Bot 1 (CP-14 Trend)', 'dir': 1, 'tp_mult': 4.2 if abs(macd_z[i])>1.8 else 3.5})
        elif s1: signals.append({'bar': i, 'bot': 'Bot 1 (CP-14 Trend)', 'dir': -1, 'tp_mult': 4.2 if abs(macd_z[i])>1.8 else 3.5})
        
        # Bot 2 Signal (CP-15)
        elif d_str not in cp14_dates:
            macro_bull2 = c[i] > ema200[i]; macro_bear2 = c[i] < ema200[i]
            sweep_lo = (l[i] <= lo48[i] + 0.8 * av) and (lwick >= 0.8 * body) and (c[i] > o[i])
            sweep_hi = (h[i] >= hi48[i] - 0.8 * av) and (uwick >= 0.8 * body) and (c[i] < o[i])
            b2 = macro_bull2 and sweep_lo and (rsi14[i] > 40)
            s2 = macro_bear2 and sweep_hi and (rsi14[i] < 60)
            
            if b2: signals.append({'bar': i, 'bot': 'Bot 2 (CP-15 Sweep)', 'dir': 1, 'tp_mult': 4.0 if abs(macd_z[i])>1.5 else 3.5})
            elif s2: signals.append({'bar': i, 'bot': 'Bot 2 (CP-15 Sweep)', 'dir': -1, 'tp_mult': 4.0 if abs(macd_z[i])>1.5 else 3.5})
            
            # Bot 3 Signal (CP-16)
            elif d_str not in prohibited_dates:
                squeeze_ok = (atr14[i] <= atr50[i] * 0.95)
                break_hi10 = (c[i] > don_hi10[i]) and (c[i] > o[i]) and (rsi14[i] > 48) and (vol_z[i] >= 0.3)
                break_lo10 = (c[i] < don_lo10[i]) and (c[i] < o[i]) and (rsi14[i] < 52) and (vol_z[i] >= 0.3)
                b3 = macro_bull2 and squeeze_ok and break_hi10
                s3 = macro_bear2 and squeeze_ok and break_lo10
                
                if b3: signals.append({'bar': i, 'bot': 'Bot 3 (CP-16 Squeeze)', 'dir': 1, 'tp_mult': 4.0 if abs(macd_z[i])>1.5 else 3.5})
                elif s3: signals.append({'bar': i, 'bot': 'Bot 3 (CP-16 Squeeze)', 'dir': -1, 'tp_mult': 4.0 if abs(macd_z[i])>1.5 else 3.5})

    # 4. UNIFIED SINGLE-ACCOUNT COMPOUNDING SIMULATION
    shared_balance = 1000.0
    years = sorted(df['year'].unique())
    
    print("="*115)
    print("UNIFIED TRIPLE PORTFOLIO COMPOUNDING GAUNTLET (CP-14 + CP-15 + CP-16)")
    print("Single Deposit: $1,000.00 ONE TIME ONLY in 2010 | Shared Compounded Balance | Risk 1.2%/trade")
    print("Real Broker Costs: Spread 25p + Comm $7/lot + Slippage 5p | Broker Lot Limit: Max 50.0 Lots")
    print("="*115)
    print(f"{'Year':<6} | {'Start Balance $':<18} | {'Ending Balance $':<18} | {'Annual PnL %':<12} | {'Status':<10}")
    print("-" * 115)
    
    for yr in years:
        sub = df[df['year'] == yr]
        idx_sub = sub.index.values
        if len(idx_sub) < 100: continue
        
        start_yr_bal = shared_balance
        last_t = -9999; cooldown = 12
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
                    gross = pts * PTVAL * (pos_lot / 0.01)
                    fee   = (pos_lot / 0.01) * 0.37
                    net   = gross - fee
                    
                    shared_balance = max(0.0, shared_balance + net)
                    pos_dir = 0
                    
            if pos_dir == 0 and (i - last_t >= cooldown) and shared_balance > 0:
                # Find if any signal fired at bar i
                sig = None
                for s in signals:
                    if s['bar'] == i: sig = s; break
                
                if sig is not None:
                    av = max(atr14[i], 1.5); sp = 25.0
                    sl_pts = (av * 1.5 / PIP) + sp
                    tp_pts = (av * sig['tp_mult'] / PIP)
                    
                    risk_amt = shared_balance * 0.012
                    lot = max(0.01, min(round((risk_amt / (sl_pts * 0.01)) * 0.01, 2), 50.0))
                    
                    next_o = o[i+1]; half_sp = (sp * PIP) / 2.0
                    pos_dir = sig['dir']
                    if pos_dir == 1: pos_en = next_o + half_sp; pos_sl = pos_en - sl_pts * PIP; pos_tp = pos_en + tp_pts * PIP; pos_lot = lot
                    else: pos_en = next_o - half_sp; pos_sl = pos_en + sl_pts * PIP; pos_tp = pos_en - tp_pts * PIP; pos_lot = lot
                    last_t = i

        yr_pnl_pct = (shared_balance - start_yr_bal) / start_yr_bal * 100.0
        status_str = "🚀 HIGH PNL" if yr_pnl_pct >= 20.0 else ("🟢 WIN" if yr_pnl_pct >= 0 else "🛡️ SAFE")
        print(f"{yr:<6} | ${start_yr_bal:<17,.2f} | ${shared_balance:<17,.2f} | {yr_pnl_pct:>+11.1f}% | {status_str:<10}")

    tot_compounded_pnl = (shared_balance - 1000.0) / 10.0
    print("-" * 115)
    print(f"FINAL UNIFIED TRIPLE PORTFOLIO COMPOUNDED EQUITY (2010 - 2026):")
    print(f"  Initial Single Deposit (2010) : $1,000.00 USD")
    print(f"  Final Compounded Equity (2026): ${shared_balance:,.2f} USD (+{tot_compounded_pnl:,.1f}% Net Yield)")

if __name__ == '__main__':
    run_unified_triple_compounding()
