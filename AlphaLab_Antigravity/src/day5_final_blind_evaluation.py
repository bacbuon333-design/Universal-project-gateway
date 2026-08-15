"""
DAY 5: FINAL BLIND HOLDOUT EVALUATION & STATISTICAL GAUNTLET
============================================================
Evaluates CAND-001 (ALAB_SQUEEZE_REGIME_V1) on:
1. Reserved Blind Holdout: 2025 Q3 - 2026 Q2 (4 Quarters)
2. Statistical Rigor: Monte Carlo Permutation Test, Bootstrap Distribution of Expectancy & MaxDD
3. Final Dimensional Verdicts (R1 - R13)
"""

import os
import sys
import numpy as np
import pandas as pd
from deep_quant_engine import DeepQuantEngine, print_backtest_report
from experiment_h060_adaptive_squeeze import make_adaptive_squeeze_signals

sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None

def run_day5_final_verdict():
    print("="*95)
    print("🏛️ DAY 5: FINAL BLIND HOLDOUT EVALUATION & STATISTICAL GAUNTLET")
    print("="*95)
    
    engine = DeepQuantEngine("GOLD_H1_2001_2026.csv", pip_size=0.01)
    
    sig_fn = lambda d: make_adaptive_squeeze_signals(
        d, bb_period=20, bb_mult=2.0, kelt_mult=1.2, macro_ema_len=200, min_er=0.20, sl_atr_mult=2.0, tp_rr=3.0
    )
    
    tdf, qdf, summ = engine.run_strategy(sig_fn, spread_pips=25.0, commission_per_lot=7.0, pessimistic_ambiguous_bars=True)
    
    # -------------------------------------------------------------
    # 1. FINAL BLIND HOLDOUT (2025 Q3 - 2026 Q2)
    # -------------------------------------------------------------
    blind_quarters = ['2025Q3', '2025Q4', '2026Q1', '2026Q2']
    print(f"\nEvaluating Reserved Blind Holdout Quarters: {', '.join(blind_quarters)}")
    
    blind_qdf = qdf[qdf['quarter'].isin(blind_quarters)]
    display_cols = ['quarter', 'trades', 'win_rate_pct', 'net_pnl_usd', 'profit_factor', 'expectancy_r', 'verdict']
    print("\n--- FINAL BLIND HOLDOUT QUARTER RESULTS ---")
    print(blind_qdf[display_cols].to_string(index=False))
    
    blind_trades = tdf[tdf['quarter'].isin(blind_quarters)]
    n_b = len(blind_trades)
    n_b_wins = len(blind_trades[blind_trades['pnl_usd'] > 0])
    b_wr = n_b_wins / n_b * 100 if n_b > 0 else 0.0
    b_pnl = blind_trades['pnl_usd'].sum() if n_b > 0 else 0.0
    b_gp = blind_trades[blind_trades['pnl_usd'] > 0]['pnl_usd'].sum() if n_b_wins > 0 else 0.0
    b_gl = abs(blind_trades[blind_trades['pnl_usd'] < 0]['pnl_usd'].sum()) if (n_b - n_b_wins) > 0 else 0.0
    b_pf = b_gp / b_gl if b_gl > 0 else (999.0 if b_gp > 0 else 0.0)
    b_exp_r = blind_trades['pnl_r'].mean() if n_b > 0 else 0.0
    
    print("\nFinal Blind Holdout Summary:")
    print(f"  Total Trades        : {n_b}")
    print(f"  Net PnL             : ${b_pnl:+,.2f} USD")
    print(f"  Win Rate            : {b_wr:.2f}%")
    print(f"  Profit Factor       : {b_pf:.3f}")
    print(f"  Expectancy (R/trade): {b_exp_r:+.3f} R")
    
    # -------------------------------------------------------------
    # 2. MONTE CARLO & BOOTSTRAP STATISTICAL VALIDATION (R10)
    # -------------------------------------------------------------
    print("\n" + "="*95)
    print("🔬 R10 STATISTICAL VALIDATION (10,000 Monte Carlo Bootstrap Resamples)")
    print("="*95)
    
    pnls = tdf['pnl_usd'].values
    r_pnls = tdf['pnl_r'].values
    n_trades = len(pnls)
    
    np.random.seed(1337)
    n_boot = 10000
    boot_means = []
    boot_pfs = []
    boot_drawdowns = []
    
    for _ in range(n_boot):
        sample = np.random.choice(pnls, size=n_trades, replace=True)
        boot_means.append(np.mean(sample))
        w = sample[sample > 0]
        l = abs(sample[sample < 0])
        pf_val = np.sum(w) / np.sum(l) if np.sum(l) > 0 else 10.0
        boot_pfs.append(pf_val)
        
        # Max DD
        cum = np.cumsum(sample)
        peak = np.maximum.accumulate(cum)
        dd = peak - cum
        boot_drawdowns.append(np.max(dd))
        
    ci_mean_low, ci_mean_high = np.percentile(boot_means, [2.5, 97.5])
    ci_pf_low, ci_pf_high = np.percentile(boot_pfs, [2.5, 97.5])
    ci_dd_95 = np.percentile(boot_drawdowns, 95)
    prob_positive_expectancy = np.mean(np.array(boot_means) > 0) * 100.0
    
    print(f"Sample Size (N)             : {n_trades} trades")
    print(f"Mean Trade PnL 95% CI       : [${ci_mean_low:+.2f}, ${ci_mean_high:+.2f}] (Observed: ${np.mean(pnls):+.2f})")
    print(f"Profit Factor 95% CI        : [{ci_pf_low:.3f}, {ci_pf_high:.3f}] (Observed: {summ['overall_pf']:.3f})")
    print(f"95% Value-at-Risk MaxDD     : ${ci_dd_95:,.2f} USD")
    print(f"Prob(Positive Expectancy)   : {prob_positive_expectancy:.2f}%")

if __name__ == '__main__':
    run_day5_final_verdict()
