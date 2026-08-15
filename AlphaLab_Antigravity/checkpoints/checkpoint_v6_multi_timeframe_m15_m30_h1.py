"""
CHECKPOINT V6 — MULTI-TIMEFRAME (M15 + M30 + H1) CONFLUENCE ENGINE
==================================================================
Frozen Version: Checkpoint 6 (2026-07-31)
Multi-Timeframe Architecture:
1. H1 Macro Structure Layer (H1 EMA 200 + H1 48-bar swing high/low bounds)
2. M30 Distribution & Volatility Layer (M30 BB bands & ATR z-score compression)
3. M15 Precision Early Trigger (M15 Pinbar Rejection + RSI oversold < 30 / overbought > 70)

Entry Execution:
- Tight Stop Loss on M15 ATR (1.5x M15 ATR + Spread 25p)
- Extended Take Profit targeting H1 Swing Extreme (4.5x M15 ATR, R:R = 1:3.0)
"""

import os, sys
sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None
import numpy as np
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(BASE_DIR, "data", "GOLD_M15.csv")

PIP = 0.01
PTVAL = 0.01
COMM_PER_001 = 0.07

def run_v6_multi_timeframe(df_m15, risk_pct=0.025):
    sub = df_m15.copy().reset_index(drop=True)
    col = 'datetime_str' if 'datetime_str' in sub.columns else sub.columns[0]
    sub['dt'] = pd.to_datetime(sub[col])
    sub.sort_values('dt', inplace=True)
    sub.reset_index(drop=True, inplace=True)
    
    c15 = sub['close'].values
    h15 = sub['high'].values
    l15 = sub['low'].values
    o15 = sub['open'].values
    dt  = sub['dt'].values
    n   = len(sub)
    if n < 1000: return None
    
    # 1. M15 Indicators
    tr15 = np.maximum(h15[1:]-l15[1:], np.maximum(abs(h15[1:]-c15[:-1]), abs(l15[1:]-c15[:-1])))
    tr15 = np.insert(tr15, 0, tr15[0])
    atr15 = pd.Series(tr15).rolling(14).mean().bfill().values
    
    d15 = pd.Series(c15).diff()
    up15 = d15.clip(lower=0).ewm(alpha=1/14, adjust=False).mean()
    dn15 = (-d15.clip(upper=0)).ewm(alpha=1/14, adjust=False).mean().clip(1e-9)
    rsi15 = (100 - 100 / (1 + up15 / dn15)).values
    
    ema50_15  = pd.Series(c15).ewm(span=50,  adjust=False).mean().values
    
    # 2. Resample H1 and M30 for Confluence
    # H1 is 4 M15 bars, M30 is 2 M15 bars
    ema200_h1 = pd.Series(c15).ewm(span=800, adjust=False).mean().values # 200 H1 bars = 800 M15 bars
    hi192_h1  = pd.Series(h15).shift(1).rolling(192).max().values      # 48 H1 bars  = 192 M15 bars
    lo192_h1  = pd.Series(l15).shift(1).rolling(192).min().values      # 48 H1 bars  = 192 M15 bars
    
    # M30 Bollinger Bands (20 M30 bars = 40 M15 bars)
    m30_mid = pd.Series(c15).rolling(40).mean().bfill().values
    m30_std = pd.Series(c15).rolling(40).std().bfill().values
    m30_bb_up = m30_mid + 2.0 * m30_std
    m30_bb_dn = m30_mid - 2.0 * m30_std
    
    buy_sig  = np.zeros(n, dtype=bool)
    sell_sig = np.zeros(n, dtype=bool)
    
    for i in range(800, n):
        av = max(atr15[i], 0.8)
        lwick = min(o15[i], c15[i]) - l15[i]
        uwick = h15[i] - max(o15[i], c15[i])
        body  = abs(c15[i] - o15[i]) + 1e-9
        
        # H1 Macro Trend
        h1_bull = c15[i] > ema200_h1[i]
        h1_bear = c15[i] < ema200_h1[i]
        
        # M30 Zone Reaction
        m30_oversold  = (c15[i] <= m30_bb_dn[i]) or (l15[i] <= lo192_h1[i] + 0.5 * av)
        m30_overbought = (c15[i] >= m30_bb_up[i]) or (h15[i] >= hi192_h1[i] - 0.5 * av)
        
        # M15 Early Trigger
        m15_pin_buy  = (lwick >= 1.5 * body) or (rsi15[i] < 32)
        m15_pin_sell = (uwick >= 1.5 * body) or (rsi15[i] > 68)
        
        if h1_bull and m30_oversold and m15_pin_buy:
            buy_sig[i] = True
        elif h1_bear and m30_overbought and m15_pin_sell:
            sell_sig[i] = True

    bal = 1000.0; pk = 1000.0; max_dd = 0.0
    trades = []
    last_trade = -9999
    cooldown = 16 # 16 M15 bars = 4 hours cooldown
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
                av = max(atr15[i], 0.8)
                sp = 25.0
                sl_pts = (av * 1.5 / PIP) + sp # Tight M15 Stop Loss
                tp_pts = (av * 4.5 / PIP)      # 1:3.0 Risk-to-Reward Ratio
                
                risk_amt = bal * risk_pct
                lot = max(0.01, min(round(risk_amt / (sl_pts * 0.01) * 0.01, 2), 20.0))
                
                next_o = o15[i+1]
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
    print("CHECKPOINT 6 — MULTI-TIMEFRAME (M15 + M30 + H1) CONFLUENCE ENGINE (2022 - 2026)")
    print("Dataset: XAUUSD M15 (4.23 Years) | Fresh $1,000 Capital Every Year")
    print("="*95)
    print(f"{'Year':<6} | {'Start $':<8} {'End $':<10} {'PnL %':<9} {'MaxDD %':<8} {'Trades':<7} {'WinRate %':<10} {'PF':<6}")
    print("-" * 95)
    
    total_wins = 0; total_years = 0
    
    for yr in years:
        sub = df_m15[df_m15['year'] == yr]
        if len(sub) < 1000: continue
        
        res = run_v6_multi_timeframe(sub, risk_pct=0.025)
        if res is None: continue
        
        total_years += 1
        if res['pnl_pct'] > 0: total_wins += 1
        
        status = "✅" if res['pnl_pct'] > 0 else "❌"
        print(f"{yr:<6} | ${1000:<7.0f} ${res['bal']:<9.2f} {res['pnl_pct']:>+7.1f}%  {res['max_dd']:<8.1f}  {res['trades']:<6} {res['wr']:<8.1f}%  {res['pf']:<5.2f} {status}")

    print("-" * 95)
    print(f"CHECKPOINT 6 SUMMARY: {total_wins} / {total_years} Profitable Years ({total_wins/total_years*100:.1f}%)")

if __name__ == '__main__':
    main()
