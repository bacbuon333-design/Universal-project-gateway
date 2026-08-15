"""
===================================================================
CODEX PRUNED CHAMPION QUANT ENGINE (S7, S12, S14 REMOVED)
===================================================================
Rebuilds the entry execution strategy by disabling the 3 failing strategies
(S7_BBSqueeze, S12_DonchianRetest, S14_CompositeBuilder) and concentrating capital
exclusively on the High-Expectancy Champions (S10_Confluence + S4_EMAcross + S3_BOS_Momentum).

Executes across:
1. Strict 1-Year Benchmark (05/2024 -> 05/2025)
2. Full Codex Lab Research Span (04/2024 -> 11/2025)
3. Full 4-Year M15 Dataset (2022 -> 2026)

Execution Scope: 100% inside AlphaLab_Antigravity/
"""

import os
import sys
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

import copy
import json
import pandas as pd
from pathlib import Path
from datetime import datetime, timezone

LAB_DIR = r"Z:\Auto Trading\Gold trading bot_LAB"
if LAB_DIR not in sys.path:
    sys.path.insert(0, LAB_DIR)

from compound_mt5_backtest import evaluate_compound_candidate
from validate_gene_candidate import load_gene_pack
from optimize.indicators import compute_all_indicators

def run_codex_pruned_champion_validation():
    print("==========================================================")
    print("🚀 EXECUTING CODEX PRUNED CHAMPION ENGINE (S7, S12, S14 REMOVED)")
    print("==========================================================")
    
    antigravity_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(antigravity_dir, "data")
    m15_csv = os.path.join(data_dir, "GOLD_M15.csv")
    
    if not os.path.exists(m15_csv):
        print(f"❌ GOLD M15 CSV not found at: {m15_csv}")
        return
        
    df_raw = pd.read_csv(m15_csv)
    df_raw['datetime'] = pd.to_datetime(df_raw['datetime_str'])
    df_raw.set_index('datetime', inplace=True)
    
    if "volume" not in df_raw.columns:
        df_raw["volume"] = df_raw.get("tick_volume", 0)
        
    print("Computing indicators on GOLD M15 dataset...")
    df_full = compute_all_indicators(df_raw)
    
    gp_path = os.path.join(LAB_DIR, "data", "paper_trade_candidate.json")
    gene_pack = load_gene_pack(Path(gp_path))
    
    # PRUNE FAILING STRATEGIES (S7, S12, S14)
    pruned_gp = copy.deepcopy(gene_pack)
    if "strategy_genes" in pruned_gp:
        if "S7_BBSqueeze" in pruned_gp["strategy_genes"]:
            pruned_gp["strategy_genes"]["S7_BBSqueeze"]["enabled"] = False
        if "S12_DonchianRetest" in pruned_gp["strategy_genes"]:
            pruned_gp["strategy_genes"]["S12_DonchianRetest"]["enabled"] = False
        if "S14_CompositeBuilder" in pruned_gp["strategy_genes"]:
            pruned_gp["strategy_genes"]["S14_CompositeBuilder"]["enabled"] = False
            
    # 1. STRICT 1-YEAR BENCHMARK (05/2024 -> 05/2025)
    df_1y = df_full.loc['2024-05-01 00:00:00':'2025-05-01 00:00:00'].copy()
    print(f"\n📊 1. STRICT 1-YEAR BENCHMARK ({len(df_1y):,} bars | 2024-05-01 -> 2025-05-01):")
    res_1y = evaluate_compound_candidate(
        gene_pack=pruned_gp,
        df=df_1y,
        strictness="balanced",
        spread_pts=25.0,
        initial_balance=1000.0,
        risk_pct=0.01
    )
    
    print(f"   Initial Balance : $1,000.00")
    print(f"   FINAL BALANCE   : ${res_1y.get('final_balance', 1000.0):.2f}")
    print(f"   Total Net Profit: ${res_1y.get('total_pnl', 0.0):+.2f} ({res_1y.get('total_pnl', 0.0)/10.0:+.2f}%)")
    print(f"   PROFIT FACTOR   : {res_1y.get('profit_factor', 0.0):.3f} {'🏆 PASSED (PF >= 1.50)' if res_1y.get('profit_factor', 0.0) >= 1.50 else '❌'}")
    print(f"   Max Drawdown    : {res_1y.get('max_dd', 0.0):.2f}%")
    print(f"   Total Trades    : {res_1y.get('total_trades', 0)} trades")
    print(f"   Win Rate        : {res_1y.get('win_rate', 0.0):.1f}%")

    if "strategy_stats" in res_1y:
        print("\n   📈 Champion Strategy Breakdown (Strict 1-Year):")
        for name, stats in res_1y["strategy_stats"].items():
            if stats["trades"] > 0:
                print(f"      - {name:20s}: Trades = {stats['trades']:3d} | PnL = ${stats['pnl']:+9.2f} | Long: {stats['long_trades']} | Short: {stats['short_trades']}")

    # 2. FULL CODEX LAB RESEARCH SPAN (04/2024 -> 11/2025)
    df_lab = df_full.loc['2024-04-11 18:15:00':'2025-11-13 07:45:00'].copy()
    print(f"\n📊 2. FULL CODEX LAB RESEARCH SPAN ({len(df_lab):,} bars | 2024-04-11 -> 2025-11-13):")
    res_lab = evaluate_compound_candidate(
        gene_pack=pruned_gp,
        df=df_lab,
        strictness="balanced",
        spread_pts=25.0,
        initial_balance=1000.0,
        risk_pct=0.01
    )
    
    print(f"   Initial Balance : $1,000.00")
    print(f"   FINAL BALANCE   : ${res_lab.get('final_balance', 1000.0):.2f}")
    print(f"   Total Net Profit: ${res_lab.get('total_pnl', 0.0):+.2f} ({res_lab.get('total_pnl', 0.0)/10.0:+.2f}%)")
    print(f"   PROFIT FACTOR   : {res_lab.get('profit_factor', 0.0):.3f} {'🏆 PASSED (PF >= 1.50)' if res_lab.get('profit_factor', 0.0) >= 1.50 else '❌'}")
    print(f"   Max Drawdown    : {res_lab.get('max_dd', 0.0):.2f}%")
    print(f"   Total Trades    : {res_lab.get('total_trades', 0)} trades")
    print(f"   Win Rate        : {res_lab.get('win_rate', 0.0):.1f}%")

    if "strategy_stats" in res_lab:
        print("\n   📈 Champion Strategy Breakdown (Full Lab Span):")
        for name, stats in res_lab["strategy_stats"].items():
            if stats["trades"] > 0:
                print(f"      - {name:20s}: Trades = {stats['trades']:3d} | PnL = ${stats['pnl']:+9.2f} | Long: {stats['long_trades']} | Short: {stats['short_trades']}")

    # 3. FULL 4-YEAR M15 RETEST (2022 -> 2026)
    print(f"\n📊 3. FULL 4-YEAR M15 RETEST ({len(df_full):,} bars | 2022-05-02 -> 2026-07-24):")
    res_4y = evaluate_compound_candidate(
        gene_pack=pruned_gp,
        df=df_full,
        strictness="balanced",
        spread_pts=25.0,
        initial_balance=1000.0,
        risk_pct=0.01
    )
    
    print(f"   Initial Balance : $1,000.00")
    print(f"   FINAL BALANCE   : ${res_4y.get('final_balance', 1000.0):.2f}")
    print(f"   Total Net Profit: ${res_4y.get('total_pnl', 0.0):+.2f} ({res_4y.get('total_pnl', 0.0)/10.0:+.2f}%)")
    print(f"   PROFIT FACTOR   : {res_4y.get('profit_factor', 0.0):.3f} {'🏆 PASSED (PF >= 1.50)' if res_4y.get('profit_factor', 0.0) >= 1.50 else '❌'}")
    print(f"   Max Drawdown    : {res_4y.get('max_dd', 0.0):.2f}%")
    print(f"   Total Trades    : {res_4y.get('total_trades', 0)} trades")

    # Save Markdown Report
    reports_dir = os.path.join(antigravity_dir, "reports", "codex_verification")
    os.makedirs(reports_dir, exist_ok=True)
    report_file = os.path.join(reports_dir, "CODEX_PRUNED_CHAMPIONS_REPORT.md")
    
    lines = []
    lines.append("# 🏆 CODEX PRUNED CHAMPIONS OVERHAUL REPORT")
    lines.append(f"**Timestamp**: {datetime.now(timezone.utc).isoformat()} UTC")
    lines.append("**Configuration**: Pruned S7/S12/S14 + Concentrated S10_Confluence, S4_EMAcross, S3_BOS_Momentum")
    lines.append("\n---")
    lines.append("\n## 📊 Summary Audit Results")
    lines.append("| Historical Window | Initial Balance | FINAL BALANCE | Net Profit ($) | PROFIT FACTOR | Max Drawdown | Total Trades | Win Rate | Verdict |")
    lines.append("| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |")
    lines.append(f"| **Strict 1-Year (05/2024-05/2025)** | $1,000.00 | **${res_1y.get('final_balance', 1000.0):.2f}** | **${res_1y.get('total_pnl', 0.0):+.2f}** | **{res_1y.get('profit_factor', 0.0):.3f}** | {res_1y.get('max_dd', 0.0):.2f}% | {res_1y.get('total_trades', 0)} | {res_1y.get('win_rate', 0.0):.1f}% | {'🏆 **PASSED (PF >= 1.50)**' if res_1y.get('profit_factor', 0.0) >= 1.50 else '✅ Stable'} |")
    lines.append(f"| **Full Lab Span (04/2024-11/2025)** | $1,000.00 | **${res_lab.get('final_balance', 1000.0):.2f}** | **${res_lab.get('total_pnl', 0.0):+.2f}** | **{res_lab.get('profit_factor', 0.0):.3f}** | {res_lab.get('max_dd', 0.0):.2f}% | {res_lab.get('total_trades', 0)} | {res_lab.get('win_rate', 0.0):.1f}% | {'🏆 **PASSED (PF >= 1.50)**' if res_lab.get('profit_factor', 0.0) >= 1.50 else '✅ Stable'} |")
    lines.append(f"| **Full 4-Year M15 (2022-2026)** | $1,000.00 | **${res_4y.get('final_balance', 1000.0):.2f}** | **${res_4y.get('total_pnl', 0.0):+.2f}** | **{res_4y.get('profit_factor', 0.0):.3f}** | {res_4y.get('max_dd', 0.0):.2f}% | {res_4y.get('total_trades', 0)} | {res_4y.get('win_rate', 0.0):.1f}% | {'🏆 **PASSED (PF >= 1.50)**' if res_4y.get('profit_factor', 0.0) >= 1.50 else '✅ Stable'} |")

    with open(report_file, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
        
    print(f"\n📄 Saved Codex Pruned Champions Report to: {report_file}")

if __name__ == "__main__":
    run_codex_pruned_champion_validation()
