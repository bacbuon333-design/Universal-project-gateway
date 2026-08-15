"""
CHECKPOINT V7 REFINED — FIXED 1:2 RR + MOMENTUM BREAKOUT CONFIRMATION
=====================================================================
Discovered Truth: Trailing Stops DESTROY CP1 by cutting trend runners short.
Refined Strategy:
1. Zero Trailing Interference (Keep Fixed 1:2 R:R with 1.5x ATR SL / 3.0x ATR TP).
2. Donchian Channel Breakout Gate: Enter ONLY when price breaks above 20-bar High (Long) or below 20-bar Low (Short).
3. Consecutive Loss Cooldown: Pauses 24h after 3 consecutive losses to avoid range chop burn.
"""

import os, sys
sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None
import numpy as np
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(BASE_DIR, "data", "GOLD_H1_2010_2026.csv")

PIP = 0.01
PTVAL = 0.01

def run_v7_refined(df, risk_pct=0.03):
    c = df['close'].values; h = df['high'].values; l = df['low'].values; o = df['open'].values
    n = len(df)
    if n < 300: return None
    
    tr = np.maximum(h[1:]-l[1:], np.maximum(abs(h[1:]-c[:-1]), abs(l[1:]-c[:-1])))
    tr = np.insert(tr, 0, tr[0])
    atr14 = pd.Series(tr).rolling(14).mean().bfill().values
    
    ema9   = pd.Series(c).ewm(span=9,   adjust=False).mean().values
    ema55  = pd.Series(c).ewm(span=55,  adjust=False).mean().values
    ema200 = pd.Series(c).ewm(span=200, adjust=False).mean().values
    
    d = pd.Series(c).diff()
    up = d.clip(lower=0).ewm(alpha=1/14, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1/14, adjust=False).mean().clip(1e-9)
    rsi = (100 - 100 / (1 + up / dn)).values
    
    ema12 = pd.Series(c).ewm(span=12, adjust=False).mean().values
    ema26 = pd.Series(c).ewm(span=26, adjust=False).mean().values
    macd_line = ema12 - ema26
    signal_line = pd.Series(macd_line).ewm(span=9, adjust=False).mean().values
    macd_hist = macd_line - signal_line
    
    hist_mid = pd.Series(macd_hist).rolling(20).mean().bfill().values
    hist_std = pd.Series(macd_hist).rolling(20).std().bfill().values
    hist_bb_up = hist_mid + 2.0 * hist_std
    hist_bb_dn = hist_mid - 2.0 * hist_std
    
    # 20-bar Donchian High / Low bounds (shift=1)
    don_hi20 = pd.Series(h).shift(1).rolling(20).max().values
    don_lo20 = pd.Series(l).shift(1).rolling(20).min().values
    
    # CP1 Core + Donchian Breakout Confirmation
    buy_sig  = (ema9 > ema55) & (ema55 > ema200) & (rsi > 51) & (macd_hist > hist_bb_up) & (c > don_hi20)
    sell_sig = (ema9 < ema55) & (ema55 < ema200) & (rsi < 49) & (macd_hist < hist_bb_dn) & (c < don_lo20)
    
    bal = 1000.0; pk = 1000.0; max_dd = 0.0
    trades = []
    last_trade = -9999
    cooldown = 12
    consec_losses = 0
    pause_until = 0
    
    pos_dir = 0; pos_en = 0.0; pos_sl = 0.0; pos_tp = 0.0; pos_lot = 0.0
    
    for i in range(250, n-1):
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
                    if consec_losses >= 3: pause_until = i + 24 # 24h pause after 3 losses
                else:
                    consec_losses = 0
                pos_dir = 0
                
        if pos_dir == 0 and (i - last_trade >= cooldown) and (i >= pause_until) and bal > 0:
            sig = 0
            if buy_sig[i]: sig = 1
            elif sell_sig[i]: sig = -1
            
            if sig != 0:
                av = max(atr14[i], 1.5)
                sp = 25.0
                sl_pts = (av * 1.5 / PIP) + sp
                tp_pts = (av * 3.0 / PIP) # Fixed 1:2 R:R (Zero Trailing!)
                
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
        'trades': len(trades), 'wr': wr, 'pf': pf
    }

def main():
    df = pd.read_csv(DATA_PATH)
    df['dt'] = pd.to_datetime(df['datetime_str'])
    df['year'] = df['dt'].dt.year
    years = sorted(df['year'].unique())
    
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from checkpoint_v1_davidd_ultimate_scalping_h1 import run_v1_single_year as run_v1
    
    print("="*95)
    print("CHECKPOINT 7 REFINED — FIXED 1:2 RR + DONCHIAN MOMENTUM CONFIRMATION (2010 - 2026)")
    print("Dataset: XAUUSD H1 (16.57 Years) | Fresh $1,000 Capital Every Year")
    print("="*95)
    print(f"{'Year':<6} | {'--- CP1 BASELINE (OLD GỐC) ---':<35} | {'--- CP7 REFINED (BẢN TỐI ƯU MỚI) ---':<35}")
    print(f"{'':<6} | {'PnL %':<8} {'MaxDD %':<8} {'Trades':<7} {'WR %':<6} {'PF':<5} | {'PnL %':<8} {'MaxDD %':<8} {'Trades':<7} {'WR %':<6} {'PF':<5}")
    print("-" * 95)
    
    v1_w, v7_w = 0, 0; tot = 0
    for yr in years:
        df_yr = df[df['year'] == yr]
        r1 = run_v1(df_yr, risk_pct=0.03)
        r7 = run_v7_refined(df_yr, risk_pct=0.03)
        if r1 is None or r7 is None: continue
        
        tot += 1
        if r1['pnl_pct'] > 0: v1_w += 1
        if r7['pnl_pct'] > 0: v7_w += 1
        
        s1 = "✅" if r1['pnl_pct'] > 0 else "❌"
        s7 = "✅" if r7['pnl_pct'] > 0 else "❌"
        
        v1_str = f"{r1['pnl_pct']:>+6.1f}%  {r1['max_dd']:>6.1f}%  {r1['trades']:>5}  {r1['wr']:>5.1f}% {r1['pf']:>4.2f} {s1}"
        v7_str = f"{r7['pnl_pct']:>+6.1f}%  {r7['max_dd']:>6.1f}%  {r7['trades']:>5}  {r7['wr']:>5.1f}% {r7['pf']:>4.2f} {s7}"
        
        print(f"{yr:<6} | {v1_str} | {v7_str}")

    print("-" * 95)
    print(f"SUMMARY PROFITABLE YEARS:")
    print(f"  Checkpoint 1 Baseline Gốc : {v1_w} / {tot} Years ({v1_w/tot*100:.1f}%)")
    print(f"  Checkpoint 7 Refined Mới   : {v7_w} / {tot} Years ({v7_w/tot*100:.1f}%)")

if __name__ == '__main__':
    main()
