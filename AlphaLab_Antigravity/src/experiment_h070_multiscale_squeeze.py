"""
EXPERIMENT H-070: MULTI-SCALE ADAPTIVE VOLATILITY SQUEEZE
=========================================================
Evaluates the Adaptive Volatility Squeeze across multiple timeframes (M15, M30, H1)
and measures quarterly trade frequency, distributed robustness, and cross-timeframe consistency.
"""

import os
import sys
import numpy as np
import pandas as pd
from deep_quant_engine import DeepQuantEngine, print_backtest_report
from experiment_h060_adaptive_squeeze import make_adaptive_squeeze_signals

sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None

def run_experiment():
    print("="*95)
    print("EXPERIMENT H-070: MULTI-SCALE ADAPTIVE VOLATILITY SQUEEZE")
    print("="*95)
    
    # Evaluate across timeframes with balanced parameters
    # M15 parameters: BB period 20, Keltner 1.2, Macro EMA 200 (~50h trend), ER >= 0.20, SL 2.0 ATR, RR 3.0
    # M30 parameters: BB period 20, Keltner 1.2, Macro EMA 200 (~100h trend), ER >= 0.20, SL 2.0 ATR, RR 3.0
    # H1 parameters: BB period 20, Keltner 1.2, Macro EMA 200 (~200h trend), ER >= 0.20, SL 2.0 ATR, RR 3.0
    
    sig_fn_balanced = lambda d: make_adaptive_squeeze_signals(d, bb_period=20, bb_mult=2.0, kelt_mult=1.2, macro_ema_len=200, min_er=0.20, sl_atr_mult=2.0, tp_rr=3.0)
    
    datasets = [
        ("GOLD_M15.csv", 0.01, 25.0, "Gold M15 (2022 - 2026)"),
        ("GOLD_M30.csv", 0.01, 25.0, "Gold M30 (2018 - 2026)"),
        ("GOLD_H1_2001_2026.csv", 0.01, 25.0, "Gold H1 (2001 - 2026)"),
        ("EURUSD_H1.csv", 0.0001, 15.0, "EURUSD H1 (2014 - 2026)"),
        ("GBPUSD_H1.csv", 0.0001, 15.0, "GBPUSD H1 (2014 - 2026)"),
        ("USDJPY_H1.csv", 0.01, 18.0, "USDJPY H1 (2014 - 2026)")
    ]
    
    for filename, pip, spr, title in datasets:
        eng = DeepQuantEngine(filename, pip_size=pip)
        tdf, qdf, summ = eng.run_strategy(sig_fn_balanced, spread_pips=spr, commission_per_lot=7.0)
        print_backtest_report(f"H-070 Multi-Scale Evaluation: {title}", tdf, qdf, summ)

if __name__ == '__main__':
    run_experiment()
