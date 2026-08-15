"""
100% FAIR CONTINUOUS COMPOUNDING GAUNTLET (2010 - 2026)
======================================================
Identical Conditions for ALL 5 Checkpoints:
- Initial Capital: $1,000.00 USD on Jan 4, 2010 (Zero extra deposits)
- Risk per Trade: Standardized 2.5% Dynamic Equity Risk for ALL
- Broker Costs: Spread 25 pips + Commission $7/lot + Slippage 5 pips ($0.37/0.01 lot)
- Dataset: XAUUSD H1 (2010 - 2026, 79,288 bars, 16.57 Years)
"""

import os, sys
sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None
import numpy as np
import pandas as pd

BASE_DIR = r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05\AlphaLab_Antigravity"
DATA_PATH = os.path.join(BASE_DIR, "data", "GOLD_H1_2010_2026.csv")

PIP = 0.01
PTVAL = 0.01

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

# Indicators
ema9   = pd.Series(c).ewm(span=9,   adjust=False).mean().values
ema55  = pd.Series(c).ewm(span=55,  adjust=False).mean().values
ema50  = pd.Series(c).ewm(span=50,  adjust=False).mean().values
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

def calc_adx_fast(h, l, c, period=14):
    tr_ = np.maximum(h[1:]-l[1:], np.maximum(abs(h[1:]-c[:-1]), abs(l[1:]-c[:-1])))
    tr_ = np.insert(tr_, 0, tr_[0])
    up_ = pd.Series(h).diff().values
    dn_ = -pd.Series(l).diff().values
    pdm = np.where((up_ > dn_) & (up_ > 0), up_, 0.0)
    ndm = np.where((dn_ > up_) & (dn_ > 0), dn_, 0.0)
    atr_ser = pd.Series(tr_).ewm(alpha=1/period, adjust=False).mean()
    pdi = 100 * pd.Series(pdm).ewm(alpha=1/period, adjust=False).mean() / atr_ser.replace(0, 1e-9)
    ndi = 100 * pd.Series(ndm).ewm(alpha=1/period, adjust=False).mean() / atr_ser.replace(0, 1e-9)
    dx = 100 * (pdi - ndi).abs() / (pdi + ndi).replace(0, 1e-9)
    return dx.ewm(alpha=1/period, adjust=False).mean().values

adx14 = calc_adx_fast(h, l, c, 14)

def run_checkpoint_runner(cp_id=1, risk_pct=0.025):
    buy_sig = np.zeros(n, dtype=bool)
    sell_sig = np.zeros(n, dtype=bool)
    sl_mult = 1.5; tp_mult = 3.0; cooldown = 12
    
    if cp_id == 1: # CP1 Baseline
        buy_sig  = (ema9 > ema55) & (ema55 > ema200) & (rsi > 51) & (macd_hist > hist_bb_up)
        sell_sig = (ema9 < ema55) & (ema55 < ema200) & (rsi < 49) & (macd_hist < hist_bb_dn)
        sl_mult = 1.5; tp_mult = 3.0; cooldown = 12
        
    elif cp_id == 2: # CP2 Upgraded
        buy_sig  = (ema9 > ema55) & (ema55 > ema200) & (rsi > 51) & (macd_hist > hist_bb_up) & (adx14 > 20) & session_ok
        sell_sig = (ema9 < ema55) & (ema55 < ema200) & (rsi < 49) & (macd_hist < hist_bb_dn) & (adx14 > 20) & session_ok
        sl_mult = 2.0; tp_mult = 4.0; cooldown = 12
        
    elif cp_id == 3: # CP3 Prop Firm VaR
        buy_sig  = (ema9 > ema55) & (ema55 > ema200) & (rsi > 51) & (macd_hist > hist_bb_up) & (adx14 > 20) & session_ok
        sell_sig = (ema9 < ema55) & (ema55 < ema200) & (rsi < 49) & (macd_hist < hist_bb_dn) & (adx14 > 20) & session_ok
        sl_mult = 2.0; tp_mult = 4.0; cooldown = 12
        
    elif cp_id == 4: # CP4 Corrected Exact Specs
        buy_sig  = (ema9 > ema55) & (ema55 > ema200) & (rsi > 51) & (macd_hist > hist_bb_up) & session_ok
        sell_sig = (ema9 < ema55) & (ema55 < ema200) & (rsi < 49) & (macd_hist < hist_bb_dn) & session_ok
        sl_mult = 2.0; tp_mult = 4.0; cooldown = 12
        
    elif cp_id == 5: # CP5 Reaction Zone Sweep
        hi48 = pd.Series(h).shift(1).rolling(48).max().values
        lo48 = pd.Series(l).shift(1).rolling(48).min().values
        mom3m = np.zeros(n, dtype=bool)
        for i in range(1440, n): mom3m[i] = c[i] > c[i-1440]
        
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
            
            if macro_bull and (sweep_lo or (pin_lo and l[i] <= ema50[i])): buy_sig[i] = True
            elif macro_bear and (sweep_hi or (pin_hi and h[i] >= ema50[i])): sell_sig[i] = True
        sl_mult = 2.0; tp_mult = 4.5; cooldown = 24

    bal = 1000.0; pk = 1000.0; max_dd = 0.0
    trades = []
    last_trade = -9999
    pos_dir = 0; pos_en = 0.0; pos_sl = 0.0; pos_tp = 0.0; pos_lot = 0.0
    
    # Monthly VaR tracker for CP3
    curr_month = -1; month_start_bal = 1000.0; month_halted = False
    
    for i in range(250, n-1):
        if cp_id == 3: # Check monthly VaR cap 6.5% for CP3
            m_now = pd.Timestamp(dt[i]).month
            if m_now != curr_month:
                curr_month = m_now
                month_start_bal = bal
                month_halted = False
            if month_start_bal > 0 and (month_start_bal - bal) / month_start_bal >= 0.065:
                month_halted = True
            if month_halted:
                if pos_dir != 0: pass # manage open position
                else: continue # do not open new position
                
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
                sl_pts = (av * sl_mult / PIP) + sp
                tp_pts = (av * tp_mult / PIP)
                
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
    
    return bal, (bal-1000.0)/10.0, max_dd, len(trades), wr, pf

print("="*95)
print("100% FAIR CONTINUOUS COMPOUNDING GAUNTLET (2010 - 2026)")
print("Initial Capital: $1,000.00 USD | Standardized Risk: 2.5% Dynamic Equity per Trade")
print("="*95)
print(f"{'Checkpoint Model':<35} | {'Final Balance':<15} | {'Net Return %':<12} | {'MaxDD %':<9} | {'Trades':<7} {'PF':<5}")
print("-" * 95)

names = {
    1: "CP1 Baseline (Old Breakout Chase)",
    2: "CP2 Upgraded (ADX > 20 + Session)",
    3: "CP3 Prop Firm (ADX + VaR 6.5%)",
    4: "CP4 Corrected Exact Specs",
    5: "CP5 Reaction Zone (Vùng Phản Ứng)"
}

for cp in [1, 2, 3, 4, 5]:
    b, p, d, n_tr, wr, pf = run_checkpoint_runner(cp, risk_pct=0.025)
    print(f"{names[cp]:<35} | ${b:<14,.2f} | {p:>+10.2f}%   | {d:<8.1f}% | {n_tr:<6} {pf:<5.2f}")

