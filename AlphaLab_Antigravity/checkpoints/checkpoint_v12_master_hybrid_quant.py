"""
CHECKPOINT V12 MASTER HYBRID QUANT ENGINE (ALAB_Nexus_v36_Master)
===================================================================
Frozen Version: Checkpoint 12 Master (2026-07-31)

Combines the #1 and #2 most profitable engines in the entire lab:
1. Engine Core A (CP5 Reaction Zone Sweep): Buy when price sweeps 48-bar Support & forms Rejection Pinbar.
2. Engine Core B (CP7 Donchian Breakout Gate): Buy when price breaks 20-bar Donchian High in Macro Bull regime (EMA9 > EMA55 > EMA200).
3. Risk Protection: 24-hour Cooldown after 2 consecutive losses.
4. R:R Execution: Hard Fixed 1:2.0 Risk-to-Reward Ratio (No Trailing Stop interference).

Dataset: XAUUSD H1 (16.57 Years: 2010 - 2026, 79,288 bars)
Execution: Real broker costs (Spread 25p + Comm $7/lot + Slippage 5p)
"""

import os, sys
sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None
import numpy as np
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(BASE_DIR, "data", "GOLD_H1_2010_2026.csv")

PIP = 0.01
PTVAL = 0.01

def run_checkpoint_v12_master(df, risk_pct=0.025):
    c = df['close'].values; h = df['high'].values; l = df['low'].values; o = df['open'].values
    n = len(df)
    if n < 500: return None
    
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
    
    hi48 = pd.Series(h).shift(1).rolling(48).max().bfill().values
    lo48 = pd.Series(l).shift(1).rolling(48).min().bfill().values
    
    buy_sig  = np.zeros(n, dtype=bool)
    sell_sig = np.zeros(n, dtype=bool)
    
    for i in range(200, n):
        av = max(atr14[i], 1.5)
        lwick = min(o[i], c[i]) - l[i]
        uwick = h[i] - max(o[i], c[i])
        body  = abs(c[i] - o[i]) + 1e-9
        
        macro_bull = (ema9[i] > ema55[i]) and (ema55[i] > ema200[i])
        macro_bear = (ema9[i] < ema55[i]) and (ema55[i] < ema200[i])
        
        # Core A: Reaction Zone Sweep
        sweep_lo = (l[i] <= lo48[i] + 0.5 * av) and (lwick >= 1.2 * body) and (c[i] > o[i])
        sweep_hi = (h[i] >= hi48[i] - 0.5 * av) and (uwick >= 1.2 * body) and (c[i] < o[i])
        
        # Core B: Donchian 20 Breakout
        break_hi = macro_bull and (c[i] > don_hi20[i]) and (rsi14[i] > 51)
        break_lo = macro_bear and (c[i] < don_lo20[i]) and (rsi14[i] < 49)
        
        if (macro_bull and sweep_lo) or break_hi:
            buy_sig[i] = True
        elif (macro_bear and sweep_hi) or break_lo:
            sell_sig[i] = True

    bal = 1000.0; pk = 1000.0; max_dd = 0.0
    trades = []
    last_trade = -9999; cooldown = 24
    consec_losses = 0; pause_until = 0
    pos_dir = 0; pos_en = 0.0; pos_sl = 0.0; pos_tp = 0.0; pos_lot = 0.0
    
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
                gross = pts * PTVAL * (pos_lot / 0.01)
                fee   = (pos_lot / 0.01) * 0.37
                net   = gross - fee
                
                bal = max(0.0, bal + net)
                pk  = max(pk, bal)
                dd  = (pk - bal) / pk * 100.0 if pk > 0 else 0
                max_dd = max(max_dd, dd)
                trades.append(net)
                
                if net < 0:
                    consec_losses += 1
                    if consec_losses >= 2: pause_until = i + 24 # 24h pause after 2 losses
                else:
                    consec_losses = 0
                pos_dir = 0
                
        if pos_dir == 0 and (i - last_trade >= cooldown) and (i >= pause_until) and bal > 0:
            sig = 0
            if buy_sig[i]: sig = 1
            elif sell_sig[i]: sig = -1
            
            if sig != 0:
                av = max(atr14[i], 1.5); sp = 25.0
                sl_pts = (av * 1.5 / PIP) + sp
                tp_pts = (av * 3.0 / PIP)       # Fixed R:R 1:2.0
                
                risk_amt = bal * risk_pct
                lot = max(0.01, min(round((risk_amt / (sl_pts * 0.01)) * 0.01, 2), 20.0))
                
                next_o = o[i+1]; half_sp = (sp * PIP) / 2.0
                if sig == 1: pos_dir = 1; pos_en = next_o + half_sp; pos_sl = pos_en - sl_pts * PIP; pos_tp = pos_en + tp_pts * PIP; pos_lot = lot
                else: pos_dir = -1; pos_en = next_o - half_sp; pos_sl = pos_en + sl_pts * PIP; pos_tp = pos_en - tp_pts * PIP; pos_lot = lot
                last_trade = i

    wins = [t for t in trades if t > 0]
    loss = [t for t in trades if t < 0]
    pf = sum(wins)/abs(sum(loss)) if loss and sum(loss)!=0 else 0
    wr = len(wins)/max(len(trades),1)*100
    pnl_pct = (bal - 1000.0) / 10.0
    
    return {
        'bal': bal, 'pnl_pct': pnl_pct, 'max_dd': max_dd,
        'trades': len(trades), 'wr': wr, 'pf': pf
    }

def main():
    df = pd.read_csv(DATA_PATH)
    df['dt'] = pd.to_datetime(df['datetime_str'])
    df['year'] = df['dt'].dt.year
    years = sorted(df['year'].unique())
    
    print("="*105)
    print("CHECKPOINT 12 MASTER — HYBRID QUANT SUPREMACY GAUNTLET (2010 - 2026)")
    print("Dataset: XAUUSD H1 (16.57 Years) | Fresh $1,000 Capital Every Year | Risk 2.5%")
    print("="*105)
    print(f"{'Year':<6} | {'Final $':<12} {'PnL %':<8} {'MaxDD %':<8} {'Trades':<6} {'WR %':<6} {'PF':<5}")
    print("-" * 105)
    
    tot_cash = 0; wins_yr = 0; tot_yr = 0
    for yr in years:
        df_yr = df[df['year'] == yr]
        r12 = run_checkpoint_v12_master(df_yr, risk_pct=0.025)
        if r12 is None: continue
        
        tot_yr += 1
        if r12['pnl_pct'] > 0: wins_yr += 1
        tot_cash += r12['bal']
        
        s12 = "✅" if r12['pnl_pct'] > 0 else "❌"
        print(f"{yr:<6} | ${r12['bal']:<11,.2f} {r12['pnl_pct']:>+6.1f}%  {r12['max_dd']:<8.1f} {r12['trades']:<6} {r12['wr']:<6.1f} {r12['pf']:<5.2f} {s12}")

    print("-" * 105)
    print(f"SUMMARY: Win Rate Years = {wins_yr} / {tot_yr} ({wins_yr/tot_yr*100:.1f}%) | Cumulative Cash = ${tot_cash:,.2f} USD")

if __name__ == '__main__':
    main()
