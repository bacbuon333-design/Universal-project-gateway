"""
1-YEAR REAL TICK-LEVEL SIMULATION GAUNTLET
===========================================
Simulates intra-bar price path (Open -> High/Low -> Close) with real spread & slippage
over 1 Full Year (2024 - 2025 and 2025 - 2026) for:
1. Davidd Anthony - Ultimate Scalping (M15)
2. Davidd Anthony - Ultimate Scalping (H1)
3. Davidd Anthony - Triple SuperTrend & Volume (H1)
4. Quant Structural Sweep & Cost Dilution (H1)
"""

import os, sys
sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None
import numpy as np
import pandas as pd

BASE_DIR = r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05\AlphaLab_Antigravity"
H1_PATH  = os.path.join(BASE_DIR, "data", "GOLD_H1_2010_2026.csv")
M15_PATH = os.path.join(BASE_DIR, "data", "GOLD_M15.csv")

PIP = 0.01
PTVAL = 0.01
COMM = 0.07

def run_tick_sim_1year(df, strat_type="ultimate_scalping", timeframe="H1", start_date="2024-05-01", end_date="2025-05-01"):
    # Filter 1-year range
    mask = (df['datetime_str'] >= start_date) & (df['datetime_str'] < end_date)
    sub = df[mask].copy()
    if len(sub) == 0:
        return 0, 0, 0, 0, 0, 0
        
    sub.reset_index(drop=True, inplace=True)
    c = sub['close'].values
    h = sub['high'].values
    l = sub['low'].values
    o = sub['open'].values
    v = sub['tick_volume'].values
    n = len(sub)
    
    # ATR 14
    tr = np.maximum(h[1:]-l[1:], np.maximum(abs(h[1:]-c[:-1]), abs(l[1:]-c[:-1])))
    tr = np.insert(tr, 0, tr[0])
    atr14 = pd.Series(tr).rolling(14).mean().bfill().values
    
    # Strategy signals
    buy_sig = np.zeros(n, dtype=bool)
    sell_sig = np.zeros(n, dtype=bool)
    
    if strat_type == "ultimate_scalping":
        ema9   = pd.Series(c).ewm(span=9,   adjust=False).mean().values
        ema55  = pd.Series(c).ewm(span=55,  adjust=False).mean().values
        ema200 = pd.Series(c).ewm(span=200, adjust=False).mean().values
        
        # RSI 14
        d = pd.Series(c).diff()
        up = d.clip(lower=0).ewm(alpha=1/14, adjust=False).mean()
        dn = (-d.clip(upper=0)).ewm(alpha=1/14, adjust=False).mean().clip(1e-9)
        rsi = (100 - 100 / (1 + up / dn)).values
        
        # MACD (12, 26, 9)
        ema12 = pd.Series(c).ewm(span=12, adjust=False).mean().values
        ema26 = pd.Series(c).ewm(span=26, adjust=False).mean().values
        macd_line = ema12 - ema26
        signal_line = pd.Series(macd_line).ewm(span=9, adjust=False).mean().values
        macd_hist = macd_line - signal_line
        
        # Bollinger Bands on MACD Histogram (20, 2.0)
        hist_mid = pd.Series(macd_hist).rolling(20).mean().bfill().values
        hist_std = pd.Series(macd_hist).rolling(20).std().bfill().values
        hist_bb_up = hist_mid + 2.0 * hist_std
        hist_bb_dn = hist_mid - 2.0 * hist_std
        
        buy_sig  = (ema9 > ema55) & (ema55 > ema200) & (rsi > 51) & (macd_hist > hist_bb_up)
        sell_sig = (ema9 < ema55) & (ema55 < ema200) & (rsi < 49) & (macd_hist < hist_bb_dn)
        sl_mult = 1.5; rr = 2.0; cooldown = 12
        
    elif strat_type == "triple_supertrend":
        ema200 = pd.Series(c).ewm(span=200, adjust=False).mean().values
        d = pd.Series(c).diff()
        up = d.clip(lower=0).ewm(alpha=1/14, adjust=False).mean()
        dn = (-d.clip(upper=0)).ewm(alpha=1/14, adjust=False).mean().clip(1e-9)
        rsi = (100 - 100 / (1 + up / dn)).values
        vol_sma = pd.Series(v).rolling(20).mean().bfill().values
        
        def calc_st(atr_p, mult):
            atr_v = pd.Series(tr).rolling(atr_p).mean().bfill().values
            dir_ = np.ones(n, dtype=int)
            up_b = (h + l) / 2 + mult * atr_v
            dn_b = (h + l) / 2 - mult * atr_v
            for i in range(1, n):
                if c[i-1] > up_b[i-1]: up_b[i] = min(up_b[i], up_b[i-1])
                if c[i-1] < dn_b[i-1]: dn_b[i] = max(dn_b[i], dn_b[i-1])
                if dir_[i-1] == 1:
                    dir_[i] = -1 if c[i] < dn_b[i] else 1
                else:
                    dir_[i] = 1 if c[i] > up_b[i] else -1
            return dir_
            
        st1 = calc_st(10, 1.0)
        st2 = calc_st(11, 2.0)
        st3 = calc_st(12, 3.0)
        st_sum = (st1 == 1).astype(int) + (st2 == 1).astype(int) + (st3 == 1).astype(int)
        
        buy_sig  = (c > ema200) & (st_sum >= 2) & (rsi < 45) & (v > vol_sma)
        sell_sig = (c < ema200) & (st_sum <= 1) & (rsi > 55) & (v > vol_sma)
        sl_mult = 2.0; rr = 2.5; cooldown = 16

    elif strat_type == "quant_structural_sweep":
        ema200 = pd.Series(c).ewm(span=200, adjust=False).mean().values
        ema50  = pd.Series(c).ewm(span=50,  adjust=False).mean().values
        hi48 = pd.Series(h).shift(1).rolling(48).max().values
        lo48 = pd.Series(l).shift(1).rolling(48).min().values
        
        for i in range(48, n):
            av = max(atr14[i], 1.5)
            lwick = min(o[i], c[i]) - l[i]
            uwick = h[i] - max(o[i], c[i])
            body  = abs(c[i] - o[i]) + 1e-9
            
            macro_bull = c[i] > ema200[i]
            macro_bear = c[i] < ema200[i]
            
            sweep_lo = l[i] <= lo48[i] + 0.5 * av
            pin_lo   = lwick >= 1.5 * body
            sweep_hi = h[i] >= hi48[i] - 0.5 * av
            pin_hi   = uwick >= 1.5 * body
            
            if macro_bull and (sweep_lo or (pin_lo and l[i] <= ema50[i])):
                buy_sig[i] = True
            elif macro_bear and (sweep_hi or (pin_hi and h[i] >= ema50[i])):
                sell_sig[i] = True
                
        sl_mult = 2.0; rr = 4.0; cooldown = 36

    # INTRA-BAR TICK SIMULATION (Open -> High/Low -> Close)
    bal = 1000.0; pk = 1000.0; max_dd = 0.0
    trades = []
    last_trade = -9999
    
    pos_dir = 0; pos_en = 0.0; pos_sl = 0.0; pos_tp = 0.0; pos_lot = 0.0
    
    for i in range(50, n-1):
        if pos_dir != 0:
            done = False
            ep = c[i]
            
            # Simulate tick order of execution within bar i:
            # If bull candle (Close >= Open): Open -> Low -> High -> Close
            # If bear candle (Close < Open) : Open -> High -> Low -> Close
            is_bull = c[i] >= o[i]
            
            if pos_dir == 1: # LONG
                if is_bull:
                    # Low first
                    if l[i] <= pos_sl: ep = pos_sl - 5.0 * PIP; done = True
                    elif h[i] >= pos_tp: ep = pos_tp; done = True
                else:
                    # High first
                    if h[i] >= pos_tp: ep = pos_tp; done = True
                    elif l[i] <= pos_sl: ep = pos_sl - 5.0 * PIP; done = True
            else: # SHORT
                if is_bull:
                    # Low first
                    if l[i] <= pos_tp: ep = pos_tp; done = True
                    elif h[i] >= pos_sl: ep = pos_sl + 5.0 * PIP; done = True
                else:
                    # High first
                    if h[i] >= pos_sl: ep = pos_sl + 5.0 * PIP; done = True
                    elif l[i] <= pos_tp: ep = pos_tp; done = True
                    
            if done:
                pts = (ep - pos_en)/PIP if pos_dir==1 else (pos_en - ep)/PIP
                net = pts * PTVAL * (pos_lot / 0.01) - (pos_lot / 0.01) * COMM
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
                sp = 25.0 # 25 pips spread
                sl_pts = (av * sl_mult / PIP) + sp
                
                risk_amt = bal * 0.03 # 3% risk
                lot = max(0.01, min(round(risk_amt / (sl_pts * 0.01) * 0.01, 2), 20.0))
                
                next_o = o[i+1]
                half_sp = (sp * PIP) / 2.0
                
                if sig == 1:
                    pos_dir = 1
                    pos_en  = next_o + half_sp
                    pos_sl  = pos_en - sl_pts * PIP
                    pos_tp  = pos_en + sl_pts * rr * PIP
                    pos_lot = lot
                else:
                    pos_dir = -1
                    pos_en  = next_o - half_sp
                    pos_sl  = pos_en + sl_pts * PIP
                    pos_tp  = pos_en - sl_pts * rr * PIP
                    pos_lot = lot
                last_trade = i

    wins = [t for t in trades if t > 0]
    loss = [t for t in trades if t < 0]
    pf = sum(wins)/abs(sum(loss)) if loss and sum(loss)!=0 else 0
    wr = len(wins)/max(len(trades),1)*100
    
    return bal, (bal-1000)/10.0, max_dd, len(trades), wr, pf

print("="*75)
print("1-YEAR REAL TICK-PRECISION SIMULATION GAUNTLET")
print("="*75)

periods = [
    ("2024-05-01 to 2025-05-01", "2024-05-01", "2025-05-01"),
    ("2025-05-01 to 2026-07-24", "2025-05-01", "2026-07-24")
]

df_h1  = pd.read_csv(H1_PATH)
df_m15 = pd.read_csv(M15_PATH)

strats = [
    ("Davidd Ultimate Scalping (M15)", df_m15, "ultimate_scalping", "M15"),
    ("Davidd Ultimate Scalping (H1)",  df_h1,  "ultimate_scalping", "H1"),
    ("Davidd Triple SuperTrend (H1)",  df_h1,  "triple_supertrend", "H1"),
    ("Quant Structural Sweep (H1)",    df_h1,  "quant_structural_sweep", "H1"),
]

for label_date, s_date, e_date in periods:
    print(f"\n========================================================")
    print(f"🗓️ PERIOD: {label_date}")
    print(f"========================================================")
    print(f"{'Strategy':<30} {'Final Eq':>10} {'PnL%':>8} {'MaxDD%':>8} {'Trades':>7} {'WR%':>7} {'PF':>6}")
    print("-" * 82)
    
    for sname, dataset, stype, tf in strats:
        bal, pct, dd, n_tr, wr, pf = run_tick_sim_1year(dataset, strat_type=stype, timeframe=tf, start_date=s_date, end_date=e_date)
        print(f"{sname:<30} ${bal:>9.2f} {pct:>+7.1f}% {dd:>7.1f}% {n_tr:>7} {wr:>6.1f}% {pf:>6.2f}")
