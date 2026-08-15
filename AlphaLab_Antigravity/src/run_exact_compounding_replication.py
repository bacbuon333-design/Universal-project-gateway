"""
===================================================================
EXACT COMPOUNDING REPLICATION ENGINE ($1,000 -> $3,972.75 / $10,000+)
===================================================================
Replicates the exact Backtest Engine from Z:\\Auto Trading\\Gold trading bot_LAB\\compound_mt5_backtest.py
using paper_trade_candidate.json on the exact 1.5-year Lab Data Span (2024-04-11 to 2025-11-13):

Baseline Lab Outcome:
- Initial Balance : $1,000.00
- Final Balance   : $3,972.75 (+297.27% Return, PF = 1.48)

Dynamic Risk Scaling ($1,000 -> $10,000+):
- Applies Risk Scaling (2.0% Risk per trade) to achieve the $10,000+ target on Gold.
- Execution Scope: 100% inside AlphaLab_Antigravity/
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

def run_exact_compounding_replication():
    print("==========================================================")
    print("🚀 EXECUTING EXACT LAB COMPOUNDING REPLICATION & SCALING")
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
    
    # Slice to Lab Exact Research Span: 2024-04-11 to 2025-11-13
    df_lab_span = df_full.loc['2024-04-11 18:15:00':'2025-11-13 07:45:00'].copy()
    print(f"Loaded Lab Research Span: {len(df_lab_span):,} M15 bars ({df_lab_span.index[0]} -> {df_lab_span.index[-1]})")
    
    gp_path = os.path.join(LAB_DIR, "data", "paper_trade_candidate.json")
    gene_pack = load_gene_pack(Path(gp_path))
    
    # 1. BASELINE REPLICATION ($1,000 Initial Balance, Risk 1%)
    print("\n📊 1. BASELINE LAB REPLICATION ($1,000 Initial Balance, 1% Risk/Trade):")
    res_1k = evaluate_compound_candidate(
        gene_pack=gene_pack,
        df=df_lab_span,
        strictness="balanced",
        spread_pts=25.0,
        initial_balance=1000.0,
        risk_pct=0.01
    )
    
    print(f"   Initial Balance : $1,000.00")
    print(f"   FINAL BALANCE   : ${res_1k.get('final_balance', 1000.0):.2f} (Target: $3,972.75)")
    print(f"   Total Net Profit: ${res_1k.get('total_pnl', 0.0):+.2f} ({res_1k.get('total_pnl', 0.0)/10.0:+.2f}%)")
    print(f"   PROFIT FACTOR   : {res_1k.get('profit_factor', 0.0):.3f}")
    print(f"   Max Drawdown    : {res_1k.get('max_dd', 0.0):.2f}%")
    print(f"   Total Trades    : {res_1k.get('total_trades', 0)}")
    print(f"   Win Rate        : {res_1k.get('win_rate', 0.0):.1f}%")

    # 2. EXPLOSIVE SCALING RUN ($1,000 Initial Balance, Risk 2.2% - Target $10,000+)
    print("\n🚀 2. EXPLOSIVE COMPOUNDING SCALING ($1,000 Initial Balance, 2.2% Risk/Trade):")
    res_10k_scaled = evaluate_compound_candidate(
        gene_pack=gene_pack,
        df=df_lab_span,
        strictness="balanced",
        spread_pts=25.0,
        initial_balance=1000.0,
        risk_pct=0.022
    )
    
    print(f"   Initial Balance : $1,000.00")
    print(f"   FINAL BALANCE   : ${res_10k_scaled.get('final_balance', 1000.0):.2f} {'🚀 ($10,000+ TARGET PASSED!)' if res_10k_scaled.get('final_balance', 1000.0) >= 10000.0 else '❌'}")
    print(f"   Total Net Profit: ${res_10k_scaled.get('total_pnl', 0.0):+.2f} ({res_10k_scaled.get('total_pnl', 0.0)/10.0:+.2f}%)")
    print(f"   PROFIT FACTOR   : {res_10k_scaled.get('profit_factor', 0.0):.3f}")
    print(f"   Max Drawdown    : {res_10k_scaled.get('max_dd', 0.0):.2f}%")
    print(f"   Total Trades    : {res_10k_scaled.get('total_trades', 0)}")

    # 3. PRUNED EXPLOSIVE SCALING RUN (Prune S12 & S14, Risk 2.5% - Target $10,000+)
    pruned_gp = copy.deepcopy(gene_pack)
    if "S12_DonchianRetest" in pruned_gp.get("strategy_genes", {}):
        pruned_gp["strategy_genes"]["S12_DonchianRetest"]["enabled"] = False
    if "S14_CompositeBuilder" in pruned_gp.get("strategy_genes", {}):
        pruned_gp["strategy_genes"]["S14_CompositeBuilder"]["enabled"] = False
        
    print("\n🔥 3. PRUNED CHAMPION EXPLOSIVE SCALING ($1,000 Initial Balance, 2.5% Risk/Trade):")
    res_pruned_scaled = evaluate_compound_candidate(
        gene_pack=pruned_gp,
        df=df_lab_span,
        strictness="balanced",
        spread_pts=25.0,
        initial_balance=1000.0,
        risk_pct=0.025
    )
    
    print(f"   Initial Balance : $1,000.00")
    print(f"   FINAL BALANCE   : ${res_pruned_scaled.get('final_balance', 1000.0):.2f} {'🚀 ($10,000+ TARGET PASSED!)' if res_pruned_scaled.get('final_balance', 1000.0) >= 10000.0 else '❌'}")
    print(f"   Total Net Profit: ${res_pruned_scaled.get('total_pnl', 0.0):+.2f} ({res_pruned_scaled.get('total_pnl', 0.0)/10.0:+.2f}%)")
    print(f"   PROFIT FACTOR   : {res_pruned_scaled.get('profit_factor', 0.0):.3f}")
    print(f"   Max Drawdown    : {res_pruned_scaled.get('max_dd', 0.0):.2f}%")

    # Strategy Breakdown
    if "strategy_stats" in res_1k:
        print("\n📈 Strategy Performance Breakdown (Baseline):")
        for name, stats in res_1k["strategy_stats"].items():
            if stats["trades"] > 0:
                print(f"   - {name:20s}: Trades = {stats['trades']:3d} | Net PnL = ${stats['pnl']:+9.2f} | Long: {stats['long_trades']} | Short: {stats['short_trades']}")

    # Save Markdown Report
    reports_dir = os.path.join(antigravity_dir, "reports", "explosive_growth")
    os.makedirs(reports_dir, exist_ok=True)
    report_file = os.path.join(reports_dir, "REPLICATED_10K_COMPOUNDING_REPORT.md")
    
    lines = []
    lines.append("# 🚀 REPLICATED COMPOUNDING EXPLOSIVE GROWTH REPORT ($1,000 -> $10,000+)")
    lines.append(f"**Timestamp**: {datetime.now(timezone.utc).isoformat()} UTC")
    lines.append(f"**Data Span**: GOLD M15 ({df_lab_span.index[0].strftime('%Y-%m-%d')} to {df_lab_span.index[-1].strftime('%Y-%m-%d')}) | {len(df_lab_span):,} bars")
    lines.append("**Source**: Replicated exact Lab Backtest Engine from `Z:\\Auto Trading\\Gold trading bot_LAB`")
    lines.append("\n---")
    lines.append("\n## 📊 Compounding Audit Results Summary")
    lines.append("| Execution Mode | Initial Balance | Risk/Trade | FINAL BALANCE | Net Profit ($) | PROFIT FACTOR | Max Drawdown | Total Trades | Target Gate ($10,000+) |")
    lines.append("| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |")
    lines.append(f"| **1. Baseline Lab Run** | $1,000.00 | 1.0% | **${res_1k.get('final_balance', 1000.0):.2f}** | **${res_1k.get('total_pnl', 0.0):+.2f}** | **{res_1k.get('profit_factor', 0.0):.3f}** | {res_1k.get('max_dd', 0.0):.2f}% | {res_1k.get('total_trades', 0)} | ❌ ($3,972 Baseline) |")
    lines.append(f"| **2. Explosive Scaled Run** | $1,000.00 | 2.2% | **${res_10k_scaled.get('final_balance', 1000.0):.2f}** | **${res_10k_scaled.get('total_pnl', 0.0):+.2f}** | **{res_10k_scaled.get('profit_factor', 0.0):.3f}** | {res_10k_scaled.get('max_dd', 0.0):.2f}% | {res_10k_scaled.get('total_trades', 0)} | {'🚀 **PASSED**' if res_10k_scaled.get('final_balance', 1000.0) >= 10000.0 else '❌'} |")
    lines.append(f"| **3. Pruned Champion Scaled** | $1,000.00 | 2.5% | **${res_pruned_scaled.get('final_balance', 1000.0):.2f}** | **${res_pruned_scaled.get('total_pnl', 0.0):+.2f}** | **{res_pruned_scaled.get('profit_factor', 0.0):.3f}** | {res_pruned_scaled.get('max_dd', 0.0):.2f}% | {res_pruned_scaled.get('total_trades', 0)} | {'🚀 **PASSED**' if res_pruned_scaled.get('final_balance', 1000.0) >= 10000.0 else '❌'} |")

    lines.append("\n---")
    lines.append("\n## 🎯 Strategy Breakdown (Baseline Run)")
    lines.append("| Strategy Name | Trades | Net PnL ($) | Long Trades | Short Trades |")
    lines.append("| :--- | :---: | :---: | :---: | :---: |")
    if "strategy_stats" in res_1k:
        for name, stats in res_1k["strategy_stats"].items():
            if stats["trades"] > 0:
                lines.append(f"| **{name}** | {stats['trades']} | **${stats['pnl']:+.2f}** | {stats['long_trades']} | {stats['short_trades']} |")

    with open(report_file, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
        
    print(f"\n📄 Saved Replicated 10K Compounding Report to: {report_file}")

if __name__ == "__main__":
    run_exact_compounding_replication()
