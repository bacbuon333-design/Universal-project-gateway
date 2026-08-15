"""
CHECKPOINT V6 UPGRADED — H1 STRUCTURE + M15 PRECISION TRIGGER ENGINE
=====================================================================
Frozen Version: Checkpoint 6 Upgraded (2026-07-31)

Architecture:
1. H1 Structure Gate: H1 Macro Trend + H1 48-Bar Support/Resistance Reaction Zone (Restricts trades to ~40-50/year).
2. M15 Precision Trigger: Within the H1 setup window, enters immediately on the first M15 sub-bar bullish/bearish confirmation.
3. H1 Structural SL: Stop Loss uses H1 ATR (2.0x H1 ATR) to prevent micro-whipsaw stopouts.
4. M15 Entry Advantage: Secures entry early on M15 rather than waiting for H1 candle close.
"""

import os, sys
sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None
import numpy as np
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(BASE_DIR, "data", "GOLD_M15.csv")

PIP = 0.01
PTVAL = 0.01

def run_v6_upgraded_h1_m15(df_m15, risk_pct=0.025):
    sub = df_m15.copy().reset_index(drop=True)
    col = 'datetime_str' if 'datetime_str' in sub.columns else sub.columns[0]
    sub['dt'] = pd.to_datetime(sub[col])
    sub.sort_values('dt', inplace=True)
    sub.reset_index(drop=True, inplace=True)
    
    c15 = sub['close'].values; h15 = sub['high'].values; l15 = sub['low'].values; o15 = sub['open'].values
    dt  = sub['dt'].values; n = len(sub)
    if n < 1000: return None
    
    # Calculate H1 equivalents on M15 bars (4 M15 bars = 1 H1 bar)
    tr15 = np.maximum(h15[1:]-l15[1:], np.maximum(abs(h15[1:]-c15[:-1]), abs(l15[1:]-c15[:-1])))
    tr15 = np.insert(tr15, 0, tr15[0])
    atr15 = pd.Series(tr15).rolling(14).mean().bfill().values
    
    # H1 indicators (scaled to M15 index)
    ema200_h1 = pd.Series(c15).ewm(span=800, adjust=False).mean().values
    atr14_h1  = pd.Series(tr15).rolling(56).mean().bfill().values * 2.0 # Approx H1 ATR
    hi192_h1  = pd.Series(h15).shift(1).rolling(192).max().values      # 48 H1 bars
    lo192_h1  = pd.Series(l15).shift(1).rolling(192).min().values      # 48 H1 bars
    
    mom3m = np.zeros(n, dtype=bool)
    for i in range(1440, n): mom3m[i] = c15[i] > c15[i-1440] if i >= 1440 else True
    
    buy_sig  = np.zeros(n, dtype=bool)
    sell_sig = np.zeros(n, dtype=bool)
    
    for i in range(800, n):
        av_h1 = max(atr14_h1[i], 1.5)
        lwick15 = min(o15[i], c15[i]) - l15[i]
        uwick15 = h15[i] - max(o15[i], c15[i])
        body15  = abs(c15[i] - o15[i]) + 1e-9
        
        # H1 Macro Filter
        macro_bull = mom3m[i] and c15[i] > ema200_h1[i]
        macro_bear = (not mom3m[i]) and c15[i] < ema200_h1[i]
        
        # H1 Reaction Zone Condition
        h1_sweep_lo = l15[i] <= lo192_h1[i] + 0.5 * av_h1
        h1_sweep_hi = h15[i] >= hi192_h1[i] - 0.5 * av_h1
        
        # M15 Precision Confirmation (Refined Entry Trigger)
        m15_confirm_buy  = (lwick15 >= 1.2 * body15) and (c15[i] > o15[i])
        m15_confirm_sell = (uwick15 >= 1.2 * body15) and (c15[i] < o15[i])
        
        if macro_bull and h1_sweep_lo and m15_confirm_buy:
            buy_sig[i] = True
        elif macro_bear and h1_sweep_hi and m15_confirm_sell:
            sell_sig[i] = True

    bal = 1000.0; pk = 1000.0; max_dd = 0.0
    trades = []
    last_trade = -9999
    cooldown = 32 # 32 M15 bars = 8 hours cooldown
    pos_dir = 0; pos_en = 0.0; pos_sl = 0.0; pos_tp = 0.0; pos_lot = 0.0
    total_fees = 0.0
    
    for i in range(800, n-1):
        if pos_dir != 0:
            done = False; ep = c15[i]
            if pos_dir == 1:
                if l15[i] <= pos_sl: ep = pos_sl - 5.0 * PIP; done = True
                elif h15[i] >= pos_tp: ep = pos_tp; done = True
            else:
                if h15[i] >= pos_sl: ep = pos_sl + 5.0 * PIP; done = True
                elif l15[i] <= pos_tp: ep = pos_tp; done = True
                    
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
                av_h1 = max(atr14_h1[i], 1.5)
                sp = 25.0
                sl_pts = (av_h1 * 2.0 / PIP) + sp # Robust H1 Stop Loss
                tp_pts = (av_h1 * 4.5 / PIP)
                
                risk_amt = bal * risk_pct
                lot = max(0.01, min(round(risk_amt / (sl_pts * 0.01) * 0.01, 2), 20.0))
                
                next_o = o15[i+1] # Entry precision on M15!
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
    pnl_pct = (bal - 1000.0) / 10.0
    
    return {
        'bal': bal, 'pnl_pct': pnl_pct, 'max_dd': max_dd,
        'trades': len(trades), 'wr': wr, 'pf': pf, 'fees': total_fees
    }

def main():
    df_m15 = pd.read_csv(DATA_PATH)
    col = 'datetime_str' if 'datetime_str' in df_m15.columns else df_m15.columns[0]
    df_m15['dt'] = pd.to_datetime(df_m15[col])
    df_m15['year'] = df_m15['dt'].dt.year
    years = sorted(df_m15['year'].unique())
    
    print("="*95)
    print("CHECKPOINT 6 UPGRADED: LOOK AT H1 STRUCTURE + EXECUTE ON M15 PRECISION (2022 - 2026)")
    print("Dataset: XAUUSD M15 (4.23 Years) | Fresh $1,000 Capital Every Year")
    print("="*95)
    print(f"{'Year':<6} | {'Start $':<8} {'End $':<10} {'PnL %':<9} {'MaxDD %':<8} {'Trades':<7} {'WinRate %':<10} {'PF':<6}")
    print("-" * 95)
    
    total_wins = 0; total_years = 0
    
    for yr in years:
        sub = df_m15[df_m15['year'] == yr]
        if len(sub) < 1000: continue
        
        res = run_v6_upgraded_h1_m15(sub, risk_pct=0.025)
        if res is None: continue
        
        total_years += 1
        if res['pnl_pct'] > 0: total_wins += 1
        
        status = "✅" if res['pnl_pct'] > 0 else "❌"
        print(f"{yr:<6} | ${1000:<7.0f} ${res['bal']:<9.2f} {res['pnl_pct']:>+7.1f}%  {res['max_dd']:<8.1f}  {res['trades']:<6} {res['wr']:<8.1f}%  {res['pf']:<5.2f} {status}")

    print("-" * 95)
    print(f"CHECKPOINT 6 UPGRADED SUMMARY: {total_wins} / {total_years} Profitable Years ({total_wins/total_years*100:.1f}%)")

if __name__ == '__main__':
    main()
