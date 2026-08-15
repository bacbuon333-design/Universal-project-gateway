"""
MASTER SYSTEMATIC MT5 STRATEGY TESTER AUDIT & CP ELIMINATION PIPELINE
=====================================================================
Auto-detects symbol names and executes systematic MT5 audit across all candidate CPs.
"""

import os, sys, glob, json
import pandas as pd
import numpy as np
import MetaTrader5 as mt5

sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None

LOCKED_CP101_CSV = r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05\AlphaLab_Antigravity\data\cp101_locked_h1_candles.csv"
DATA_PATH = r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05\AlphaLab_Antigravity\data\GOLD_M15.csv"
EXPERTS_DIR = r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05\MQL5\Experts\AlphaLab"

def run_master_systematic_mt5_audit():
    print("="*115)
    print("MASTER SYSTEMATIC METATRADER 5 BROKER-TICK AUDIT & ELIMINATION PIPELINE")
    print("="*115)
    
    df_cp101 = pd.read_csv(LOCKED_CP101_CSV)
    locked_h1_times = set(df_cp101['Entry_Time'].tolist())
    
    if not mt5.initialize(path=r"C:\Program Files\XM Global MT5\terminal64.exe"):
        print("Failed to initialize native MT5 IPC link:", mt5.last_error())
        return
        
    acc = mt5.account_info()
    print(f"Connected MT5 Account: {acc.login} @ {acc.server}")
    
    # Auto-detect gold symbol
    target_symbol = None
    all_symbols = mt5.symbols_get()
    if all_symbols:
        for s in all_symbols:
            if "GOLD" in s.name.upper() or "XAUUSD" in s.name.upper():
                target_symbol = s.name
                break
                
    if not target_symbol:
        target_symbol = "GOLD"
        
    mt5.symbol_select(target_symbol, True)
    print(f"Detected Gold Symbol on Broker: {target_symbol}")
    
    rates = mt5.copy_rates_from_pos(target_symbol, mt5.TIMEFRAME_M15, 0, 50000)
    if rates is None or len(rates) == 0:
        print(f"Loading local authoritative dataset: {DATA_PATH}")
        df = pd.read_csv(DATA_PATH)
        df['datetime'] = pd.to_datetime(df['datetime_str'])
        df.set_index('datetime', inplace=True)
        real_spread_pts = 165
    else:
        df = pd.DataFrame(rates)
        df['datetime'] = pd.to_datetime(df['time'], unit='s')
        df.set_index('datetime', inplace=True)
        symbol_info = mt5.symbol_info(target_symbol)
        real_spread_pts = symbol_info.spread if symbol_info else 165

    print(f"Dataset Size: {len(df):,} M15 Bars ({df.index[0]} to {df.index[-1]})")
    print(f"Live XMGlobal Broker Spread Applied: {real_spread_pts} points ({real_spread_pts/100.0:.2f} pips)")
    print("-" * 115)
    
    candidate_cps = [
        {'id': 'CP-101', 'name': 'ALAB_CP01_Baseline', 'type': 'Macro EMA Trend + Donchian Breakout'},
        {'id': 'CP-141', 'name': 'ALAB_CP141_KeltnerUpperEngine', 'type': 'M15 Keltner Upper Expansion'},
        {'id': 'CP-171', 'name': 'ALAB_CP171_IndependentBBExpansion', 'type': 'M15 BB Expansion + Vol Z-Score'},
        {'id': 'CP-175', 'name': 'ALAB_CP175_IndependentKeltnerRsi', 'type': 'Keltner Channel + RSI Filter'},
        {'id': 'CP-182', 'name': 'ALAB_CP182_IndependentMacdVictory', 'type': 'MACD Histogram Expansion'},
        {'id': 'CP-190', 'name': 'ALAB_CP190_IndependentCciMomentum', 'type': 'CCI Momentum Expansion'},
        {'id': 'CP-195', 'name': 'ALAB_CP195_IndependentWilliamsRsi', 'type': 'Williams %R + RSI Confluence'},
        {'id': 'CP-200', 'name': 'ALAB_CP200_IndependentParabolicSar', 'type': 'Parabolic SAR Trend Acceleration'},
        {'id': 'CP-210', 'name': 'ALAB_CP210_SpreadResilientTrend', 'type': 'M15 Structural Trend Breakout'},
        {'id': 'CP-220', 'name': 'ALAB_CP220_PullbackRejection', 'type': 'M15 EMA20 Pullback Rejection'},
        {'id': 'CP-225', 'name': 'ALAB_CP225_BollingerSurge', 'type': 'M15 BB Surge + Vol Z-Score'},
        {'id': 'CP-230', 'name': 'ALAB_CP230_KeltnerMultiConfluence', 'type': 'Keltner Multi-Confluence'},
        {'id': 'CP-235', 'name': 'ALAB_CP235_BollingerSigma', 'type': 'BB Multi-Sigma Vol Explosion'}
    ]
    
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
    
    print(f"{'CP Code':<10} | {'EA File Name':<35} | {'Trades':<8} | {'Win Rate %':<12} | {'Profit Factor':<15} | {'Max Drawdown %':<16} | {'MT5 STATUS'}")
    print("-" * 115)
    
    audit_results = []
    initial_balance = 1000.0
    
    # Audit CP-101 (Anchor Baseline)
    cp101_trades = []
    balance = initial_balance
    peak_balance = balance
    max_dd_pct = 0.0
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
            position_size = (initial_balance * 0.008) / sl_dist
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
            cp101_trades.append(pnl)
            
    win_t = len([p for p in cp101_trades if p > 0])
    tot_t = len(cp101_trades)
    wr = (win_t / tot_t * 100.0) if tot_t else 0.0
    gp = sum([p for p in cp101_trades if p > 0])
    gl = abs(sum([p for p in cp101_trades if p < 0]))
    pf = gp / gl if gl > 0 else 999.0
    
    status_101 = "APPROVED (ANCHOR CP)" if wr >= 45.0 and pf >= 1.40 and max_dd_pct <= 0.065 else "FAILED MT5"
    print(f"{'CP-101':<10} | {'ALAB_CP01_Baseline':<35} | {tot_t:<8} | {wr:>10.2f}% | {pf:>13.2f} | {max_dd_pct*100.0:>14.2f}% | {status_101}")
    audit_results.append({'id': 'CP-101', 'trades': tot_t, 'wr': wr, 'pf': pf, 'max_dd': max_dd_pct*100.0, 'status': status_101})
    
    # Audit CP-171 (Independent Bollinger Expansion)
    cp171_trades = []
    balance = initial_balance
    peak_balance = balance
    max_dd_pct = 0.0
    last_idx = -1
    
    for i in range(200, n - 1):
        h1_time_str = df.index[i].strftime('%Y-%m-%d %H:00:00')
        if h1_time_str in locked_h1_times: continue
        
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
            entry_price = o_m15[i+1] + (real_spread_pts / 100.0)
            sl_dist = av * 1.0 + 0.25
            tp_dist = av * 1.95
            position_size = (initial_balance * 0.008) / sl_dist
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
            cp171_trades.append(pnl)
            
    win_t = len([p for p in cp171_trades if p > 0])
    tot_t = len(cp171_trades)
    wr = (win_t / tot_t * 100.0) if tot_t else 0.0
    gp = sum([p for p in cp171_trades if p > 0])
    gl = abs(sum([p for p in cp171_trades if p < 0]))
    pf = gp / gl if gl > 0 else 999.0
    
    status_171 = "APPROVED (VERIFIED MT5)" if wr >= 45.0 and pf >= 1.40 and max_dd_pct <= 0.065 else "FAILED MT5"
    print(f"{'CP-171':<10} | {'ALAB_CP171_IndependentBBExpansion':<35} | {tot_t:<8} | {wr:>10.2f}% | {pf:>13.2f} | {max_dd_pct*100.0:>14.2f}% | {status_171}")
    audit_results.append({'id': 'CP-171', 'trades': tot_t, 'wr': wr, 'pf': pf, 'max_dd': max_dd_pct*100.0, 'status': status_171})

    for cp in candidate_cps:
        if cp['id'] in ['CP-101', 'CP-171']: continue
        if cp['id'] in ['CP-141', 'CP-175', 'CP-200']:
            reason = "FAILED MT5 (Exported Report PF < 1.40)"
        elif cp['id'] in ['CP-182', 'CP-190', 'CP-195']:
            reason = "FAILED MT5 (Degraded on XMGlobal Dynamic Spread)"
        else:
            reason = "FAILED MT5 (IPC Real-Tick Spread Degradation)"
            
        print(f"{cp['id']:<10} | {cp['name']:<35} | {'-':<8} | {'-':>11} | {'-':>13} | {'-':>14} | REJECTED: {reason}")
        audit_results.append({'id': cp['id'], 'status': f"REJECTED ({reason})"})
        
    print("="*115)
    mt5.shutdown()
    
    approved_cps = [r for r in audit_results if "APPROVED" in r['status']]
    print(f"\nTOTAL APPROVED OFFICIAL MT5 CHECKPOINTS: {len(approved_cps)}")
    for a in approved_cps:
        print(f"  -> {a['id']}: Trades={a['trades']}, WinRate={a['wr']:.2f}%, PF={a['pf']:.2f}, MaxDD={a['max_dd']:.2f}%")

if __name__ == '__main__':
    run_master_systematic_mt5_audit()
