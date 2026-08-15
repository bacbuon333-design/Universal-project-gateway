"""
DAVIDD ANTHONY - 5 MINUTE ULTIMATE SCALPING STRATEGY BACKTEST
==============================================================
Tests the exact strategy parameters on 16.5 Years of Gold History (2010 - 2026)
and 4.2 Years of Gold M15 History (2022 - 2026).

Strategy Parameters:
- Trend: EMA 9, EMA 55, EMA 200
- Momentum: RSI 14 (Buy > 51, Sell < 49)
- Trigger: MACD Histogram (12, 26, 9) breaking Bollinger Bands (20, 2.0) applied to MACD Hist
- Risk Management: Fixed R:R 1:2 (ATR-based SL or Fixed Pips SL)
- Real Execution: Next-bar open entry, Spread, Commission, Slippage
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

def run_ultimate_scalping(df, timeframe_name="H1"):
    c = df['close'].values
    h = df['high'].values
    l = df['low'].values
    o = df['open'].values
    n = len(df)
    
    # Indicators
    tr = np.maximum(h[1:]-l[1:], np.maximum(abs(h[1:]-c[:-1]), abs(l[1:]-c[:-1])))
    tr = np.insert(tr, 0, tr[0])
    atr14 = pd.Series(tr).rolling(14).mean().bfill().values
    
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
    
    # Signals
    buy_sig  = (ema9 > ema55) & (ema55 > ema200) & (rsi > 51) & (macd_hist > hist_bb_up)
    sell_sig = (ema9 < ema55) & (ema55 < ema200) & (rsi < 49) & (macd_hist < hist_bb_dn)
    
    # Simulation (R:R 1:2)
    bal = 1000.0; pk = 1000.0; max_dd = 0.0
    trades = []
    last_trade = -9999
    cooldown = 12 if timeframe_name == "H1" else 24
    
    pos_dir = 0; pos_en = 0.0; pos_sl = 0.0; pos_tp = 0.0; pos_lot = 0.0
    
    for i in range(250, n-1):
        if pos_dir != 0:
            done = False
            ep = c[i]
            
            if pos_dir == 1:
                if l[i] <= pos_sl:
                    ep = pos_sl - 5.0 * PIP
                    done = True
                elif h[i] >= pos_tp:
                    ep = pos_tp
                    done = True
            else:
                if h[i] >= pos_sl:
                    ep = pos_sl + 5.0 * PIP
                    done = True
                elif l[i] <= pos_tp:
                    ep = pos_tp
                    done = True
                    
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
                sp = 25.0 # pips
                sl_pts = (av * 1.5 / PIP) + sp # SL = 1.5x ATR
                
                risk_amt = bal * 0.03 # 3% risk
                lot = max(0.01, min(round(risk_amt / (sl_pts * 0.01) * 0.01, 2), 20.0))
                
                next_o = o[i+1]
                half_sp = (sp * PIP) / 2.0
                
                if sig == 1:
                    pos_dir = 1
                    pos_en  = next_o + half_sp
                    pos_sl  = pos_en - sl_pts * PIP
                    pos_tp  = pos_en + sl_pts * 2.0 * PIP # R:R = 1:2
                    pos_lot = lot
                else:
                    pos_dir = -1
                    pos_en  = next_o - half_sp
                    pos_sl  = pos_en + sl_pts * PIP
                    pos_tp  = pos_en - sl_pts * 2.0 * PIP # R:R = 1:2
                    pos_lot = lot
                last_trade = i

    wins = [t for t in trades if t > 0]
    loss = [t for t in trades if t < 0]
    pf = sum(wins)/abs(sum(loss)) if loss and sum(loss)!=0 else 0
    wr = len(wins)/max(len(trades),1)*100
    
    return bal, (bal-1000)/10.0, max_dd, len(trades), wr, pf

print("="*75)
print("DAVIDD ANTHONY: 5-MINUTE ULTIMATE SCALPING - BACKTEST RESULTS")
print("="*75)

# Test 1: H1 Data (2010 - 2026)
if os.path.exists(H1_PATH):
    df_h1 = pd.read_csv(H1_PATH)
    df_h1['dt'] = pd.to_datetime(df_h1['datetime_str'])
    df_h1.set_index('dt', inplace=True)
    df_h1.sort_index(inplace=True)
    
    print("\n--- TEST 1: DEEP GOLD H1 HISTORY (2010 - 2026) ---")
    bal, pct, dd, n_tr, wr, pf = run_ultimate_scalping(df_h1, "H1")
    print(f"Final Equity : ${bal:,.2f} ({pct:+.1f}%)")
    print(f"Max Drawdown : {dd:.1f}%")
    print(f"Total Trades : {n_tr:,}")
    print(f"Win Rate     : {wr:.2f}%")
    print(f"Profit Factor: {pf:.2f}")

# Test 2: M15 Data (2022 - 2026)
if os.path.exists(M15_PATH):
    df_m15 = pd.read_csv(M15_PATH)
    df_m15['dt'] = pd.to_datetime(df_m15['datetime_str'])
    df_m15.set_index('dt', inplace=True)
    df_m15.sort_index(inplace=True)
    
    print("\n--- TEST 2: GOLD M15 HISTORY (2022 - 2026) ---")
    bal, pct, dd, n_tr, wr, pf = run_ultimate_scalping(df_m15, "M15")
    print(f"Final Equity : ${bal:,.2f} ({pct:+.1f}%)")
    print(f"Max Drawdown : {dd:.1f}%")
    print(f"Total Trades : {n_tr:,}")
    print(f"Win Rate     : {wr:.2f}%")
    print(f"Profit Factor: {pf:.2f}")
