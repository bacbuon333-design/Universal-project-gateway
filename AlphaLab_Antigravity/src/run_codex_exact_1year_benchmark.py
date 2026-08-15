"""
===================================================================
CODEX STRICT 1-YEAR HISTORICAL BENCHMARK & AUDIT ENGINE
===================================================================
Executes strict trade-by-trade audit using Codex's exact Lab backtest engine:
1. Source: Z:\\Auto Trading\\Gold trading bot_LAB\\compound_mt5_backtest.py
2. Parameters: paper_trade_candidate.json
3. Windows Analyzed:
   - Window A: Strict 1-Year Period (2024-05-01 -> 2025-05-01 | 24,960 M15 bars)
   - Window B: Full Codex Research Span (2024-04-11 -> 2025-11-13 | 37,652 M15 bars)

Outputs trade-level granularity, win rate, profit factor, max drawdown, and strategy breakdown.
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

def run_strict_1year_benchmark():
    print("==========================================================")
    print("🔬 EXECUTING CODEX STRICT 1-YEAR HISTORICAL BENCHMARK")
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
    
    # 1. STRICT 1-YEAR WINDOW (2024-05-01 to 2025-05-01)
    df_1year = df_full.loc['2024-05-01 00:00:00':'2025-05-01 00:00:00'].copy()
    print(f"\n📊 1. STRICT 1-YEAR WINDOW ({len(df_1year):,} bars | {df_1year.index[0]} -> {df_1year.index[-1]}):")
    
    res_1y = evaluate_compound_candidate(
        gene_pack=gene_pack,
        df=df_1year,
        strictness="balanced",
        spread_pts=25.0,
        initial_balance=1000.0,
        risk_pct=0.01
    )
    
    print(f"   Initial Balance : $1,000.00")
    print(f"   FINAL BALANCE   : ${res_1y.get('final_balance', 1000.0):.2f}")
    print(f"   Total Net Profit: ${res_1y.get('total_pnl', 0.0):+.2f} ({res_1y.get('total_pnl', 0.0)/10.0:+.2f}%)")
    print(f"   PROFIT FACTOR   : {res_1y.get('profit_factor', 0.0):.3f}")
    print(f"   Max Drawdown    : {res_1y.get('max_dd', 0.0):.2f}%")
    print(f"   Total Trades    : {res_1y.get('total_trades', 0)} trades (Mật độ: {res_1y.get('total_trades', 0)} lệnh/năm)")
    print(f"   Win Rate        : {res_1y.get('win_rate', 0.0):.1f}%")

    if "strategy_stats" in res_1y:
        print("\n   📈 Trade & Strategy Breakdown (Strict 1-Year):")
        for name, stats in res_1y["strategy_stats"].items():
            if stats["trades"] > 0:
                print(f"      - {name:20s}: Trades = {stats['trades']:3d} | PnL = ${stats['pnl']:+9.2f} | Long: {stats['long_trades']} | Short: {stats['short_trades']}")

    # 2. FULL CODEX LAB RESEARCH SPAN (2024-04-11 to 2025-11-13)
    df_lab = df_full.loc['2024-04-11 18:15:00':'2025-11-13 07:45:00'].copy()
    print(f"\n📊 2. FULL CODEX LAB RESEARCH SPAN ({len(df_lab):,} bars | {df_lab.index[0]} -> {df_lab.index[-1]}):")
    
    res_lab = evaluate_compound_candidate(
        gene_pack=gene_pack,
        df=df_lab,
        strictness="balanced",
        spread_pts=25.0,
        initial_balance=1000.0,
        risk_pct=0.01
    )
    
    print(f"   Initial Balance : $1,000.00")
    print(f"   FINAL BALANCE   : ${res_lab.get('final_balance', 1000.0):.2f}")
    print(f"   Total Net Profit: ${res_lab.get('total_pnl', 0.0):+.2f} ({res_lab.get('total_pnl', 0.0)/10.0:+.2f}%)")
    print(f"   PROFIT FACTOR   : {res_lab.get('profit_factor', 0.0):.3f}")
    print(f"   Max Drawdown    : {res_lab.get('max_dd', 0.0):.2f}%")
    print(f"   Total Trades    : {res_lab.get('total_trades', 0)} trades")
    print(f"   Win Rate        : {res_lab.get('win_rate', 0.0):.1f}%")

    if "strategy_stats" in res_lab:
        print("\n   📈 Trade & Strategy Breakdown (Full Lab Span):")
        for name, stats in res_lab["strategy_stats"].items():
            if stats["trades"] > 0:
                print(f"      - {name:20s}: Trades = {stats['trades']:3d} | PnL = ${stats['pnl']:+9.2f} | Long: {stats['long_trades']} | Short: {stats['short_trades']}")

    # Save Markdown Report
    reports_dir = os.path.join(antigravity_dir, "reports", "codex_verification")
    os.makedirs(reports_dir, exist_ok=True)
    report_file = os.path.join(reports_dir, "CODEX_1YEAR_EXACT_BENCHMARK_REPORT.md")
    
    lines = []
    lines.append("# 🔬 CODEX STRICT 1-YEAR HISTORICAL BENCHMARK REPORT")
    lines.append(f"**Timestamp**: {datetime.now(timezone.utc).isoformat()} UTC")
    lines.append("**Source Engine**: `Z:\\Auto Trading\\Gold trading bot_LAB\\compound_mt5_backtest.py`")
    lines.append("**Gene Pack**: `paper_trade_candidate.json`")
    lines.append("\n---")
    lines.append("\n## 📊 Summary Comparison")
    lines.append("| Historical Window | Initial Balance | FINAL BALANCE | Net Profit ($) | PROFIT FACTOR | Max Drawdown | Total Trades | Win Rate | Trade Density |")
    lines.append("| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |")
    lines.append(f"| **Strict 1-Year (05/2024-05/2025)** | $1,000.00 | **${res_1y.get('final_balance', 1000.0):.2f}** | **${res_1y.get('total_pnl', 0.0):+.2f}** | **{res_1y.get('profit_factor', 0.0):.3f}** | {res_1y.get('max_dd', 0.0):.2f}% | {res_1y.get('total_trades', 0)} | {res_1y.get('win_rate', 0.0):.1f}% | {res_1y.get('total_trades', 0)} lệnh/năm |")
    lines.append(f"| **Full Lab Span (04/2024-11/2025)** | $1,000.00 | **${res_lab.get('final_balance', 1000.0):.2f}** | **${res_lab.get('total_pnl', 0.0):+.2f}** | **{res_lab.get('profit_factor', 0.0):.3f}** | {res_lab.get('max_dd', 0.0):.2f}% | {res_lab.get('total_trades', 0)} | {res_lab.get('win_rate', 0.0):.1f}% | {res_lab.get('total_trades', 0)/1.58:.0f} lệnh/năm |")

    lines.append("\n---")
    lines.append("\n## 🎯 Strategy-Level Granularity (Strict 1-Year)")
    lines.append("| Strategy Name | Trades | Net PnL ($) | Long Trades | Short Trades |")
    lines.append("| :--- | :---: | :---: | :---: | :---: |")
    if "strategy_stats" in res_1y:
        for name, stats in res_1y["strategy_stats"].items():
            if stats["trades"] > 0:
                lines.append(f"| **{name}** | {stats['trades']} | **${stats['pnl']:+.2f}** | {stats['long_trades']} | {stats['short_trades']} |")

    with open(report_file, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
        
    print(f"\n📄 Saved Codex 1-Year Benchmark Report to: {report_file}")

if __name__ == "__main__":
    run_strict_1year_benchmark()
