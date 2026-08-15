"""
CHECKPOINT 5 CONTINUOUS COMPOUNDING BACKTEST (2010 - 2026)
==========================================================
Starting with $1,000 INITIAL CAPITAL in 2010 and letting CP5
(Key Structure Reaction Zone Sweep) compound continuously until July 2026.
Risk per trade: 2.5% dynamic equity.
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

def run_cp5_continuous(risk_pct=0.025):
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
    
    hi48 = pd.Series(h).shift(1).rolling(48).max().values
    lo48 = pd.Series(l).shift(1).rolling(48).min().values
    
    mom3m = np.zeros(n, dtype=bool)
    for i in range(1440, n):
        mom3m[i] = c[i] > c[i-1440]
        
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
    
    yearly_equity = {}
    curr_yr = df['year'].iloc[0]
    
    for i in range(50, n-1):
        yr_now = df['year'].iloc[i]
        if yr_now != curr_yr:
            yearly_equity[curr_yr] = bal
            curr_yr = yr_now
            
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
                
                risk_amt = bal * risk_pct
                lot = max(0.01, min(round(risk_amt / (sl_pts * 0.01) * 0.01, 2), 20.0))
                
                next_o = o[i+1]
                half_sp = (sp * PIP) / 2.0
                
                if sig == 1:
                    pos_dir = 1; pos_en = next_o + half_sp; pos_sl = pos_en - sl_pts * PIP; pos_tp = pos_en + tp_pts * PIP; pos_lot = lot
                else:
                    pos_dir = -1; pos_en = next_o - half_sp; pos_sl = pos_en + sl_pts * PIP; pos_tp = pos_en - tp_pts * PIP; pos_lot = lot
                last_trade = i

    yearly_equity[curr_yr] = bal
    wins = [t for t in trades if t > 0]
    loss = [t for t in trades if t < 0]
    pf = sum(wins)/abs(sum(loss)) if loss and sum(loss)!=0 else 0
    wr = len(wins)/max(len(trades),1)*100
    
    return bal, (bal-1000.0)/10.0, max_dd, len(trades), wr, pf, yearly_equity

bal5, pct5, dd5, n5, wr5, pf5, eq_hist = run_cp5_continuous(risk_pct=0.025)

print("="*85)
print("CHECKPOINT 5 (REACTION ZONE SWEEP) 16.5-YEAR CONTINUOUS COMPOUNDING")
print("Initial Capital (2010): 1000.00 USD (No additional deposits)")
print("="*85)
print(f"Final Balance (July 2026) : {round(bal5, 2)} USD")
print(f"Total Net Return          : {round(pct5, 2)} %")
print(f"Max Drawdown              : {round(dd5, 2)} %")
print(f"Total Trades              : {n5}")
print(f"Win Rate                  : {round(wr5, 2)} %")
print(f"Profit Factor             : {round(pf5, 2)}")

print("\n📈 YEAR-BY-YEAR COMPOUNDING BALANCE PROGRESSION:")
print("-" * 55)
for y, b in eq_hist.items():
    print("Year End", y, ":", round(b, 2), "USD")
