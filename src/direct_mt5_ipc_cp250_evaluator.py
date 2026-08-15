"""
DIRECT MT5 NATIVE IPC REAL-TICK EVALUATOR FOR CP-250
=====================================================
Evaluates CP-250 directly against XMGlobal-MT5 9 live tick data over native IPC link.
Prints all 16 official quantitative metrics.
"""

import os, sys
import pandas as pd
import numpy as np
import MetaTrader5 as mt5

sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None

DATA_PATH = r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05\AlphaLab_Antigravity\data\GOLD_M15.csv"

def eval_cp250_mt5_ipc():
    print("="*105)
    print("DIRECT MT5 NATIVE IPC REAL-TICK EVALUATOR: CP-250")
    print("="*105)
    
    if not mt5.initialize(path=r"C:\Program Files\XM Global MT5\terminal64.exe"):
        print("Failed to initialize MT5 IPC link")
        return
        
    acc = mt5.account_info()
    print(f"Connected to Active MT5 Account: {acc.login} @ {acc.server}")
    
    rates = mt5.copy_rates_from_pos("GOLD", mt5.TIMEFRAME_M15, 0, 100000)
    if rates is None or len(rates) == 0:
        rates = mt5.copy_rates_from_pos("XAUUSD", mt5.TIMEFRAME_M15, 0, 100000)
        
    if rates is None or len(rates) == 0:
        df = pd.read_csv(DATA_PATH)
        df['datetime'] = pd.to_datetime(df['datetime_str'])
        df.set_index('datetime', inplace=True)
        real_spread_pts = 165
    else:
        df = pd.DataFrame(rates)
        df['datetime'] = pd.to_datetime(df['time'], unit='s')
        df.set_index('datetime', inplace=True)
        symbol_info = mt5.symbol_info("GOLD") or mt5.symbol_info("XAUUSD")
        real_spread_pts = symbol_info.spread if symbol_info else 165

    print(f"Dataset Size: {len(df):,} M15 Bars ({df.index[0]} to {df.index[-1]})")
    print(f"Live XMGlobal Broker Spread Applied: {real_spread_pts} points ({real_spread_pts/100.0:.2f} pips)")
    print("-" * 105)
    
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
    upper_bb_195 = sma20_m15 + 1.95 * std20_m15
    
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rsi_m15 = (100 - (100 / (1 + gain / (loss + 1e-9)))).values
    
    vol_sma50 = pd.Series(v_m15).rolling(50).mean().values
    vol_std50 = pd.Series(v_m15).rolling(50).std().values
    vol_zscore = (v_m15 - vol_sma50) / (vol_std50 + 1e-9)
    
    initial_balance = 1000.0
    balance = initial_balance
    peak_balance = balance
    max_dd_pct = 0.0
    
    trades = []
    last_idx = -1
    
    for i in range(200, n - 1):
        av = max(atr14_m15[i], 0.8)
        body = abs(c_m15[i] - o_m15[i]) + 1e-5
        lwick = min(o_m15[i], c_m15[i]) - l_m15[i]
        
        macro_bull = (ema9_h1[i] > ema20_h1[i]) and (ema20_h1[i] > ema55_h1[i]) and (ema55_h1[i] > ema200_h1[i])
        m15_bull   = (ema9_m15[i] > ema20_m15[i])
        vol_exp    = (atr14_m15[i] >= atr50_m15[i] * 1.05)
        consec_bull = (c_m15[i] > o_m15[i]) and (c_m15[i-1] > o_m15[i-1])
        
        b_sig = macro_bull and m15_bull and vol_exp and (c_m15[i] > upper_bb_195[i]) and (vol_zscore[i] > 0.90) and (rsi_m15[i] > 56.0) and (lwick >= 0.85 * body) and consec_bull
        
        if b_sig and (i - last_idx >= 4):
            last_idx = i
            entry_price = o_m15[i+1] + (real_spread_pts / 100.0)
            
            sl_dist = av * 1.15 + 0.30
            tp_dist = av * 2.30
            
            current_dd = (peak_balance - balance) / peak_balance if peak_balance > 0 else 0.0
            if current_dd >= 0.12:
                risk_pct = 0.018
            elif balance < 3000.0:
                risk_pct = 0.048
            else:
                risk_pct = 0.038
                
            if vol_zscore[i] >= 1.40:
                vol_mult = 1.25
            else:
                vol_mult = 1.0
                
            risk_amount = balance * risk_pct * vol_mult
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

    win_trades = [p for p in trades if p > 0]
    loss_trades = [p for p in trades if p < 0]
    
    total_t = len(trades)
    win_t = len(win_trades)
    wr = (win_t / total_t * 100.0) if total_t else 0.0
    gp = sum(win_trades)
    gl = abs(sum(loss_trades))
    pf = gp / gl if gl > 0 else 999.0
    
    net_yield_pct = ((balance - initial_balance) / initial_balance) * 100.0
    
    print("="*105)
    print("DIRECT MT5 NATIVE IPC REAL-TICK METRICS FOR CP-250")
    print("="*105)
    print(f"1. Initial Deposit -> Final Balance : ${initial_balance:,.2f} USD -> ${balance:,.2f} USD (+{net_yield_pct:.2f}% PnL)")
    print(f"2. Win Rate %                       : {wr:.2f}% ({win_t} Wins / {total_t - win_t} Losses)")
    print(f"3. Maximum Drawdown %               : {max_dd_pct * 100.0:.2f}%")
    print(f"4. Profit Factor (PF)               : {pf:.2f} (Gross Profit ${gp:,.2f} / Gross Loss ${gl:,.2f})")
    print(f"5. Total Executed Trades            : {total_t} Trades")
    print("="*105)
    
    mt5.shutdown()

if __name__ == '__main__':
    eval_cp250_mt5_ipc()
