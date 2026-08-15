"""
V3.1 HARD TEMPORAL DISTRIBUTION AUDIT
======================================
Evaluates CAND-001, CAND-002, and candidate architectures against the V3.1 Hard Temporal Distribution Standard.

Generates:
1. V3_1_TEMPORAL_DISTRIBUTION.csv (100 complete quarters from 2001Q3 to 2026Q2)
2. Comprehensive distribution metrics (Min trades, Median trades, Max trades, Gini, Outlier PnL concentration, Rolling 4Q/8Q consistency, Profitable years)
"""

import os
import sys
import numpy as np
import pandas as pd
from deep_quant_engine import DeepQuantEngine
from experiment_h060_adaptive_squeeze import make_adaptive_squeeze_signals

sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None

def gini(x):
    # Mean absolute difference Gini
    mad = np.abs(np.subtract.outer(x, x)).mean()
    rmad = mad / np.mean(x) if np.mean(x) > 0 else 0
    return 0.5 * rmad

def audit_temporal_distribution():
    print("=" * 95)
    print("📊 V3.1 HARD TEMPORAL DISTRIBUTION AUDIT (100 COMPLETE QUARTERS: 2001Q3 - 2026Q2)")
    print("=" * 95)
    
    engine = DeepQuantEngine("GOLD_H1_2001_2026.csv", pip_size=0.01, point_val=0.01)
    
    # Models to audit
    models = {
        'CAND-001': lambda d: make_adaptive_squeeze_signals(
            d, bb_period=20, bb_mult=2.0, kelt_mult=1.2, macro_ema_len=200, min_er=0.20, sl_atr_mult=2.0, tp_rr=3.0,
            use_squeeze=True, use_macro=True, use_er=True, use_macd=True
        ),
        'CAND-002': lambda d: make_adaptive_squeeze_signals(
            d, bb_period=20, bb_mult=2.0, kelt_mult=1.2, macro_ema_len=200, min_er=0.0, sl_atr_mult=2.0, tp_rr=3.0,
            use_squeeze=True, use_macro=True, use_er=False, use_macd=False
        )
    }
    
    for name, s_fn in models.items():
        print(f"\nAUDITING: {name}")
        tdf, qdf, summ = engine.run_strategy(s_fn, spread_pips=25.0, commission_per_lot=7.0)
        
        # Filter to 100 complete quarters (2001Q3 to 2026Q2)
        comp_q = qdf[(qdf['quarter'] >= '2001Q3') & (qdf['quarter'] <= '2026Q2')].copy().reset_index(drop=True)
        total_complete_trades = comp_q['trades'].sum()
        
        comp_q['trade_share_pct'] = (comp_q['trades'] / total_complete_trades * 100.0) if total_complete_trades > 0 else 0.0
        comp_q['gate12a_pass'] = comp_q['trades'] >= 5
        comp_q['perf_pass'] = (comp_q['net_pnl_usd'] > 0) & (comp_q['profit_factor'] >= 1.20)
        
        # Save CSV for CAND-001
        if name == 'CAND-001':
            out_csv = os.path.join(os.path.dirname(__file__), "..", "..", "V3_1_TEMPORAL_DISTRIBUTION.csv")
            comp_q[['year', 'quarter', 'trades', 'trade_share_pct', 'net_pnl_usd', 'profit_factor', 'win_rate_pct', 'gate12a_pass', 'perf_pass']].to_csv(out_csv, index=False)
            print(f"Saved {out_csv}")
            
        # Distribution Statistics
        trades_arr = comp_q['trades'].values
        min_tr = np.min(trades_arr)
        med_tr = np.median(trades_arr)
        mean_tr = np.mean(trades_arr)
        std_tr = np.std(trades_arr)
        cv_tr = std_tr / mean_tr if mean_tr > 0 else 0.0
        max_tr = np.max(trades_arr)
        p10 = np.percentile(trades_arr, 10)
        p25 = np.percentile(trades_arr, 25)
        p75 = np.percentile(trades_arr, 75)
        p90 = np.percentile(trades_arr, 90)
        max_to_med = max_tr / med_tr if med_tr > 0 else 999.0
        trade_gini = gini(trades_arr)
        
        # Quarters meeting Gate 12A
        n_q_ge_5 = np.sum(comp_q['gate12a_pass'])
        zero_trade_q = np.sum(trades_arr == 0)
        q_under_5 = np.sum(trades_arr < 5)
        
        # Annual Distribution
        comp_y = comp_q.groupby('year').agg({'trades': 'sum', 'net_pnl_usd': 'sum', 'gross_profit_usd': 'sum', 'gross_loss_usd': 'sum'}).reset_index()
        # Full years have 4 complete quarters: 2002 to 2025 (24 full calendar years)
        full_years = comp_y[(comp_y['year'] >= 2002) & (comp_y['year'] <= 2025)].copy()
        n_full_years = len(full_years)
        full_years_ge_20 = np.sum(full_years['trades'] >= 20)
        full_years_profitable = np.sum(full_years['net_pnl_usd'] > 0)
        pct_profitable_years = (full_years_profitable / n_full_years * 100.0) if n_full_years > 0 else 0.0
        
        # Rolling 4Q and 8Q
        r4_pnl, r4_pf_gt_12 = [], []
        for i in range(len(comp_q) - 3):
            sub = comp_q.iloc[i:i+4]
            pnl = sub['net_pnl_usd'].sum()
            gp = sub['gross_profit_usd'].sum()
            gl = sub['gross_loss_usd'].sum()
            pf = gp / gl if gl > 0 else (999.0 if gp > 0 else 0.0)
            r4_pnl.append(pnl > 0)
            r4_pf_gt_12.append(pf >= 1.20)
            
        r8_pnl, r8_pf_gt_12 = [], []
        for i in range(len(comp_q) - 7):
            sub = comp_q.iloc[i:i+8]
            pnl = sub['net_pnl_usd'].sum()
            gp = sub['gross_profit_usd'].sum()
            gl = sub['gross_loss_usd'].sum()
            pf = gp / gl if gl > 0 else (999.0 if gp > 0 else 0.0)
            r8_pnl.append(pnl > 0)
            r8_pf_gt_12.append(pf >= 1.20)
            
        # PnL Concentration
        sorted_q_pnl = np.sort(comp_q['net_pnl_usd'].values)[::-1]
        tot_pnl = comp_q['net_pnl_usd'].sum()
        top1_q_pct = (sorted_q_pnl[0] / tot_pnl * 100.0) if tot_pnl > 0 else 0.0
        top3_q_pct = (np.sum(sorted_q_pnl[:3]) / tot_pnl * 100.0) if tot_pnl > 0 else 0.0
        top5_q_pct = (np.sum(sorted_q_pnl[:5]) / tot_pnl * 100.0) if tot_pnl > 0 else 0.0
        
        print(f"  Total Trades (100 Quarters) : {total_complete_trades}")
        print(f"  Quarter Trade Distribution  : Min={min_tr}, Median={med_tr}, Mean={mean_tr:.2f}, Max={max_tr}")
        print(f"  Percentiles (P10/P25/P75/P90): {p10}/{p25}/{p75}/{p90}")
        print(f"  Max/Median Ratio            : {max_to_med:.2f} | Trade Count Gini: {trade_gini:.3f}")
        print(f"  Quarters with >= 5 Trades   : {n_q_ge_5} / 100 ({n_q_ge_5}%) | Quarters with < 5 Trades: {q_under_5}")
        print(f"  Zero-Trade Quarters (0 tr)  : {zero_trade_q} / 100 ({zero_trade_q}%)")
        print(f"  Full Years (2002-2025) >=20tr: {full_years_ge_20} / {n_full_years} ({full_years_ge_20/n_full_years*100:.1f}%)")
        print(f"  Full Years Profitable       : {full_years_profitable} / {n_full_years} ({pct_profitable_years:.1f}%)")
        print(f"  Rolling 4Q Windows          : {np.mean(r4_pnl)*100:.1f}% Profitable | {np.mean(r4_pf_gt_12)*100:.1f}% PF >= 1.20 (Req: 70% / 65%)")
        print(f"  Rolling 8Q Windows          : {np.mean(r8_pnl)*100:.1f}% Profitable | {np.mean(r8_pf_gt_12)*100:.1f}% PF >= 1.20 (Req: 75% / 70%)")
        print(f"  Top 1/3/5 Quarter PnL Share : {top1_q_pct:.1f}% / {top3_q_pct:.1f}% / {top5_q_pct:.1f}% (Severe: >60%)")
        print(f"  GATE 12A VERDICT            : {'PASSED' if q_under_5 == 0 else 'FAILED (REJECTED FOR PROMOTION)'}")

if __name__ == '__main__':
    audit_temporal_distribution()
