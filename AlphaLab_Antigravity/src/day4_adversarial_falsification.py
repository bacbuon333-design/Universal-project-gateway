"""
DAY 4: ADVERSARIAL FALSIFICATION & STRESS TESTING
==================================================
Hostile review and stress testing of CAND-001 (ALAB_SQUEEZE_REGIME_V1):
1. Spread Stress: 25 pips -> 40 pips -> 60 pips -> 80 pips (Break-even spread calculation)
2. Slippage Stress: 0 -> 2 -> 5 -> 10 pips
3. Directional Ablation: Long-Only vs Short-Only vs Symmetrical (2013-2015 Bear Market vs 2024-2026 Bull Market)
4. Component Ablation:
   - Baseline CAND-001
   - Ablation A: Remove Kaufman Efficiency Ratio (ER)
   - Ablation B: Remove Macro EMA Trend Filter
   - Ablation C: Remove Squeeze (Pure Bollinger Breakout)
5. Parameter Sensitivity & Cliff Analysis
"""

import os
import sys
import numpy as np
import pandas as pd
from deep_quant_engine import DeepQuantEngine, print_backtest_report
from experiment_h060_adaptive_squeeze import make_adaptive_squeeze_signals

sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None

def run_adversarial_tests():
    print("="*95)
    print("⚔️ DAY 4: ADVERSARIAL FALSIFICATION OF CAND-001")
    print("="*95)
    
    engine = DeepQuantEngine("GOLD_H1_2001_2026.csv", pip_size=0.01)
    
    base_sig_fn = lambda d: make_adaptive_squeeze_signals(
        d, bb_period=20, bb_mult=2.0, kelt_mult=1.2, macro_ema_len=200, min_er=0.20, sl_atr_mult=2.0, tp_rr=3.0
    )
    
    # -------------------------------------------------------------
    # 1. SPREAD STRESS TEST
    # -------------------------------------------------------------
    print("\n" + "="*95)
    print("TEST 1: SPREAD STRESS TEST (Finding the Edge Degradation & Break-Even Boundary)")
    print("="*95)
    spread_levels = [25.0, 35.0, 45.0, 60.0, 80.0, 100.0]
    spread_results = []
    for spr in spread_levels:
        tdf, qdf, summ = engine.run_strategy(base_sig_fn, spread_pips=spr, commission_per_lot=7.0)
        spread_results.append({
            'Spread (pips)': f"{spr:.1f}",
            'Net PnL ($)': f"${summ['total_pnl_usd']:+,.2f}",
            'Profit Factor': f"{summ['overall_pf']:.3f}",
            'Win Rate %': f"{summ['overall_wr_pct']:.1f}%",
            'Expectancy (USD)': f"${summ['avg_expectancy_usd']:+.2f}",
            'Expectancy (R)': f"{summ['avg_expectancy_r']:+.3f} R",
            'Status': 'SURVIVES' if summ['total_pnl_usd'] > 0 and summ['overall_pf'] > 1.20 else 'DESTROYED'
        })
    print(pd.DataFrame(spread_results).to_string(index=False))
    
    # -------------------------------------------------------------
    # 2. SLIPPAGE STRESS TEST
    # -------------------------------------------------------------
    print("\n" + "="*95)
    print("TEST 2: SLIPPAGE STRESS TEST (Adverse Fill Latency)")
    print("="*95)
    slippage_levels = [0.0, 2.0, 5.0, 10.0, 15.0]
    slip_results = []
    for slp in slippage_levels:
        tdf, qdf, summ = engine.run_strategy(base_sig_fn, spread_pips=25.0, commission_per_lot=7.0, slippage_pips=slp)
        slip_results.append({
            'Slippage (pips)': f"{slp:.1f}",
            'Net PnL ($)': f"${summ['total_pnl_usd']:+,.2f}",
            'Profit Factor': f"{summ['overall_pf']:.3f}",
            'Win Rate %': f"{summ['overall_wr_pct']:.1f}%",
            'Expectancy (USD)': f"${summ['avg_expectancy_usd']:+.2f}",
            'Status': 'SURVIVES' if summ['total_pnl_usd'] > 0 and summ['overall_pf'] > 1.20 else 'DESTROYED'
        })
    print(pd.DataFrame(slip_results).to_string(index=False))
    
    # -------------------------------------------------------------
    # 3. DIRECTIONAL ABLATION (Long vs Short Leg in Bull vs Bear Regimes)
    # -------------------------------------------------------------
    print("\n" + "="*95)
    print("TEST 3: DIRECTIONAL LEG ABLATION (Is edge purely long-biased or symmetrically robust?)")
    print("="*95)
    
    def make_long_only_signals(df):
        sig, sl, tp = base_sig_fn(df)
        sig[sig == -1] = 0
        return sig, sl, tp
        
    def make_short_only_signals(df):
        sig, sl, tp = base_sig_fn(df)
        sig[sig == 1] = 0
        return sig, sl, tp
        
    tdf_sym, _, summ_sym = engine.run_strategy(base_sig_fn, spread_pips=25.0)
    tdf_long, _, summ_long = engine.run_strategy(make_long_only_signals, spread_pips=25.0)
    tdf_short, _, summ_short = engine.run_strategy(make_short_only_signals, spread_pips=25.0)
    
    # Check Gold Bear Market (2013 - 2015: Gold crashed from $1800 to $1050)
    tdf_sym_bear = tdf_sym[(tdf_sym['year'] >= 2013) & (tdf_sym['year'] <= 2015)] if len(tdf_sym) > 0 else pd.DataFrame()
    tdf_long_bear = tdf_long[(tdf_long['year'] >= 2013) & (tdf_long['year'] <= 2015)] if len(tdf_long) > 0 else pd.DataFrame()
    tdf_short_bear = tdf_short[(tdf_short['year'] >= 2013) & (tdf_short['year'] <= 2015)] if len(tdf_short) > 0 else pd.DataFrame()
    
    dir_results = [
        {
            'Configuration': 'Symmetrical (Long + Short)',
            'Full History PnL': f"${summ_sym['total_pnl_usd']:+,.2f}",
            'Full PF': f"{summ_sym['overall_pf']:.3f}",
            'Trades': summ_sym['total_trades'],
            '2013-2015 Bear PnL': f"${tdf_sym_bear['pnl_usd'].sum():+,.2f}" if len(tdf_sym_bear) > 0 else "$0.00"
        },
        {
            'Configuration': 'Long-Only Leg',
            'Full History PnL': f"${summ_long['total_pnl_usd']:+,.2f}",
            'Full PF': f"{summ_long['overall_pf']:.3f}",
            'Trades': summ_long['total_trades'],
            '2013-2015 Bear PnL': f"${tdf_long_bear['pnl_usd'].sum():+,.2f}" if len(tdf_long_bear) > 0 else "$0.00"
        },
        {
            'Configuration': 'Short-Only Leg',
            'Full History PnL': f"${summ_short['total_pnl_usd']:+,.2f}",
            'Full PF': f"{summ_short['overall_pf']:.3f}",
            'Trades': summ_short['total_trades'],
            '2013-2015 Bear PnL': f"${tdf_short_bear['pnl_usd'].sum():+,.2f}" if len(tdf_short_bear) > 0 else "$0.00"
        }
    ]
    print(pd.DataFrame(dir_results).to_string(index=False))
    
    # -------------------------------------------------------------
    # 4. COMPONENT ARCHITECTURAL ABLATION
    # -------------------------------------------------------------
    print("\n" + "="*95)
    print("TEST 4: COMPONENT ARCHITECTURAL ABLATION (Measuring marginal contribution of each layer)")
    print("="*95)
    
    # Ablation A: Without Kaufman ER (min_er = 0)
    sig_no_er = lambda d: make_adaptive_squeeze_signals(d, bb_period=20, bb_mult=2.0, kelt_mult=1.2, macro_ema_len=200, min_er=0.0, sl_atr_mult=2.0, tp_rr=3.0)
    tdf_no_er, _, summ_no_er = engine.run_strategy(sig_no_er, spread_pips=25.0)
    
    # Ablation B: Without Macro EMA (macro_ema_len = 1, neutral)
    sig_no_macro = lambda d: make_adaptive_squeeze_signals(d, bb_period=20, bb_mult=2.0, kelt_mult=1.2, macro_ema_len=1, min_er=0.20, sl_atr_mult=2.0, tp_rr=3.0)
    tdf_no_macro, _, summ_no_macro = engine.run_strategy(sig_no_macro, spread_pips=25.0)
    
    # Ablation C: Without Squeeze (Keltner = 0 -> pure BB breakout with Macro + ER)
    sig_no_sqz = lambda d: make_adaptive_squeeze_signals(d, bb_period=20, bb_mult=2.0, kelt_mult=0.0, macro_ema_len=200, min_er=0.20, sl_atr_mult=2.0, tp_rr=3.0)
    tdf_no_sqz, _, summ_no_sqz = engine.run_strategy(sig_no_sqz, spread_pips=25.0)
    
    ablation_summary = [
        {'Model Layer': 'Full CAND-001 (Squeeze + Macro + ER)', 'Trades': summ_sym['total_trades'], 'PnL ($)': f"${summ_sym['total_pnl_usd']:+,.2f}", 'PF': f"{summ_sym['overall_pf']:.3f}", 'Exp (R)': f"{summ_sym['avg_expectancy_r']:+.3f}"},
        {'Model Layer': 'Ablation A: Remove Kaufman ER Filter', 'Trades': summ_no_er['total_trades'], 'PnL ($)': f"${summ_no_er['total_pnl_usd']:+,.2f}", 'PF': f"{summ_no_er['overall_pf']:.3f}", 'Exp (R)': f"{summ_no_er['avg_expectancy_r']:+.3f}"},
        {'Model Layer': 'Ablation B: Remove Macro EMA Filter', 'Trades': summ_no_macro['total_trades'], 'PnL ($)': f"${summ_no_macro['total_pnl_usd']:+,.2f}", 'PF': f"{summ_no_macro['overall_pf']:.3f}", 'Exp (R)': f"{summ_no_macro['avg_expectancy_r']:+.3f}"},
        {'Model Layer': 'Ablation C: Remove Squeeze Compression', 'Trades': summ_no_sqz['total_trades'], 'PnL ($)': f"${summ_no_sqz['total_pnl_usd']:+,.2f}", 'PF': f"{summ_no_sqz['overall_pf']:.3f}", 'Exp (R)': f"{summ_no_sqz['avg_expectancy_r']:+.3f}"}
    ]
    print(pd.DataFrame(ablation_summary).to_string(index=False))

if __name__ == '__main__':
    run_adversarial_tests()
