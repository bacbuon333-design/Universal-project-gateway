"""
REVALIDATION V2 RUNNER: CLEAN SCIENTIFIC REVALIDATION OF CAND-001
=================================================================
Executes clean revalidation of CAND-001 following all auditor corrections:
1. Symmetric Execution (Bid/Ask, 1 round-trip spread on both BUY & SELL)
2. Accurate Historical Partitioning (Development vs Contaminated vs Candidate Holdout)
3. Full 100/100 Calendar Quarter Distribution (No truncation of inactive quarters)
4. Long vs Short Comparative Impact of SELL Spread Fix
5. Corrected Spread Stress Gauntlet (25, 35, 45, 60, 80, 100 pips)
6. True Component Ablations using Boolean Flags
7. Multi-Method Bootstrap: IID Trade vs Quarter Block vs Temporal Block
"""

import os
import sys
import json
import numpy as np
import pandas as pd
from deep_quant_engine import DeepQuantEngine, print_backtest_report
from experiment_h060_adaptive_squeeze import make_adaptive_squeeze_signals

sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None

def run_revalidation():
    print("=" * 95)
    print("🔬 REVALIDATION V2: CLEAN SCIENTIFIC EVALUATION OF CAND-001")
    print("=" * 95)
    
    engine = DeepQuantEngine("GOLD_H1_2001_2026.csv", pip_size=0.01, point_val=0.01)
    
    # Exact Frozen Candidate Signal Function
    base_sig_fn = lambda d: make_adaptive_squeeze_signals(
        d, bb_period=20, bb_mult=2.0, kelt_mult=1.2, macro_ema_len=200, min_er=0.20, sl_atr_mult=2.0, tp_rr=3.0,
        use_squeeze=True, use_macro=True, use_er=True, use_macd=True
    )
    
    # -------------------------------------------------------------
    # 1. FULL HISTORY & TIME PARTITIONS
    # -------------------------------------------------------------
    tdf, qdf, summ = engine.run_strategy(base_sig_fn, spread_pips=25.0, commission_per_lot=7.0, pessimistic_ambiguous_bars=True)
    
    # Partitions
    tdf_dev = tdf[tdf['year'] < 2022] # 2001 - 2021
    tdf_contam = tdf[(tdf['year'] >= 2022) & (tdf['quarter'] < '2025Q3')] # 2022 - 2025 Q2
    tdf_holdout = tdf[tdf['quarter'] >= '2025Q3'] # 2025 Q3 - 2026 Q2
    
    def calc_stats(df_sub, label):
        n = len(df_sub)
        if n == 0:
            return {'label': label, 'trades': 0, 'pnl': 0.0, 'pf': 0.0, 'wr': 0.0, 'exp_r': 0.0, 'exp_usd': 0.0}
        wins = len(df_sub[df_sub['pnl_usd'] > 0])
        wr = (wins / n) * 100.0
        pnl = df_sub['pnl_usd'].sum()
        gp = df_sub[df_sub['pnl_usd'] > 0]['pnl_usd'].sum() if wins > 0 else 0.0
        gl = abs(df_sub[df_sub['pnl_usd'] < 0]['pnl_usd'].sum()) if (n - wins) > 0 else 0.0
        pf = gp / gl if gl > 0 else (999.0 if gp > 0 else 0.0)
        exp_r = df_sub['pnl_r'].mean()
        exp_usd = df_sub['pnl_usd'].mean()
        return {'label': label, 'trades': n, 'pnl': pnl, 'pf': pf, 'wr': wr, 'exp_r': exp_r, 'exp_usd': exp_usd}
        
    part_stats = [
        calc_stats(tdf, "Full History (2001-2026)"),
        calc_stats(tdf_dev, "Development Data (2001-2021)"),
        calc_stats(tdf_contam, "Contaminated Validation (2022-2025Q2)"),
        calc_stats(tdf_holdout, "Candidate Holdout (2025Q3-2026Q2)")
    ]
    
    print("\n" + "="*95)
    print("SECTION 1: DATA PARTITION PERFORMANCE UNDER CORRECTED EXECUTION")
    print("="*95)
    part_df = pd.DataFrame(part_stats)
    part_df['pnl_str'] = part_df['pnl'].apply(lambda x: f"${x:+,.2f}")
    part_df['pf_str'] = part_df['pf'].apply(lambda x: f"{x:.3f}")
    part_df['wr_str'] = part_df['wr'].apply(lambda x: f"{x:.1f}%")
    part_df['exp_r_str'] = part_df['exp_r'].apply(lambda x: f"{x:+.3f} R")
    part_df['exp_usd_str'] = part_df['exp_usd'].apply(lambda x: f"${x:+.2f}")
    
    print(part_df[['label', 'trades', 'pnl_str', 'pf_str', 'wr_str', 'exp_r_str', 'exp_usd_str']].to_string(index=False))
    
    # -------------------------------------------------------------
    # 2. LONG VS SHORT BREAKDOWN & IMPACT OF SELL SPREAD FIX
    # -------------------------------------------------------------
    print("\n" + "="*95)
    print("SECTION 2: DIRECTIONAL LEG BREAKDOWN & IMPACT OF SELL SPREAD REPAIR")
    print("="*95)
    
    tdf_long = tdf[tdf['direction'] == 'BUY']
    tdf_short = tdf[tdf['direction'] == 'SELL']
    
    stat_long = calc_stats(tdf_long, "Corrected Long-Only Leg")
    stat_short = calc_stats(tdf_short, "Corrected Short-Only Leg")
    
    dir_summary = [
        {
            'Leg': 'Long Leg (BUY)',
            'Old Reported PF': '1.682',
            'Corrected PF': f"{stat_long['pf']:.3f}",
            'Old Net PnL': '+$2,717.56',
            'Corrected Net PnL': f"${stat_long['pnl']:+,.2f}",
            'Trades': stat_long['trades'],
            'Win Rate': f"{stat_long['wr']:.1f}%"
        },
        {
            'Leg': 'Short Leg (SELL)',
            'Old Reported PF': '2.514',
            'Corrected PF': f"{stat_short['pf']:.3f}",
            'Old Net PnL': '+$5,484.04',
            'Corrected Net PnL': f"${stat_short['pnl']:+,.2f}",
            'Trades': stat_short['trades'],
            'Win Rate': f"{stat_short['wr']:.1f}%"
        },
        {
            'Leg': 'Combined Full CAND-001',
            'Old Reported PF': '2.078',
            'Corrected PF': f"{summ['overall_pf']:.3f}",
            'Old Net PnL': '+$8,201.60',
            'Corrected Net PnL': f"${summ['total_pnl_usd']:+,.2f}",
            'Trades': summ['total_trades'],
            'Win Rate': f"{summ['overall_wr_pct']:.1f}%"
        }
    ]
    print(pd.DataFrame(dir_summary).to_string(index=False))
    
    # -------------------------------------------------------------
    # 3. FULL 100-QUARTER DISTRIBUTION ACCOUNTING
    # -------------------------------------------------------------
    print("\n" + "="*95)
    print("SECTION 3: FULL 100/100 CALENDAR QUARTER ACCOUNTING")
    print("="*95)
    print(f"Total Calendar Quarters Evaluated : {summ['total_calendar_quarters']} (100.0%)")
    print(f"  - No-Trade Quarters (0 trades)  : {summ['no_trade_quarters']} ({summ['no_trade_quarters']/summ['total_calendar_quarters']*100:.1f}%)")
    print(f"  - Low-Trade Quarters (1-2 trades): {summ['low_trade_quarters']} ({summ['low_trade_quarters']/summ['total_calendar_quarters']*100:.1f}%)")
    print(f"  - Active Quarters (>=3 trades)  : {summ['active_quarters']} ({summ['active_quarters']/summ['total_calendar_quarters']*100:.1f}%)")
    print(f"Quarter Verdicts:")
    print(f"  - PASS Quarters (PF>=1.25, PnL>0): {summ['pass_quarters']}")
    print(f"  - FAIL Quarters (PF<0.90, PnL<0) : {summ['fail_quarters']}")
    print(f"  - INCONCLUSIVE Quarters (<3 tr)  : {summ['inconclusive_quarters']}")
    print(f"Pass Rates:")
    print(f"  - Active Quarter Pass Rate      : {summ['active_quarter_pass_pct']:.1f}% ({summ['pass_quarters']}/{summ['active_quarters']})")
    print(f"  - Full Calendar Quarter Pass Rate: {summ['full_calendar_pass_pct']:.1f}% ({summ['pass_quarters']}/{summ['total_calendar_quarters']})")
    
    # -------------------------------------------------------------
    # 4. SPREAD STRESS GAUNTLET (SYMMETRICAL)
    # -------------------------------------------------------------
    print("\n" + "="*95)
    print("SECTION 4: SPREAD STRESS GAUNTLET (CORRECTED SYMMETRICAL COST)")
    print("="*95)
    spreads = [25.0, 35.0, 45.0, 60.0, 80.0, 100.0]
    stress_records = []
    
    def make_long_only_fn(df):
        s, sl, tp = base_sig_fn(df)
        s[s == -1] = 0
        return s, sl, tp
        
    def make_short_only_fn(df):
        s, sl, tp = base_sig_fn(df)
        s[s == 1] = 0
        return s, sl, tp
        
    for spr in spreads:
        _, _, s_full = engine.run_strategy(base_sig_fn, spread_pips=spr)
        _, _, s_lng = engine.run_strategy(make_long_only_fn, spread_pips=spr)
        _, _, s_sht = engine.run_strategy(make_short_only_fn, spread_pips=spr)
        stress_records.append({
            'Spread': f"{spr:.1f} pips",
            'Full PnL': f"${s_full['total_pnl_usd']:+,.2f}",
            'Full PF': f"{s_full['overall_pf']:.3f}",
            'Long PnL': f"${s_lng['total_pnl_usd']:+,.2f}",
            'Long PF': f"{s_lng['overall_pf']:.3f}",
            'Short PnL': f"${s_sht['total_pnl_usd']:+,.2f}",
            'Short PF': f"{s_sht['overall_pf']:.3f}"
        })
    print(pd.DataFrame(stress_records).to_string(index=False))
    
    # -------------------------------------------------------------
    # 5. TRUE COMPONENT ABLATION TESTS (BOOLEAN FLAGS)
    # -------------------------------------------------------------
    print("\n" + "="*95)
    print("SECTION 5: TRUE COMPONENT ABLATION (EXPLICIT BOOLEAN FLAGS)")
    print("="*95)
    
    ablations = [
        ("Full CAND-001 (Squeeze + Macro + ER + MACD)", {'use_squeeze': True, 'use_macro': True, 'use_er': True, 'use_macd': True}),
        ("Ablation A: No Kaufman ER", {'use_squeeze': True, 'use_macro': True, 'use_er': False, 'use_macd': True}),
        ("Ablation B: No Macro EMA Trend Filter", {'use_squeeze': True, 'use_macro': False, 'use_er': True, 'use_macd': True}),
        ("Ablation C: No Volatility Squeeze", {'use_squeeze': False, 'use_macro': True, 'use_er': True, 'use_macd': True}),
        ("Ablation D: No MACD Momentum Filter", {'use_squeeze': True, 'use_macro': True, 'use_er': True, 'use_macd': False}),
        ("Sub-system E: Squeeze Only (No Filters)", {'use_squeeze': True, 'use_macro': False, 'use_er': False, 'use_macd': False}),
        ("Sub-system F: Squeeze + Macro (No ER/MACD)", {'use_squeeze': True, 'use_macro': True, 'use_er': False, 'use_macd': False}),
        ("Sub-system G: Squeeze + ER (No Macro/MACD)", {'use_squeeze': True, 'use_macro': False, 'use_er': True, 'use_macd': False})
    ]
    
    ablation_results = []
    for name, flags in ablations:
        fn = lambda d, fl=flags: make_adaptive_squeeze_signals(
            d, bb_period=20, bb_mult=2.0, kelt_mult=1.2, macro_ema_len=200, min_er=0.20, sl_atr_mult=2.0, tp_rr=3.0, **fl
        )
        t_ab, _, s_ab = engine.run_strategy(fn, spread_pips=25.0)
        ablation_results.append({
            'Model Architecture': name,
            'Trades': s_ab['total_trades'],
            'Net PnL ($)': f"${s_ab['total_pnl_usd']:+,.2f}",
            'Profit Factor': f"{s_ab['overall_pf']:.3f}",
            'Win Rate': f"{s_ab['overall_wr_pct']:.1f}%",
            'Exp (R)': f"{s_ab['avg_expectancy_r']:+.3f} R"
        })
    print(pd.DataFrame(ablation_results).to_string(index=False))
    
    # -------------------------------------------------------------
    # 6. MULTI-METHOD BOOTSTRAP RESAMPLING GAUNTLET
    # -------------------------------------------------------------
    print("\n" + "="*95)
    print("SECTION 6: MULTI-METHOD BOOTSTRAP RESAMPLING (10,000 ITERATIONS)")
    print("="*95)
    
    pnls = tdf['pnl_usd'].values
    n_t = len(pnls)
    np.random.seed(42)
    n_boot = 10000
    
    # A. IID Trade Bootstrap
    iid_means = []
    iid_pfs = []
    for _ in range(n_boot):
        samp = np.random.choice(pnls, size=n_t, replace=True)
        iid_means.append(np.mean(samp))
        w = samp[samp > 0]
        l = abs(samp[samp < 0])
        pf_val = np.sum(w) / np.sum(l) if np.sum(l) > 0 else 10.0
        iid_pfs.append(pf_val)
        
    ci_iid_mean = np.percentile(iid_means, [2.5, 97.5])
    ci_iid_pf = np.percentile(iid_pfs, [2.5, 97.5])
    prob_pos_iid = np.mean(np.array(iid_means) > 0) * 100.0
    
    # B. Quarter Block Bootstrap (Resampling entire calendar quarters)
    quarter_groups = [tdf[tdf['quarter'] == q]['pnl_usd'].values for q in qdf['quarter'].unique()]
    n_q = len(quarter_groups)
    q_means = []
    q_pfs = []
    for _ in range(n_boot):
        idx = np.random.choice(n_q, size=n_q, replace=True)
        samp_q = np.concatenate([quarter_groups[i] for i in idx if len(quarter_groups[i]) > 0])
        if len(samp_q) > 0:
            q_means.append(np.mean(samp_q))
            w = samp_q[samp_q > 0]
            l = abs(samp_q[samp_q < 0])
            pf_val = np.sum(w) / np.sum(l) if np.sum(l) > 0 else 10.0
            q_pfs.append(pf_val)
            
    ci_q_mean = np.percentile(q_means, [2.5, 97.5])
    ci_q_pf = np.percentile(q_pfs, [2.5, 97.5])
    prob_pos_q = np.mean(np.array(q_means) > 0) * 100.0
    
    # C. Temporal Block Bootstrap (Block length = 5 trades)
    block_len = 5
    num_blocks = int(np.ceil(n_t / block_len))
    blocks = [pnls[i:i+block_len] for i in range(0, n_t - block_len + 1)]
    tb_means = []
    tb_pfs = []
    for _ in range(n_boot):
        b_idx = np.random.choice(len(blocks), size=num_blocks, replace=True)
        samp_tb = np.concatenate([blocks[i] for i in b_idx])[:n_t]
        tb_means.append(np.mean(samp_tb))
        w = samp_tb[samp_tb > 0]
        l = abs(samp_tb[samp_tb < 0])
        pf_val = np.sum(w) / np.sum(l) if np.sum(l) > 0 else 10.0
        tb_pfs.append(pf_val)
        
    ci_tb_mean = np.percentile(tb_means, [2.5, 97.5])
    ci_tb_pf = np.percentile(tb_pfs, [2.5, 97.5])
    prob_pos_tb = np.mean(np.array(tb_means) > 0) * 100.0
    
    mc_table = [
        {'Method': 'A. IID Trade Bootstrap', 'Mean PnL 95% CI': f"[${ci_iid_mean[0]:+.2f}, ${ci_iid_mean[1]:+.2f}]", 'PF 95% CI': f"[{ci_iid_pf[0]:.3f}, {ci_iid_pf[1]:.3f}]", 'Prob(Pos Expectancy)': f"{prob_pos_iid:.2f}%"},
        {'Method': 'B. Quarter Block Bootstrap', 'Mean PnL 95% CI': f"[${ci_q_mean[0]:+.2f}, ${ci_q_mean[1]:+.2f}]", 'PF 95% CI': f"[{ci_q_pf[0]:.3f}, {ci_q_pf[1]:.3f}]", 'Prob(Pos Expectancy)': f"{prob_pos_q:.2f}%"},
        {'Method': 'C. Temporal Block Bootstrap', 'Mean PnL 95% CI': f"[${ci_tb_mean[0]:+.2f}, ${ci_tb_mean[1]:+.2f}]", 'PF 95% CI': f"[{ci_tb_pf[0]:.3f}, {ci_tb_pf[1]:.3f}]", 'Prob(Pos Expectancy)': f"{prob_pos_tb:.2f}%"}
    ]
    print(pd.DataFrame(mc_table).to_string(index=False))
    
    # Save machine-readable output
    os.makedirs(os.path.join(os.path.dirname(__file__), '..', 'reports'), exist_ok=True)
    tdf.to_csv(os.path.join(os.path.dirname(__file__), '..', 'reports', 'revalidation_v2_trades.csv'), index=False)
    qdf.to_csv(os.path.join(os.path.dirname(__file__), '..', 'reports', 'revalidation_v2_quarters.csv'), index=False)
    
    summary_export = {
        'candidate_id': 'CAND-001',
        'overall_trades': summ['total_trades'],
        'overall_pnl_usd': summ['total_pnl_usd'],
        'overall_pf': summ['overall_pf'],
        'overall_wr_pct': summ['overall_wr_pct'],
        'expectancy_r': summ['avg_expectancy_r'],
        'data_partitions': part_stats,
        'directional_breakdown': {'long': stat_long, 'short': stat_short},
        'quarter_summary': summ,
        'bootstrap': {
            'iid_trade': {'mean_ci': list(ci_iid_mean), 'pf_ci': list(ci_iid_pf), 'prob_pos': prob_pos_iid},
            'quarter_block': {'mean_ci': list(ci_q_mean), 'pf_ci': list(ci_q_pf), 'prob_pos': prob_pos_q},
            'temporal_block': {'mean_ci': list(ci_tb_mean), 'pf_ci': list(ci_tb_pf), 'prob_pos': prob_pos_tb}
        }
    }
    with open(os.path.join(os.path.dirname(__file__), '..', 'reports', 'revalidation_v2_summary.json'), 'w', encoding='utf-8') as f:
        json.dump(summary_export, f, indent=2)
    print("\nSaved machine-readable reports to AlphaLab_Antigravity/reports/.")

if __name__ == '__main__':
    run_revalidation()
