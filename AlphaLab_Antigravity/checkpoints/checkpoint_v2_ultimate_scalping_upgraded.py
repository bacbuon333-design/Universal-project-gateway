"""
CHECKPOINT V2 — DAVIDD TECH UPGRADED ULTIMATE SCALPING (H1)
============================================================
Upgrades over Checkpoint v1 Baseline:
1. ADX Trend-Strength Filter: ADX(14) > 20 (Avoids weak consolidation chop)
2. ATR Dynamic Exits & Risk: SL = 2.0x ATR, TP = 4.0x ATR (R:R = 1:2), Max risk = 2.5% equity
3. Session Time Filter: Entry only between 12:00 and 18:00 GMT (London/NY Overlap & US Open)

Dataset: XAUUSD H1 (2010 - 2026, 79,288 bars, 16.57 years)
Execution: Next-bar Open + Spread (25 pips) + Comm ($0.07/0.01 lot) + Slippage (5 pips)
"""

import os, sys
sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None
import numpy as np
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(BASE_DIR, "data", "GOLD_H1_2010_2026.csv")

PIP = 0.01
PTVAL = 0.01
COMM_PER_001 = 0.07

def calc_adx(high, low, close, period=14):
    n = len(close)
    tr = np.maximum(high[1:]-low[1:], np.maximum(abs(high[1:]-close[:-1]), abs(low[1:]-close[:-1])))
    tr = np.insert(tr, 0, tr[0])
    
    up = pd.Series(high).diff().values
    dn = -pd.Series(low).diff().values
    
    pdm = np.where((up > dn) & (up > 0), up, 0.0)
    ndm = np.where((dn > up) & (dn > 0), dn, 0.0)
    
    atr_ser = pd.Series(tr).ewm(alpha=1/period, adjust=False).mean()
    pdi = 100 * pd.Series(pdm).ewm(alpha=1/period, adjust=False).mean() / atr_ser.replace(0, 1e-9)
    ndi = 100 * pd.Series(ndm).ewm(alpha=1/period, adjust=False).mean() / atr_ser.replace(0, 1e-9)
    
    dx = 100 * (pdi - ndi).abs() / (pdi + ndi).replace(0, 1e-9)
    adx = dx.ewm(alpha=1/period, adjust=False).mean().values
    return adx

def run_checkpoint_v2_year(sub, risk_pct=0.025, adx_min=20):
    c = sub['close'].values
    h = sub['high'].values
    l = sub['low'].values
    o = sub['open'].values
    dt = pd.to_datetime(sub['datetime_str']).values
    n = len(sub)
    if n < 250: return None
    
    tr = np.maximum(h[1:]-l[1:], np.maximum(abs(h[1:]-c[:-1]), abs(l[1:]-c[:-1])))
    tr = np.insert(tr, 0, tr[0])
    atr14 = pd.Series(tr).rolling(14).mean().bfill().values
    adx14 = calc_adx(h, l, c, 14)
    
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
    
    # Session filter: Hour 12 to 18 GMT
    hours = pd.Series(dt).dt.hour.values
    session_ok = (hours >= 12) & (hours <= 18)
    
    # Signals with ADX > 20 filter
    buy_sig  = (ema9 > ema55) & (ema55 > ema200) & (rsi > 51) & (macd_hist > hist_bb_up) & (adx14 > adx_min) & session_ok
    sell_sig = (ema9 < ema55) & (ema55 < ema200) & (rsi < 49) & (macd_hist < hist_bb_dn) & (adx14 > adx_min) & session_ok
    
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
                sl_pts = (av * 2.0 / PIP) + sp # Checkpoint 2: SL = 2.0x ATR
                tp_pts = (av * 4.0 / PIP)      # Checkpoint 2: TP = 4.0x ATR (R:R = 1:2)
                
                risk_amt = bal * risk_pct # Checkpoint 2: 2.5% max risk
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
    pnl_pct = (bal - 1000.0) / 10.0
    
    return {
        'bal': bal, 'pnl_pct': pnl_pct, 'max_dd': max_dd,
        'trades': len(trades), 'wr': wr, 'pf': pf, 'fees': total_fees
    }

def main():
    if not os.path.exists(DATA_PATH):
        print("Data file not found")
        return
        
    df = pd.read_csv(DATA_PATH)
    df['dt'] = pd.to_datetime(df['datetime_str'])
    df['year'] = df['dt'].dt.year
    years = sorted(df['year'].unique())
    
    # Import Checkpoint 1 runner
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from checkpoint_v1_davidd_ultimate_scalping_h1 import run_v1_single_year as run_v1_year
    
    print("="*95)
    print("BENCHMARK COMPARISON: CHECKPOINT 1 (BASELINE) vs CHECKPOINT 2 (UPGRADED)")
    print("Dataset: XAUUSD H1 (2010 - 2026, 16.57 Years) | Fresh $1,000 Capital Every Year")
    print("="*95)
    print(f"{'Year':<6} | {'--- CHECKPOINT 1 (BASELINE) ---':<36} | {'--- CHECKPOINT 2 (UPGRADED v2) ---':<36}")
    print(f"{'':<6} | {'PnL %':<8} {'MaxDD %':<8} {'Trades':<7} {'WR %':<6} {'PF':<5} | {'PnL %':<8} {'MaxDD %':<8} {'Trades':<7} {'WR %':<6} {'PF':<5}")
    print("-" * 95)
    
    v1_prof_years = 0
    v2_prof_years = 0
    total_years = 0
    
    for yr in years:
        df_yr = df[df['year'] == yr]
        r1 = run_v1_year(df_yr, risk_pct=0.03)
        r2 = run_checkpoint_v2_year(df_yr)
        if r1 is None or r2 is None: continue
        
        total_years += 1
        if r1['pnl_pct'] > 0: v1_prof_years += 1
        if r2['pnl_pct'] > 0: v2_prof_years += 1
        
        s1 = "✅" if r1['pnl_pct'] > 0 else "❌"
        s2 = "✅" if r2['pnl_pct'] > 0 else "❌"
        
        v1_str = f"{r1['pnl_pct']:>+6.1f}%  {r1['max_dd']:>6.1f}%  {r1['trades']:>5}  {r1['wr']:>5.1f}% {r1['pf']:>4.2f} {s1}"
        v2_str = f"{r2['pnl_pct']:>+6.1f}%  {r2['max_dd']:>6.1f}%  {r2['trades']:>5}  {r2['wr']:>5.1f}% {r2['pf']:>4.2f} {s2}"
        
        print(f"{yr:<6} | {v1_str} | {v2_str}")
        
    print("-" * 95)
    print(f"SUMMARY PROFITABLE YEARS:")
    print(f"  Checkpoint 1 Baseline : {v1_prof_years} / {total_years} Years ({v1_prof_years/total_years*100:.1f}%)")
    print(f"  Checkpoint 2 Upgraded : {v2_prof_years} / {total_years} Years ({v2_prof_years/total_years*100:.1f}%)")

if __name__ == '__main__':
    main()
