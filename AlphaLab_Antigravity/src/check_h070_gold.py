import pandas as pd
from deep_quant_engine import DeepQuantEngine, print_backtest_report
from experiment_h060_adaptive_squeeze import make_adaptive_squeeze_signals

sig_fn_balanced = lambda d: make_adaptive_squeeze_signals(d, bb_period=20, bb_mult=2.0, kelt_mult=1.2, macro_ema_len=200, min_er=0.20, sl_atr_mult=2.0, tp_rr=3.0)

for tf_file, title in [("GOLD_M15.csv", "Gold M15 (2022 - 2026)"), ("GOLD_M30.csv", "Gold M30 (2018 - 2026)"), ("GOLD_H1_2001_2026.csv", "Gold H1 (2001 - 2026)")]:
    eng = DeepQuantEngine(tf_file, pip_size=0.01)
    tdf, qdf, summ = eng.run_strategy(sig_fn_balanced, spread_pips=25.0, commission_per_lot=7.0)
    print_backtest_report(f"H-070 Multi-Scale Evaluation: {title}", tdf, qdf, summ)
