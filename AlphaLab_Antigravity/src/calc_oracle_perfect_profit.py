"""
===================================================================
ORACLE PERFECT PRESCIENCE ANALYSIS (PERFECT TOP/BOTTOM CATCHING)
===================================================================
Calculates the theoretical maximum potential profit (Theoretical Upper Bound)
if an ideal system bought at every local bottom and sold at every local top
over 1 Year of GOLD M15 historical data (2024-05-01 to 2025-05-01 | 23,571 bars).

Calculates:
1. Cumulative Total Price Trajectory (Sum of High - Low of every swing).
2. Fixed Lot (0.01 lot) Max Potential PnL.
3. Compounding (1% Risk / Trade) Max Potential PnL.

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

def compute_zigzag_swings(df: pd.DataFrame, threshold_pct: float = 0.003): # 0.3% price move (~$7-$8 Gold move)
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
        elif current_dir == 1: # Uptrend swing, looking for top
            if p_high > last_pivot_price:
                last_pivot_price = p_high
                last_pivot_idx = i
            elif p_low <= last_pivot_price * (1 - threshold_pct):
                # Peak formed, record swing
                swings.append({
                    "type": "UP",
                    "start_price": df['low'].values[last_pivot_idx],
                    "end_price": last_pivot_price,
                    "pts": (last_pivot_price - df['low'].values[last_pivot_idx]) / PIP_SIZE
                })
                current_dir = -1
                last_pivot_price = p_low
                last_pivot_idx = i
        elif current_dir == -1: # Downtrend swing, looking for bottom
            if p_low < last_pivot_price:
                last_pivot_price = p_low
                last_pivot_idx = i
            elif p_high >= last_pivot_price * (1 + threshold_pct):
                # Trough formed, record swing
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

def run_oracle_analysis():
    print("==========================================================")
    print("🔮 EXECUTING ORACLE PERFECT PRESCIENCE ANALYSIS (PERFECT TOPS & BOTTOMS)")
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
    
    # Slice to 1 Strict Year (2024-05-01 to 2025-05-01)
    df_1y = df_raw.loc['2024-05-01 00:00:00':'2025-05-01 00:00:00'].copy()
    print(f"Loaded 1-Year Dataset: {len(df_1y):,} M15 bars ({df_1y.index[0]} -> {df_1y.index[-1]})")
    
    # 1. Bar-by-Bar Theoretical Maximum (Sum of High - Low of every bar)
    bar_ranges = (df_1y['high'] - df_1y['low']) / PIP_SIZE
    total_bar_pips = bar_ranges.sum()
    total_bar_pnl_fixed_001 = total_bar_pips * POINT_VALUE * 1.0 # 0.01 lot
    
    # 2. Realistic Swing Tops/Bottoms (ZigZag 0.3% / ~$8 Gold Reversal)
    swings = compute_zigzag_swings(df_1y, threshold_pct=0.003)
    swing_pts = [s["pts"] for s in swings]
    total_swing_pips = sum(swing_pts)
    
    # PnL calculations
    net_swing_pips_after_spread = sum([s["pts"] - SPREAD_PTS for s in swings if s["pts"] > SPREAD_PTS])
    fixed_001_pnl = net_swing_pips_after_spread * POINT_VALUE # 0.01 lot
    
    # Dynamic Compounding PnL (Risk 1% per swing trade)
    balance_compounding = 1000.0
    for s in swings:
        pts = s["pts"] - SPREAD_PTS
        if pts > 0:
            # 1% risk per trade with 1:3 RR equivalent
            gain_pct = 0.025 # 2.5% gain per perfect swing
            balance_compounding += balance_compounding * gain_pct
            
    print(f"\n📊 1-YEAR ORACLE THEORETICAL UPPER BOUND SUMMARY:")
    print(f"   Total Swing Peaks & Troughs Identified: {len(swings)} swings (~{len(swings)/12:.0f} swings/tháng)")
    print(f"   Total Gross Gold Price Trajectory     : {total_swing_pips:,.0f} pips (${total_swing_pips*PIP_SIZE:,.2f} USD tổng biên độ dao động)")
    print(f"   Net Trajectory (Minus XM Spread 25pt) : {net_swing_pips_after_spread:,.0f} pips")
    print(f"\n💰 POTENTIAL PROFIT BREAKDOWN ($1,000 Initial Balance):")
    print(f"   1. Standard Fixed Lot (0.01 Lot per trade) : ${fixed_001_pnl:+,.2f} USD (+{fixed_001_pnl/10.0:,.1f}%)")
    print(f"   2. Dynamic Compounding (1% Risk / Trade)    : ${balance_compounding:+,.2f} USD (+{(balance_compounding-1000.0)/10.0:,.1f}%)")
    
    # Save Report
    reports_dir = os.path.join(antigravity_dir, "reports", "codex_verification")
    os.makedirs(reports_dir, exist_ok=True)
    report_file = os.path.join(reports_dir, "ORACLE_PERFECT_PROFIT_REPORT.md")
    
    lines = []
    lines.append("# 🔮 ORACLE PERFECT PRESCIENCE REPORT (LỢI NHUẬN TRẦN LÝ THUYẾT VÀNG 1 NĂM)")
    lines.append(f"**Timestamp**: {datetime.now(timezone.utc).isoformat()} UTC")
    lines.append("**Period**: 2024-05-01 to 2025-05-01 (23,571 M15 bars)")
    lines.append("\n---")
    lines.append("\n## 📊 Theoretical Max Profit Summary")
    lines.append(f"- **Tổng số Sóng Đỉnh - Đáy trong 1 năm**: {len(swings)} sóng (~{len(swings)/12:.0f} sóng/tháng)")
    lines.append(f"- **Tổng biên độ sóng di chuyển**: {total_swing_pips:,.0f} pips (${total_swing_pips*PIP_SIZE:,.2f} Giá Vàng)")
    lines.append(f"- **Tổng Lợi Nhuận Trần Lớp 1 (Cố định 0.01 Lot)**: **${fixed_001_pnl:+,.2f} USD** (+{fixed_001_pnl/10.0:,.1f}%)")
    lines.append(f"- **Tổng Lợi Nhuận Trần Lớp 2 (Lãi kép Compounding 1% Risk)**: **${balance_compounding:+,.2f} USD** (+{(balance_compounding-1000.0)/10.0:,.1f}%)")

    with open(report_file, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
        
    print(f"\n📄 Saved Oracle Analysis Report to: {report_file}")

if __name__ == "__main__":
    run_oracle_analysis()
