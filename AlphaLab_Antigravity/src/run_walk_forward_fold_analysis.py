"""
===================================================================
WALK-FORWARD FOLD PROFIT FACTOR AUDITOR
===================================================================
Evaluates paper_trade_candidate.json across 4 Walk-Forward Folds:
- Fold 0 (Q1)
- Fold 1 (Q2)
- Fold 2 (Q3)
- Fold 3 (Q4)

Shows exact Profit Factor for each fold to prove PF >= 1.50 capability.
Execution Scope: 100% inside AlphaLab_Antigravity/
"""

import os
import sys
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

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

def run_wf_fold_analysis():
    print("==========================================================")
    print("🚀 EXECUTING WALK-FORWARD FOLD AUDIT ON GOLD M15 DATASET")
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
    
    # Slice into 4 equal Walk-Forward Folds
    n_bars = len(df_span)
    fold_size = n_bars // 4
    
    folds = [
        ("Fold 0 (Q1)", df_span.iloc[:fold_size]),
        ("Fold 1 (Q2)", df_span.iloc[fold_size:2*fold_size]),
        ("Fold 2 (Q3)", df_span.iloc[2*fold_size:3*fold_size]),
        ("Fold 3 (Q4)", df_span.iloc[3*fold_size:]),
    ]
    
    gp_path = os.path.join(LAB_DIR, "data", "paper_trade_candidate.json")
    gene_pack = load_gene_pack(Path(gp_path))
    
    print(f"Candidate: 'paper_trade_candidate.json' | Total Span: {n_bars:,} bars")
    print("\n" + "="*70)
    print(f"{'Walk-Forward Fold':15s} | {'Time Period':35s} | {'PF':6s} | {'Trades':6s} | {'PnL ($)':10s} | {'Status':8s}")
    print("="*70)
    
    results = []
    for fname, fold_df in folds:
        start_str = fold_df.index[0].strftime("%Y-%m-%d")
        end_str = fold_df.index[-1].strftime("%Y-%m-%d")
        period_str = f"{start_str} -> {end_str}"
        
        res = evaluate_compound_candidate(
            gene_pack=gene_pack,
            df=fold_df,
            strictness="balanced",
            spread_pts=25.0,
            initial_balance=1000.0,
            risk_pct=0.01
        )
        
        pf = res.get("profit_factor", 0.0)
        trades = res.get("total_trades", 0)
        pnl = res.get("total_pnl", 0.0)
        status = "PASSED" if pf >= 1.50 else "OK" if pf >= 1.0 else "FAIL"
        
        results.append({
            "fold": fname,
            "period": period_str,
            "pf": pf,
            "trades": trades,
            "pnl": pnl,
            "status": status,
            "res": res
        })
        
        print(f"{fname:15s} | {period_str:35s} | {pf:6.3f} | {trades:6d} | ${pnl:+9.2f} | {status:8s}")
        
    print("="*70)
    
    # Save Report
    reports_dir = os.path.join(antigravity_dir, "reports", "strict_gauntlet")
    os.makedirs(reports_dir, exist_ok=True)
    report_file = os.path.join(reports_dir, "WALK_FORWARD_FOLD_REPORT.md")
    
    lines = []
    lines.append("# 🏆 WALK-FORWARD FOLD PROFIT FACTOR AUDIT REPORT")
    lines.append(f"**Timestamp**: {datetime.now(timezone.utc).isoformat()} UTC")
    lines.append(f"**Dataset**: GOLD M15 ({df_span.index[0].strftime('%Y-%m-%d')} to {df_span.index[-1].strftime('%Y-%m-%d')}) | {n_bars:,} bars")
    lines.append("\n---")
    lines.append("\n## 📊 Walk-Forward Fold Results")
    lines.append("| Fold | Time Period | Profit Factor | Total Trades | Net PnL ($) | Target Gate (PF >= 1.50) |")
    lines.append("| :--- | :---: | :---: | :---: | :---: | :---: |")
    for r in results:
        passed = "🏆 **PASSED (PF >= 1.50)**" if r["pf"] >= 1.50 else ("✅ Profit" if r["pnl"] > 0 else "❌ Fail")
        lines.append(f"| **{r['fold']}** | {r['period']} | **{r['pf']:.3f}** | {r['trades']} | **${r['pnl']:+.2f}** | {passed} |")

    with open(report_file, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
        
    print(f"\n📄 Saved Walk-Forward Fold Report to: {report_file}")

if __name__ == "__main__":
    run_wf_fold_analysis()
