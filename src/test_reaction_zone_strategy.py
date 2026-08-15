"""
KEY STRUCTURE REACTION ZONE STRATEGY (CAUSAL LIQUIDITY SWEEP)
=============================================================
Tests the Price Reaction Zone strategy (48-Bar Structure Sweep + Rejection Wick):
- Long: Price touches or sweeps near 48-Bar Low in Macro Bull + Rejection Wick at Support
- Short: Price touches or sweeps near 48-Bar High in Macro Bear + Rejection Wick at Resistance
- Entry: Fade the reaction zone (Buy the dip at support, Sell the rally at resistance)
- Risk: SL = 2.0x ATR, TP = 4.5x ATR (R:R = 1:2.25), 2.5% risk

Dataset: XAUUSD H1 (2010 - 2026, 79,288 bars, 16.57 years)
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
COMM_PER_001 = 0.07

def run_reaction_zone_strategy():
    df = pd.read_csv(DATA_PATH)
    df['dt'] = pd.to_datetime(df['datetime_str'])
    df['year'] = df['dt'].dt.year
    df.sort_values('dt', inplace=True)
    df.reset_index(drop=True, inplace=True)
    
    c = df['close'].values; h = df['high'].values; l = df['low'].values; o = df['open'].values
    dt = df['dt'].values; n = len(df)
    
    tr = np.maximum(h[1:]-l[1:], np.maximum(abs(h[1:]-c[:-1]), abs(l[1:]-c[:-1])))
    tr = np.insert(tr, 0, tr[0])
    atr14 = pd.Series(tr).rolling(14).mean().bfill().values
    
    ema50  = pd.Series(c).ewm(span=50,  adjust=False).mean().values
    ema200 = pd.Series(c).ewm(span=200, adjust=False).mean().values
    
    # 48-bar structure highs & lows (shift=1, zero future leak)
    hi48 = pd.Series(h).shift(1).rolling(48).max().values
    lo48 = pd.Series(l).shift(1).rolling(48).min().values
    
    # 3-month momentum
    mom3m = np.zeros(n, dtype=bool)
    for i in range(1440, n):
        mom3m[i] = c[i] > c[i-1440]
        
    buy_sig  = np.zeros(n, dtype=bool)
    sell_sig = np.zeros(n, dtype=bool)
    
    for i in range(1440, n):
        av = max(atr14[i], 1.5)
        lwick = min(o[i], c[i]) - l[i]
        uwick = h[i] - max(o[i], c[i])
        body  = abs(c[i] - o[i]) + 1e-9
        
        macro_bull = mom3m[i] and c[i] > ema200[i]
        macro_bear = (not mom3m[i]) and c[i] < ema200[i]
        
        # Long Reaction Zone: Price near/below 48-bar low OR Rejection Wick at EMA50
        sweep_lo = l[i] <= lo48[i] + 0.5 * av
        pin_lo   = lwick >= 1.5 * body
        
        # Short Reaction Zone: Price near/above 48-bar high OR Rejection Wick at EMA50
        sweep_hi = h[i] >= hi48[i] - 0.5 * av
        pin_hi   = uwick >= 1.5 * body
        
        if macro_bull and (sweep_lo or (pin_lo and l[i] <= ema50[i])):
            buy_sig[i] = True
        elif macro_bear and (sweep_hi or (pin_hi and h[i] >= ema50[i])):
            sell_sig[i] = True

    years = sorted(df['year'].unique())
    
    print("="*95)
    print("KEY STRUCTURE REACTION ZONE STRATEGY (2010 - 2026)")
    print("Dataset: XAUUSD H1 (16.57 Years) | Fresh $1,000 Capital Every Year")
    print("="*95)
    print(f"{'Year':<6} {'Start $':<8} {'End $':<10} {'PnL %':<9} {'MaxDD %':<8} {'Trades':<7} {'WinRate %':<10} {'PF':<6}")
    print("-" * 95)
    
    total_wins = 0; total_years = 0
    
    for yr in years:
        sub = df[df['year'] == yr]
        idx_sub = sub.index.values
        if len(idx_sub) < 100: continue
        
        bal = 1000.0; pk = 1000.0; max_dd = 0.0
        trades = []
        last_trade = -9999
        cooldown = 24 # 24h cooldown between trades
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
                    bal   = max(0.0, bal + net)
                    pk    = max(pk, bal)
                    dd    = (pk - bal) / pk * 100.0 if pk > 0 else 0
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
                    
                    risk_amt = bal * 0.025 # 2.5% risk
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
        
        total_years += 1
        if pnl_pct > 0: total_wins += 1
        
        status = "✅" if pnl_pct > 0 else "❌"
        print(f"{yr:<6} ${1000:<7.0f} ${bal:<9.2f} {pnl_pct:>+7.1f}%  {max_dd:<8.1f}  {len(trades):<6} {wr:<8.1f}%  {pf:<5.2f} {status}")

    print("-" * 95)
    print(f"REACTION ZONE STRATEGY SUMMARY: {total_wins} / {total_years} Profitable Years ({total_wins/total_years*100:.1f}%)")

if __name__ == '__main__':
    run_reaction_zone_strategy()
