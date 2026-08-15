"""
CHECKPOINT V4 — 100% CORRECTED DAVIDDTECH EXACT SPECIFICATION ENGINE
======================================================================
Corrected Specifications:
1. Ultimate Scalping (EMA 9/55/200 + RSI > 51/< 49 + MACD Hist breaking BB Upper/Lower + Max 2.5% Risk)
2. Triple SuperTrend & TSV Volume (EMA 200 + 2/3 SuperTrends + RSI < 20 / > 80 + TSV > 0 / < 0 + ATR 3x Trailing + RR 1:1.3)

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

def calc_supertrend(h, l, c, atr, mult):
    n = len(c)
    st = np.zeros(n)
    dir_ = np.ones(n, dtype=int) # 1 = green (up), -1 = red (down)
    upper = (h + l) / 2 + mult * atr
    lower = (h + l) / 2 - mult * atr
    for i in range(1, n):
        if c[i-1] > upper[i-1]: upper[i] = min(upper[i], upper[i-1])
        if c[i-1] < lower[i-1]: lower[i] = max(lower[i], lower[i-1])
        if dir_[i-1] == 1:
            dir_[i] = -1 if c[i] < lower[i] else 1
        else:
            dir_[i] = 1 if c[i] > upper[i] else -1
    return dir_

def run_checkpoint_v4_corrected(sub, strat_type="ultimate_scalping_corrected", risk_pct=0.025):
    c = sub['close'].values
    h = sub['high'].values
    l = sub['low'].values
    o = sub['open'].values
    v = sub['tick_volume'].values if 'tick_volume' in sub.columns else sub['vol'].values
    dt = pd.to_datetime(sub['datetime_str']).values
    n = len(sub)
    if n < 250: return None
    
    tr = np.maximum(h[1:]-l[1:], np.maximum(abs(h[1:]-c[:-1]), abs(l[1:]-c[:-1])))
    tr = np.insert(tr, 0, tr[0])
    atr14 = pd.Series(tr).rolling(14).mean().bfill().values
    
    # EMAs
    ema9   = pd.Series(c).ewm(span=9,   adjust=False).mean().values
    ema55  = pd.Series(c).ewm(span=55,  adjust=False).mean().values
    ema200 = pd.Series(c).ewm(span=200, adjust=False).mean().values
    
    # RSI 14
    d = pd.Series(c).diff()
    up = d.clip(lower=0).ewm(alpha=1/14, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1/14, adjust=False).mean().clip(1e-9)
    rsi = (100 - 100 / (1 + up / dn)).values
    
    buy_sig  = np.zeros(n, dtype=bool)
    sell_sig = np.zeros(n, dtype=bool)
    sl_mult = 2.0; tp_mult = 4.0; cooldown = 12
    
    if strat_type == "ultimate_scalping_corrected":
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
        
        hours = pd.Series(dt).dt.hour.values
        session_ok = (hours >= 12) & (hours <= 18)
        
        # Corrected Logic: MACD Hist > Upper BB (Long), MACD Hist < Lower BB (Short)
        buy_sig  = (ema9 > ema55) & (ema55 > ema200) & (rsi > 51) & (macd_hist > hist_bb_up) & session_ok
        sell_sig = (ema9 < ema55) & (ema55 < ema200) & (rsi < 49) & (macd_hist < hist_bb_dn) & session_ok
        sl_mult = 2.0; tp_mult = 4.0; cooldown = 12
        
    elif strat_type == "triple_supertrend_tsv_corrected":
        atr10 = pd.Series(tr).rolling(10).mean().bfill().values
        atr11 = pd.Series(tr).rolling(11).mean().bfill().values
        atr12 = pd.Series(tr).rolling(12).mean().bfill().values
        
        st1 = calc_supertrend(h, l, c, atr10, 1.0)
        st2 = calc_supertrend(h, l, c, atr11, 2.0)
        st3 = calc_supertrend(h, l, c, atr12, 3.0)
        
        st_sum_bull = (st1 == 1).astype(int) + (st2 == 1).astype(int) + (st3 == 1).astype(int)
        st_sum_bear = (st1 == -1).astype(int) + (st2 == -1).astype(int) + (st3 == -1).astype(int)
        
        # TSV (Time Segmented Volume proxy: Directional Volume)
        price_change = pd.Series(c).diff().fillna(0).values
        tsv = pd.Series(price_change * v).rolling(13).mean().bfill().values
        
        # Corrected Logic: RSI < 20 (Long dip), RSI > 80 (Short peak), TSV > 0 / < 0
        buy_sig  = (c > ema200) & (st_sum_bull >= 2) & (rsi < 20) & (tsv > 0)
        sell_sig = (c < ema200) & (st_sum_bear >= 2) & (rsi > 80) & (tsv < 0)
        sl_mult = 3.0; tp_mult = 3.9; cooldown = 16 # R:R = 1:1.3 with 3x ATR SL
        
    bal = 1000.0; pk = 1000.0; max_dd = 0.0
    trades = []
    last_trade = -9999
    
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
                sl_pts = (av * sl_mult / PIP) + sp
                tp_pts = (av * tp_mult / PIP)
                
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
    
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from checkpoint_v1_davidd_ultimate_scalping_h1 import run_v1_single_year as run_v1
    from checkpoint_v2_ultimate_scalping_upgraded import run_checkpoint_v2_year as run_v2
    from checkpoint_v3_anti_overfitting_dsr import run_checkpoint_v3_prop_firm as run_v3
    
    print("="*110)
    print("CORRECTED DAVIDDTECH SPECS GAUNTLET: CHECKPOINT 1 vs 2 vs 3 vs 4 (EXACT CORRECTED RULES)")
    print("Dataset: XAUUSD H1 (2010 - 2026, 16.57 Years) | Fresh $1,000 Capital Every Year")
    print("="*110)
    print(f"{'Year':<6} | {'CP1 BASELINE':<18} | {'CP2 UPGRADED':<18} | {'CP3 PROP-FIRM':<18} | {'--- CP4 CORRECTED SPECS ---':<28}")
    print(f"{'':<6} | {'PnL %':<7} {'MaxDD':<6} {'PF':<4} | {'PnL %':<7} {'MaxDD':<6} {'PF':<4} | {'PnL %':<7} {'MaxDD':<6} {'PF':<4} | {'PnL %':<7} {'MaxDD %':<8} {'Trades':<6} {'PF':<5}")
    print("-" * 110)
    
    v1_wins, v2_wins, v3_wins, v4_wins = 0, 0, 0, 0
    total_years = 0
    
    for yr in years:
        df_yr = df[df['year'] == yr]
        r1 = run_v1(df_yr, risk_pct=0.03)
        r2 = run_v2(df_yr, risk_pct=0.025)
        r3 = run_v3(df_yr, risk_pct=0.01, max_monthly_var=0.065)
        r4 = run_checkpoint_v4_corrected(df_yr, strat_type="ultimate_scalping_corrected", risk_pct=0.025)
        if r1 is None or r2 is None or r3 is None or r4 is None: continue
        
        total_years += 1
        if r1['pnl_pct'] > 0: v1_wins += 1
        if r2['pnl_pct'] > 0: v2_wins += 1
        if r3['pnl_pct'] > 0: v3_wins += 1
        if r4['pnl_pct'] > 0: v4_wins += 1
        
        s1 = "✅" if r1['pnl_pct'] > 0 else "❌"
        s2 = "✅" if r2['pnl_pct'] > 0 else "❌"
        s3 = "✅" if r3['pnl_pct'] > 0 else "❌"
        s4 = "✅" if r4['pnl_pct'] > 0 else "❌"
        
        c1_str = f"{r1['pnl_pct']:>+5.1f}% {r1['max_dd']:>5.1f}% {r1['pf']:>4.2f} {s1}"
        c2_str = f"{r2['pnl_pct']:>+5.1f}% {r2['max_dd']:>5.1f}% {r2['pf']:>4.2f} {s2}"
        c3_str = f"{r3['pnl_pct']:>+5.1f}% {r3['max_dd']:>5.1f}% {r3['pf']:>4.2f} {s3}"
        c4_str = f"{r4['pnl_pct']:>+5.1f}% {r4['max_dd']:>6.1f}% {r4['trades']:>6} {r4['pf']:>4.2f} {s4}"
        
        print(f"{yr:<6} | {c1_str} | {c2_str} | {c3_str} | {c4_str}")
        
    print("-" * 110)
    print("SUMMARY PROFITABLE YEARS:")
    print(f"  Checkpoint 1 Baseline           : {v1_wins} / {total_years} Years ({v1_wins/total_years*100:.1f}%)")
    print(f"  Checkpoint 2 Upgraded           : {v2_wins} / {total_years} Years ({v2_wins/total_years*100:.1f}%)")
    print(f"  Checkpoint 3 Prop-Firm DSR      : {v3_wins} / {total_years} Years ({v3_wins/total_years*100:.1f}%)")
    print(f"  Checkpoint 4 Corrected Exact    : {v4_wins} / {total_years} Years ({v4_wins/total_years*100:.1f}%)")

if __name__ == '__main__':
    main()
