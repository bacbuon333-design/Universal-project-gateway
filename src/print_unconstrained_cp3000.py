"""
PRINT UNCONSTRAINED TOP CP-3000 CONFIGURATIONS
===============================================
"""

import os, sys
import pandas as pd
import numpy as np

sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None

DATA_PATH = r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05\AlphaLab_Antigravity\data\GOLD_M15.csv"

def run_test():
    df = pd.read_csv(DATA_PATH)
    df['datetime'] = pd.to_datetime(df['datetime_str'])
    df.set_index('datetime', inplace=True)
    df = df[df.index >= '2023-11-17']
    
    o = df['open'].values
    h = df['high'].values
    l = df['low'].values
    c = df['close'].values
    v = df['tick_volume'].values
    n = len(c)
    
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
    atr50_m15 = pd.Series(tr).rolling(50).mean().values
    
    sma20_m15 = pd.Series(c).rolling(20).mean().values
    std20_m15 = pd.Series(c).rolling(20).std().values
    upper_bb = sma20_m15 + 2.0 * std20_m15
    
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rsi_m15 = (100 - (100 / (1 + gain / (loss + 1e-9)))).values
    
    vol_sma50 = pd.Series(v).rolling(50).mean().values
    vol_std50 = pd.Series(v).rolling(50).std().values
    vol_zscore = (v - vol_sma50) / (vol_std50 + 1e-9)
    
    spread_pts = 25
    all_configs = []
    
    for base_risk in [0.035, 0.038, 0.040, 0.042]:
        for accel_step in [1.6, 1.7, 1.8, 1.9, 2.0]:
            for dd_thresh in [0.07, 0.08, 0.09]:
                for dd_mult in [0.20, 0.25, 0.30]:
                    for sl_mult in [1.0, 1.1]:
                        for tp_mult in [3.5, 3.8, 4.0]:
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
                                
                                macro_bull = (ema9_h1[i] > ema20_h1[i]) and (ema20_h1[i] > ema55_h1[i]) and (ema55_h1[i] > ema200_h1[i])
                                m15_bull   = (ema9_m15[i] > ema20_m15[i])
                                vol_exp    = (atr14_m15[i] >= atr50_m15[i] * 1.05)
                                consec_bull = (c[i] > o[i]) and (c[i-1] > o[i-1])
                                
                                b_sig = macro_bull and m15_bull and vol_exp and (c[i] > upper_bb[i]) and (vol_zscore[i] > 1.0) and (rsi_m15[i] > 58.0) and (lwick >= 0.85 * body) and consec_bull
                                
                                if b_sig and (i - last_idx >= 4):
                                    last_idx = i
                                    entry_price = o[i+1] + (spread_pts / 100.0)
                                    sl_dist = av * sl_mult + 0.25
                                    tp_dist = av * tp_mult
                                    sl_price = entry_price - sl_dist
                                    tp_price = entry_price + tp_dist
                                    
                                    current_dd = (peak_balance - balance) / peak_balance if peak_balance > 0 else 0.0
                                    profit_mult = min(3.5, 1.0 + (balance - 1000.0) / 1000.0 * (accel_step - 1.0))
                                    current_risk = base_risk * profit_mult
                                    active_risk = (current_risk * dd_mult) if current_dd >= dd_thresh else current_risk
                                    
                                    risk_amount = balance * active_risk
                                    pos_size = risk_amount / sl_dist
                                    
                                    exit_price = entry_price
                                    hit_tp = False; hit_sl = False
                                    
                                    for j in range(i + 1, min(i + 240, n)):
                                        if l[j] <= sl_price: exit_price = sl_price; hit_sl = True; break
                                        elif h[j] >= tp_price: exit_price = tp_price; hit_tp = True; break
                                                
                                    if not hit_tp and not hit_sl: exit_price = c[min(i + 240, n - 1)]
                                    
                                    trade_pnl = (exit_price - entry_price) * pos_size
                                    balance += trade_pnl
                                    
                                    if balance > peak_balance: peak_balance = balance
                                    dd = (peak_balance - balance) / peak_balance
                                    if dd > max_dd_pct: max_dd_pct = dd
                                    trades.append(trade_pnl)
                                    
                            win_trades = [p for p in trades if p > 0]
                            total_t = len(trades)
                            win_t = len(win_trades)
                            wr = (win_t / total_t * 100.0) if total_t else 0.0
                            gp = sum(win_trades)
                            gl = abs(sum([p for p in trades if p < 0]))
                            pf = gp / gl if gl > 0 else 999.0
                            net_p = balance - 1000.0
                            
                            all_configs.append((balance, net_p, wr, max_dd_pct, pf, total_t, base_risk, accel_step, dd_thresh, dd_mult, sl_mult, tp_mult))
                            
    all_configs.sort(key=lambda x: x[0], reverse=True)
    print("Top 15 Unconstrained CP-3000 Configurations:")
    for c in all_configs[:15]:
        print(f"Bal: ${c[0]:,.2f} | NetP: ${c[1]:,.2f} | WR: {c[2]:.2f}% | MaxDD: {c[3]*100:.2f}% | PF: {c[4]:.2f} | Trades: {c[5]} | BaseRisk: {c[6]*100:.1f}% | Accel: {c[7]}x | DDBrake: {c[8]*100:.0f}%->{c[9]:.2f}x | SL: {c[10]}x | TP: {c[11]}x")

if __name__ == '__main__':
    run_test()
