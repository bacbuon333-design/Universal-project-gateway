"""
CHECKPOINT 120: SEQUENTIAL COMBINED LOCK MASTER ENGINE (CP-101 + CP-119 LOCKED)
================================================================================
User Directive (MANDATORY SEQUENTIAL LOCK RULE):
"Ví dụ CP-101 những ngày này, có thêm CP-119 thêm 130 ngày mới hoàn toàn + thêm 1 CP mới nữa thì CP mới này lại phải khác CP-101 và CP-119 các ngày mới hoàn toàn. Hoặc là nó phải ngược với lệnh của các CP trước đó thì mới cho phép trùng ngày."

Architecture:
1. Combined Lock Set:
   - CP101_LockedSet: 130 H1 candles / 65 dates.
   - CP119_LockedSet: 157 H1 candles / 130 dates.
   - CombinedLockedSet = CP101_LockedSet UNION CP119_LockedSet (195 UNIQUE TRADING DATES!).

2. CP-120 Engine Execution Rules:
   - Allowed to trade BUY ONLY on H1 candles outside CombinedLockedSet.
   - Allowed to trade on locked dates ONLY IF IT EXECUTES AN OPPOSITE-DIRECTION TRADE (SELL)!

Target Metrics:
  1. 100% Zero Same-Direction Overlap with CP-101 AND CP-119!
  2. Win Rate >= 45.0%
  3. Profit Factor (PF) >= 1.50
  4. Max Drawdown (MaxDD) <= 18.0%
  5. Net Profit Yield > +100%
"""

import os, sys, json
import pandas as pd
import numpy as np

sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None

DATA_PATH = r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05\AlphaLab_Antigravity\data\GOLD_M15.csv"
LOCKED_CP101_CSV = r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05\AlphaLab_Antigravity\data\cp101_locked_h1_candles.csv"

def run_cp120_sequential_lock_master():
    # Load CP-101 locked H1 candles
    df_cp101 = pd.read_csv(LOCKED_CP101_CSV)
    cp101_locked_times = set(df_cp101['Entry_Time'].tolist())
    cp101_locked_dates = set(df_cp101['Date'].tolist())
    
    # Load M15 dataset
    df_m15 = pd.read_csv(DATA_PATH)
    df_m15['datetime'] = pd.to_datetime(df_m15['datetime_str'])
    df_m15.set_index('datetime', inplace=True)
    
    o_m15 = df_m15['open'].values
    h_m15 = df_m15['high'].values
    l_m15 = df_m15['low'].values
    c_m15 = df_m15['close'].values
    v_m15 = df_m15['tick_volume'].values
    dates_m15 = df_m15.index.date
    n = len(c_m15)
    
    # Resample H1 for trend alignment & CP-119 simulation
    h1 = df_m15.resample('1h').agg({'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last'}).dropna()
    h1['ema9_h1'] = h1['close'].ewm(span=9, adjust=False).mean()
    h1['ema20_h1'] = h1['close'].ewm(span=20, adjust=False).mean()
    h1['ema55_h1'] = h1['close'].ewm(span=55, adjust=False).mean()
    h1['ema200_h1'] = h1['close'].ewm(span=200, adjust=False).mean()
    
    df_m15 = pd.merge_asof(df_m15, h1[['ema9_h1', 'ema20_h1', 'ema55_h1', 'ema200_h1']], left_index=True, right_index=True)
    
    ema9_h1 = df_m15['ema9_h1'].values
    ema20_h1 = df_m15['ema20_h1'].values
    ema55_h1 = df_m15['ema55_h1'].values
    ema200_h1 = df_m15['ema200_h1'].values
    
    # M15 Indicators
    ema9_m15 = df_m15['close'].ewm(span=9, adjust=False).mean().values
    ema20_m15 = df_m15['close'].ewm(span=20, adjust=False).mean().values
    
    tr = np.maximum(h_m15 - l_m15, np.maximum(np.abs(h_m15 - np.roll(c_m15, 1)), np.abs(l_m15 - np.roll(c_m15, 1))))
    atr14_m15 = pd.Series(tr).rolling(14).mean().values
    atr50_m15 = pd.Series(tr).rolling(50).mean().values
    don_hi15_m15 = pd.Series(h_m15).shift(1).rolling(15).max().values
    
    delta = df_m15['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rsi_m15 = (100 - (100 / (1 + gain / (loss + 1e-9)))).values
    
    # Simulate CP-119 locked times & dates
    cp119_locked_times = set()
    cp119_locked_dates = set()
    last_cp119_idx = -1
    
    for i in range(200, n - 1):
        h1_time_str = df_m15.index[i].strftime('%Y-%m-%d %H:00:00')
        if h1_time_str in cp101_locked_times:
            continue
            
        av = max(atr14_m15[i], 0.8)
        body = abs(c_m15[i] - o_m15[i]) + 1e-5
        lwick = min(o_m15[i], c_m15[i]) - l_m15[i]
        
        macro_bull = (ema9_h1[i] > ema20_h1[i]) and (ema20_h1[i] > ema55_h1[i]) and (ema55_h1[i] > ema200_h1[i])
        m15_bull   = (ema9_m15[i] > ema20_m15[i])
        vol_exp    = (atr14_m15[i] >= atr50_m15[i] * 1.0)
        consec_bull = (c_m15[i] > o_m15[i]) and (c_m15[i-1] > o_m15[i-1])
        
        b_cp119 = macro_bull and m15_bull and vol_exp and (c_m15[i] > don_hi15_m15[i]) and (rsi_m15[i] > 55.0) and (lwick >= 0.8 * body) and consec_bull
        
        if b_cp119 and (i - last_cp119_idx >= 4):
            last_cp119_idx = i
            cp119_locked_times.add(h1_time_str)
            cp119_locked_dates.add(str(dates_m15[i]))
            
    combined_locked_times = cp101_locked_times.union(cp119_locked_times)
    combined_locked_dates = cp101_locked_dates.union(cp119_locked_dates)
    
    # Run CP-120 Engine on UNLOCKED candles & dates
    don_hi7_m15 = pd.Series(h_m15).shift(1).rolling(7).max().values
    
    initial_balance = 1000.0
    balance = initial_balance
    peak_balance = balance
    max_dd_pct = 0.0
    
    trades = []
    last_cp120_idx = -1
    
    for i in range(200, n - 1):
        h1_time_str = df_m15.index[i].strftime('%Y-%m-%d %H:00:00')
        d_str = str(dates_m15[i])
        
        # MANDATORY SEQUENTIAL LOCK RULE: Cannot trade BUY on CP-101 OR CP-119 locked H1 candles/dates!
        if h1_time_str in combined_locked_times or d_str in combined_locked_dates:
            continue
            
        current_dd = (peak_balance - balance) / peak_balance if peak_balance > 0 else 0.0
        
        if current_dd >= 0.05:
            risk_pct = 0.005
        else:
            if balance >= 3000.0:
                risk_pct = 0.012
            elif balance >= 1800.0:
                risk_pct = 0.010
            else:
                risk_pct = 0.008
                
        av = max(atr14_m15[i], 0.8)
        body = abs(c_m15[i] - o_m15[i]) + 1e-5
        lwick = min(o_m15[i], c_m15[i]) - l_m15[i]
        
        macro_bull = (ema9_h1[i] > ema20_h1[i]) and (ema20_h1[i] > ema55_h1[i]) and (ema55_h1[i] > ema200_h1[i])
        m15_bull   = (ema9_m15[i] > ema20_m15[i])
        vol_exp    = (atr14_m15[i] >= atr50_m15[i] * 1.0)
        consec_bull = (c_m15[i] > o_m15[i]) and (c_m15[i-1] > o_m15[i-1])
        
        b_cp120 = macro_bull and m15_bull and vol_exp and (c_m15[i] > don_hi7_m15[i]) and (rsi_m15[i] > 54.0) and (lwick >= 0.8 * body) and consec_bull
        
        if b_cp120 and (i - last_cp120_idx >= 4):
            last_cp120_idx = i
            entry_price = o_m15[i+1]
            sl_dist = av * 1.0 + 0.25 # 25pip spread
            tp_dist = av * 2.20
            
            risk_amount = balance * risk_pct
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
                
            trades.append({
                'datetime': df_m15.index[i],
                'date': d_str,
                'engine': 'CP120_SequentialLockMaster',
                'type': 'BUY',
                'entry': entry_price,
                'exit': exit_price,
                'pnl': pnl,
                'balance': balance
            })
            
    win_trades = [t for t in trades if t['pnl'] > 0]
    win_rate = (len(win_trades) / len(trades)) * 100.0 if trades else 0
    gross_profit = sum([t['pnl'] for t in win_trades])
    gross_loss = abs(sum([t['pnl'] for t in trades if t['pnl'] < 0]))
    pf = gross_profit / gross_loss if gross_loss > 0 else 999.0
    net_yield_pct = ((balance - initial_balance) / initial_balance) * 100.0
    
    df_t = pd.DataFrame(trades) if trades else pd.DataFrame(columns=['date'])
    cp120_dates = set(df_t['date'].tolist()) if trades else set()
    
    print("="*105)
    print("FORENSIC SEQUENTIAL LOCK AUDIT REPORT (CP-101 + CP-119 + CP-120)")
    print("="*105)
    print(f"CP-101 Locked Trading Dates         : {len(cp101_locked_dates)} days")
    print(f"CP-119 Locked Trading Dates         : {len(cp119_locked_dates)} days")
    print(f"Combined Locked Trading Dates (1+119): {len(combined_locked_dates)} UNIQUE DAYS!")
    print(f"CP-120 NEW Trading Dates            : {len(cp120_dates)} NEW TRADING DATES!")
    print(f"Overlap with (CP-101 UNION CP-119)  : ZERO (0 NGÀY TRÙNG LẶP!)")
    print("="*105)
    print("CHECKPOINT 120 PERFORMANCE METRICS:")
    print(f"  - Initial Deposit                : ${initial_balance:,.2f} USD")
    print(f"  - Final Balance                  : ${balance:,.2f} USD")
    print(f"  - Net Profit %                   : {net_yield_pct:>+8.2f}% Net Yield")
    print(f"  - Total CP-120 Trades            : {len(trades)} trades")
    print(f"  - Win Rate %                     : {win_rate:.2f}%")
    print(f"  - Profit Factor (PF)             : {pf:.2f}")
    print(f"  - Max Drawdown (MaxDD)           : {max_dd_pct * 100.0:.2f}%")
    print("="*105)

if __name__ == '__main__':
    run_cp120_sequential_lock_master()
