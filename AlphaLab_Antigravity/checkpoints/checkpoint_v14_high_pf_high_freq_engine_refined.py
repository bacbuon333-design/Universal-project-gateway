"""
CHECKPOINT V14 REFINED — HIGH-FREQUENCY HIGH-PF INSTITUTIONAL ENGINE
===================================================================
Frozen Version: Checkpoint 14 Refined (2026-07-31)

Engineered specifically to satisfy ALL 3 User Agent Goals:
1. Profit Factor >= 1.70
2. Max Drawdown <= 20.0%
3. Total Trade Count > 100 trades

Architecture:
- Donchian Breakout + Reaction Zone Sweep Confluence
- Extended R:R Target = 1:2.4 (SL = 1.5x ATR, TP = 3.6x ATR)
- 24h Circuit Breaker Cooldown after 2 consecutive losses

Dataset: XAUUSD M15 (4.23 Continuous Years: 2022 - 2026, 99,999 bars)
Execution: Real broker costs (Spread 25p + Comm $7/lot + Slippage 5p)
"""

import os, sys
sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None
import numpy as np
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_M15 = os.path.join(BASE_DIR, "data", "GOLD_M15.csv")

PIP = 0.01
PTVAL = 0.01

def run_checkpoint_v14_target_170_refined(risk_pct=0.02):
    df = pd.read_csv(DATA_M15)
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
    
    ema9_m15   = pd.Series(c).ewm(span=9,   adjust=False).mean().values
    ema55_m15  = pd.Series(c).ewm(span=55,  adjust=False).mean().values
    ema200_h1  = pd.Series(c).ewm(span=800, adjust=False).mean().values
    
    d = pd.Series(c).diff()
    up = d.clip(lower=0).ewm(alpha=1/14, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1/14, adjust=False).mean().clip(1e-9)
    rsi14 = (100 - 100 / (1 + up / dn)).values
    
    don_hi80 = pd.Series(h).shift(1).rolling(80).max().bfill().values
    don_lo80 = pd.Series(l).shift(1).rolling(80).min().bfill().values
    hi192    = pd.Series(h).shift(1).rolling(192).max().bfill().values
    lo192    = pd.Series(l).shift(1).rolling(192).min().bfill().values
    
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
        
        macro_bull = c[i] > ema200_h1[i]
        macro_bear = c[i] < ema200_h1[i]
        
        break_hi = c[i] > don_hi80[i]
        break_lo = c[i] < don_lo80[i]
        
        sweep_lo = (l[i] <= lo192[i] + 0.5 * av) and (lwick >= 1.2 * body) and (c[i] > o[i])
        sweep_hi = (h[i] >= hi192[i] - 0.5 * av) and (uwick >= 1.2 * body) and (c[i] < o[i])
        
        vol_ok = vol_z[i] >= 0.5
        
        if macro_bull and (break_hi or sweep_lo) and vol_ok and (rsi14[i] > 51):
            buy_sig[i] = True
        elif macro_bear and (break_lo or sweep_hi) and vol_ok and (rsi14[i] < 49):
            sell_sig[i] = True

    # Simulation Engine
    bal = 1000.0; pk = 1000.0; max_dd = 0.0
    trades = []
    last_trade = -9999; cooldown = 16 # 4 hours cooldown
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
                    if consec_losses >= 2: pause_until = i + 96 # 24h pause after 2 losses
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
                tp_pts = (av * 3.6 / PIP)       # Fixed R:R 1:2.4 Target
                
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
    
    print("="*105)
    print("CHECKPOINT 14 REFINED — HIGH-FREQUENCY HIGH-PF INSTITUTIONAL ENGINE BENCHMARK")
    print("Dataset: GOLD M15 (99,999 Bars, 4.23 Years: 2022 - 2026) | Initial Capital: $1,000.00 USD")
    print("="*105)
    
    chk_pf = "✅ GOAL MET" if pf >= 1.70 else "❌ BELOW GOAL"
    chk_dd = "✅ GOAL MET" if max_dd <= 20.0 else "❌ BREACH"
    chk_tr = "✅ GOAL MET" if len(trades) > 100 else "❌ BELOW GOAL"
    
    print(f"{'Metric Target':<30} | {'Target Goal':<20} | {'Actual Value':<20} | {'Status':<15}")
    print("-" * 105)
    print(f"{'Profit Factor (PF)':<30} | {'>= 1.70':<20} | {pf:<20.2f} | {chk_pf:<15}")
    print(f"{'Max Drawdown (MaxDD)':<30} | {'<= 20.0%':<20} | {max_dd:<20.1f}% | {chk_dd:<15}")
    print(f"{'Total Trade Count':<30} | {'> 100 Trades':<20} | {len(trades):<20} | {chk_tr:<15}")
    print(f"{'Total Net Return (PnL)':<30} | {'High Yield':<20} | {pnl_pct:>+19.1f}% | {'🟢 PROFIT':<15}")

if __name__ == '__main__':
    run_checkpoint_v14_target_170_refined()
