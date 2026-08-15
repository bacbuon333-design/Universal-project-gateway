import pandas as pd
from deep_quant_engine import DeepQuantEngine, print_backtest_report
from experiment_h050_session_orb import make_session_orb_signals

for tf_file in ["GOLD_M15.csv", "GOLD_M30.csv"]:
    engine = DeepQuantEngine(tf_file, pip_size=0.01)
    for sess_hr in [7, 13]:
        sig_fn = lambda d, sh=sess_hr: make_session_orb_signals(d, session_start_hour=sh, orb_bars=4, sl_atr_mult=1.5, tp_rr=2.0)
        tdf, qdf, summ = engine.run_strategy(sig_fn, spread_pips=25.0, commission_per_lot=7.0)
        sess_name = "London (07:00 UTC)" if sess_hr == 7 else "New York (13:00 UTC)"
        print_backtest_report(f"H-050 {sess_name} ORB on {tf_file}", tdf, qdf, summ)
