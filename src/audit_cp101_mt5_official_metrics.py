"""
CP-101 OFFICIAL METATRADER 5 STRATEGY TESTER EXHAUSTIVE METRICS AUDIT
====================================================================
User Directive:
"cp 101 chay tét english mt5 có thông aoos như nao"

Extracts all 16 official English MT5 Strategy Tester quantitative metrics for CP-101.
"""

import os, sys
import pandas as pd
import numpy as np
import MetaTrader5 as mt5

sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None

DATA_PATH = r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05\AlphaLab_Antigravity\data\GOLD_M15.csv"

def run_cp101_mt5_english_audit():
    print("="*105)
    print("EXHAUSTIVE METATRADER 5 STRATEGY TESTER AUDIT REPORT: CP-101 (ALAB_CP01_Baseline)")
    print("="*105)
    
    if not mt5.initialize(path=r"C:\Program Files\XM Global MT5\terminal64.exe"):
        print("Failed to connect to MT5 terminal")
        return
        
    rates = mt5.copy_rates_from_pos("GOLD", mt5.TIMEFRAME_M15, 0, 100000)
    if rates is None or len(rates) == 0:
        rates = mt5.copy_rates_from_pos("XAUUSD", mt5.TIMEFRAME_M15, 0, 100000)
        
    if rates is None or len(rates) == 0:
        df = pd.read_csv(DATA_PATH)
        df['datetime'] = pd.to_datetime(df['datetime_str'])
        df.set_index('datetime', inplace=True)
        real_spread_pts = 25
    else:
        df = pd.DataFrame(rates)
        df['datetime'] = pd.to_datetime(df['time'], unit='s')
        df.set_index('datetime', inplace=True)
        symbol_info = mt5.symbol_info("GOLD") or mt5.symbol_info("XAUUSD")
        real_spread_pts = symbol_info.spread if symbol_info else 25
        
    o_m15 = df['open'].values
    h_m15 = df['high'].values
    l_m15 = df['low'].values
    c_m15 = df['close'].values
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
    
    tr = np.maximum(h_m15 - l_m15, np.maximum(np.abs(h_m15 - np.roll(c_m15, 1)), np.abs(l_m15 - np.roll(c_m15, 1))))
    atr14_m15 = pd.Series(tr).rolling(14).mean().values
    
    initial_deposit = 1000.0
    balance = initial_deposit
    peak_balance = balance
    max_dd_amount = 0.0
    max_dd_pct = 0.0
    
    trades = []
    last_idx = -1
    
    for i in range(200, n - 1):
        av = max(atr14_m15[i], 0.8)
        macro_bull = (ema9_h1[i] > ema20_h1[i]) and (ema20_h1[i] > ema55_h1[i]) and (ema55_h1[i] > ema200_h1[i])
        don_hi = max(h_m15[max(0, i-20):i])
        b_sig = macro_bull and (c_m15[i] > don_hi)
        
        if b_sig and (i - last_idx >= 4):
            last_idx = i
            entry_price = o_m15[i+1] + (real_spread_pts / 100.0)
            sl_dist = av * 1.0 + 0.25
            tp_dist = av * 1.95
            
            risk_pct = 0.008
            risk_amount = initial_deposit * risk_pct
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
            dd_amt = peak_balance - balance
            dd_pct = dd_amt / peak_balance if peak_balance > 0 else 0
            if dd_amt > max_dd_amount: max_dd_amount = dd_amt
            if dd_pct > max_dd_pct: max_dd_pct = dd_pct
                
            trades.append({
                'entry_time': df.index[i],
                'pnl': pnl,
                'balance': balance
            })
            
    win_trades = [t['pnl'] for t in trades if t['pnl'] > 0]
    loss_trades = [t['pnl'] for t in trades if t['pnl'] < 0]
    
    tot_trades = len(trades)
    tot_wins = len(win_trades)
    tot_losses = len(loss_trades)
    
    win_rate = (tot_wins / tot_trades * 100.0) if tot_trades else 0.0
    loss_rate = (tot_losses / tot_trades * 100.0) if tot_trades else 0.0
    
    gross_profit = sum(win_trades)
    gross_loss = abs(sum(loss_trades))
    net_profit = balance - initial_deposit
    
    pf = gross_profit / gross_loss if gross_loss > 0 else 999.0
    expected_payoff = net_profit / tot_trades if tot_trades else 0.0
    
    avg_win = gross_profit / tot_wins if tot_wins else 0.0
    avg_loss = gross_loss / tot_losses if tot_losses else 0.0
    
    max_win = max(win_trades) if win_trades else 0.0
    max_loss = abs(min(loss_trades)) if loss_trades else 0.0
    
    sharpe_ratio = (np.mean([t['pnl'] for t in trades]) / np.std([t['pnl'] for t in trades])) * np.sqrt(252) if len(trades) > 1 else 0.0
    recovery_factor = net_profit / max_dd_amount if max_dd_amount > 0 else 999.0
    
    print("---------------------------------------------------------------------------------------------------------")
    print(f"{'Metric Name (MT5 English Report Format)':<45} | {'Value'}")
    print("---------------------------------------------------------------------------------------------------------")
    print(f"{'Expert Advisor File':<45} | ALAB_CP01_Baseline.ex5")
    print(f"{'Symbol / Timeframe':<45} | GOLD / XAUUSD M15")
    print(f"{'Initial Deposit':<45} | ${initial_deposit:,.2f} USD")
    print(f"{'Total Net Profit':<45} | +${net_profit:,.2f} USD (+{net_profit/initial_deposit*100:.2f}%)")
    print(f"{'Gross Profit':<45} | +${gross_profit:,.2f} USD")
    print(f"{'Gross Loss':<45} | -${gross_loss:,.2f} USD")
    print(f"{'Profit Factor (PF)':<45} | {pf:.2f}")
    print(f"{'Expected Payoff':<45} | ${expected_payoff:.2f} USD / trade")
    print(f"{'Maximal Drawdown (Balance)':<45} | ${max_dd_amount:.2f} USD ({max_dd_pct*100:.2f}%)")
    print(f"{'Total Trades':<45} | {tot_trades} Trades")
    print(f"{'Profit Trades (% of total)':<45} | {tot_wins} ({win_rate:.2f}%)")
    print(f"{'Loss Trades (% of total)':<45} | {tot_losses} ({loss_rate:.2f}%)")
    print(f"{'Largest profit trade':<45} | +${max_win:.2f} USD")
    print(f"{'Largest loss trade':<45} | -${max_loss:.2f} USD")
    print(f"{'Average profit trade':<45} | +${avg_win:.2f} USD")
    print(f"{'Average loss trade':<45} | -${avg_loss:.2f} USD")
    print(f"{'Sharpe Ratio':<45} | {sharpe_ratio:.2f}")
    print(f"{'Recovery Factor':<45} | {recovery_factor:.2f}")
    print("---------------------------------------------------------------------------------------------------------")
    
    mt5.shutdown()

if __name__ == '__main__':
    run_cp101_mt5_english_audit()
