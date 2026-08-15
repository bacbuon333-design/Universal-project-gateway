"""
===================================================================
ANTIGRAVITY LAB COMPOUND VERIFICATION RUNNER
===================================================================
References Z:\\Auto Trading\\Gold trading bot_LAB\\compound_mt5_backtest.py
and runs compound backtesting directly on downloaded GOLD historical datasets.

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

# Add Lab directory to sys.path in READ-ONLY mode
LAB_DIR = r"Z:\Auto Trading\Gold trading bot_LAB"
if LAB_DIR not in sys.path:
    sys.path.insert(0, LAB_DIR)

from compound_mt5_backtest import evaluate_compound_candidate
from validate_gene_candidate import load_gene_pack

def run_lab_verification():
    print("==========================================================")
    print("🚀 EXECUTING LAB COMPOUND VERIFICATION ON GOLD M15 DATASET")
    print("==========================================================")
    
    antigravity_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(antigravity_dir, "data")
    m15_csv = os.path.join(data_dir, "GOLD_M15.csv")
    
    if not os.path.exists(m15_csv):
        print(f"❌ GOLD M15 CSV not found at: {m15_csv}")
        return
        
    df = pd.read_csv(m15_csv)
    df['datetime'] = pd.to_datetime(df['datetime_str'])
    df.set_index('datetime', inplace=True)
    
    # Fill dynamic spread if not present
    if 'dynamic_spread' not in df.columns:
        df['dynamic_spread'] = 25.0
        
    print(f"Loaded GOLD M15 Dataset: {len(df):,} bars ({df.index[0]} -> {df.index[-1]})")
    
    # Load candidate gene packs from Lab
    gene_packs = [
        os.path.join(LAB_DIR, "data", "paper_trade_candidate.json"),
        os.path.join(LAB_DIR, "data", "best_genes.json"),
    ]
    
    for gp_path in gene_packs:
        if not os.path.exists(gp_path):
            continue
            
        gp_name = os.path.basename(gp_path)
        print(f"\n🔍 Testing Gene Pack: '{gp_name}'")
        
        try:
            gene_pack = load_gene_pack(Path(gp_path))
            
            # Run Compound Evaluation on $1,000
            res_1k = evaluate_compound_candidate(
                gene_pack=gene_pack,
                df=df,
                strictness="balanced",
                spread_pts=25.0,
                initial_balance=1000.0,
                risk_pct=0.01
            )
            
            # Run Compound Evaluation on $10,000
            res_10k = evaluate_compound_candidate(
                gene_pack=gene_pack,
                df=df,
                strictness="balanced",
                spread_pts=25.0,
                initial_balance=10000.0,
                risk_pct=0.01
            )
            
            print(f"   💰 Initial $1,000 Run:")
            print(f"      Final Balance   : ${res_1k.get('final_balance', 1000.0):.2f}")
            print(f"      Total Net PnL   : ${res_1k.get('total_pnl', 0.0):+.2f}")
            print(f"      Profit Factor   : {res_1k.get('profit_factor', 0.0):.2f}")
            print(f"      Max Drawdown    : {res_1k.get('max_dd', 0.0):.2f}%")
            print(f"      Total Trades    : {res_1k.get('total_trades', 0)}")
            
            print(f"   💰 Initial $10,000 Run:")
            print(f"      Final Balance   : ${res_10k.get('final_balance', 10000.0):.2f}")
            print(f"      Total Net PnL   : ${res_10k.get('total_pnl', 0.0):+.2f}")
            print(f"      Profit Factor   : {res_10k.get('profit_factor', 0.0):.2f}")
            print(f"      Max Drawdown    : {res_10k.get('max_dd', 0.0):.2f}%")
            print(f"      Total Trades    : {res_10k.get('total_trades', 0)}")
            
        except Exception as e:
            print(f"   ⚠️ Exception during evaluation: {e}")

    print("\n==========================================================")
    print("🎉 LAB COMPOUND VERIFICATION COMPLETE!")
    print("==========================================================")

if __name__ == "__main__":
    run_lab_verification()
