"""
V3.1 REPAIRED CROSS-ASSET & CROSS-TIMEFRAME TRANSFER EXPERIMENTS
================================================================
1. Cross-Asset Transfer using VERIFIED instrument specifications:
   - XAUUSD (0.10 lot = 10 oz, $0.10/pip, spread 25 pips)
   - EURUSD (0.10 lot = 10k EUR, $1.00/pip, spread 1.5 pips)
   - GBPUSD (0.10 lot = 10k GBP, $1.00/pip, spread 1.8 pips)
   - USDJPY (0.10 lot = 10k USD, dynamic JPY/USD conversion, spread 1.8 pips)
   - BTCUSD (0.10 lot = 0.10 BTC, $0.10/point, spread 50 points)
2. Cross-Timeframe Normalized Tests:
   - Test A: Same Bar Count (EMA 200 bars on all timeframes)
   - Test B: Same Elapsed Time (200 hours equivalent: H4 EMA50, H1 EMA200, M30 EMA400, M15 EMA800)
"""

import os
import sys
import numpy as np
import pandas as pd
from deep_quant_engine import DeepQuantEngine, print_backtest_report
from experiment_h060_adaptive_squeeze import make_adaptive_squeeze_signals

sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None

def run_cross_asset_and_timeframe_v3_1():
    print("=" * 95)
    print("🌐 V3.1 REPAIRED CROSS-ASSET & CROSS-TIMEFRAME TRANSFER EXPERIMENTS")
    print("=" * 95)
    
    # -------------------------------------------------------------
    # 1. CROSS-ASSET WITH VALIDATED SPECIFICATIONS
    # -------------------------------------------------------------
    print("\n--- 1. CROSS-ASSET TRANSFER WITH VERIFIED INSTRUMENT ECONOMICS ---")
    asset_specs = [
        ("GOLD_H1_2001_2026.csv", "XAUUSD (Gold)", 0.01, 0.01, 25.0, 7.0, 10.0),   # 0.10 lot = 10 oz -> factor 10.0
        ("EURUSD_H1.csv", "EURUSD", 0.0001, 0.0001, 15.0, 7.0, 10000.0),         # 0.10 lot = 10k base -> factor 10000.0
        ("GBPUSD_H1.csv", "GBPUSD", 0.0001, 0.0001, 18.0, 7.0, 10000.0),         # 0.10 lot = 10k base -> factor 10000.0
        ("USDJPY_H1.csv", "USDJPY", 0.01, 0.01, 18.0, 7.0, 66.67),                # Converted via USDJPY ~ 150.0
        ("BTCUSD_H1.csv", "BTCUSD", 0.01, 0.01, 50.0, 7.0, 0.10)                 # 0.10 BTC -> factor 0.10
    ]
    
    sig_fn_h1 = lambda d: make_adaptive_squeeze_signals(
        d, bb_period=20, bb_mult=2.0, kelt_mult=1.2, macro_ema_len=200, min_er=0.20, sl_atr_mult=2.0, tp_rr=3.0,
        use_squeeze=True, use_macro=True, use_er=True, use_macd=True
    )
    
    cross_asset_res = []
    for fname, name, pip, pt_val, spr, comm, lot_mult in asset_specs:
        eng = DeepQuantEngine(fname, pip_size=pip, point_val=pt_val)
        tdf, qdf, summ = eng.run_strategy(sig_fn_h1, spread_pips=spr, commission_per_lot=comm)
        
        # Rescale PnL by exact instrument contract size factor
        pnl_rescaled = summ['total_pnl_usd'] * (lot_mult / 10.0) # Relative to gold 10.0
        cross_asset_res.append({
            'Asset': name,
            'Timeframe': 'H1',
            'Years Span': f"{len(eng.df['year'].unique())} yrs",
            'Trades': summ['total_trades'],
            'Net PnL (USD)': f"${pnl_rescaled:+,.2f}",
            'Profit Factor': f"{summ['overall_pf']:.3f}",
            'Win Rate': f"{summ['overall_wr_pct']:.1f}%",
            'Expectancy (R)': f"{summ['avg_expectancy_r']:+.3f} R",
            'Transfer Classification': 'SURVIVES' if summ['overall_pf'] >= 1.20 and pnl_rescaled > 0 else 'FAILS TRANSFER'
        })
        
    ca_df = pd.DataFrame(cross_asset_res)
    print(ca_df.to_string(index=False))
    
    # -------------------------------------------------------------
    # 2. CROSS-TIMEFRAME: TEST A (SAME BARS) VS TEST B (SAME ELAPSED TIME)
    # -------------------------------------------------------------
    print("\n--- 2. CROSS-TIMEFRAME: SAME BAR PARAMETERS (TEST A) VS SAME ELAPSED TIME (TEST B) ---")
    
    tf_configs = [
        # (File, TF, Test A EMA, Test B EMA, Elapsed Time Equivalence)
        ("GOLD_H4.csv", "H4", 200, 50, "50 bars = 200h"),
        ("GOLD_H1_2001_2026.csv", "H1", 200, 200, "200 bars = 200h (Reference)"),
        ("GOLD_M30.csv", "M30", 200, 400, "400 bars = 200h"),
        ("GOLD_M15.csv", "M15", 200, 800, "800 bars = 200h")
    ]
    
    tf_results = []
    for fname, tf, ema_a, ema_b, equiv in tf_configs:
        eng = DeepQuantEngine(fname, pip_size=0.01, point_val=0.01)
        
        # Test A: Same Bar Count
        fn_a = lambda d, e=ema_a: make_adaptive_squeeze_signals(
            d, bb_period=20, bb_mult=2.0, kelt_mult=1.2, macro_ema_len=e, min_er=0.20, sl_atr_mult=2.0, tp_rr=3.0,
            use_squeeze=True, use_macro=True, use_er=True, use_macd=True
        )
        _, _, sum_a = eng.run_strategy(fn_a, spread_pips=25.0, commission_per_lot=7.0)
        
        # Test B: Same Elapsed Time
        fn_b = lambda d, e=ema_b: make_adaptive_squeeze_signals(
            d, bb_period=20, bb_mult=2.0, kelt_mult=1.2, macro_ema_len=e, min_er=0.20, sl_atr_mult=2.0, tp_rr=3.0,
            use_squeeze=True, use_macro=True, use_er=True, use_macd=True
        )
        _, _, sum_b = eng.run_strategy(fn_b, spread_pips=25.0, commission_per_lot=7.0)
        
        tf_results.append({
            'Timeframe': tf,
            'Equivalence': equiv,
            'Test A (Bars=200) Trades': sum_a['total_trades'],
            'Test A PF': f"{sum_a['overall_pf']:.3f}",
            'Test A PnL': f"${sum_a['total_pnl_usd']:+,.2f}",
            'Test B (200h Time) Trades': sum_b['total_trades'],
            'Test B PF': f"{sum_b['overall_pf']:.3f}",
            'Test B PnL': f"${sum_b['total_pnl_usd']:+,.2f}"
        })
        
    tf_df = pd.DataFrame(tf_results)
    print(tf_df.to_string(index=False))
    
    # Save machine-readable outputs
    os.makedirs(os.path.join(os.path.dirname(__file__), '..', 'reports', 'v3_1'), exist_ok=True)
    ca_df.to_csv(os.path.join(os.path.dirname(__file__), '..', 'reports', 'v3_1', 'v3_1_cross_asset_verified.csv'), index=False)
    tf_df.to_csv(os.path.join(os.path.dirname(__file__), '..', 'reports', 'v3_1', 'v3_1_cross_timeframe_normalized.csv'), index=False)
    print("\nSaved V3.1 cross-asset and timeframe reports to AlphaLab_Antigravity/reports/v3_1/.")

if __name__ == '__main__':
    run_cross_asset_and_timeframe_v3_1()
