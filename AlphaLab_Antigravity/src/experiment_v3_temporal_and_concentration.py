"""
V3 TEMPORAL ROBUSTNESS & CONCENTRATION STRESS ANALYSIS
======================================================
1. Rolling Temporal Windows (Rolling 4-Quarter and 8-Quarter evaluation)
2. Complete vs Partial Quarter Accounting (100 Complete Quarters from 2001Q3 to 2026Q2)
3. Profit & Outlier Concentration Analysis (Removal of Top 1, Top 3, Top 5 trades & Best Quarter)
4. Macro Regime & Crisis Episode Breakdown
Evaluated for both CAND-001 (Benchmark) and H-105 (Minimalist Squeeze+Macro).
"""

import os
import sys
import numpy as np
import pandas as pd
from deep_quant_engine import DeepQuantEngine, print_backtest_report
from experiment_h060_adaptive_squeeze import make_adaptive_squeeze_signals

sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None

def run_temporal_and_concentration_analysis():
    print("=" * 95)
    print("🔍 V3 TEMPORAL ROBUSTNESS & CONCENTRATION ANALYSIS")
    print("=" * 95)
    
    engine = DeepQuantEngine("GOLD_H1_2001_2026.csv", pip_size=0.01, point_val=0.01)
    
    # Models to test: CAND-001 and H-105
    cand001_fn = lambda d: make_adaptive_squeeze_signals(
        d, bb_period=20, bb_mult=2.0, kelt_mult=1.2, macro_ema_len=200, min_er=0.20, sl_atr_mult=2.0, tp_rr=3.0,
        use_squeeze=True, use_macro=True, use_er=True, use_macd=True
    )
    h105_fn = lambda d: make_adaptive_squeeze_signals(
        d, bb_period=20, bb_mult=2.0, kelt_mult=1.2, macro_ema_len=200, min_er=0.0, sl_atr_mult=2.0, tp_rr=3.0,
        use_squeeze=True, use_macro=True, use_er=False, use_macd=False
    )
    
    for model_name, sig_fn in [("CAND-001 Benchmark", cand001_fn), ("H-105 Minimalist (Squeeze+Macro)", h105_fn)]:
        print("\n" + "=" * 95)
        print(f"EVALUATING: {model_name.upper()}")
        print("=" * 95)
        
        tdf, qdf, summ = engine.run_strategy(sig_fn, spread_pips=25.0, commission_per_lot=7.0)
        
        # ---------------------------------------------------------
        # 1. OUTLIER & PROFIT CONCENTRATION ANALYSIS
        # ---------------------------------------------------------
        pnls = tdf['pnl_usd'].values
        total_pnl = np.sum(pnls)
        sorted_pnls = np.sort(pnls)[::-1]
        
        top1_val = sorted_pnls[0] if len(sorted_pnls) > 0 else 0
        top3_val = np.sum(sorted_pnls[:3]) if len(sorted_pnls) >= 3 else 0
        top5_val = np.sum(sorted_pnls[:5]) if len(sorted_pnls) >= 5 else 0
        top10pct_n = max(1, int(len(sorted_pnls) * 0.10))
        top10pct_val = np.sum(sorted_pnls[:top10pct_n])
        
        # Best Quarter & Year
        q_pnl = tdf.groupby('quarter')['pnl_usd'].sum()
        best_q_name = q_pnl.idxmax() if len(q_pnl) > 0 else "None"
        best_q_val = q_pnl.max() if len(q_pnl) > 0 else 0
        
        y_pnl = tdf.groupby('year')['pnl_usd'].sum()
        best_y_name = y_pnl.idxmax() if len(y_pnl) > 0 else 0
        best_y_val = y_pnl.max() if len(y_pnl) > 0 else 0
        
        print("\n--- PROFIT CONCENTRATION PROFILE ---")
        print(f"Total Net PnL            : ${total_pnl:+,.2f} USD")
        print(f"Top 1 Trade Contribution : ${top1_val:+,.2f} ({top1_val/total_pnl*100:.1f}%)")
        print(f"Top 3 Trades Contribution: ${top3_val:+,.2f} ({top3_val/total_pnl*100:.1f}%)")
        print(f"Top 5 Trades Contribution: ${top5_val:+,.2f} ({top5_val/total_pnl*100:.1f}%)")
        print(f"Top 10% Trades ({top10pct_n} tr)   : ${top10pct_val:+,.2f} ({top10pct_val/total_pnl*100:.1f}%)")
        print(f"Best Quarter ({best_q_name})      : ${best_q_val:+,.2f} ({best_q_val/total_pnl*100:.1f}%)")
        print(f"Best Year ({best_y_name})         : ${best_y_val:+,.2f} ({best_y_val/total_pnl*100:.1f}%)")
        
        # Outlier Removal Gauntlet
        def calc_trimmed_metrics(pnls_trimmed):
            n = len(pnls_trimmed)
            w = pnls_trimmed[pnls_trimmed > 0]
            l = abs(pnls_trimmed[pnls_trimmed < 0])
            pnl = np.sum(pnls_trimmed)
            pf = np.sum(w) / np.sum(l) if np.sum(l) > 0 else 999.0
            return n, pnl, pf
            
        n_base, pnl_base, pf_base = calc_trimmed_metrics(pnls)
        n_no1, pnl_no1, pf_no1 = calc_trimmed_metrics(sorted_pnls[1:])
        n_no3, pnl_no3, pf_no3 = calc_trimmed_metrics(sorted_pnls[3:])
        n_no5, pnl_no5, pf_no5 = calc_trimmed_metrics(sorted_pnls[5:])
        
        # Remove best quarter trades
        tdf_nobestq = tdf[tdf['quarter'] != best_q_name]
        pnl_nobestq = tdf_nobestq['pnl_usd'].sum()
        w_nbq = tdf_nobestq[tdf_nobestq['pnl_usd'] > 0]['pnl_usd'].sum()
        l_nbq = abs(tdf_nobestq[tdf_nobestq['pnl_usd'] < 0]['pnl_usd'].sum())
        pf_nobestq = w_nbq / l_nbq if l_nbq > 0 else 999.0
        
        trim_summary = [
            {'Stress Condition': 'Full Uncut History', 'Trades': n_base, 'Net PnL ($)': f"${pnl_base:+,.2f}", 'Profit Factor': f"{pf_base:.3f}", 'Status': 'SURVIVES'},
            {'Stress Condition': 'Remove Top 1 Best Trade', 'Trades': n_no1, 'Net PnL ($)': f"${pnl_no1:+,.2f}", 'Profit Factor': f"{pf_no1:.3f}", 'Status': 'SURVIVES' if pf_no1 >= 1.20 else 'COLLAPSED'},
            {'Stress Condition': 'Remove Top 3 Best Trades', 'Trades': n_no3, 'Net PnL ($)': f"${pnl_no3:+,.2f}", 'Profit Factor': f"{pf_no3:.3f}", 'Status': 'SURVIVES' if pf_no3 >= 1.20 else 'COLLAPSED'},
            {'Stress Condition': 'Remove Top 5 Best Trades', 'Trades': n_no5, 'Net PnL ($)': f"${pnl_no5:+,.2f}", 'Profit Factor': f"{pf_no5:.3f}", 'Status': 'SURVIVES' if pf_no5 >= 1.20 else 'COLLAPSED'},
            {'Stress Condition': f'Remove Best Single Quarter ({best_q_name})', 'Trades': len(tdf_nobestq), 'Net PnL ($)': f"${pnl_nobestq:+,.2f}", 'Profit Factor': f"{pf_nobestq:.3f}", 'Status': 'SURVIVES' if pf_nobestq >= 1.20 else 'COLLAPSED'}
        ]
        print("\n--- OUTLIER REMOVAL STRESS GAUNTLET ---")
        print(pd.DataFrame(trim_summary).to_string(index=False))
        
        # ---------------------------------------------------------
        # 2. ROLLING TEMPORAL WINDOWS (4-QUARTER & 8-QUARTER)
        # ---------------------------------------------------------
        # Filter to complete quarters (2001Q3 to 2026Q2 = 100 complete quarters)
        complete_qdf = qdf[(qdf['quarter'] >= '2001Q3') & (qdf['quarter'] <= '2026Q2')].reset_index(drop=True)
        n_comp_q = len(complete_qdf)
        
        # Rolling 4-Quarter (1 Year) Windows
        r4_results = []
        for i in range(n_comp_q - 3):
            w_qs = complete_qdf.iloc[i:i+4]
            w_name = f"{w_qs.iloc[0]['quarter']} -> {w_qs.iloc[-1]['quarter']}"
            w_trades = w_qs['trades'].sum()
            w_pnl = w_qs['net_pnl_usd'].sum()
            w_gp = w_qs['gross_profit_usd'].sum()
            w_gl = w_qs['gross_loss_usd'].sum()
            w_pf = w_gp / w_gl if w_gl > 0 else (999.0 if w_gp > 0 else 0.0)
            r4_results.append({'window': w_name, 'trades': w_trades, 'pnl': w_pnl, 'pf': w_pf})
            
        r4_df = pd.DataFrame(r4_results)
        r4_pos = np.mean(r4_df['pnl'] > 0) * 100.0
        r4_pf_gt_1 = np.mean(r4_df['pf'] >= 1.20) * 100.0
        
        # Rolling 8-Quarter (2 Year) Windows
        r8_results = []
        for i in range(n_comp_q - 7):
            w_qs = complete_qdf.iloc[i:i+8]
            w_name = f"{w_qs.iloc[0]['quarter']} -> {w_qs.iloc[-1]['quarter']}"
            w_trades = w_qs['trades'].sum()
            w_pnl = w_qs['net_pnl_usd'].sum()
            w_gp = w_qs['gross_profit_usd'].sum()
            w_gl = w_qs['gross_loss_usd'].sum()
            w_pf = w_gp / w_gl if w_gl > 0 else (999.0 if w_gp > 0 else 0.0)
            r8_results.append({'window': w_name, 'trades': w_trades, 'pnl': w_pnl, 'pf': w_pf})
            
        r8_df = pd.DataFrame(r8_results)
        r8_pos = np.mean(r8_df['pnl'] > 0) * 100.0
        r8_pf_gt_1 = np.mean(r8_df['pf'] >= 1.20) * 100.0
        
        print("\n--- ROLLING TEMPORAL WINDOW CONSISTENCY ---")
        print(f"Complete Quarters Analyzed     : {n_comp_q} Quarters (2001Q3 to 2026Q2)")
        print(f"Rolling 4-Quarter (1-Yr) Windows: {len(r4_df)} total | Profitable: {r4_pos:.1f}% | PF >= 1.20: {r4_pf_gt_1:.1f}%")
        print(f"Rolling 8-Quarter (2-Yr) Windows: {len(r8_df)} total | Profitable: {r8_pos:.1f}% | PF >= 1.20: {r8_pf_gt_1:.1f}%")
        
        # ---------------------------------------------------------
        # 3. MACRO CRISIS & REGIME EPISODE BREAKDOWN
        # ---------------------------------------------------------
        crises = [
            ("2001-2007 Secular Bull Start", 2001, 2007),
            ("2008 GFC & Liquidity Shock", 2008, 2008),
            ("2009-2011 Post-Crisis Gold Run", 2009, 2011),
            ("2012-2015 Gold Bear Market / Crash", 2012, 2015),
            ("2016-2019 Range & Accumulation", 2016, 2019),
            ("2020 COVID Shock", 2020, 2020),
            ("2021-2023 Inflation Cycle", 2021, 2023),
            ("2024-2026 Record Gold Bull Run", 2024, 2026)
        ]
        
        regime_records = []
        for c_name, y_start, y_end in crises:
            sub = tdf[(tdf['year'] >= y_start) & (tdf['year'] <= y_end)]
            n = len(sub)
            if n > 0:
                pnl = sub['pnl_usd'].sum()
                w = sub[sub['pnl_usd'] > 0]['pnl_usd'].sum()
                l = abs(sub[sub['pnl_usd'] < 0]['pnl_usd'].sum())
                pf = w / l if l > 0 else 999.0
                wr = len(sub[sub['pnl_usd'] > 0]) / n * 100.0
            else:
                pnl, pf, wr = 0.0, 0.0, 0.0
            regime_records.append({
                'Market Regime': c_name,
                'Years': f"{y_start}-{y_end}",
                'Trades': n,
                'Net PnL ($)': f"${pnl:+,.2f}",
                'Profit Factor': f"{pf:.3f}",
                'Win Rate': f"{wr:.1f}%"
            })
        print("\n--- MACRO REGIME & CRISIS BREAKDOWN ---")
        print(pd.DataFrame(regime_records).to_string(index=False))

if __name__ == '__main__':
    run_temporal_and_concentration_analysis()
