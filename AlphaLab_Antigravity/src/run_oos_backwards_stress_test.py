"""
===================================================================
OUT-OF-SAMPLE (OOS) BACKWARDS STRESS TEST & COUNTER-AUDIT
===================================================================
Tests the exact 20% Wave Capture Engine configuration on PREVIOUS Out-Of-Sample years
to perform rigorous counter-audit (Curve-Fitting Detection):

OOS Windows Tested:
1. Baseline In-Sample (IS): 2024-05-01 -> 2025-05-01 (Codex 1-Year Standard)
2. Previous OOS Year 1: 2023-05-01 -> 2024-05-01 (Previous 1-Year Out-Of-Sample)
3. Previous OOS Year 2: 2022-05-02 -> 2023-05-01 (Oldest 1-Year Out-Of-Sample)
4. Forward OOS Year 3: 2025-05-01 -> 2026-07-24 (Recent Out-Of-Sample)

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
import numpy as np
import pandas as pd
from datetime import datetime, timezone
from dataclasses import dataclass
from typing import List, Dict, Optional

from run_20pct_wave_capture_factory import WaveCaptureFactoryEngine

def run_oos_backwards_stress_test():
    print("==========================================================")
    print("🔍 EXECUTING OUT-OF-SAMPLE (OOS) BACKWARDS STRESS TEST")
    print("==========================================================")
    
    antigravity_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(antigravity_dir, "data")
    m15_csv = os.path.join(data_dir, "GOLD_M15.csv")
    
    if not os.path.exists(m15_csv):
        print(f"❌ GOLD M15 CSV not found at: {m15_csv}")
        return
        
    df_m15 = pd.read_csv(m15_csv)
    df_m15['datetime'] = pd.to_datetime(df_m15['datetime_str'])
    df_m15.set_index('datetime', inplace=True)
    
    # EXACT Engine Instance (No parameter changes!)
    engine = WaveCaptureFactoryEngine(initial_balance=1000.0, base_risk_pct=0.055, spread_pts=25.0)
    
    # 1. BASELINE IN-SAMPLE (2024-05-01 -> 2025-05-01)
    df_is = df_m15.loc['2024-05-01 00:00:00':'2025-05-01 00:00:00'].copy()
    res_is = engine.run_backtest(df_is)
    
    # 2. PREVIOUS OOS YEAR 1 (2023-05-01 -> 2024-05-01)
    df_oos1 = df_m15.loc['2023-05-01 00:00:00':'2024-05-01 00:00:00'].copy()
    res_oos1 = engine.run_backtest(df_oos1)
    
    # 3. PREVIOUS OOS YEAR 2 (2022-05-02 -> 2023-05-01)
    df_oos2 = df_m15.loc['2022-05-02 00:00:00':'2023-05-01 00:00:00'].copy()
    res_oos2 = engine.run_backtest(df_oos2)
    
    # 4. FORWARD OOS YEAR 3 (2025-05-01 -> 2026-07-24)
    df_oos3 = df_m15.loc['2025-05-01 00:00:00':'2026-07-24 23:45:00'].copy()
    res_oos3 = engine.run_backtest(df_oos3)
    
    print("\n📊 OUT-OF-SAMPLE MULTI-YEAR AUDIT RESULTS SUMMARY:")
    print(f"1. Baseline In-Sample (2024-2025) : Final=${res_is['final_balance']:,.2f} | Net=${res_is['total_pnl']:+,.2f} | PF={res_is['profit_factor']:.3f} | MaxDD={res_is['max_dd_pct']:.2f}% | Trades={res_is['total_trades']}")
    print(f"2. Previous OOS Year 1 (2023-2024): Final=${res_oos1['final_balance']:,.2f} | Net=${res_oos1['total_pnl']:+,.2f} | PF={res_oos1['profit_factor']:.3f} | MaxDD={res_oos1['max_dd_pct']:.2f}% | Trades={res_oos1['total_trades']}")
    print(f"3. Previous OOS Year 2 (2022-2023): Final=${res_oos2['final_balance']:,.2f} | Net=${res_oos2['total_pnl']:+,.2f} | PF={res_oos2['profit_factor']:.3f} | MaxDD={res_oos2['max_dd_pct']:.2f}% | Trades={res_oos2['total_trades']}")
    print(f"4. Forward OOS Year 3 (2025-2026) : Final=${res_oos3['final_balance']:,.2f} | Net=${res_oos3['total_pnl']:+,.2f} | PF={res_oos3['profit_factor']:.3f} | MaxDD={res_oos3['max_dd_pct']:.2f}% | Trades={res_oos3['total_trades']}")

    # Save Markdown Report
    reports_dir = os.path.join(antigravity_dir, "reports", "codex_verification")
    os.makedirs(reports_dir, exist_ok=True)
    report_file = os.path.join(reports_dir, "OOS_BACKWARDS_STRESS_TEST_REPORT.md")
    
    lines = []
    lines.append("# 🔍 OUT-OF-SAMPLE (OOS) BACKWARDS STRESS TEST REPORT")
    lines.append(f"**Timestamp**: {datetime.now(timezone.utc).isoformat()} UTC")
    lines.append("**Counter-Audit Focus**: Testing identical configuration on Out-Of-Sample historical years")
    lines.append("\n---")
    lines.append("\n## 📊 Multi-Year OOS Audit Matrix")
    lines.append("| Historical Window | Sample Type | Initial Balance | FINAL BALANCE | Net Profit ($) | PROFIT FACTOR | Max Drawdown | Total Trades | Win Rate | Verdict |")
    lines.append("| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |")
    lines.append(f"| **2024-05-01 -> 2025-05-01** | In-Sample (IS) | $1,000.00 | **${res_is['final_balance']:,.2f}** | **${res_is['total_pnl']:+,.2f}** | **{res_is['profit_factor']:.3f}** | {res_is['max_dd_pct']:.2f}% | {res_is['total_trades']} | {res_is['win_rate']:.1f}% | 🏆 **Baseline Champion** |")
    lines.append(f"| **2023-05-01 -> 2024-05-01** | Previous OOS 1 | $1,000.00 | **${res_oos1['final_balance']:,.2f}** | **${res_oos1['total_pnl']:+,.2f}** | **{res_oos1['profit_factor']:.3f}** | {res_oos1['max_dd_pct']:.2f}% | {res_oos1['total_trades']} | {res_oos1['win_rate']:.1f}% | {'🏆 **PASSED**' if res_oos1['total_pnl'] > 0 else '❌ Sụt giảm'} |")
    lines.append(f"| **2022-05-02 -> 2023-05-01** | Previous OOS 2 | $1,000.00 | **${res_oos2['final_balance']:,.2f}** | **${res_oos2['total_pnl']:+,.2f}** | **{res_oos2['profit_factor']:.3f}** | {res_oos2['max_dd_pct']:.2f}% | {res_oos2['total_trades']} | {res_oos2['win_rate']:.1f}% | {'🏆 **PASSED**' if res_oos2['total_pnl'] > 0 else '❌ Sụt giảm'} |")
    lines.append(f"| **2025-05-01 -> 2026-07-24** | Forward OOS 3 | $1,000.00 | **${res_oos3['final_balance']:,.2f}** | **${res_oos3['total_pnl']:+,.2f}** | **{res_oos3['profit_factor']:.3f}** | {res_oos3['max_dd_pct']:.2f}% | {res_oos3['total_trades']} | {res_oos3['win_rate']:.1f}% | {'🏆 **PASSED**' if res_oos3['total_pnl'] > 0 else '❌ Sụt giảm'} |")

    with open(report_file, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
        
    print(f"\n📄 Saved OOS Backwards Stress Test Report to: {report_file}")

if __name__ == "__main__":
    run_oos_backwards_stress_test()
