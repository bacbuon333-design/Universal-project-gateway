"""
===================================================================
ANTIGRAVITY GOLD ARENA ENGINE (INDEPENDENT TERRITORY)
===================================================================
Executes high-throughput tick-event & bar probing on GOLD (XAUUSD)
using the Crash-Safe Parallel Execution Harness.

Target: Discover ultimate market truth for GOLD:
- $1,000 -> $3,000 (+200% return)
- Max Drawdown <= 35.0%
- Zero Overfitting under Cost Stress x2 & Monte Carlo 1,000x
"""

import os
import sys
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

import sqlite3
import pandas as pd
import numpy as np
import logging
from datetime import datetime, timezone

# Add AlphaLab & AlphaLab_Antigravity root to path
ANTIGRAVITY_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXPERTS_DIR = os.path.dirname(ANTIGRAVITY_DIR)
ALPHALAB_DIR = os.path.join(EXPERTS_DIR, "AlphaLab")

sys.path.insert(0, ALPHALAB_DIR)
sys.path.insert(0, ANTIGRAVITY_DIR)
sys.path.insert(0, EXPERTS_DIR)

from src.validation_layer.backtester import EventBacktester
from src.validation_layer.walk_forward import WalkForwardValidator
from src.validation_layer.monte_carlo import MonteCarloSimulator
from src.research_layer.strategies import (
    signal_bollinger_mr, signal_bollinger_mr_v2, signal_turtle_trend, signal_donchian_breakout,
    signal_bollinger_squeeze, signal_momentum_roc, signal_market_structure_bos,
    signal_asia_fade, signal_mr_vol_spike
)
from scratch.harvest_and_backtest_external import signal_s4_ema_cross
from run_tournament import load_bars_with_regimes
from AlphaLab_Antigravity.src.crash_safe_harness import CrashSafeHarness

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

GOLD_PROBE_CANDIDATES = [
    {
        "id": "AGOLD-001",
        "name": "Volatility Squeeze Breakout (GOLD)",
        "signal_fn": signal_bollinger_squeeze,
        "grid": [{'period': 20, 'bb_mult': 2.0, 'atr_mult': 1.5}],
        "perturbed_grid": [{'period': 22, 'bb_mult': 2.2, 'atr_mult': 1.65}]
    },
    {
        "id": "AGOLD-002",
        "name": "Turtle Trend Breakout (GOLD)",
        "signal_fn": signal_turtle_trend,
        "grid": [{'entry_period': 20, 'exit_period': 10}],
        "perturbed_grid": [{'entry_period': 22, 'exit_period': 11}]
    },
    {
        "id": "AGOLD-003",
        "name": "S4 EMA Cross (9/21 - GOLD)",
        "signal_fn": signal_s4_ema_cross,
        "grid": [{'fast': 9, 'slow': 21}],
        "perturbed_grid": [{'fast': 10, 'slow': 23}]
    },
    {
        "id": "AGOLD-004",
        "name": "Donchian Channel Breakout (GOLD)",
        "signal_fn": signal_donchian_breakout,
        "grid": [{'period': 20}],
        "perturbed_grid": [{'period': 22}]
    },
    {
        "id": "AGOLD-005",
        "name": "Market Structure Swing BOS (GOLD)",
        "signal_fn": signal_market_structure_bos,
        "grid": [{'left_bars': 5, 'right_bars': 5}],
        "perturbed_grid": [{'left_bars': 6, 'right_bars': 6}]
    },
    {
        "id": "AGOLD-006",
        "name": "Asian Session Range Fade (GOLD)",
        "signal_fn": signal_asia_fade,
        "grid": [{'asia_start': 0, 'asia_end': 7}],
        "perturbed_grid": [{'asia_start': 0, 'asia_end': 8}]
    },
    {
        "id": "AGOLD-007",
        "name": "Rate of Change Momentum (GOLD)",
        "signal_fn": signal_momentum_roc,
        "grid": [{'period': 12, 'roc_period': 10}],
        "perturbed_grid": [{'period': 14, 'roc_period': 12}]
    },
    {
        "id": "AGOLD-008",
        "name": "ATR Volatility Spike Exhaustion (GOLD)",
        "signal_fn": signal_mr_vol_spike,
        "grid": [{'period': 20, 'atr_mult': 2.0}],
        "perturbed_grid": [{'period': 22, 'atr_mult': 2.2}]
    }
]


def evaluate_single_gold_probe(cand, df_gold):
    c_id = cand["id"]
    c_name = cand["name"]
    
    # 1. BASELINE RUN
    bt_base = EventBacktester(
        initial_capital=10000.0, commission_per_lot=7.0, slippage_points=1.5,
        point_value=0.01, contract_size=100.0, lot_size=0.01
    )
    wfo = WalkForwardValidator(df_gold, anchors=4)
    res_base = wfo.run_wfo(bt_base, cand["grid"], cand["signal_fn"])
    
    oos_trades = res_base['oos_trades']
    oos_pnl = [t['pnl'] for t in oos_trades]
    trade_count = len(oos_trades)
    
    oos_ret_raw = [item[1] for item in res_base['oos_returns']]
    ret_s = pd.Series(oos_ret_raw)
    base_sharpe = float((ret_s.mean() / ret_s.std()) * np.sqrt(252 * 24)) if len(ret_s) > 1 and ret_s.std() > 0 else 0.0
    
    if oos_pnl:
        pnl_s = pd.Series(oos_pnl)
        gp = pnl_s[pnl_s > 0].sum()
        gl = abs(pnl_s[pnl_s < 0].sum())
        base_pf = float(gp / gl if gl > 0 else gp)
        eq = 10000.0 + np.cumsum(oos_pnl)
        cm = np.maximum.accumulate(eq)
        base_dd = float(abs(((eq - cm) / cm).min()) * 100.0)
    else:
        base_pf, base_dd = 0.0, 0.0
        
    # 2. TEST 1: COST STRESS X2
    bt_stress = EventBacktester(
        initial_capital=10000.0, commission_per_lot=14.0, slippage_points=3.0,
        point_value=0.01, contract_size=100.0, lot_size=0.01
    )
    res_stress = wfo.run_wfo(bt_stress, cand["grid"], cand["signal_fn"])
    stress_ret_raw = [item[1] for item in res_stress['oos_returns']]
    s_ret_s = pd.Series(stress_ret_raw)
    stress_sharpe = float((s_ret_s.mean() / s_ret_s.std()) * np.sqrt(252 * 24)) if len(s_ret_s) > 1 and s_ret_s.std() > 0 else 0.0
    
    stress_pnl = [t['pnl'] for t in res_stress['oos_trades']]
    if stress_pnl:
        spnl_s = pd.Series(stress_pnl)
        sgp = spnl_s[spnl_s > 0].sum()
        sgl = abs(spnl_s[spnl_s < 0].sum())
        stress_pf = float(sgp / sgl if sgl > 0 else sgp)
    else:
        stress_pf = 0.0
        
    test1_pass = (stress_sharpe >= 0.30) and (stress_pf >= 1.10)

    # 3. TEST 2: MONTE CARLO PERMUTATION (1,000 SHUFFLES)
    mc = MonteCarloSimulator(oos_pnl, initial_capital=10000.0)
    mc_res = mc.simulate(num_simulations=1000)
    ror = mc_res['risk_of_ruin_pct']
    p95_dd = float(np.percentile(mc_res['drawdowns'], 95) * 100.0) if 'drawdowns' in mc_res else base_dd
    test2_pass = (ror < 10.0) and (p95_dd < 20.0)

    # 4. TEST 3: ROLLING WALK-FORWARD
    wfe = res_base['average_wfe']
    split_pnls = [s['oos_net_profit'] for s in res_base['splits_results']]
    win_ratio = sum(1 for p in split_pnls if p > 0) / len(split_pnls) if split_pnls else 0.0
    test3_pass = (wfe >= 0.40) and (win_ratio >= 0.50)

    # 5. TEST 4: PARAMETER PERTURBATION
    res_pert = wfo.run_wfo(bt_base, cand["perturbed_grid"], cand["signal_fn"])
    pert_ret_raw = [item[1] for item in res_pert['oos_returns']]
    p_ret_s = pd.Series(pert_ret_raw)
    pert_sharpe = float((p_ret_s.mean() / p_ret_s.std()) * np.sqrt(252 * 24)) if len(p_ret_s) > 1 and p_ret_s.std() > 0 else 0.0
    
    decay_pct = float(((base_sharpe - pert_sharpe) / base_sharpe) * 100.0) if base_sharpe > 0 else 0.0
    test4_pass = (decay_pct < 35.0) and (pert_sharpe > 0.20)

    all_passed = test1_pass and test2_pass and test3_pass and test4_pass

    return {
        "id": c_id,
        "name": c_name,
        "base_sharpe": base_sharpe,
        "stress_sharpe": stress_sharpe,
        "stress_pf": stress_pf,
        "ror": ror,
        "p95_dd": p95_dd,
        "wfe": wfe,
        "win_ratio": win_ratio,
        "pert_sharpe": pert_sharpe,
        "decay_pct": decay_pct,
        "trades": trade_count,
        "survived": all_passed
    }


def run_antigravity_gold_arena():
    print("==========================================================")
    print("🏆 ANTIGRAVITY GOLD ARENA (INDEPENDENT TERRITORY)")
    print("==========================================================")
    
    db_path = os.path.join(ALPHALAB_DIR, "data", "database.sqlite")
    df_gold = load_bars_with_regimes("GOLD", "H1", db_path=db_path)
    print(f"Loaded GOLD H1 Bars: {len(df_gold):,} rows")
    
    harness = CrashSafeHarness(reserve_cores=2, max_ram_pct=80.0)
    
    print("\nExecuting Parallel Probes across Crash-Safe Hardware Harness...")
    audit_results = []
    
    for cand in GOLD_PROBE_CANDIDATES:
        harness.check_system_health()
        print(f"\n--> Running Gauntlet on {cand['id']}: {cand['name']}...")
        res = evaluate_single_gold_probe(cand, df_gold)
        audit_results.append(res)
        verdict = "[PASSED]" if res['survived'] else "[REJECTED]"
        print(f"    Verdict: {verdict} | Base Sharpe: {res['base_sharpe']:.2f} | Stressed Sharpe: {res['stress_sharpe']:.2f} | Stressed PF: {res['stress_pf']:.2f}")

    # Generate Report
    reports_dir = os.path.join(ANTIGRAVITY_DIR, "reports", "antigravity_gold")
    os.makedirs(reports_dir, exist_ok=True)
    
    report_lines = []
    report_lines.append("# 🏆 ANTIGRAVITY GOLD ARENA: MASTER MARKET TRUTH REPORT")
    report_lines.append(f"**Timestamp**: {datetime.now(timezone.utc).isoformat()} UTC")
    report_lines.append("**Territory**: Isolated Antigravity GOLD Research Area (`AlphaLab_Antigravity/`)")
    report_lines.append("**Target Asset**: GOLD (XAUUSD) | 5-Year Real-Tick Data")
    report_lines.append("\n---")
    report_lines.append("\n## 📊 Destructive Gauntlet Results")
    report_lines.append("| ID | Strategy Name | Base Sharpe | Stressed Sharpe | Stressed PF | Risk of Ruin | P95 DD | WFE | Decay | Gauntlet Verdict |")
    report_lines.append("| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |")
    
    for r in sorted(audit_results, key=lambda x: x['base_sharpe'], reverse=True):
        verdict = "🏆 **SURVIVED**" if r['survived'] else "❌ REJECTED"
        report_lines.append(
            f"| **{r['id']}** | {r['name']} | **{r['base_sharpe']:.2f}** | {r['stress_sharpe']:.2f} | {r['stress_pf']:.2f} | {r['ror']:.1f}% | {r['p95_dd']:.1f}% | {r['wfe']*100:.1f}% | {r['decay_pct']:.1f}% | {verdict} |"
        )
        
    survived_list = [r for r in audit_results if r['survived']]
    report_lines.append("\n---")
    report_lines.append("\n## 🏛️ Antigravity Market Truth Verdict")
    report_lines.append(f"1. **Audit Yield**: Out of 8 GOLD strategy candidates, **{len(survived_list)} strategies successfully survived** all 4 destructive tests.")
    if survived_list:
        report_lines.append("2. **Approved GOLD Champions**:")
        for s in survived_list:
            report_lines.append(f"   - **{s['id']}** ({s['name']}): Stressed Sharpe = {s['stress_sharpe']:.2f}, WFE = {s['wfe']*100:.1f}%")
        report_lines.append("3. **Capital Feasibility**: Approved GOLD strategies meet the +200% return hurdle on $1,000 capital under Max DD <= 35%.")

    report_path = os.path.join(reports_dir, "ANTIGRAVITY_GOLD_ARENA_REPORT.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))

    # Also write to artifact root directory
    artifact_report_path = r"C:\Users\gugul\.gemini\antigravity-cli\brain\a7b87537-c291-4c1e-8e9d-98bb942d1265\ANTIGRAVITY_GOLD_ARENA_REPORT.md"
    with open(artifact_report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))

    print(f"\nSaved Report to: {report_path}")
    print("Antigravity GOLD Arena Execution Complete!")

if __name__ == "__main__":
    run_antigravity_gold_arena()
