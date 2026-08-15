"""
THEORETICAL MAXIMUM ALPHA (ORACLE SWING LIMIT SIMULATION)
=========================================================
Dataset: XAUUSD M15 (02/05/2022 - 24/07/2026, 99,999 bars, 4.23 years)
Simulates an ideal swing trader catching all major swing lows to high (BUY)
and swing highs to low (SELL) with minimum swing threshold = 2.0x ATR.

Calculates the MAXIMUM THEORETICAL CAPITAL GROWTH achievable from $1,000.
Execution includes full broker fees ($0.37/0.01 lot) and 2.5% dynamic risk per trade.
"""

import os, sys
sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None
import numpy as np
import pandas as pd

BASE_DIR = r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05\AlphaLab_Antigravity"
DATA_PATH = os.path.join(BASE_DIR, "data", "GOLD_M15.csv")

PIP = 0.01
PTVAL = 0.01

def run_oracle_simulation(risk_pct=0.025):
    df = pd.read_csv(DATA_PATH)
    col = 'datetime_str' if 'datetime_str' in df.columns else df.columns[0]
    df['dt'] = pd.to_datetime(df[col])
    df.sort_values('dt', inplace=True)
    df.reset_index(drop=True, inplace=True)
    
    c = df['close'].values; h = df['high'].values; l = df['low'].values; o = df['open'].values
    dt = df['dt'].values; n = len(df)
    
    tr = np.maximum(h[1:]-l[1:], np.maximum(abs(h[1:]-c[:-1]), abs(l[1:]-c[:-1])))
    tr = np.insert(tr, 0, tr[0])
    atr14 = pd.Series(tr).rolling(14).mean().bfill().values
    
    # ZigZag Swing High / Low detection (2.0x ATR minimum reversal)
    pivot_dir = 0 # 1 = searching high, -1 = searching low
    last_p_val = c[0]; last_p_idx = 0
    swings = []
    
    for i in range(1, n):
        av = max(atr14[i], 1.5)
        thresh = 2.0 * av
        
        if pivot_dir == 0:
            if h[i] - last_p_val >= thresh: pivot_dir = 1; last_p_val = h[i]; last_p_idx = i
            elif last_p_val - l[i] >= thresh: pivot_dir = -1; last_p_val = l[i]; last_p_idx = i
        elif pivot_dir == 1: # Uptrend swing
            if h[i] > last_p_val:
                last_p_val = h[i]; last_p_idx = i
            elif last_p_val - l[i] >= thresh: # Reversal to Down
                swings.append({'type': 'HIGH', 'idx': last_p_idx, 'price': last_p_val})
                pivot_dir = -1; last_p_val = l[i]; last_p_idx = i
        elif pivot_dir == -1: # Downtrend swing
            if l[i] < last_p_val:
                last_p_val = l[i]; last_p_idx = i
            elif h[i] - last_p_val >= thresh: # Reversal to Up
                swings.append({'type': 'LOW', 'idx': last_p_idx, 'price': last_p_val})
                pivot_dir = 1; last_p_val = h[i]; last_p_idx = i

    df_swings = pd.DataFrame(swings)
    print(f"Total Ideal Swing Points Detected on M15 (4.23 Years): {len(df_swings)} swings")
    
    # Run perfect compounding on these swing trades
    bal = 1000.0; pk = 1000.0; max_dd = 0.0
    trades = []
    
    for k in range(len(swings)-1):
        s_curr = swings[k]
        s_next = swings[k+1]
        
        p_type = s_curr['type']
        en_price = s_curr['price']
        ex_price = s_next['price']
        idx_en = s_curr['idx']
        
        av = max(atr14[idx_en], 1.5)
        sp = 25.0
        sl_pts = (av * 1.5 / PIP) + sp
        
        if p_type == 'LOW': # BUY Swing
            pts = (ex_price - en_price) / PIP
            pos_dir = 1
        else: # SELL Swing
            pts = (en_price - ex_price) / PIP
            pos_dir = -1
            
        risk_amt = bal * risk_pct
        lot = max(0.01, min(round(risk_amt / (sl_pts * 0.01) * 0.01, 2), 50.0))
        
        gross = pts * PTVAL * (lot / 0.01)
        fee   = (lot / 0.01) * 0.37
        net   = gross - fee
        
        bal = max(0.0, bal + net)
        pk  = max(pk, bal)
        dd  = (pk - bal) / pk * 100.0 if pk > 0 else 0
        max_dd = max(max_dd, dd)
        trades.append(net)

    wins = [t for t in trades if t > 0]
    loss = [t for t in trades if t < 0]
    pf = sum(wins)/abs(sum(loss)) if loss and sum(loss)!=0 else 999.0
    wr = len(wins)/max(len(trades),1)*100
    
    return bal, (bal-1000.0)/10.0, max_dd, len(trades), wr, pf

bal, pct, dd, n_tr, wr, pf = run_oracle_simulation(risk_pct=0.025)

print("="*90)
print("THEORETICAL MAXIMUM ALPHA SIMULATION (ORACLE LIMIT ON M15)")
print("Dataset: XAUUSD M15 (02/05/2022 - 24/07/2026, 4.23 Years)")
print("Initial Capital: $1,000.00 USD (Risk: 2.5% Dynamic Equity per Swing)")
print("="*90)
print(f"Final Balance (July 2026) : ${bal:,.2f} USD")
print(f"Total Net Return          : {pct:+,.2f}%")
print(f"Max Drawdown              : {dd:.2f}%")
print(f"Total Swing Trades        : {n_tr:,}")
print(f"Win Rate                  : {wr:.2f}%")
print(f"Profit Factor             : {pf:.2f}")
