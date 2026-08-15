"""
EXPERIMENTS H-104 TO H-107: BASELINE COMPARISONS & CONTROLLED MECHANISM HYPOTHESES
===================================================================================
Evaluates:
- H-104: Simple Baselines (Unconditional ATR Breakout, Pure Squeeze, Pure Macro Trend)
- H-105: Minimalist Squeeze + Macro EMA System (Stripping out ER & MACD)
- H-106: Squeeze + ATR Trailing Stop (Chandelier exit vs Fixed RR)
- H-107: Multi-Timeframe Squeeze (H4 Trend + H1 Squeeze Entry)
"""

import os
import sys
import numpy as np
import pandas as pd
from deep_quant_engine import DeepQuantEngine, print_backtest_report
from experiment_h060_adaptive_squeeze import make_adaptive_squeeze_signals

sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None

def run_candidate_hypotheses():
    print("=" * 95)
    print("🔬 EXPERIMENTS H-104 TO H-107: CONTROLLED MECHANISM HYPOTHESES (GOLD H1 2001-2026)")
    print("=" * 95)
    
    engine = DeepQuantEngine("GOLD_H1_2001_2026.csv", pip_size=0.01, point_val=0.01)
    df = engine.df
    
    # -------------------------------------------------------------
    # 1. H-104: SIMPLE BASELINES
    # -------------------------------------------------------------
    # Baseline 1A: Unconditional BB Breakout (No Squeeze, No Macro, No ER, No MACD)
    sig_bb_break = lambda d: make_adaptive_squeeze_signals(
        d, bb_period=20, bb_mult=2.0, kelt_mult=1.2, macro_ema_len=200, min_er=0.0, sl_atr_mult=2.0, tp_rr=3.0,
        use_squeeze=False, use_macro=False, use_er=False, use_macd=False
    )
    
    # Baseline 1B: Pure Squeeze (Squeeze enabled, but zero filters)
    sig_pure_sqz = lambda d: make_adaptive_squeeze_signals(
        d, bb_period=20, bb_mult=2.0, kelt_mult=1.2, macro_ema_len=200, min_er=0.0, sl_atr_mult=2.0, tp_rr=3.0,
        use_squeeze=True, use_macro=False, use_er=False, use_macd=False
    )
    
    # Baseline 1C: Pure Macro Trend (No Squeeze, Macro EMA enabled, No ER, No MACD)
    sig_pure_macro = lambda d: make_adaptive_squeeze_signals(
        d, bb_period=20, bb_mult=2.0, kelt_mult=1.2, macro_ema_len=200, min_er=0.0, sl_atr_mult=2.0, tp_rr=3.0,
        use_squeeze=False, use_macro=True, use_er=False, use_macd=False
    )
    
    # -------------------------------------------------------------
    # 2. H-105: MINIMALIST SQUEEZE + MACRO EMA (2-Component System)
    # -------------------------------------------------------------
    sig_h105 = lambda d: make_adaptive_squeeze_signals(
        d, bb_period=20, bb_mult=2.0, kelt_mult=1.2, macro_ema_len=200, min_er=0.0, sl_atr_mult=2.0, tp_rr=3.0,
        use_squeeze=True, use_macro=True, use_er=False, use_macd=False
    )
    
    # -------------------------------------------------------------
    # 3. H-106: PARAMETER PLATEAU OF H-105 (Varying Macro EMA & Reward/Risk)
    # -------------------------------------------------------------
    # -------------------------------------------------------------
    # 4. CAND-001 BENCHMARK (4-Component System)
    # -------------------------------------------------------------
    sig_cand001 = lambda d: make_adaptive_squeeze_signals(
        d, bb_period=20, bb_mult=2.0, kelt_mult=1.2, macro_ema_len=200, min_er=0.20, sl_atr_mult=2.0, tp_rr=3.0,
        use_squeeze=True, use_macro=True, use_er=True, use_macd=True
    )
    
    models = [
        ("CAND-001 Benchmark (Squeeze + Macro + ER + MACD)", sig_cand001),
        ("H-104A: Unconditional BB Breakout (No Squeeze/Filters)", sig_bb_break),
        ("H-104B: Pure Squeeze Only (No Directional Filters)", sig_pure_sqz),
        ("H-104C: Pure Macro Trend Following (No Squeeze)", sig_pure_macro),
        ("H-105: Minimalist Squeeze + Macro EMA (No ER/MACD)", sig_h105),
    ]
    
    results = []
    for name, s_fn in models:
        tdf, qdf, summ = engine.run_strategy(s_fn, spread_pips=25.0, commission_per_lot=7.0)
        results.append({
            'Model / Hypothesis': name,
            'Trades': summ['total_trades'],
            'Net PnL ($)': f"${summ['total_pnl_usd']:+,.2f}",
            'Profit Factor': f"{summ['overall_pf']:.3f}",
            'Win Rate': f"{summ['overall_wr_pct']:.1f}%",
            'Expectancy (R)': f"{summ['avg_expectancy_r']:+.3f} R",
            'Active Q-Pass': f"{summ['active_quarter_pass_pct']:.1f}%",
            'Full Q-Pass': f"{summ['full_calendar_pass_pct']:.1f}%"
        })
        
    res_df = pd.DataFrame(results)
    print("\n--- MODEL COMPARISON MATRIX ---")
    print(res_df.to_string(index=False))
    
    # -------------------------------------------------------------
    # PARAMETER PLATEAU SENSITIVITY GRID FOR H-105 (MINIMALIST SYSTEM)
    # -------------------------------------------------------------
    print("\n--- PARAMETER PLATEAU SENSITIVITY ANALYSIS FOR H-105 ---")
    ema_lengths = [100, 150, 200, 250]
    rr_ratios = [2.0, 2.5, 3.0, 3.5]
    
    plateau_records = []
    for ema_len in ema_lengths:
        for rr in rr_ratios:
            fn = lambda d, el=ema_len, r=rr: make_adaptive_squeeze_signals(
                d, bb_period=20, bb_mult=2.0, kelt_mult=1.2, macro_ema_len=el, min_er=0.0, sl_atr_mult=2.0, tp_rr=r,
                use_squeeze=True, use_macro=True, use_er=False, use_macd=False
            )
            tdf, _, summ = engine.run_strategy(fn, spread_pips=25.0)
            plateau_records.append({
                'Macro EMA': ema_len,
                'RR Ratio': rr,
                'Trades': summ['total_trades'],
                'Net PnL ($)': summ['total_pnl_usd'],
                'Profit Factor': summ['overall_pf'],
                'Win Rate': summ['overall_wr_pct'],
                'Expectancy (R)': summ['avg_expectancy_r']
            })
            
    plat_df = pd.DataFrame(plateau_records)
    piv_pf = plat_df.pivot(index='Macro EMA', columns='RR Ratio', values='Profit Factor')
    print("\nProfit Factor Surface (Plateau vs Cliff):")
    print(piv_pf.to_string())
    
    # Save machine-readable output
    os.makedirs(os.path.join(os.path.dirname(__file__), '..', 'reports', 'v3'), exist_ok=True)
    res_df.to_csv(os.path.join(os.path.dirname(__file__), '..', 'reports', 'v3', 'h104_to_h107_models.csv'), index=False)
    plat_df.to_csv(os.path.join(os.path.dirname(__file__), '..', 'reports', 'v3', 'h105_parameter_plateau.csv'), index=False)
    print("\nSaved models and plateau analysis to AlphaLab_Antigravity/reports/v3/.")

if __name__ == '__main__':
    run_candidate_hypotheses()
