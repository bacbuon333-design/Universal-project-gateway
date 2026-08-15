"""
TEST SYMMETRICAL CAUSAL ENGINE (BUY + SELL)
===========================================
"""

import os, sys
import pandas as pd
import numpy as np

sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None

DATA_PATH = r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05\AlphaLab_Antigravity\data\GOLD_M15.csv"

def test_symmetrical():
    print("="*105)
    print("TESTING SYMMETRICAL CAUSAL ENGINE (BUY + SELL WITH H1 TREND ALIGNMENT)")
    print("="*105)
    
    df = pd.read_csv(DATA_PATH)
    df['datetime'] = pd.to_datetime(df['datetime_str'])
    df.set_index('datetime', inplace=True)
    
    o = df['open'].values
    h = df['high'].values
    l = df['low'].values
    c = df['close'].values
    v = df['tick_volume'].values
    n = len(c)
    
    # H1 Aggregation (Shifted by 1 for Causal Execution)
    h1 = df.resample('1h').agg({'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last'}).dropna()
    h1['ema9_h1'] = h1['close'].ewm(span=9, adjust=False).mean()
    h1['ema20_h1'] = h1['close'].ewm(span=20, adjust=False).mean()
    h1['ema55_h1'] = h1['close'].ewm(span=55, adjust=False).mean()
    h1['ema200_h1'] = h1['close'].ewm(span=200, adjust=False).mean()
    h1_causal = h1.shift(1)
    
    df = pd.merge_asof(df, h1_causal[['ema9_h1', 'ema20_h1', 'ema55_h1', 'ema200_h1']], left_index=True, right_index=True)
    
    ema9_h1 = df['ema9_h1'].values
    ema20_h1 = df['ema20_h1'].values
    ema55_h1 = df['ema55_h1'].values
    ema200_h1 = df['ema200_h1'].values
    
    ema9_m15 = df['close'].ewm(span=9, adjust=False).mean().values
    ema20_m15 = df['close'].ewm(span=20, adjust=False).mean().values
    
    tr = np.maximum(h - l, np.maximum(np.abs(h - np.roll(c, 1)), np.abs(l - np.roll(c, 1))))
    atr14_m15 = pd.Series(tr).rolling(14).mean().values
    
    sma20_m15 = pd.Series(c).rolling(20).mean().values
    std20_m15 = pd.Series(c).rolling(20).std().values
    upper_bb = sma20_m15 + 2.0 * std20_m15
    lower_bb = sma20_m15 - 2.0 * std20_m15
    
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rsi_m15 = (100 - (100 / (1 + gain / (loss + 1e-9)))).values
    
    vol_sma50 = pd.Series(v).rolling(50).mean().values
    vol_std50 = pd.Series(v).rolling(50).std().values
    vol_zscore = (v - vol_sma50) / (vol_std50 + 1e-9)
    
    spread_pts = 25
    results = []
    
    for rsi_b in [52.0, 55.0, 58.0]:
        for risk_pct in [0.035, 0.045, 0.055, 0.065]:
            for tp_mult in [1.8, 2.15, 2.5]:
                balance = 1000.0
                peak_balance = balance
                max_dd_pct = 0.0
                trades = []
                last_idx = -1
                
                for i in range(200, n - 1):
                    if np.isnan(ema9_h1[i]): continue
                    av = max(atr14_m15[i], 0.8)
                    body = abs(c[i] - o[i]) + 1e-5
                    lwick = min(o[i], c[i]) - l[i]
                    uwick = h[i] - max(o[i], c[i])
                    
                    macro_bull = (ema9_h1[i] > ema20_h1[i]) and (ema20_h1[i] > ema55_h1[i]) and (ema55_h1[i] > ema200_h1[i])
                    macro_bear = (ema9_h1[i] < ema20_h1[i]) and (ema20_h1[i] < ema55_h1[i]) and (ema55_h1[i] < ema200_h1[i])
                    
                    buy_sig  = macro_bull and (ema9_m15[i] > ema20_m15[i]) and (c[i] > upper_bb[i]) and (vol_zscore[i] > 0.85) and (rsi_m15[i] > rsi_b) and (lwick >= 0.70 * body) and (c[i] > o[i]) and (c[i-1] > o[i-1])
                    sell_sig = macro_bear and (ema9_m15[i] < ema20_m15[i]) and (c[i] < lower_bb[i]) and (vol_zscore[i] > 0.85) and (rsi_m15[i] < (100.0 - rsi_b)) and (uwick >= 0.70 * body) and (c[i] < o[i]) and (c[i-1] < o[i-1])
                    
                    if (buy_sig or sell_sig) and (i - last_idx >= 4):
                        last_idx = i
                        direction = 1 if buy_sig else -1
                        
                        if direction == 1:
                            entry_price = o[i+1] + (spread_pts / 100.0)
                            sl_dist = av * 1.0 + 0.25
                            tp_dist = av * tp_mult
                            sl_price = entry_price - sl_dist
                            tp_price = entry_price + tp_dist
                        else:
                            entry_price = o[i+1] - (spread_pts / 100.0)
                            sl_dist = av * 1.0 + 0.25
                            tp_dist = av * tp_mult
                            sl_price = entry_price + sl_dist
                            tp_price = entry_price - tp_dist
                            
                        current_dd = (peak_balance - balance) / peak_balance if peak_balance > 0 else 0.0
                        active_risk = 0.015 if current_dd >= 0.10 else risk_pct
                        
                        risk_amount = balance * active_risk
                        position_size = risk_amount / sl_dist
                        
                        exit_price = entry_price
                        hit_tp = False; hit_sl = False
                        
                        for j in range(i + 1, min(i + 240, n)):
                            if direction == 1:
                                if l[j] <= sl_price: exit_price = sl_price; hit_sl = True; break
                                elif h[j] >= tp_price: exit_price = tp_price; hit_tp = True; break
                            else:
                                if h[j] >= sl_price: exit_price = sl_price; hit_sl = True; break
                                elif l[j] <= tp_price: exit_price = tp_price; hit_tp = True; break
                                
                        if not hit_tp and not hit_sl: exit_price = c[min(i + 240, n - 1)]
                        
                        pnl = (exit_price - entry_price) * position_size if direction == 1 else (entry_price - exit_price) * position_size
                        balance += pnl
                        
                        if balance > peak_balance: peak_balance = balance
                        dd = (peak_balance - balance) / peak_balance
                        if dd > max_dd_pct: max_dd_pct = dd
                        trades.append(pnl)
                        
                win_trades = [p for p in trades if p > 0]
                total_t = len(trades)
                win_t = len(win_trades)
                wr = (win_t / total_t * 100.0) if total_t else 0.0
                gp = sum(win_trades)
                gl = abs(sum([p for p in trades if p < 0]))
                pf = gp / gl if gl > 0 else 999.0
                
                results.append((balance, wr, max_dd_pct, pf, total_t, rsi_b, risk_pct, tp_mult))

    results.sort(key=lambda x: x[0], reverse=True)
    print("Top Symmetrical Causal Configurations:")
    for r in results[:10]:
        print(f"Bal: ${r[0]:,.2f} | WR: {r[1]:.2f}% | MaxDD: {r[2]*100:.2f}% | PF: {r[3]:.2f} | Trades: {r[4]} | RSI: {r[5]} | Risk: {r[6]*100:.1f}% | TP: {r[7]}x")

if __name__ == '__main__':
    test_symmetrical()
