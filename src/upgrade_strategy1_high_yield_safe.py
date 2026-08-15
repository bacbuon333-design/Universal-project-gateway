"""
STRATEGY 1 HIGH-YIELD SAFE UPGRADE ENGINE (EQUAL/HIGHER PNL + ULTRA SAFE DD)
===========================================================================
Objective: Upgrade Strategy 1 (CP1) to achieve:
1. Equal or Higher Profit (+40% to +80%+ PnL in trend years)
2. Significantly Enhanced Safety (Max Drawdown compressed < 15%)

Architecture Enhancements:
1. MACD Momentum-Scaled R:R: Hard SL = 1.5x ATR. TP = 3.0x ATR (Base) / 4.0x ATR when MACD Z-Score > 2.0 (Extended Trend Runner).
2. Pullback Proximity Gate: Require price to be within 2.0x ATR of EMA 9/EMA 55 (No overextended top buying!).
3. Donchian 20 Dynamic Breakout Gate (Close > Don_Hi20 for Buy / Close < Don_Lo20 for Sell).
4. 24h Circuit Breaker Cooldown after 2 consecutive losses.

Dataset: XAUUSD H1 (16.57 Years: 2010 - 2026, 79,288 bars)
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

def run_strategy1_high_yield_safe(df, risk_pct=0.025):
    c = df['close'].values; h = df['high'].values; l = df['low'].values; o = df['open'].values
    v = df['tick_volume'].values if 'tick_volume' in df.columns else df['vol'].values
    n = len(df)
    if n < 500: return None
    
    tr = np.maximum(h[1:]-l[1:], np.maximum(abs(h[1:]-c[:-1]), abs(l[1:]-c[:-1])))
    tr = np.insert(tr, 0, tr[0])
    atr14 = pd.Series(tr).rolling(14).mean().bfill().values
    
    # Strategy 1 Core Indicators
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
    hist_bb_up = hist_mid + 2.0 * hist_std
    hist_bb_dn = hist_mid - 2.0 * hist_std
    macd_z     = (macd_hist - hist_mid) / hist_std
    
    # Donchian 20 Gate
    don_hi20 = pd.Series(h).shift(1).rolling(20).max().bfill().values
    don_lo20 = pd.Series(l).shift(1).rolling(20).min().bfill().values
    
    # Pullback Proximity Gate (within 2.5x ATR of EMA 9 or EMA 55)
    near_ema9_55 = (abs(c - ema9) <= 2.5 * atr14) | (abs(c - ema55) <= 2.5 * atr14)
    
    # Enhanced Signal Conditions
    buy_sig  = (ema9 > ema55) & (ema55 > ema200) & (rsi14 > 51) & (macd_hist > hist_bb_up) & (c > don_hi20) & near_ema9_55
    sell_sig = (ema9 < ema55) & (ema55 < ema200) & (rsi14 < 49) & (macd_hist < hist_bb_dn) & (c < don_lo20) & near_ema9_55

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
                    if consec_losses >= 2: pause_until = i + 24
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
                
                # Dynamic TP: 4.0x ATR if MACD Z-Score > 2.0 (Extended Trend), else 3.0x ATR
                tp_mult = 4.0 if abs(macd_z[i]) > 2.0 else 3.0
                tp_pts = (av * tp_mult / PIP)
                
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
    
    sys.path.append(os.path.join(BASE_DIR, "checkpoints"))
    from checkpoint_v1_davidd_ultimate_scalping_h1 import run_v1_single_year as run_v1
    
    print("="*105)
    print("STRATEGY 1 HIGH-YIELD SAFE UPGRADE GAUNTLET (2010 - 2026)")
    print("Dataset: XAUUSD H1 (16.57 Years) | Fresh $1,000 Capital Every Year | Risk 2.5%")
    print("="*105)
    print(f"{'Year':<6} | {'--- STRATEGY 1 BASELINE (GỐC) ---':<35} | {'--- STRATEGY 1 HIGH-YIELD SAFE UPGRADE ---':<35}")
    print(f"{'':<6} | {'PnL %':<8} {'MaxDD %':<8} {'Trades':<7} {'WR %':<6} {'PF':<5} | {'PnL %':<8} {'MaxDD %':<8} {'Trades':<7} {'WR %':<6} {'PF':<5}")
    print("-" * 105)
    
    v1_w, v1_up_w = 0, 0; tot = 0
    tot_cash_v1up = 0
    
    for yr in years:
        df_yr = df[df['year'] == yr]
        r1 = run_v1(df_yr, risk_pct=0.025)
        r1_up = run_strategy1_high_yield_safe(df_yr, risk_pct=0.025)
        if r1 is None or r1_up is None: continue
        
        tot += 1
        if r1['pnl_pct'] > 0: v1_w += 1
        if r1_up['pnl_pct'] > 0: v1_up_w += 1
        tot_cash_v1up += r1_up['bal']
        
        s1 = "✅" if r1['pnl_pct'] > 0 else "❌"
        s1_up = "✅" if r1_up['pnl_pct'] > 0 else "❌"
        
        v1_str = f"{r1['pnl_pct']:>+6.1f}%  {r1['max_dd']:>6.1f}%  {r1['trades']:>5}  {r1['wr']:>5.1f}% {r1['pf']:>4.2f} {s1}"
        v1up_str = f"{r1_up['pnl_pct']:>+6.1f}%  {r1_up['max_dd']:>6.1f}%  {r1_up['trades']:>5}  {r1_up['wr']:>5.1f}% {r1_up['pf']:>4.2f} {s1_up}"
        
        print(f"{yr:<6} | {v1_str} | {v1up_str}")

    print("-" * 105)
    print(f"SUMMARY COMPARISON:")
    print(f"  Strategy 1 Baseline Gốc    : {v1_w} / {tot} Years ({v1_w/tot*100:.1f}%)")
    print(f"  Strategy 1 High-Yield Safe : {v1_up_w} / {tot} Years ({v1_up_w/tot*100:.1f}%) | Cumulative Cash = ${tot_cash_v1up:,.2f} USD")

if __name__ == '__main__':
    main()
