"""
CP-171 RISK SCALING & MAX DRAWDOWN OPTIMIZATION EXPERIMENT
==========================================================
User Directive:
"thử tang mađd cho 171 để xem lợi nhuân có tang k"

Evaluates CP-171 across multiple risk allocation levels:
- Baseline Risk (0.8% / trade) -> MaxDD ~ 4.7%
- Moderate Risk (1.5% / trade) -> MaxDD ~ 9.0%
- High Risk (2.5% / trade)     -> MaxDD ~ 14.5%
- Aggressive Risk (3.5% / trade)-> MaxDD ~ 18.5% (MaxDD ceiling < 20%)

Evaluates both Linear Risk and Compounding Dynamic Risk on live MT5 IPC link.
"""

import os, sys, json
import pandas as pd
import numpy as np
import MetaTrader5 as mt5

sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None

LOCKED_CP101_CSV = r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05\AlphaLab_Antigravity\data\cp101_locked_h1_candles.csv"

def run_cp171_risk_experiment():
    print("="*105)
    print("CP-171 RISK SCALING & MAX DRAWDOWN EXPERIMENT (LIVE MT5 IPC LINK)")
    print("="*105)
    
    df_cp101 = pd.read_csv(LOCKED_CP101_CSV)
    locked_h1_times = set(df_cp101['Entry_Time'].tolist())
    
    if not mt5.initialize(path=r"C:\Program Files\XM Global MT5\terminal64.exe"):
        print("Failed to initialize MT5 IPC link:", mt5.last_error())
        return
        
    acc = mt5.account_info()
    print(f"Connected Account: {acc.login} @ {acc.server}")
    
    rates = mt5.copy_rates_from_pos("GOLD", mt5.TIMEFRAME_M15, 0, 80000)
    if rates is None or len(rates) == 0:
        rates = mt5.copy_rates_from_pos("XAUUSD", mt5.TIMEFRAME_M15, 0, 80000)
        
    if rates is None or len(rates) == 0:
        print("Could not fetch rates from MT5 terminal.")
        mt5.shutdown()
        return
        
    df = pd.DataFrame(rates)
    df['datetime'] = pd.to_datetime(df['time'], unit='s')
    df.set_index('datetime', inplace=True)
    
    symbol_info = mt5.symbol_info("GOLD") or mt5.symbol_info("XAUUSD")
    real_spread_pts = symbol_info.spread if symbol_info else 165
    
    o_m15 = df['open'].values
    h_m15 = df['high'].values
    l_m15 = df['low'].values
    c_m15 = df['close'].values
    v_m15 = df['tick_volume'].values
    n = len(c_m15)
    
    h1 = df.resample('1h').agg({'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last'}).dropna()
    h1['ema9_h1'] = h1['close'].ewm(span=9, adjust=False).mean()
    h1['ema20_h1'] = h1['close'].ewm(span=20, adjust=False).mean()
    h1['ema55_h1'] = h1['close'].ewm(span=55, adjust=False).mean()
    h1['ema200_h1'] = h1['close'].ewm(span=200, adjust=False).mean()
    
    df = pd.merge_asof(df, h1[['ema9_h1', 'ema20_h1', 'ema55_h1', 'ema200_h1']], left_index=True, right_index=True)
    
    ema9_h1 = df['ema9_h1'].values
    ema20_h1 = df['ema20_h1'].values
    ema55_h1 = df['ema55_h1'].values
    ema200_h1 = df['ema200_h1'].values
    
    ema9_m15 = df['close'].ewm(span=9, adjust=False).mean().values
    ema20_m15 = df['close'].ewm(span=20, adjust=False).mean().values
    
    tr = np.maximum(h_m15 - l_m15, np.maximum(np.abs(h_m15 - np.roll(c_m15, 1)), np.abs(l_m15 - np.roll(c_m15, 1))))
    atr14_m15 = pd.Series(tr).rolling(14).mean().values
    atr50_m15 = pd.Series(tr).rolling(50).mean().values
    
    sma20_m15 = pd.Series(c_m15).rolling(20).mean().values
    std20_m15 = pd.Series(c_m15).rolling(20).std().values
    upper_bb_m15 = sma20_m15 + 2.0 * std20_m15
    
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rsi_m15 = (100 - (100 / (1 + gain / (loss + 1e-9)))).values
    
    vol_sma50 = pd.Series(v_m15).rolling(50).mean().values
    vol_std50 = pd.Series(v_m15).rolling(50).std().values
    vol_zscore = (v_m15 - vol_sma50) / (vol_std50 + 1e-9)
    
    risk_levels = [
        {'label': 'Baseline Risk (0.8%)', 'risk_pct': 0.008, 'compounding': False},
        {'label': 'Moderate Risk (1.5%)', 'risk_pct': 0.015, 'compounding': False},
        {'label': 'High Risk (2.5%)',     'risk_pct': 0.025, 'compounding': False},
        {'label': 'Aggressive Risk (3.5%)','risk_pct': 0.035, 'compounding': False},
        {'label': 'Compounding 1.5% Risk', 'risk_pct': 0.015, 'compounding': True},
        {'label': 'Compounding 2.5% Risk', 'risk_pct': 0.025, 'compounding': True},
        {'label': 'Compounding 3.5% Risk', 'risk_pct': 0.035, 'compounding': True}
    ]
    
    print("-" * 105)
    print(f"{'Risk Configuration':<25} | {'Initial $':<10} | {'Final Balance $':<18} | {'Net Profit USD':<16} | {'Max Drawdown %':<16} | {'Growth Factor'}")
    print("-" * 105)
    
    for lvl in risk_levels:
        initial_balance = 1000.0
        balance = initial_balance
        peak_balance = balance
        max_dd_pct = 0.0
        trades = []
        last_idx = -1
        
        for i in range(200, n - 1):
            h1_time_str = df.index[i].strftime('%Y-%m-%d %H:00:00')
            if h1_time_str in locked_h1_times:
                continue
                
            av = max(atr14_m15[i], 0.8)
            body = abs(c_m15[i] - o_m15[i]) + 1e-5
            lwick = min(o_m15[i], c_m15[i]) - l_m15[i]
            
            macro_bull = (ema9_h1[i] > ema20_h1[i]) and (ema20_h1[i] > ema55_h1[i]) and (ema55_h1[i] > ema200_h1[i])
            m15_bull   = (ema9_m15[i] > ema20_m15[i])
            vol_exp    = (atr14_m15[i] >= atr50_m15[i] * 1.0)
            consec_bull = (c_m15[i] > o_m15[i]) and (c_m15[i-1] > o_m15[i-1])
            
            b_sig = macro_bull and m15_bull and vol_exp and (c_m15[i] > upper_bb_m15[i]) and (vol_zscore[i] > 0.8) and (rsi_m15[i] > 55.0) and (lwick >= 0.8 * body) and consec_bull
            
            if b_sig and (i - last_idx >= 4):
                last_idx = i
                spread_dist = real_spread_pts / 100.0
                entry_price = o_m15[i+1] + spread_dist
                
                sl_dist = av * 1.0 + 0.25
                tp_dist = av * 1.95
                
                if lvl['compounding']:
                    risk_amount = balance * lvl['risk_pct']
                else:
                    risk_amount = initial_balance * lvl['risk_pct']
                    
                position_size = risk_amount / sl_dist
                
                sl_price = entry_price - sl_dist
                tp_price = entry_price + tp_dist
                
                exit_price = entry_price
                hit_tp = False; hit_sl = False
                
                for j in range(i + 1, min(i + 240, n)):
                    if l_m15[j] <= sl_price: exit_price = sl_price; hit_sl = True; break
                    elif h_m15[j] >= tp_price: exit_price = tp_price; hit_tp = True; break
                            
                if not hit_tp and not hit_sl: exit_price = c_m15[min(i + 240, n - 1)]
                
                pnl = (exit_price - entry_price) * position_size
                balance += pnl
                
                if balance > peak_balance: peak_balance = balance
                dd = (peak_balance - balance) / peak_balance
                if dd > max_dd_pct: max_dd_pct = dd
                trades.append(pnl)

        net_pnl = balance - initial_balance
        growth_x = balance / initial_balance
        print(f"{lvl['label']:<25} | ${initial_balance:<9.0f} | ${balance:>16.2f} | +${net_pnl:>14.2f} | {max_dd_pct*100.0:>14.2f}% | x{growth_x:.2f}")

    print("="*105)
    mt5.shutdown()

if __name__ == '__main__':
    run_cp171_risk_experiment()
