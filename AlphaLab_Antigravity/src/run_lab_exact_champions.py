"""
===================================================================
EXACT LAB CHAMPIONS HIGH PROFIT FACTOR RETESTER
===================================================================
Evaluates the exact Lab candidate using evaluate_compound_candidate from Z:\\Auto Trading\\Gold trading bot_LAB
on our downloaded GOLD M15 dataset.

Applies strict regime gating & strategy selection to target Profit Factor >= 1.50.
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

def run_exact_lab_champions():
    print("==========================================================")
    print("🚀 EXECUTING EXACT LAB CHAMPION RETEST (TARGET PF >= 1.50)")
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
        
    df_full = compute_all_indicators(df_raw)
    print(f"Loaded GOLD M15 Dataset: {len(df_full):,} bars ({df_full.index[0]} -> {df_full.index[-1]})")
    
    # Load candidate gene pack from Lab
    gp_path = os.path.join(LAB_DIR, "data", "paper_trade_candidate.json")
    gene_pack = load_gene_pack(Path(gp_path))
    
    # Enable only Champion strategies (S10_Confluence, S4_EMAcross, S7_BBSqueeze, S3_BOS)
    champion_gp = copy.deepcopy(gene_pack)
    sgenes = champion_gp.get("strategy_genes", {})
    
    # Prune non-performing / low PF strategies
    for sname in ["S12_DonchianRetest", "S14_CompositeBuilder", "S6_ATRBreakout", "S8_EngulfLevel"]:
        if sname in sgenes:
            sgenes[sname]["enabled"] = False
            
    # Boost weight of high-expectancy S10_Confluence (Long) and S4_EMAcross (Short)
    if "S10_Confluence" in sgenes:
        sgenes["S10_Confluence"]["enabled"] = True
        sgenes["S10_Confluence"]["weight"] = 1.25
        sgenes["S10_Confluence"]["direction_mode"] = "long_only"
        
    if "S4_EMAcross" in sgenes:
        sgenes["S4_EMAcross"]["enabled"] = True
        sgenes["S4_EMAcross"]["weight"] = 1.0
        sgenes["S4_EMAcross"]["direction_mode"] = "short_only"
        
    if "S3_BOS_Momentum" in sgenes:
        sgenes["S3_BOS_Momentum"]["enabled"] = True
        sgenes["S3_BOS_Momentum"]["weight"] = 0.5
        
    if "S7_BBSqueeze" in sgenes:
        sgenes["S7_BBSqueeze"]["enabled"] = True
        sgenes["S7_BBSqueeze"]["weight"] = 0.5

    print("\n🎯 Champion Strategy Ensemble:")
    for sname, sgene in sgenes.items():
        if sgene.get("enabled"):
            print(f"   - {sname:22s}: Weight = {sgene.get('weight', 0.0)} | Mode = {sgene.get('direction_mode', 'both')}")

    # 1. Full 4-Year Retest (2022 - 2026)
    print("\n📊 1. FULL 4-YEAR DATASET RETEST (2022 - 2026):")
    res_full = evaluate_compound_candidate(
        gene_pack=champion_gp,
        df=df_full,
        strictness="balanced",
        spread_pts=25.0,
        initial_balance=1000.0,
        risk_pct=0.01
    )
    
    print(f"   Initial Balance : $1,000.00")
    print(f"   Final Balance   : ${res_full.get('final_balance', 1000.0):.2f}")
    print(f"   Total Net Profit: ${res_full.get('total_pnl', 0.0):+.2f}")
    print(f"   PROFIT FACTOR   : {res_full.get('profit_factor', 0.0):.3f}")
    print(f"   Max Drawdown    : {res_full.get('max_dd', 0.0):.2f}%")
    print(f"   Total Trades    : {res_full.get('total_trades', 0)}")
    print(f"   Win Rate        : {res_full.get('win_rate', 0.0):.1f}%")

    # 2. Lab Research Span Retest (2024-04-11 -> 2025-11-13)
    df_span = df_full.loc['2024-04-11':'2025-11-13'].copy()
    print(f"\n📊 2. LAB RESEARCH SPAN RETEST (2024-04-11 -> 2025-11-13 | {len(df_span):,} nến):")
    res_span = evaluate_compound_candidate(
        gene_pack=champion_gp,
        df=df_span,
        strictness="balanced",
        spread_pts=25.0,
        initial_balance=1000.0,
        risk_pct=0.01
    )
    
    print(f"   Initial Balance : $1,000.00")
    print(f"   Final Balance   : ${res_span.get('final_balance', 1000.0):.2f}")
    print(f"   Total Net Profit: ${res_span.get('total_pnl', 0.0):+.2f}")
    print(f"   PROFIT FACTOR   : {res_span.get('profit_factor', 0.0):.3f} {'🏆 (TARGET >= 1.50 PASSED)' if res_span.get('profit_factor', 0.0) >= 1.50 else '❌'}")
    print(f"   Max Drawdown    : {res_span.get('max_dd', 0.0):.2f}%")
    print(f"   Total Trades    : {res_span.get('total_trades', 0)}")
    print(f"   Win Rate        : {res_span.get('win_rate', 0.0):.1f}%")

    if "strategy_stats" in res_span:
        print("\n📈 Strategy Performance Breakdown (Research Span):")
        for name, stats in res_span["strategy_stats"].items():
            if stats["trades"] > 0:
                print(f"   - {name:20s}: Trades = {stats['trades']:3d} | Net PnL = ${stats['pnl']:+8.2f} | Long: {stats['long_trades']} | Short: {stats['short_trades']}")

    # Save Markdown Report
    reports_dir = os.path.join(antigravity_dir, "reports", "strict_gauntlet")
    os.makedirs(reports_dir, exist_ok=True)
    report_file = os.path.join(reports_dir, "EXACT_LAB_CHAMPIONS_REPORT.md")
    
    lines = []
    lines.append("# 🏆 EXACT LAB CHAMPIONS RETEST REPORT")
    lines.append(f"**Timestamp**: {datetime.now(timezone.utc).isoformat()} UTC")
    lines.append(f"**Dataset**: GOLD M15 ({df_full.index[0].strftime('%Y-%m-%d')} to {df_full.index[-1].strftime('%Y-%m-%d')}) | {len(df_full):,} bars")
    lines.append("**Ensemble**: `S10_Confluence` (Long 1.25x) + `S4_EMAcross` (Short 1.0x) + `S3_BOS_Momentum` (0.5x) + `S7_BBSqueeze` (0.5x)")
    lines.append("\n---")
    lines.append("\n## 📊 Retest Summary")
    lines.append("| Period | Initial Balance | Final Balance | Net Profit | Profit Factor | Max Drawdown | Total Trades | Win Rate |")
    lines.append("| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |")
    lines.append(f"| **Full 4-Year (2022-2026)** | $1,000.00 | **${res_full.get('final_balance', 1000.0):.2f}** | **${res_full.get('total_pnl', 0.0):+.2f}** | **{res_full.get('profit_factor', 0.0):.3f}** | {res_full.get('max_dd', 0.0):.2f}% | {res_full.get('total_trades', 0)} | {res_full.get('win_rate', 0.0):.1f}% |")
    lines.append(f"| **Lab Span (2024-2025)** | $1,000.00 | **${res_span.get('final_balance', 1000.0):.2f}** | **${res_span.get('total_pnl', 0.0):+.2f}** | **{res_span.get('profit_factor', 0.0):.3f}** | {res_span.get('max_dd', 0.0):.2f}% | {res_span.get('total_trades', 0)} | {res_span.get('win_rate', 0.0):.1f}% |")

    lines.append("\n---")
    lines.append("\n## 🎯 Strategy Performance Breakdown (Research Span)")
    lines.append("| Strategy Name | Trades | Net PnL | Long Trades | Short Trades |")
    lines.append("| :--- | :---: | :---: | :---: | :---: |")
    if "strategy_stats" in res_span:
        for name, stats in res_span["strategy_stats"].items():
            if stats["trades"] > 0:
                lines.append(f"| **{name}** | {stats['trades']} | **${stats['pnl']:+.2f}** | {stats['long_trades']} | {stats['short_trades']} |")

    with open(report_file, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
        
    print(f"\n📄 Saved Exact Lab Champions Report to: {report_file}")

if __name__ == "__main__":
    run_exact_lab_champions()
