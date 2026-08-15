"""
16.5-YEAR CONTINUOUS COMPOUNDING BACKTEST (2010 - 2026)
======================================================
Starting with $1,000 INITIAL CAPITAL in 2010 and letting it compound
continuously over 16.57 Years until July 2026 for ALL 4 CHECKPOINTS.
"""
import os, sys
sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None
import numpy as np
import pandas as pd

BASE_DIR = r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05\AlphaLab_Antigravity"
sys.path.append(os.path.join(BASE_DIR, "checkpoints"))

from checkpoint_v1_davidd_ultimate_scalping_h1 import PIP, PTVAL, COMM_PER_001
from checkpoint_v2_ultimate_scalping_upgraded import calc_adx
from checkpoint_v4_corrected_daviddtech_specs import run_checkpoint_v4_corrected

DATA_PATH = os.path.join(BASE_DIR, "data", "GOLD_H1_2010_2026.csv")
df = pd.read_csv(DATA_PATH)
df['dt'] = pd.to_datetime(df['datetime_str'])
df.sort_values('dt', inplace=True)
df.reset_index(drop=True, inplace=True)

c = df['close'].values
h = df['high'].values
l = df['low'].values
o = df['open'].values
dt = df['dt'].values
n = len(df)

tr = np.maximum(h[1:]-l[1:], np.maximum(abs(h[1:]-c[:-1]), abs(l[1:]-c[:-1])))
tr = np.insert(tr, 0, tr[0])
atr14 = pd.Series(tr).rolling(14).mean().bfill().values

# Checkpoint 4 Continuous Compounder Function
def run_cp4_continuous(risk_pct=0.025):
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
    
    hours = pd.Series(dt).dt.hour.values
    session_ok = (hours >= 12) & (hours <= 18)
    
    buy_sig  = (ema9 > ema55) & (ema55 > ema200) & (rsi > 51) & (macd_hist > hist_bb_up) & session_ok
    sell_sig = (ema9 < ema55) & (ema55 < ema200) & (rsi < 49) & (macd_hist < hist_bb_dn) & session_ok
    
    bal = 1000.0; pk = 1000.0; max_dd = 0.0
    trades = []
    last_trade = -9999
    cooldown = 12
    
    pos_dir = 0; pos_en = 0.0; pos_sl = 0.0; pos_tp = 0.0; pos_lot = 0.0
    
    for i in range(250, n-1):
        if pos_dir != 0:
            done = False
            ep = c[i]
            
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
                av = max(atr14[i], 1.5)
                sp = 25.0
                sl_pts = (av * 2.0 / PIP) + sp
                tp_pts = (av * 4.0 / PIP)
                
                risk_amt = bal * risk_pct
                lot = max(0.01, min(round(risk_amt / (sl_pts * 0.01) * 0.01, 2), 20.0))
                
                next_o = o[i+1]
                half_sp = (sp * PIP) / 2.0
                
                if sig == 1:
                    pos_dir = 1
                    pos_en  = next_o + half_sp
                    pos_sl  = pos_en - sl_pts * PIP
                    pos_tp  = pos_en + tp_pts * PIP
                    pos_lot = lot
                else:
                    pos_dir = -1
                    pos_en  = next_o - half_sp
                    pos_sl  = pos_en + sl_pts * PIP
                    pos_tp  = pos_en - tp_pts * PIP
                    pos_lot = lot
                last_trade = i

    wins = [t for t in trades if t > 0]
    loss = [t for t in trades if t < 0]
    pf = sum(wins)/abs(sum(loss)) if loss and sum(loss)!=0 else 0
    wr = len(wins)/max(len(trades),1)*100
    
    return bal, (bal-1000.0)/10.0, max_dd, len(trades), wr, pf

# Run CP4 Continuous compounding test
bal4, pct4, dd4, n4, wr4, pf4 = run_cp4_continuous(risk_pct=0.025)

print("="*90)
print("CHECKPOINT 4 CONTINUOUS 16.5-YEAR COMPOUNDING RESULT (2010 - 2026)")
print("Initial Capital: $1,000.00 (No additional deposits)")
print("="*90)
print(f"Final Balance   : ${bal4:,.2f} USD")
print(f"Total Net Return: {pct4:+,.2f}%")
print(f"Max Drawdown    : {dd4:.2f}%")
print(f"Total Trades    : {n4:,}")
print(f"Win Rate        : {wr4:.2f}%")
print(f"Profit Factor   : {pf4:.2f}")
