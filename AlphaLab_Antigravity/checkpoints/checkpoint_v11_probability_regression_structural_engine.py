"""
CHECKPOINT V11 — PROBABILITY REGRESSION & STRUCTURAL SWING SL/TP ENGINE (R:R >= 2.0)
===================================================================================
Frozen Version: Checkpoint 11 (2026-07-31)

Mathematical Architecture:
1. Linear Regression Trend Channel & Gaussian Probability Bands (50 H1 Bars):
   - Linear Regression Line: y = a*x + b
   - Upper / Lower Bands: RegLine +/- 2.0 * Standard Error
   - Entry Condition: Price touches/pierces Lower Regression Band (-2.0σ) in Macro Bull Regime, or Upper Band (+2.0σ) in Macro Bear Regime.

2. Structural Swing Geometry SL & Liquidity Target TP (Guaranteed R:R >= 2.0):
   - Stop Loss (SL): Placed 0.5x ATR BELOW the 24-bar Swing Low (for Long) or ABOVE 24-bar Swing High (for Short) to give breathing room.
   - Take Profit (TP): Placed at the recent 48-bar Liquidity High/Low Target, ensuring TP >= 2.0 * SL distance (Hard Minimum R:R 1:2.0).

Dataset: XAUUSD H1 (2010 - 2026, 79,288 bars, 16.57 Years)
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

def calc_linear_regression_channel(c, window=50):
    n = len(c)
    reg_line = np.zeros(n)
    reg_std  = np.zeros(n)
    
    x = np.arange(window)
    x_mean = np.mean(x)
    x_var = np.sum((x - x_mean)**2)
    
    for i in range(window, n):
        y = c[i-window+1:i+1]
        y_mean = np.mean(y)
        slope = np.sum((x - x_mean) * (y - y_mean)) / x_var
        intercept = y_mean - slope * x_mean
        
        y_pred = slope * x + intercept
        res = y - y_pred
        std_err = np.std(res)
        
        reg_line[i] = y_pred[-1]
        reg_std[i]  = std_err
        
    return reg_line, reg_std

def run_checkpoint_v11_probability_engine(df, risk_pct=0.025):
    c = df['close'].values; h = df['high'].values; l = df['low'].values; o = df['open'].values
    n = len(df)
    if n < 500: return None
    
    tr = np.maximum(h[1:]-l[1:], np.maximum(abs(h[1:]-c[:-1]), abs(l[1:]-c[:-1])))
    tr = np.insert(tr, 0, tr[0])
    atr14 = pd.Series(tr).rolling(14).mean().bfill().values
    
    # Macro Trend Gate (EMA 200)
    ema200 = pd.Series(c).ewm(span=200, adjust=False).mean().values
    
    # 50-bar Linear Regression Channel & Gaussian Probability Bands
    reg_line, reg_std = calc_linear_regression_channel(c, window=50)
    reg_up = reg_line + 2.0 * reg_std
    reg_dn = reg_line - 2.0 * reg_std
    
    # Structural Swing Highs & Lows (24-bar and 48-bar)
    sw_lo24 = pd.Series(l).shift(1).rolling(24).min().bfill().values
    sw_hi24 = pd.Series(h).shift(1).rolling(24).max().bfill().values
    sw_hi48 = pd.Series(h).shift(1).rolling(48).max().bfill().values
    sw_lo48 = pd.Series(l).shift(1).rolling(48).min().bfill().values
    
    buy_sig  = np.zeros(n, dtype=bool)
    sell_sig = np.zeros(n, dtype=bool)
    
    for i in range(200, n):
        av = max(atr14[i], 1.5)
        lwick = min(o[i], c[i]) - l[i]
        uwick = h[i] - max(o[i], c[i])
        body  = abs(c[i] - o[i]) + 1e-9
        
        # Linear Regression Lower Band Reversal (-2.0σ) in Macro Bull Trend
        prob_buy = (c[i] <= reg_dn[i]) and (lwick >= 1.0 * body) and (c[i] > ema200[i] * 0.98)
        # Linear Regression Upper Band Reversal (+2.0σ) in Macro Bear Trend
        prob_sell = (c[i] >= reg_up[i]) and (uwick >= 1.0 * body) and (c[i] < ema200[i] * 1.02)
        
        if prob_buy: buy_sig[i] = True
        elif prob_sell: sell_sig[i] = True

    bal = 1000.0; pk = 1000.0; max_dd = 0.0
    trades = []
    last_trade = -9999; cooldown = 16
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
                pos_dir = 0
                
        if pos_dir == 0 and (i - last_trade >= cooldown) and bal > 0:
            sig = 0
            if buy_sig[i]: sig = 1
            elif sell_sig[i]: sig = -1
            
            if sig != 0:
                av = max(atr14[i], 1.5); sp = 25.0
                next_o = o[i+1]; half_sp = (sp * PIP) / 2.0
                
                if sig == 1:
                    pos_en = next_o + half_sp
                    # Structural SL: 0.5x ATR below 24-bar Swing Low
                    struct_sl_p = sw_lo24[i] - 0.5 * av
                    sl_dist = (pos_en - struct_sl_p)
                    sl_pts  = (sl_dist / PIP) + sp
                    
                    # Target TP: 48-bar Swing High Target (Minimum R:R 1:2.0)
                    target_tp_p = max(sw_hi48[i], pos_en + 2.0 * sl_dist)
                    tp_pts = (target_tp_p - pos_en) / PIP
                    
                    if tp_pts >= 2.0 * sl_pts and sl_pts >= 50.0:
                        risk_amt = bal * risk_pct
                        lot = max(0.01, min(round((risk_amt / (sl_pts * 0.01)) * 0.01, 2), 20.0))
                        pos_dir = 1; pos_sl = struct_sl_p - (sp * PIP); pos_tp = target_tp_p; pos_lot = lot
                        last_trade = i
                else:
                    pos_en = next_o - half_sp
                    # Structural SL: 0.5x ATR above 24-bar Swing High
                    struct_sl_p = sw_hi24[i] + 0.5 * av
                    sl_dist = (struct_sl_p - pos_en)
                    sl_pts  = (sl_dist / PIP) + sp
                    
                    target_tp_p = min(sw_lo48[i], pos_en - 2.0 * sl_dist)
                    tp_pts = (pos_en - target_tp_p) / PIP
                    
                    if tp_pts >= 2.0 * sl_pts and sl_pts >= 50.0:
                        risk_amt = bal * risk_pct
                        lot = max(0.01, min(round((risk_amt / (sl_pts * 0.01)) * 0.01, 2), 20.0))
                        pos_dir = -1; pos_sl = struct_sl_p + (sp * PIP); pos_tp = target_tp_p; pos_lot = lot
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
    print("CHECKPOINT 11 — PROBABILITY REGRESSION & STRUCTURAL SWING SL/TP GAUNTLET (2010 - 2026)")
    print("Dataset: XAUUSD H1 (16.57 Years) | Fresh $1,000 Capital Every Year | Risk 2.5%")
    print("="*95)
    print(f"{'Year':<6} | {'--- CP1 BASELINE (GỐC) ---':<35} | {'--- CP11 PROBABILITY STRUCTURAL ENGINE ---':<35}")
    print(f"{'':<6} | {'PnL %':<8} {'MaxDD %':<8} {'Trades':<7} {'WR %':<6} {'PF':<5} | {'PnL %':<8} {'MaxDD %':<8} {'Trades':<7} {'WR %':<6} {'PF':<5}")
    print("-" * 95)
    
    v1_w, v11_w = 0, 0; tot = 0
    for yr in years:
        df_yr = df[df['year'] == yr]
        r1 = run_v1(df_yr, risk_pct=0.025)
        r11 = run_checkpoint_v11_probability_engine(df_yr, risk_pct=0.025)
        if r1 is None or r11 is None: continue
        
        tot += 1
        if r1['pnl_pct'] > 0: v1_w += 1
        if r11['pnl_pct'] > 0: v11_w += 1
        
        s1 = "✅" if r1['pnl_pct'] > 0 else "❌"
        s11 = "✅" if r11['pnl_pct'] > 0 else "❌"
        
        v1_str = f"{r1['pnl_pct']:>+6.1f}%  {r1['max_dd']:>6.1f}%  {r1['trades']:>5}  {r1['wr']:>5.1f}% {r1['pf']:>4.2f} {s1}"
        v11_str = f"{r11['pnl_pct']:>+6.1f}%  {r11['max_dd']:>6.1f}%  {r11['trades']:>5}  {r11['wr']:>5.1f}% {r11['pf']:>4.2f} {s11}"
        
        print(f"{yr:<6} | {v1_str} | {v11_str}")

    print("-" * 95)
    print(f"SUMMARY PROFITABLE YEARS:")
    print(f"  Checkpoint 1 Baseline Gốc    : {v1_w} / {tot} Years ({v1_w/tot*100:.1f}%)")
    print(f"  Checkpoint 11 Structural Engine: {v11_w} / {tot} Years ({v11_w/tot*100:.1f}%)")

if __name__ == '__main__':
    main()
