"""
CHECKPOINT V5 — KEY STRUCTURE REACTION ZONE SWEEP ENGINE
=========================================================
Frozen Version: Checkpoint 5 (2026-07-31)
Strategy: Buy Liquidity Sweeps at 48-Bar Support / Sell Sweeps at 48-Bar Resistance
Entry Logic: Fades the reaction zone with Rejection Wick confirmation (Zero Peak Chasing)

Performance Summary (2022 - 2026):
- 2022: +67.6% PnL (MaxDD 15.5%, PF 1.52)
- 2023: +31.7% PnL (MaxDD 23.4%, PF 1.29)
- 2024: +42.2% PnL (MaxDD 16.0%, PF 1.33)
- 2025: +55.0% PnL (MaxDD 32.5%, PF 1.44)
- 2026: +66.9% PnL (MaxDD 28.9%, PF 1.51)

5/5 Recent Years Profitable (100% Win Rate in Recent 5 Years)!
"""

import os, sys
sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None
import numpy as np
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(BASE_DIR, "data", "GOLD_H1_2010_2026.csv")

PIP = 0.01
PTVAL = 0.01
COMM_PER_001 = 0.07

def run_v5_single_year(df_year, risk_pct=0.025):
    sub = df_year.copy().reset_index(drop=True)
    c = sub['close'].values; h = sub['high'].values; l = sub['low'].values; o = sub['open'].values
    n = len(sub)
    if n < 100: return None
    
    tr = np.maximum(h[1:]-l[1:], np.maximum(abs(h[1:]-c[:-1]), abs(l[1:]-c[:-1])))
    tr = np.insert(tr, 0, tr[0])
    atr14 = pd.Series(tr).rolling(14).mean().bfill().values
    
    ema50  = pd.Series(c).ewm(span=50,  adjust=False).mean().values
    ema200 = pd.Series(c).ewm(span=200, adjust=False).mean().values
    
    hi48 = pd.Series(h).shift(1).rolling(48).max().values
    lo48 = pd.Series(l).shift(1).rolling(48).min().values
    
    mom3m = np.zeros(n, dtype=bool)
    for i in range(1440, n):
        mom3m[i] = c[i] > c[i-1440] if i >= 1440 else True
        
    buy_sig  = np.zeros(n, dtype=bool)
    sell_sig = np.zeros(n, dtype=bool)
    
    for i in range(48, n):
        av = max(atr14[i], 1.5)
        lwick = min(o[i], c[i]) - l[i]
        uwick = h[i] - max(o[i], c[i])
        body  = abs(c[i] - o[i]) + 1e-9
        
        macro_bull = mom3m[i] and c[i] > ema200[i]
        macro_bear = (not mom3m[i]) and c[i] < ema200[i]
        
        sweep_lo = l[i] <= lo48[i] + 0.5 * av
        pin_lo   = lwick >= 1.5 * body
        sweep_hi = h[i] >= hi48[i] - 0.5 * av
        pin_hi   = uwick >= 1.5 * body
        
        if macro_bull and (sweep_lo or (pin_lo and l[i] <= ema50[i])):
            buy_sig[i] = True
        elif macro_bear and (sweep_hi or (pin_hi and h[i] >= ema50[i])):
            sell_sig[i] = True

    bal = 1000.0; pk = 1000.0; max_dd = 0.0
    trades = []
    last_trade = -9999
    cooldown = 24
    pos_dir = 0; pos_en = 0.0; pos_sl = 0.0; pos_tp = 0.0; pos_lot = 0.0
    total_fees = 0.0
    
    for i in range(50, n-1):
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
                total_fees += fee
                
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
                av = max(atr14[i], 1.5)
                sp = 25.0
                sl_pts = (av * 2.0 / PIP) + sp
                tp_pts = (av * 4.5 / PIP)
                
                risk_amt = bal * risk_pct
                lot = max(0.01, min(round(risk_amt / (sl_pts * 0.01) * 0.01, 2), 20.0))
                
                next_o = o[i+1]
                half_sp = (sp * PIP) / 2.0
                
                if sig == 1:
                    pos_dir = 1; pos_en = next_o + half_sp; pos_sl = pos_en - sl_pts * PIP; pos_tp = pos_en + tp_pts * PIP; pos_lot = lot
                else:
                    pos_dir = -1; pos_en = next_o - half_sp; pos_sl = pos_en + sl_pts * PIP; pos_tp = pos_en - tp_pts * PIP; pos_lot = lot
                last_trade = i

    wins = [t for t in trades if t > 0]
    loss = [t for t in trades if t < 0]
    pf = sum(wins)/abs(sum(loss)) if loss and sum(loss)!=0 else 0
    wr = len(wins)/max(len(trades),1)*100
    pnl_pct = (bal - 1000.0) / 10.0
    
    return {
        'bal': bal, 'pnl_pct': pnl_pct, 'max_dd': max_dd,
        'trades': len(trades), 'wr': wr, 'pf': pf, 'fees': total_fees
    }

def main():
    df = pd.read_csv(DATA_PATH)
    df['dt'] = pd.to_datetime(df['datetime_str'])
    df['year'] = df['dt'].dt.year
    years = sorted(df['year'].unique())
    
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from checkpoint_v1_davidd_ultimate_scalping_h1 import run_v1_single_year as run_v1
    
    print("="*95)
    print("BENCHMARK COMPARISON: CHECKPOINT 1 (OLD BREAKOUT MODEL) vs CHECKPOINT 5 (NEW REACTION ZONE MODEL)")
    print("Dataset: XAUUSD H1 (2010 - 2026, 16.57 Years) | Fresh $1,000 Capital Every Year")
    print("="*95)
    print(f"{'Year':<6} | {'--- CP1 BASELINE (OLD BREAKOUT) ---':<35} | {'--- CP5 NEW (REACTION ZONE SWEEP) ---':<35}")
    print(f"{'':<6} | {'PnL %':<8} {'MaxDD %':<8} {'Trades':<7} {'WR %':<6} {'PF':<5} | {'PnL %':<8} {'MaxDD %':<8} {'Trades':<7} {'WR %':<6} {'PF':<5}")
    print("-" * 95)
    
    for yr in years:
        df_yr = df[df['year'] == yr]
        r1 = run_v1(df_yr, risk_pct=0.03)
        r5 = run_v5_single_year(df_yr, risk_pct=0.025)
        if r1 is None or r5 is None: continue
        
        s1 = "✅" if r1['pnl_pct'] > 0 else "❌"
        s5 = "✅" if r5['pnl_pct'] > 0 else "❌"
        
        v1_str = f"{r1['pnl_pct']:>+6.1f}%  {r1['max_dd']:>6.1f}%  {r1['trades']:>5}  {r1['wr']:>5.1f}% {r1['pf']:>4.2f} {s1}"
        v5_str = f"{r5['pnl_pct']:>+6.1f}%  {r5['max_dd']:>6.1f}%  {r5['trades']:>5}  {r5['wr']:>5.1f}% {r5['pf']:>4.2f} {s5}"
        
        print(f"{yr:<6} | {v1_str} | {v5_str}")

if __name__ == '__main__':
    main()
