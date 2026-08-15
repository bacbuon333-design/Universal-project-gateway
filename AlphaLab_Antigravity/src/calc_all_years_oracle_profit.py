"""
===================================================================
ALL-YEARS ORACLE PERFECT PRESCIENCE ANALYSIS (2022 - 2026)
===================================================================
Calculates the exact theoretical maximum potential profit (Oracle Upper Bound)
if an ideal prescient system caught 100% of all tops and bottoms across EVERY historical year:

Years Analyzed:
1. Year 2024-2025 (05/2024 -> 05/2025 | 23,571 M15 bars)
2. Year 2023-2024 (05/2023 -> 05/2024 | 24,960 M15 bars)
3. Year 2022-2023 (05/2022 -> 05/2023 | 24,960 M15 bars)
4. Year 2025-2026 (05/2025 -> 07/2026 | 29,999 M15 bars)

Calculates:
- Total Swing Swings & Trajectory Pips
- 100% Oracle Max PnL (0.01 lot)
- 20% Wave Amplitude Target PnL
- 15% Wave Amplitude Target PnL

Execution Scope: 100% inside AlphaLab_Antigravity/
"""

import os
import sys
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

import numpy as np
import pandas as pd
from datetime import datetime, timezone

PIP_SIZE = 0.01          # XM Gold pip size ($0.01)
POINT_VALUE = 0.01       # USD per point per 0.01 lot
SPREAD_PTS = 25.0        # 25 pips spread ($0.25)

def compute_zigzag_swings(df: pd.DataFrame, threshold_pct: float = 0.003): # 0.3% price move (~$6-$8 Gold move)
    close = df['close'].values
    high = df['high'].values
    low = df['low'].values
    n = len(df)
    
    swings = []
    current_dir = 0 # +1 Up, -1 Down
    last_pivot_price = close[0]
    last_pivot_idx = 0
    
    for i in range(1, n):
        p_high = high[i]
        p_low = low[i]
        
        if current_dir == 0:
            if p_high >= last_pivot_price * (1 + threshold_pct):
                current_dir = 1
                last_pivot_price = p_high
                last_pivot_idx = i
            elif p_low <= last_pivot_price * (1 - threshold_pct):
                current_dir = -1
                last_pivot_price = p_low
                last_pivot_idx = i
        elif current_dir == 1:
            if p_high > last_pivot_price:
                last_pivot_price = p_high
                last_pivot_idx = i
            elif p_low <= last_pivot_price * (1 - threshold_pct):
                swings.append({
                    "type": "UP",
                    "start_price": df['low'].values[last_pivot_idx],
                    "end_price": last_pivot_price,
                    "pts": (last_pivot_price - df['low'].values[last_pivot_idx]) / PIP_SIZE
                })
                current_dir = -1
                last_pivot_price = p_low
                last_pivot_idx = i
        elif current_dir == -1:
            if p_low < last_pivot_price:
                last_pivot_price = p_low
                last_pivot_idx = i
            elif p_high >= last_pivot_price * (1 + threshold_pct):
                swings.append({
                    "type": "DOWN",
                    "start_price": df['high'].values[last_pivot_idx],
                    "end_price": last_pivot_price,
                    "pts": (df['high'].values[last_pivot_idx] - last_pivot_price) / PIP_SIZE
                })
                current_dir = 1
                last_pivot_price = p_high
                last_pivot_idx = i
                
    return swings

def analyze_year(df_year: pd.DataFrame, year_name: str):
    swings = compute_zigzag_swings(df_year, threshold_pct=0.003)
    swing_pts = [s["pts"] for s in swings]
    total_swing_pips = sum(swing_pts)
    
    net_swing_pips = sum([s["pts"] - SPREAD_PTS for s in swings if s["pts"] > SPREAD_PTS])
    oracle_100_pnl = net_swing_pips * POINT_VALUE # 0.01 lot
    target_20pct_pnl = oracle_100_pnl * 0.20
    target_15pct_pnl = oracle_100_pnl * 0.15
    
    return {
        "year": year_name,
        "bars": len(df_year),
        "swings_count": len(swings),
        "total_pips": total_swing_pips,
        "gold_price_range": total_swing_pips * PIP_SIZE,
        "oracle_100_pnl": oracle_100_pnl,
        "target_20pct_pnl": target_20pct_pnl,
        "target_15pct_pnl": target_15pct_pnl,
        "target_20pct_balance": 1000.0 + target_20pct_pnl,
        "target_15pct_balance": 1000.0 + target_15pct_pnl,
    }

def run_all_years_oracle_analysis():
    print("==========================================================")
    print("🔮 EXECUTING ALL-YEARS ORACLE PRESCIENCE ANALYSIS (2022 - 2026)")
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
    
    # Slice Years
    df_2024 = df_raw.loc['2024-05-01 00:00:00':'2025-05-01 00:00:00'].copy()
    df_2023 = df_raw.loc['2023-05-01 00:00:00':'2024-05-01 00:00:00'].copy()
    df_2022 = df_raw.loc['2022-05-02 00:00:00':'2023-05-01 00:00:00'].copy()
    df_2025 = df_raw.loc['2025-05-01 00:00:00':'2026-07-24 23:45:00'].copy()
    
    r2024 = analyze_year(df_2024, "Năm 2024 - 2025 (In-Sample)")
    r2023 = analyze_year(df_2023, "Năm 2023 - 2024 (OOS 1)")
    r2022 = analyze_year(df_2022, "Năm 2022 - 2023 (OOS 2)")
    r2025 = analyze_year(df_2025, "Năm 2025 - 2026 (OOS 3)")
    
    results = [r2024, r2023, r2022, r2025]
    
    print("\n📊 ALL-YEARS ORACLE THEORETICAL MAX & 15-20% WAVE TARGET SUMMARY:")
    for r in results:
        print(f"\n🗓️  {r['year']}:")
        print(f"   - Số nến M15                 : {r['bars']:,} nến")
        print(f"   - Tổng số Sóng Đỉnh - Đáy    : {r['swings_count']:,} sóng (~{r['swings_count']/12:.0f} sóng/tháng)")
        print(f"   - Tổng Biên độ Giá Vàng      : {r['total_pips']:,.0f} pips (${r['gold_price_range']:,.2f} USD)")
        print(f"   - 100% Lợi nhuận Trần (0.01 lot) : ${r['oracle_100_pnl']:+,.2f} USD (+{r['oracle_100_pnl']/10.0:,.1f}%)")
        print(f"   🎯 TARGET 15% SÓNG ($1,000 Vốn)  : ${r['target_15pct_pnl']:+,.2f} USD -> Số dư: ${r['target_15pct_balance']:,.2f} USD")
        print(f"   🎯 TARGET 20% SÓNG ($1,000 Vốn)  : ${r['target_20pct_pnl']:+,.2f} USD -> Số dư: ${r['target_20pct_balance']:,.2f} USD")

    # Save Report
    reports_dir = os.path.join(antigravity_dir, "reports", "codex_verification")
    os.makedirs(reports_dir, exist_ok=True)
    report_file = os.path.join(reports_dir, "ALL_YEARS_ORACLE_PROFIT_REPORT.md")
    
    lines = []
    lines.append("# 🔮 ALL-YEARS ORACLE PRESCIENCE AUDIT (2022 - 2026)")
    lines.append(f"**Timestamp**: {datetime.now(timezone.utc).isoformat()} UTC")
    lines.append("**Focus**: Exact calculation of 100% Oracle Max Profit & 15-20% Target Wave Absorption across ALL years")
    lines.append("\n---")
    lines.append("\n## 📊 All-Years Oracle Matrix")
    lines.append("| Năm Lịch sử | Số Sóng Đỉnh-Đáy | Tổng Biên độ Giá ($) | 100% Oracle Trần ($) | Target 15% Sóng ($) | Số dư Target 15% ($) | Target 20% Sóng ($) | Số dư Target 20% ($) |")
    lines.append("| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |")
    for r in results:
        lines.append(f"| **{r['year']}** | {r['swings_count']:,} | ${r['gold_price_range']:,.2f} | **${r['oracle_100_pnl']:+,.2f}** | **${r['target_15pct_pnl']:+,.2f}** | **${r['target_15pct_balance']:,.2f}** | **${r['target_20pct_pnl']:+,.2f}** | **${r['target_20pct_balance']:,.2f}** |")

    with open(report_file, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
        
    print(f"\n📄 Saved All-Years Oracle Report to: {report_file}")

if __name__ == "__main__":
    run_all_years_oracle_analysis()
