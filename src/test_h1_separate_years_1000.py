"""
H1 SEPARATE YEARS GAUNTLET (2010 - 2026) — FRESH $1,000 CAPITAL PER YEAR
========================================================================
Strategy: Davidd Anthony - 5-Minute Ultimate Scalping (H1 Adaptation)
Dataset: XAUUSD Deep History H1 (2010 - 2026)
Resets capital to exactly $1,000 at the start of EACH calendar year.

Costs per 0.01 lot:
- Spread = 25 pips ($0.25/oz)
- Commission = $0.07 / 0.01 lot
- Slippage = 5 pips ($0.05/oz)
- Total Fee per 0.01 lot = $0.37
"""

import os, sys
sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None
import numpy as np
import pandas as pd

BASE_DIR = r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05\AlphaLab_Antigravity"
H1_PATH  = os.path.join(BASE_DIR, "data", "GOLD_H1_2010_2026.csv")

PIP = 0.01
PTVAL = 0.01
COMM_PER_001 = 0.07

def run_single_year(df_year, year_label, risk_pct=0.03):
    sub = df_year.copy().reset_index(drop=True)
    c = sub['close'].values
    h = sub['high'].values
    l = sub['low'].values
    o = sub['open'].values
    dt = sub['datetime_str'].values
    n = len(sub)
    if n < 250:
        return None
        
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
    
    buy_sig  = (ema9 > ema55) & (ema55 > ema200) & (rsi > 51) & (macd_hist > hist_bb_up)
    sell_sig = (ema9 < ema55) & (ema55 < ema200) & (rsi < 49) & (macd_hist < hist_bb_dn)
    
    # Capital resets to $1,000
    bal = 1000.0; pk = 1000.0; max_dd = 0.0
    trades = []
    last_trade = -9999
    cooldown = 12
    
    pos_dir = 0; pos_en = 0.0; pos_sl = 0.0; pos_tp = 0.0; pos_lot = 0.0
    total_fees = 0.0
    
    for i in range(100, n-1):
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
                gross = pts * PTVAL * (pos_lot / 0.01)
                fee   = (pos_lot / 0.01) * 0.37
                net   = gross - fee
                total_fees += fee
                
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
                sl_pts = (av * 1.5 / PIP) + sp
                risk_amt = bal * risk_pct
                lot = max(0.01, min(round(risk_amt / (sl_pts * 0.01) * 0.01, 2), 20.0))
                
                next_o = o[i+1]
                half_sp = (sp * PIP) / 2.0
                
                if sig == 1:
                    pos_dir = 1
                    pos_en  = next_o + half_sp
                    pos_sl  = pos_en - sl_pts * PIP
                    pos_tp  = pos_en + sl_pts * 2.0 * PIP
                    pos_lot = lot
                else:
                    pos_dir = -1
                    pos_en  = next_o - half_sp
                    pos_sl  = pos_en + sl_pts * PIP
                    pos_tp  = pos_en - sl_pts * 2.0 * PIP
                    pos_lot = lot
                last_trade = i

    wins = [t for t in trades if t > 0]
    loss = [t for t in trades if t < 0]
    pf = sum(wins)/abs(sum(loss)) if loss and sum(loss)!=0 else 0
    wr = len(wins)/max(len(trades),1)*100
    
    # Gold return for that year
    gold_start = c[0]
    gold_end   = c[-1]
    gold_ret   = (gold_end - gold_start) / gold_start * 100
    
    return {
        'year': year_label,
        'start_bal': 1000.0,
        'end_bal': bal,
        'pnl_pct': (bal - 1000.0) / 10.0,
        'max_dd': max_dd,
        'trades': len(trades),
        'wr': wr,
        'pf': pf,
        'fees': total_fees,
        'gold_ret': gold_ret,
        'gold_start': gold_start,
        'gold_end': gold_end
    }

df = pd.read_csv(H1_PATH)
df['dt'] = pd.to_datetime(df['datetime_str'])
df['year'] = df['dt'].dt.year

years = sorted(df['year'].unique())

print("="*90)
print("H1 SEPARATE YEARS GAUNTLET (2010 - 2026) — FRESH $1,000 CAPITAL EVERY YEAR")
print("Strategy: Davidd Anthony Ultimate Scalping (H1)")
print("="*90)
print(f"{'Year':<6} {'Capital':<8} {'End Bal':<10} {'PnL%':<9} {'MaxDD%':<8} {'Trades':<7} {'WR%':<7} {'PF':<6} {'Fees Paid':<10} {'Gold Return':<12}")
print("-" * 90)

profitable_years = 0
total_years = 0

for yr in years:
    df_yr = df[df['year'] == yr]
    res = run_single_year(df_yr, str(yr))
    if res is None: continue
    
    total_years += 1
    if res['pnl_pct'] > 0:
        profitable_years += 1
        
    pnl_str = f"{res['pnl_pct']:+.1f}%"
    status = "✅" if res['pnl_pct'] > 0 else "❌"
    print(f"{res['year']:<6} ${res['start_bal']:<7.0f} ${res['end_bal']:<9.2f} {pnl_str:<9} {res['max_dd']:<8.1f} {res['trades']:<7} {res['wr']:<6.1f}% {res['pf']:<5.2f} ${res['fees']:<9.2f} {res['gold_ret']:>+6.1f}% {status}")

print("-" * 90)
print(f"SUMMARY: {profitable_years} / {total_years} Profitable Years ({profitable_years/total_years*100:.1f}% Win Rate by Year)")
