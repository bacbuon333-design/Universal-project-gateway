"""
CHECKPOINT V1 — BASELINE: DAVIDD ANTHONY ULTIMATE SCALPING (H1)
================================================================
Frozen Baseline Version: Checkpoint 1 (2026-07-30)
Dataset: XAUUSD H1 (2010 - 2026, 79,288 bars, 16.57 years)

This file is frozen as a baseline checkpoint. Do NOT overwrite.
All future enhancements will be created as Checkpoint v2, v3, etc.

16-Year Cumulative Result (Compound 3% Risk):
- Initial Capital : $1,000.00
- Final Balance   : $20,224.53 (+1,922.5%)
- Max Drawdown    : 48.6%
- Total Trades    : 1,045
- Win Rate        : 38.28%
- Profit Factor   : 1.14

Separate 1-Year Runs ($1,000 fresh per year):
- Profitable Years: 7 / 17 years (41.2% year win rate)
- Best Year (2020): +62.5% PnL (COVID stimulus bull)
- Worst Year (2013): -33.3% PnL (Gold bear market crash)
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

def run_v1_single_year(df_year, risk_pct=0.03):
    sub = df_year.copy().reset_index(drop=True)
    c = sub['close'].values
    h = sub['high'].values
    l = sub['low'].values
    o = sub['open'].values
    n = len(sub)
    if n < 250: return None
    
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
    pnl_pct = (bal - 1000.0) / 10.0
    
    return {
        'bal': bal, 'pnl_pct': pnl_pct, 'max_dd': max_dd,
        'trades': len(trades), 'wr': wr, 'pf': pf, 'fees': total_fees
    }

def run_checkpoint_v1(risk_pct=0.03, separate_years=True):
    if not os.path.exists(DATA_PATH):
        print(f"Error: Data file not found at {DATA_PATH}")
        return
        
    df = pd.read_csv(DATA_PATH)
    df['dt'] = pd.to_datetime(df['datetime_str'])
    df['year'] = df['dt'].dt.year
    
    years = sorted(df['year'].unique())
    
    print("="*85)
    print("CHECKPOINT V1 — DAVIDD ANTHONY ULTIMATE SCALPING (H1 BASELINE)")
    print("="*85)
    print(f"{'Year':<6} {'Start $':<9} {'End $':<10} {'PnL %':<9} {'MaxDD %':<9} {'Trades':<7} {'WinRate %':<10} {'PF':<6}")
    print("-" * 85)
    
    total_wins_years = 0
    total_years = 0
    
    for yr in years:
        sub = df[df['year'] == yr].copy().reset_index(drop=True)
        c = sub['close'].values
        h = sub['high'].values
        l = sub['low'].values
        o = sub['open'].values
        n = len(sub)
        if n < 250: continue
        
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
        
        bal = 1000.0; pk = 1000.0; max_dd = 0.0
        trades = []
        last_trade = -9999
        cooldown = 12
        
        pos_dir = 0; pos_en = 0.0; pos_sl = 0.0; pos_tp = 0.0; pos_lot = 0.0
        
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
        pnl_pct = (bal - 1000.0) / 10.0
        
        total_years += 1
        if pnl_pct > 0: total_wins_years += 1
        
        status = "✅" if pnl_pct > 0 else "❌"
        print(f"{yr:<6} ${1000:<8.0f} ${bal:<9.2f} {pnl_pct:>+7.1f}%  {max_dd:<8.1f}  {len(trades):<6} {wr:<8.1f}%  {pf:<5.2f} {status}")

    print("-" * 85)
    print(f"CHECKPOINT V1 SUMMARY: {total_wins_years} / {total_years} Profitable Years ({total_wins_years/total_years*100:.1f}%)")

if __name__ == '__main__':
    run_checkpoint_v1()
