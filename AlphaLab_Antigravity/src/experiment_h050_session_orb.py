"""
EXPERIMENT H-050: SESSION OPENING RANGE BREAKOUT (LONDON & NY OPEN)
===================================================================
Evaluates symmetrical Opening Range Breakout (ORB) on:
- London Session Open (07:00 UTC)
- New York Session Open (12:00 / 13:00 UTC)
- Evaluated on Gold M15 (2022-2026), Gold M30 (2018-2026), EURUSD, GBPUSD, USDJPY
"""

import os
import sys
import numpy as np
import pandas as pd
from deep_quant_engine import DeepQuantEngine, print_backtest_report

sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None

def make_session_orb_signals(df: pd.DataFrame, session_start_hour: int = 7, orb_bars: int = 4, sl_atr_mult: float = 1.5, tp_rr: float = 2.0):
    h = df['high'].values
    l = df['low'].values
    c = df['close'].values
    dt = df['dt']
    n = len(c)
    
    hours = dt.dt.hour.values
    dates = dt.dt.date.values
    
    # ATR 14
    tr = np.maximum(h - l, np.maximum(np.abs(h - np.roll(c, 1)), np.abs(l - np.roll(c, 1))))
    atr14 = pd.Series(tr).rolling(14).mean().values
    
    signals = np.zeros(n, dtype=int)
    sl_dists = np.zeros(n)
    tp_dists = np.zeros(n)
    
    current_date = None
    range_high = -1e9
    range_low = 1e9
    bars_in_session = 0
    trade_taken_today = False
    
    for i in range(20, n):
        d = dates[i]
        hr = hours[i]
        av = max(atr14[i], 0.1)
        
        if d != current_date:
            current_date = d
            range_high = -1e9
            range_low = 1e9
            bars_in_session = 0
            trade_taken_today = False
            
        if hr == session_start_hour:
            bars_in_session += 1
            if h[i] > range_high: range_high = h[i]
            if l[i] < range_low: range_low = l[i]
            
        elif hr > session_start_hour and hr <= session_start_hour + 4:
            if not trade_taken_today and range_high > -1e8 and range_low < 1e8:
                if c[i] > range_high:
                    signals[i] = 1
                    sl_dists[i] = av * sl_atr_mult
                    tp_dists[i] = sl_dists[i] * tp_rr
                    trade_taken_today = True
                elif c[i] < range_low:
                    signals[i] = -1
                    sl_dists[i] = av * sl_atr_mult
                    tp_dists[i] = sl_dists[i] * tp_rr
                    trade_taken_today = True
                    
    return signals, sl_dists, tp_dists

def run_experiment():
    print("="*95)
    print("EXPERIMENT H-050: SESSION OPENING RANGE BREAKOUT (ORB)")
    print("="*95)
    
    # Run on Gold M15 (2022-2026) and M30 (2018-2026)
    for tf_file in ["GOLD_M15.csv", "GOLD_M30.csv", "EURUSD_H1.csv", "GBPUSD_H1.csv", "USDJPY_H1.csv"]:
        pip = 0.01 if 'GOLD' in tf_file or 'JPY' in tf_file else 0.0001
        spr = 25.0 if 'GOLD' in tf_file else (18.0 if 'JPY' in tf_file else 15.0)
        engine = DeepQuantEngine(tf_file, pip_size=pip)
        
        for sess_hr in [7, 13]: # London (07:00) vs NY (13:00)
            sig_fn = lambda d, sh=sess_hr: make_session_orb_signals(d, session_start_hour=sh, orb_bars=4, sl_atr_mult=1.5, tp_rr=2.0)
            tdf, qdf, summ = engine.run_strategy(sig_fn, spread_pips=spr, commission_per_lot=7.0)
            sess_name = "London (07:00 UTC)" if sess_hr == 7 else "New York (13:00 UTC)"
            print_backtest_report(f"H-050 {sess_name} ORB on {tf_file}", tdf, qdf, summ)

if __name__ == '__main__':
    run_experiment()
