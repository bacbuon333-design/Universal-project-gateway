"""
EXPERIMENTS H-102 & H-103: CROSS-TIMEFRAME & CROSS-ASSET NORMALIZED TEST
========================================================================
H-102: Cross-Timeframe Mechanism Test across Gold H4, H1, M30, M15.
H-103: Cross-Asset Zero-Tuning Transfer Test across Gold, EURUSD, GBPUSD, USDJPY, BTCUSD.

Uses identical normalized parameter structure:
- Squeeze: BB(20, 2.0) inside Keltner(20, 1.2 * ATR20)
- Trend: 200 EMA slope + price position
- Noise: Kaufman ER(10) >= 0.20
- Risk: Stop Loss = 2.0 * ATR14, Take Profit = 3.0 * SL (6.0 * ATR14)
- Fixed lot: Scaled to risk 1% or standard 0.10 lot
"""

import os
import sys
import numpy as np
import pandas as pd
from deep_quant_engine import DeepQuantEngine, print_backtest_report
from experiment_h060_adaptive_squeeze import make_adaptive_squeeze_signals

sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None

def run_cross_tests():
    print("=" * 95)
    print("🌐 EXPERIMENTS H-102 & H-103: CROSS-TIMEFRAME & CROSS-ASSET NORMALIZED TESTS")
    print("=" * 95)
    
    # -------------------------------------------------------------
    # H-102: CROSS-TIMEFRAME TEST (GOLD)
    # -------------------------------------------------------------
    print("\n--- H-102: GOLD CROSS-TIMEFRAME TEST (ZERO PARAMETER MODIFICATION) ---")
    tf_files = [
        ("GOLD_H4.csv", "GOLD", "H4", 25.0),
        ("GOLD_H1_2001_2026.csv", "GOLD", "H1", 25.0),
        ("GOLD_M30.csv", "GOLD", "M30", 25.0),
        ("GOLD_M15.csv", "GOLD", "M15", 25.0)
    ]
    
    h102_results = []
    base_sig_fn = lambda d: make_adaptive_squeeze_signals(
        d, bb_period=20, bb_mult=2.0, kelt_mult=1.2, macro_ema_len=200, min_er=0.20, sl_atr_mult=2.0, tp_rr=3.0,
        use_squeeze=True, use_macro=True, use_er=True, use_macd=True
    )
    
    for fname, asset, tf, spr in tf_files:
        eng = DeepQuantEngine(fname, pip_size=0.01, point_val=0.01)
        tdf, qdf, summ = eng.run_strategy(base_sig_fn, spread_pips=spr, commission_per_lot=7.0)
        h102_results.append({
            'Timeframe': tf,
            'Years Span': f"{len(eng.df['year'].unique())} yrs",
            'Total Bars': f"{len(eng.df):,}",
            'Trades': summ['total_trades'],
            'Net PnL ($)': f"${summ['total_pnl_usd']:+,.2f}",
            'Profit Factor': f"{summ['overall_pf']:.3f}",
            'Win Rate': f"{summ['overall_wr_pct']:.1f}%",
            'Expectancy (R)': f"{summ['avg_expectancy_r']:+.3f} R",
            'Active Q-Pass': f"{summ['active_quarter_pass_pct']:.1f}%"
        })
    print(pd.DataFrame(h102_results).to_string(index=False))
    
    # -------------------------------------------------------------
    # H-103: CROSS-ASSET TEST (ZERO TUNING / NORMALIZED PIP COST)
    # -------------------------------------------------------------
    print("\n--- H-103: CROSS-ASSET ZERO-TUNING TEST (IDENTICAL NORMALIZED RULES) ---")
    asset_files = [
        ("GOLD_H1_2001_2026.csv", "GOLD", 0.01, 0.01, 25.0, 7.0),
        ("EURUSD_H1.csv", "EURUSD", 0.0001, 0.0001, 15.0, 7.0),
        ("GBPUSD_H1.csv", "GBPUSD", 0.0001, 0.0001, 18.0, 7.0),
        ("USDJPY_H1.csv", "USDJPY", 0.01, 0.01, 18.0, 7.0),
        ("BTCUSD_H1.csv", "BTCUSD", 0.01, 0.01, 50.0, 7.0)
    ]
    
    h103_results = []
    for fname, asset, pip, pt_val, spr, comm in asset_files:
        eng = DeepQuantEngine(fname, pip_size=pip, point_val=pt_val)
        tdf, qdf, summ = eng.run_strategy(base_sig_fn, spread_pips=spr, commission_per_lot=comm)
        h103_results.append({
            'Asset': asset,
            'Timeframe': 'H1',
            'Years Span': f"{len(eng.df['year'].unique())} yrs",
            'Trades': summ['total_trades'],
            'Net PnL ($)': f"${summ['total_pnl_usd']:+,.2f}",
            'Profit Factor': f"{summ['overall_pf']:.3f}",
            'Win Rate': f"{summ['overall_wr_pct']:.1f}%",
            'Expectancy (R)': f"{summ['avg_expectancy_r']:+.3f} R",
            'Status': 'SURVIVES' if summ['total_pnl_usd'] > 0 and summ['overall_pf'] >= 1.20 else 'FAILS TRANSFER'
        })
    print(pd.DataFrame(h103_results).to_string(index=False))
    
    # Save machine-readable output
    os.makedirs(os.path.join(os.path.dirname(__file__), '..', 'reports', 'v3'), exist_ok=True)
    pd.DataFrame(h102_results).to_csv(os.path.join(os.path.dirname(__file__), '..', 'reports', 'v3', 'h102_cross_timeframe.csv'), index=False)
    pd.DataFrame(h103_results).to_csv(os.path.join(os.path.dirname(__file__), '..', 'reports', 'v3', 'h103_cross_asset.csv'), index=False)
    print("\nSaved H-102 and H-103 reports to AlphaLab_Antigravity/reports/v3/.")

if __name__ == '__main__':
    run_cross_tests()
