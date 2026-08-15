"""
===================================================================
ANTIGRAVITY PRECISE LAB COMPOUND BACKTESTER
===================================================================
Executes exact compounding evaluation referenced from Z:\\Auto Trading\\Gold trading bot_LAB
on our downloaded GOLD dataset with complete Feature Engine indicators precomputed.

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
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime, timezone

# Add Lab root directory to sys.path in READ-ONLY mode
LAB_DIR = r"Z:\Auto Trading\Gold trading bot_LAB"
if LAB_DIR not in sys.path:
    sys.path.insert(0, LAB_DIR)

from compound_mt5_backtest import evaluate_compound_candidate
from validate_gene_candidate import load_gene_pack
from optimize.indicators import compute_all_indicators

def compute_lab_features(df: pd.DataFrame) -> pd.DataFrame:
    """Precomputes all indicator features expected by Lab strategies."""
    m = df.copy()
    close = m['close']
    high = m['high']
    low = m['low']
    
    # EMAs
    for span in [8, 9, 20, 21, 50, 100, 200]:
        m[f'ema_{span}'] = close.ewm(span=span, adjust=False).mean()
        
    # ATR & ATR points
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr14 = tr.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
    m['atr_14'] = atr14
    m['atr_pts_14'] = atr14 / PIP_SIZE
    
    # RSI
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1/14, min_periods=14, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1/14, min_periods=14, adjust=False).mean()
    rs = gain / (loss.replace(0, 1e-10))
    m['rsi_14'] = 100 - (100 / (1 + rs))
    
    # Stochastic
    l14 = low.rolling(14).min()
    h14 = high.rolling(14).max()
    stoch_k = 100 * (close - l14) / (h14 - l14 + 1e-10)
    m['stoch_k_14'] = stoch_k
    m['stoch_d_14'] = stoch_k.rolling(3).mean()
    
    # ADX
    up = high.diff()
    dn = -low.diff()
    pdm = up.where((up > dn) & (up > 0), 0.0)
    ndm = dn.where((dn > up) & (dn > 0), 0.0)
    atr_adx = tr.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
    pdi = 100 * pdm.ewm(alpha=1/14, min_periods=14, adjust=False).mean() / atr_adx.replace(0, 1e-10)
    ndi = 100 * ndm.ewm(alpha=1/14, min_periods=14, adjust=False).mean() / atr_adx.replace(0, 1e-10)
    dx = 100 * (pdi - ndi).abs() / (pdi + ndi).replace(0, 1e-10)
    m['adx_14'] = dx.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
    
    # Swing High & Swing Low for BOS strategy
    for lb in [10, 20, 30, 50]:
        m[f'swing_h_{lb}'] = high.rolling(lb).max().shift(1)
        m[f'swing_l_{lb}'] = low.rolling(lb).min().shift(1)
        
    # Hurst & Dynamic Spread
    m['hurst'] = 0.55
    if 'dynamic_spread' not in m.columns:
        m['dynamic_spread'] = 25.0
        
    return m

def run_precise_lab_backtest():
    print("==========================================================")
    print("🚀 EXECUTING PRECISE LAB COMPOUND BACKTEST ON GOLD DATASET")
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
    
    print(f"Loaded GOLD M15 Dataset: {len(df_raw):,} bars ({df_raw.index[0]} -> {df_raw.index[-1]})")
    print("Computing Lab indicators via compute_all_indicators()...")
    if "volume" not in df_raw.columns:
        df_raw["volume"] = df_raw.get("tick_volume", 0)
    df_full = compute_all_indicators(df_raw)
    print("Features computed successfully!")
    
    # Slice to Lab Research Span: 2024-04-11 to 2025-11-13
    df = df_full.loc['2024-04-11':'2025-11-13'].copy()
    print(f"\n🎯 Sliced to Lab Research Span (2024-04-11 -> 2025-11-13): {len(df):,} bars")
    
    # Load paper_trade_candidate.json from Lab
    gp_path = os.path.join(LAB_DIR, "data", "paper_trade_candidate.json")
    if not os.path.exists(gp_path):
        print(f"❌ Candidate gene pack not found at: {gp_path}")
        return
        
    print(f"\n🔍 Evaluating Candidate: 'paper_trade_candidate.json'")
    gene_pack = load_gene_pack(Path(gp_path))
    
    # 1. Test Initial $1,000 Balance
    res_1k = evaluate_compound_candidate(
        gene_pack=gene_pack,
        df=df,
        strictness="balanced",
        spread_pts=25.0,
        initial_balance=1000.0,
        risk_pct=0.01
    )
    
    print(f"\n📊 1. BASELINE COMPOUNDING RUN ($1,000 Initial Balance):")
    print(f"   Initial Balance : $1,000.00")
    print(f"   Final Balance   : ${res_1k.get('final_balance', 1000.0):.2f}")
    print(f"   Total Net PnL   : ${res_1k.get('total_pnl', 0.0):+.2f}")
    print(f"   Profit Factor   : {res_1k.get('profit_factor', 0.0):.3f}")
    print(f"   Max Drawdown    : {res_1k.get('max_dd', 0.0):.2f}%")
    print(f"   Total Trades    : {res_1k.get('total_trades', 0)}")
    print(f"   Win Rate        : {res_1k.get('win_rate', 0.0):.1f}%")
    print(f"   Status          : {res_1k.get('status', 'unknown')}")
    print(f"   Reject Reason   : {res_1k.get('reject_reason', 'none')}")

    # 2. Test Initial $10,000 Balance
    res_10k = evaluate_compound_candidate(
        gene_pack=gene_pack,
        df=df,
        strictness="balanced",
        spread_pts=25.0,
        initial_balance=10000.0,
        risk_pct=0.01
    )
    
    print(f"\n📊 2. HARDENED COMPOUNDING RUN ($10,000 Initial Balance):")
    print(f"   Initial Balance : $10,000.00")
    print(f"   Final Balance   : ${res_10k.get('final_balance', 10000.0):.2f}")
    print(f"   Total Net PnL   : ${res_10k.get('total_pnl', 0.0):+.2f}")
    print(f"   Profit Factor   : {res_10k.get('profit_factor', 0.0):.3f}")
    print(f"   Max Drawdown    : {res_10k.get('max_dd', 0.0):.2f}%")
    print(f"   Total Trades    : {res_10k.get('total_trades', 0)}")
    print(f"   Win Rate        : {res_10k.get('win_rate', 0.0):.1f}%")

    # Strategy Breakdown
    if "strategy_stats" in res_1k:
        print("\n📈 Strategy Performance Breakdown:")
        for name, stats in res_1k["strategy_stats"].items():
            print(f"   - {name:20s}: Trades = {stats['trades']:3d} | PnL = ${stats['pnl']:+8.2f} (Long: {stats['long_trades']}, Short: {stats['short_trades']})")

    # Save Markdown Report
    reports_dir = os.path.join(antigravity_dir, "reports", "lab_verification")
    os.makedirs(reports_dir, exist_ok=True)
    report_file = os.path.join(reports_dir, "PRECISE_LAB_COMPOUND_REPORT.md")
    
    lines = []
    lines.append("# 🏆 PRECISE LAB COMPOUNDING BACKTEST REPORT")
    lines.append(f"**Timestamp**: {datetime.now(timezone.utc).isoformat()} UTC")
    lines.append("**Source Candidate**: `Z:\\Auto Trading\\Gold trading bot_LAB\\data\\paper_trade_candidate.json`")
    lines.append(f"**Dataset**: GOLD M15 ({df.index[0].strftime('%Y-%m-%d')} to {df.index[-1].strftime('%Y-%m-%d')}) | {len(df):,} bars")
    lines.append("\n---")
    lines.append("\n## 📊 Performance Comparison")
    lines.append("| Metric | $1,000 Initial Balance | $10,000 Initial Balance |")
    lines.append("| :--- | :---: | :---: |")
    lines.append(f"| **Initial Balance** | **$1,000.00** | **$10,000.00** |")
    lines.append(f"| **Final Balance** | **${res_1k.get('final_balance', 1000.0):.2f}** | **${res_10k.get('final_balance', 10000.0):.2f}** |")
    lines.append(f"| **Total Net Profit** | **${res_1k.get('total_pnl', 0.0):+.2f}** | **${res_10k.get('total_pnl', 0.0):+.2f}** |")
    lines.append(f"| **Profit Factor** | **{res_1k.get('profit_factor', 0.0):.3f}** | **{res_10k.get('profit_factor', 0.0):.3f}** |")
    lines.append(f"| **Max Drawdown** | **{res_1k.get('max_dd', 0.0):.2f}%** | **{res_10k.get('max_dd', 0.0):.2f}%** |")
    lines.append(f"| **Total Trades** | {res_1k.get('total_trades', 0)} | {res_10k.get('total_trades', 0)} |")
    lines.append(f"| **Win Rate** | {res_1k.get('win_rate', 0.0):.1f}% | {res_10k.get('win_rate', 0.0):.1f}% |")
    lines.append(f"| **Status** | {res_1k.get('status', 'unknown')} | {res_10k.get('status', 'unknown')} |")
    
    lines.append("\n---")
    lines.append("\n## 🎯 Strategy Breakdown")
    lines.append("| Strategy Name | Trades | Net PnL | Long Trades | Short Trades |")
    lines.append("| :--- | :---: | :---: | :---: | :---: |")
    if "strategy_stats" in res_1k:
        for name, stats in res_1k["strategy_stats"].items():
            lines.append(f"| **{name}** | {stats['trades']} | **${stats['pnl']:+.2f}** | {stats['long_trades']} | {stats['short_trades']} |")
            
    with open(report_file, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
        
    print(f"\n📄 Saved Precise Lab Report to: {report_file}")

if __name__ == "__main__":
    run_precise_lab_backtest()
