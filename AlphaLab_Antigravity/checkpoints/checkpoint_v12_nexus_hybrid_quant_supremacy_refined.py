"""
CHECKPOINT V12 REFINED — ULTIMATE PRICE ACTION HYBRID QUANT ENGINE (ALAB_Nexus_v35_Refined)
=============================================================================================
Frozen Version: Checkpoint 12 Refined (2026-07-31)

Optimized Architecture:
1. Pillar 1: Macro Trend Guard (EMA 200 H1)
2. Pillar 2: Price Action Reaction Zone Pullback (Price touches/sweeps Donchian 20 Support / Resistance)
   - Smart Money Rejection Pinbar: Lower Wick >= 1.0x Body (Long) / Upper Wick >= 1.0x Body (Short)
3. Pillar 3: Tick Volume Z-Score Influx (vol_z >= 0.5)
4. Pillar 4: Fixed Asymmetric R:R (1:2.0 Target, Dynamic ATR Sizing)
5. Pillar 5: Circuit Breaker Cooldown (24h pause after 2 losses)

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

def run_checkpoint_v12_refined(df, risk_pct=0.025):
    c = df['close'].values; h = df['high'].values; l = df['low'].values; o = df['open'].values
    v = df['tick_volume'].values if 'tick_volume' in df.columns else df['vol'].values
    n = len(df)
    if n < 500: return None
    
    tr = np.maximum(h[1:]-l[1:], np.maximum(abs(h[1:]-c[:-1]), abs(l[1:]-c[:-1])))
    tr = np.insert(tr, 0, tr[0])
    atr14 = pd.Series(tr).rolling(14).mean().bfill().values
    
    # Pillar 1: Macro Guard (EMA 200 H1)
    ema200 = pd.Series(c).ewm(span=200, adjust=False).mean().values
    
    # Pillar 2: Donchian 20 Support/Resistance Zone
    don_hi20 = pd.Series(h).shift(1).rolling(20).max().bfill().values
    don_lo20 = pd.Series(l).shift(1).rolling(20).min().bfill().values
    
    # Pillar 3: Tick Volume Z-Score
    vol_mean = pd.Series(v).rolling(50).mean().bfill().values
    vol_std  = pd.Series(v).rolling(50).std().bfill().values + 1e-9
    vol_z    = (v - vol_mean) / vol_std
    
    buy_sig  = np.zeros(n, dtype=bool)
    sell_sig = np.zeros(n, dtype=bool)
    
    for i in range(200, n):
        av = max(atr14[i], 1.5)
        lwick = min(o[i], c[i]) - l[i]
        uwick = h[i] - max(o[i], c[i])
        body  = abs(c[i] - o[i]) + 1e-9
        
        macro_bull = c[i] > ema200[i]
        macro_bear = c[i] < ema200[i]
        
        # Reaction Zone Pullback & Rejection Pinbar
        near_don_lo = (c[i] - don_lo20[i]) <= 2.5 * av
        near_don_hi = (don_hi20[i] - c[i]) <= 2.5 * av
        
        pin_buy  = (lwick >= 1.0 * body) and (c[i] > o[i])
        pin_sell = (uwick >= 1.0 * body) and (c[i] < o[i])
        
        vol_ok = vol_z[i] >= 0.5
        
        if macro_bull and near_don_lo and pin_buy and vol_ok:
            buy_sig[i] = True
        elif macro_bear and near_don_hi and pin_sell and vol_ok:
            sell_sig[i] = True

    # Pillar 4 & 5: Dynamic Sizing & Circuit Breaker
    bal = 1000.0; pk = 1000.0; max_dd = 0.0
    trades = []
    last_trade = -9999; cooldown = 16
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
    print("CHECKPOINT 12 REFINED — ULTIMATE PRICE ACTION HYBRID QUANT ENGINE (2010 - 2026)")
    print("Dataset: XAUUSD H1 (16.57 Years) | Fresh $1,000 Capital Every Year | Risk 2.5%")
    print("="*105)
    print(f"{'Year':<6} | {'Final $':<12} {'PnL %':<8} {'MaxDD %':<8} {'Trades':<6} {'WR %':<6} {'PF':<5}")
    print("-" * 105)
    
    tot_cash = 0; wins_yr = 0; tot_yr = 0
    for yr in years:
        df_yr = df[df['year'] == yr]
        r12 = run_checkpoint_v12_refined(df_yr, risk_pct=0.025)
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
