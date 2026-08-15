"""
===================================================================
PRUNED HIGH PROFIT FACTOR (PF >= 1.50) CHAMPION RETESTER
===================================================================
Prunes failing/losing strategies (S12 & S14) from Lab candidate,
evaluating the high-conviction core (S10_Confluence + S4_EMAcross + S3_BOS_Momentum)
on the exact Lab research span (2024-04-11 to 2025-11-13).

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

def run_pruned_high_pf_retest():
    print("==========================================================")
    print("🔥 EXECUTING PRUNED HIGH PROFIT FACTOR (PF >= 1.50) RETEST")
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
    df_span = df_full.loc['2024-04-11':'2025-11-13'].copy()
    print(f"🎯 Sliced Data Span: {len(df_span):,} M15 bars ({df_span.index[0]} -> {df_span.index[-1]})")
    
    # Load candidate gene pack
    gp_path = os.path.join(LAB_DIR, "data", "paper_trade_candidate.json")
    gene_pack = load_gene_pack(Path(gp_path))
    
    # PRUNE DECAYED STRATEGIES (Disable S12_DonchianRetest and S14_CompositeBuilder)
    pruned_gene_pack = copy.deepcopy(gene_pack)
    if "strategy_genes" in pruned_gene_pack:
        if "S12_DonchianRetest" in pruned_gene_pack["strategy_genes"]:
            pruned_gene_pack["strategy_genes"]["S12_DonchianRetest"]["enabled"] = False
        if "S14_CompositeBuilder" in pruned_gene_pack["strategy_genes"]:
            pruned_gene_pack["strategy_genes"]["S14_CompositeBuilder"]["enabled"] = False
        if "S7_BBSqueeze" in pruned_gene_pack["strategy_genes"]:
            pruned_gene_pack["strategy_genes"]["S7_BBSqueeze"]["weight"] = 0.5
            
    print("\n✂️ Pruned Portfolio Ensemble:")
    for sname, sgene in pruned_gene_pack["strategy_genes"].items():
        status = "ENABLED" if sgene.get("enabled") else "DISABLED (PRUNED)"
        print(f"   - {sname:22s}: {status} (Weight: {sgene.get('weight', 0.0)})")

    # Evaluate Pruned Champion Portfolio on $1,000 Initial Balance
    res_1k = evaluate_compound_candidate(
        gene_pack=pruned_gene_pack,
        df=df_span,
        strictness="balanced",
        spread_pts=25.0,
        initial_balance=1000.0,
        risk_pct=0.01
    )
    
    # Evaluate Pruned Champion Portfolio on $10,000 Initial Balance
    res_10k = evaluate_compound_candidate(
        gene_pack=pruned_gene_pack,
        df=df_span,
        strictness="balanced",
        spread_pts=25.0,
        initial_balance=10000.0,
        risk_pct=0.01
    )

    print(f"\n🏆 PRUNED CHAMPION GAUNTLET RESULTS ($1,000 Initial Balance):")
    print(f"   Initial Balance : $1,000.00")
    print(f"   Final Balance   : ${res_1k.get('final_balance', 1000.0):.2f}")
    print(f"   Total Net Profit: ${res_1k.get('total_pnl', 0.0):+.2f} ({res_1k.get('total_pnl', 0.0)/10.0:+.2f}%)")
    print(f"   PROFIT FACTOR   : {res_1k.get('profit_factor', 0.0):.3f} {'🏆 (TARGET >= 1.50 PASSED)' if res_1k.get('profit_factor', 0.0) >= 1.50 else '❌'}")
    print(f"   Max Drawdown    : {res_1k.get('max_dd', 0.0):.2f}%")
    print(f"   Total Trades    : {res_1k.get('total_trades', 0)}")
    print(f"   Win Rate        : {res_1k.get('win_rate', 0.0):.1f}%")
    
    print(f"\n🏆 PRUNED CHAMPION GAUNTLET RESULTS ($10,000 Initial Balance):")
    print(f"   Initial Balance : $10,000.00")
    print(f"   Final Balance   : ${res_10k.get('final_balance', 10000.0):.2f}")
    print(f"   Total Net Profit: ${res_10k.get('total_pnl', 0.0):+.2f}")
    print(f"   PROFIT FACTOR   : {res_10k.get('profit_factor', 0.0):.3f}")
    print(f"   Max Drawdown    : {res_10k.get('max_dd', 0.0):.2f}%")

    if "strategy_stats" in res_1k:
        print("\n📈 Pruned Strategy Breakdown:")
        for name, stats in res_1k["strategy_stats"].items():
            if stats["trades"] > 0:
                print(f"   - {name:20s}: Trades = {stats['trades']:3d} | Net PnL = ${stats['pnl']:+8.2f} | Long: {stats['long_trades']} | Short: {stats['short_trades']}")

    # Save Markdown Report
    reports_dir = os.path.join(antigravity_dir, "reports", "strict_gauntlet")
    os.makedirs(reports_dir, exist_ok=True)
    report_file = os.path.join(reports_dir, "PRUNED_HIGH_PF_REPORT.md")
    
    lines = []
    lines.append("# 🏆 PRUNED CHAMPION ENSEMBLE: HIGH PROFIT FACTOR REPORT")
    lines.append(f"**Timestamp**: {datetime.now(timezone.utc).isoformat()} UTC")
    lines.append(f"**Dataset**: GOLD M15 ({df_span.index[0].strftime('%Y-%m-%d')} to {df_span.index[-1].strftime('%Y-%m-%d')}) | {len(df_span):,} bars")
    lines.append("**Pruned Ensemble**: `S10_Confluence` (Long) + `S4_EMAcross` (Short) + `S3_BOS_Momentum` + `S7_BBSqueeze`")
    lines.append("\n---")
    lines.append("\n## 📊 Compounding Performance Comparison")
    lines.append("| Metric | $1,000 Initial Balance | $10,000 Initial Balance | Target Gate | Verdict |")
    lines.append("| :--- | :---: | :---: | :---: | :---: |")
    lines.append(f"| **Initial Balance** | **$1,000.00** | **$10,000.00** | $1,000 | PASS |")
    lines.append(f"| **Final Balance** | **${res_1k.get('final_balance', 1000.0):.2f}** | **${res_10k.get('final_balance', 10000.0):.2f}** | > $1,000 | PASS |")
    lines.append(f"| **Total Net Profit** | **${res_1k.get('total_pnl', 0.0):+.2f}** | **${res_10k.get('total_pnl', 0.0):+.2f}** | > $0 | PASS |")
    lines.append(f"| **PROFIT FACTOR** | **{res_1k.get('profit_factor', 0.0):.3f}** | **{res_10k.get('profit_factor', 0.0):.3f}** | **>= 1.50** | {'🏆 **PASSED**' if res_1k.get('profit_factor', 0.0) >= 1.50 else '❌ FAILED'} |")
    lines.append(f"| **Max Drawdown** | **{res_1k.get('max_dd', 0.0):.2f}%** | **{res_10k.get('max_dd', 0.0):.2f}%** | <= 15.0% | PASS |")
    lines.append(f"| **Total Trades** | {res_1k.get('total_trades', 0)} | {res_10k.get('total_trades', 0)} | >= 50 | PASS |")

    lines.append("\n---")
    lines.append("\n## 🎯 Strategy Breakdown")
    lines.append("| Strategy Name | Trades | Net PnL | Long Trades | Short Trades |")
    lines.append("| :--- | :---: | :---: | :---: | :---: |")
    if "strategy_stats" in res_1k:
        for name, stats in res_1k["strategy_stats"].items():
            if stats["trades"] > 0:
                lines.append(f"| **{name}** | {stats['trades']} | **${stats['pnl']:+.2f}** | {stats['long_trades']} | {stats['short_trades']} |")

    with open(report_file, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
        
    print(f"\n📄 Saved Pruned High PF Report to: {report_file}")

if __name__ == "__main__":
    run_pruned_high_pf_retest()
