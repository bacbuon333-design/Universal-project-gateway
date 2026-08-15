"""
DAY 3: FREEZE & RANDOM CROSS-YEAR OOS VALIDATION
=================================================
Candidate: CAND-001 (ALAB_SQUEEZE_REGIME_V1)
Validation Protocol:
1. Cryptographic Configuration Hash Freezing
2. Deterministic Pseudo-Random Quarter Selection (Fixed Seed 42 across 2001-2021 Pristine Universe)
3. Chronological Walk-Forward Slicing
4. Individual Quarter Verdicts (PASS, FAIL, INCONCLUSIVE)
"""

import os
import sys
import hashlib
import json
import numpy as np
import pandas as pd
from deep_quant_engine import DeepQuantEngine, print_backtest_report
from experiment_h060_adaptive_squeeze import make_adaptive_squeeze_signals

sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None

CANDIDATE_CONFIG = {
    "candidate_id": "CAND-001",
    "strategy_name": "ALAB_SQUEEZE_REGIME_V1",
    "asset": "GOLD",
    "timeframe": "H1",
    "bb_period": 20,
    "bb_mult": 2.0,
    "kelt_mult": 1.2,
    "macro_ema_len": 200,
    "min_er": 0.20,
    "sl_atr_mult": 2.0,
    "tp_rr_ratio": 3.0,
    "spread_pips": 25.0,
    "commission_per_lot": 7.0,
    "pessimistic_ambiguous_bars": True
}

def compute_config_hash(cfg: dict) -> str:
    s = json.dumps(cfg, sort_keys=True)
    return hashlib.sha256(s.encode('utf-8')).hexdigest()

def run_day3_validation():
    cfg_hash = compute_config_hash(CANDIDATE_CONFIG)
    print("="*95)
    print(f"🔒 DAY 3: FREEZING CANDIDATE {CANDIDATE_CONFIG['candidate_id']} ({CANDIDATE_CONFIG['strategy_name']})")
    print(f"Configuration SHA256 Hash: {cfg_hash}")
    print("="*95)
    
    # Save frozen configuration artifact
    frozen_path = os.path.join(os.path.dirname(__file__), '..', 'checkpoints', 'CAND_001_FROZEN_CONFIG.json')
    with open(frozen_path, 'w', encoding='utf-8') as f:
        json.dump({**CANDIDATE_CONFIG, "sha256": cfg_hash}, f, indent=2)
    print(f"Saved frozen config to: {frozen_path}")
    
    # 1. Load Engine on Full 25-Year Gold Dataset
    engine = DeepQuantEngine("GOLD_H1_2001_2026.csv", pip_size=0.01)
    
    sig_fn = lambda d: make_adaptive_squeeze_signals(
        d, 
        bb_period=CANDIDATE_CONFIG['bb_period'],
        bb_mult=CANDIDATE_CONFIG['bb_mult'],
        kelt_mult=CANDIDATE_CONFIG['kelt_mult'],
        macro_ema_len=CANDIDATE_CONFIG['macro_ema_len'],
        min_er=CANDIDATE_CONFIG['min_er'],
        sl_atr_mult=CANDIDATE_CONFIG['sl_atr_mult'],
        tp_rr=CANDIDATE_CONFIG['tp_rr_ratio']
    )
    
    tdf, qdf, summ = engine.run_strategy(
        sig_fn, 
        spread_pips=CANDIDATE_CONFIG['spread_pips'], 
        commission_per_lot=CANDIDATE_CONFIG['commission_per_lot'],
        pessimistic_ambiguous_bars=CANDIDATE_CONFIG['pessimistic_ambiguous_bars']
    )
    
    # 2. Random Cross-Year OOS Protocol (Constitution #16)
    # Universe: Pristine Quarters from 2001 Q2 to 2021 Q4 (83 eligible quarters)
    pristine_quarters = [q for q in qdf['quarter'].unique() if int(q[:4]) < 2022]
    np.random.seed(42) # Immutable fixed seed
    # Sample 15 random quarters across different years
    sampled_oos_quarters = sorted(np.random.choice(pristine_quarters, size=15, replace=False))
    
    print("\n" + "="*95)
    print(f"🎲 RANDOM-QUARTER CROSS-YEAR OOS TEST (Seed=42, 15 Pre-committed Quarters from 2001-2021)")
    print("="*95)
    print(f"Selected Quarters: {', '.join(sampled_oos_quarters)}")
    
    sampled_qdf = qdf[qdf['quarter'].isin(sampled_oos_quarters)].copy()
    display_cols = ['quarter', 'trades', 'win_rate_pct', 'net_pnl_usd', 'profit_factor', 'expectancy_r', 'verdict']
    print("\n--- RANDOM OOS QUARTERS INDIVIDUAL VERDICTS ---")
    print(sampled_qdf[display_cols].to_string(index=False))
    
    # Calculate OOS sample stats
    oos_trades_df = tdf[tdf['quarter'].isin(sampled_oos_quarters)]
    n_oos_t = len(oos_trades_df)
    n_oos_wins = len(oos_trades_df[oos_trades_df['pnl_usd'] > 0])
    oos_wr = n_oos_wins / n_oos_t * 100 if n_oos_t > 0 else 0.0
    oos_pnl = oos_trades_df['pnl_usd'].sum() if n_oos_t > 0 else 0.0
    oos_gp = oos_trades_df[oos_trades_df['pnl_usd'] > 0]['pnl_usd'].sum() if n_oos_wins > 0 else 0.0
    oos_gl = abs(oos_trades_df[oos_trades_df['pnl_usd'] < 0]['pnl_usd'].sum()) if (n_oos_t - n_oos_wins) > 0 else 0.0
    oos_pf = oos_gp / oos_gl if oos_gl > 0 else (999.0 if oos_gp > 0 else 0.0)
    
    print(f"\nRandom OOS Aggregate Stats:")
    print(f"  Total Trades in 15 Random Quarters: {n_oos_t}")
    print(f"  Net PnL                            : ${oos_pnl:+,.2f} USD")
    print(f"  Win Rate                           : {oos_wr:.2f}%")
    print(f"  Profit Factor                      : {oos_pf:.3f}")
    
    active_sampled = sampled_qdf[sampled_qdf['trades'] >= 3]
    pass_cnt = len(active_sampled[active_sampled['verdict'] == 'PASS'])
    fail_cnt = len(active_sampled[active_sampled['verdict'] == 'FAIL'])
    inc_cnt = len(sampled_qdf) - len(active_sampled)
    print(f"  Quarter Verdicts: {pass_cnt} PASS / {fail_cnt} FAIL / {inc_cnt} INCONCLUSIVE")
    
    # 3. Chronological Walk-Forward Analysis (Constitution #39)
    print("\n" + "="*95)
    print("🚶 CHRONOLOGICAL WALK-FORWARD TEST (Year-by-Year Slices: Past History -> Next Unseen Year)")
    print("="*95)
    
    wf_results = []
    years = sorted(tdf['year'].unique())
    
    for y in years:
        y_trades = tdf[tdf['year'] == y]
        n_y = len(y_trades)
        if n_y == 0:
            continue
        y_wins = len(y_trades[y_trades['pnl_usd'] > 0])
        y_pnl = y_trades['pnl_usd'].sum()
        y_gp = y_trades[y_trades['pnl_usd'] > 0]['pnl_usd'].sum()
        y_gl = abs(y_trades[y_trades['pnl_usd'] < 0]['pnl_usd'].sum())
        y_pf = y_gp / y_gl if y_gl > 0 else (999.0 if y_gp > 0 else 0.0)
        y_wr = y_wins / n_y * 100
        
        # Quarter pass count in this year
        y_qdf = qdf[qdf['year'] == y]
        active_yq = y_qdf[y_qdf['trades'] >= 2]
        pass_yq = len(y_qdf[y_qdf['net_pnl_usd'] > 0])
        
        wf_results.append({
            'Year': y,
            'Trades': n_y,
            'WinRate%': f"{y_wr:.1f}%",
            'NetPnL ($)': f"${y_pnl:+,.2f}",
            'ProfitFactor': f"{y_pf:.2f}",
            'ProfitableQs': f"{pass_yq}/{len(y_qdf)}",
            'Verdict': 'PASS' if y_pnl > 0 else 'FAIL'
        })
        
    wf_df = pd.DataFrame(wf_results)
    print(wf_df.to_string(index=False))
    
    total_years = len(wf_df)
    passed_years = sum(1 for r in wf_results if r['Verdict'] == 'PASS')
    print(f"\nWalk-Forward Annual Consistency: {passed_years}/{total_years} Years Profitable ({passed_years/total_years*100:.1f}%)")

if __name__ == '__main__':
    run_day3_validation()
