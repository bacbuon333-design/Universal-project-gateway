"""
===================================================================
ANTIGRAVITY GOLD DEEP HISTORY PROBER (INDEPENDENT TERRITORY)
===================================================================
Probes MetaTrader 5 server for the absolute oldest available historical
bar data for GOLD (XAUUSD), auditing total bars, earliest timestamp,
data gaps, and missing periods.

Execution Scope: Isolated within AlphaLab_Antigravity/
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

def probe_gold_deep_history():
    print("==========================================================")
    print("🔍 PROBING DEEPEST HISTORICAL DATA FOR GOLD ON MT5")
    print("==========================================================")
    
    try:
        import MetaTrader5 as mt5
        if not mt5.initialize():
            print(f"❌ MT5 Initialize failed: {mt5.last_error()}")
            return
            
        print(f"✅ Connected to MT5 Server: {mt5.terminal_info().company} ({mt5.terminal_info().name})")
        
        # Check matching symbols for Gold
        all_symbols = [s.name for s in mt5.symbols_get()]
        gold_symbols = [s for s in all_symbols if "GOLD" in s.upper() or "XAU" in s.upper()]
        
        print(f"Found Gold Symbol Candidates: {gold_symbols}")
        
        if not gold_symbols:
            print("❌ No Gold symbol found on this broker terminal.")
            mt5.shutdown()
            return
            
        target_symbol = gold_symbols[0]
        print(f"🎯 Target Symbol selected for deep probing: '{target_symbol}'")
        
        # Ensure symbol is selected in Market Watch
        if not mt5.symbol_select(target_symbol, True):
            print(f"⚠️ Failed to select {target_symbol} in Market Watch.")
            
        timeframes = [
            ("H1", mt5.TIMEFRAME_H1),
            ("D1", mt5.TIMEFRAME_D1),
            ("M1", mt5.TIMEFRAME_M1)
        ]
        
        results = {}
        
        start_date = datetime(1995, 1, 1, tzinfo=timezone.utc)
        end_date = datetime.now(timezone.utc)
        
        for tf_name, tf_const in timeframes:
            print(f"\n--- Probing Timeframe: {tf_name} ---")
            
            # Fetch rates range from 1995 to present
            rates = mt5.copy_rates_range(target_symbol, tf_const, start_date, end_date)
            
            if rates is None or len(rates) == 0:
                # Fallback to copy_rates_from_pos with 99,999 bars
                rates = mt5.copy_rates_from_pos(target_symbol, tf_const, 0, 99999)
                
            if rates is None or len(rates) == 0:
                print(f"❌ Failed to fetch {tf_name} rates. Error: {mt5.last_error()}")
                continue
                
            df = pd.DataFrame(rates)
            df['datetime'] = pd.to_datetime(df['time'], unit='s', utc=True)
            
            first_bar = df.iloc[0]
            last_bar = df.iloc[-1]
            total_bars = len(df)
            
            earliest_dt = first_bar['datetime']
            latest_dt = last_bar['datetime']
            
            # Audit for timestamp monotonicity (reverse timestamps)
            diffs = np.diff(df['time'].values)
            reverse_count = np.count_nonzero(diffs <= 0)
            
            # Audit for expected time gaps
            if tf_name == "H1":
                # Expected gap max 72h (3 days for weekend)
                gap_hours = diffs / 3600.0
                unusual_gaps = np.count_nonzero(gap_hours > 72.0)
            elif tf_name == "D1":
                # Expected gap max 5 days for holidays/weekends
                gap_days = diffs / 86400.0
                unusual_gaps = np.count_nonzero(gap_days > 5.0)
            else:
                unusual_gaps = 0
                
            results[tf_name] = {
                "total_bars": total_bars,
                "earliest_utc": earliest_dt.isoformat(),
                "latest_utc": latest_dt.isoformat(),
                "reverse_timestamps": reverse_count,
                "unusual_gaps": unusual_gaps,
                "earliest_year": earliest_dt.year
            }
            
            print(f"   Total Bars Downloaded : {total_bars:,}")
            print(f"   Earliest Bar Date     : {earliest_dt.strftime('%Y-%m-%d %H:%M:%S')} UTC")
            print(f"   Latest Bar Date       : {latest_dt.strftime('%Y-%m-%d %H:%M:%S')} UTC")
            print(f"   Timestamp Errors      : {reverse_count}")
            print(f"   Unusual Gap Count     : {unusual_gaps}")

        mt5.shutdown()
        
        # Save Findings Report
        antigravity_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        reports_dir = os.path.join(antigravity_dir, "reports", "gold_history_probe")
        os.makedirs(reports_dir, exist_ok=True)
        
        report_path = os.path.join(reports_dir, "GOLD_DEEP_HISTORY_REPORT.md")
        lines = []
        lines.append("# 🏆 DEEP HISTORY PROBE REPORT FOR GOLD (XAUUSD)")
        lines.append(f"**Timestamp**: {datetime.now(timezone.utc).isoformat()} UTC")
        lines.append(f"**Target Symbol**: `{target_symbol}`")
        lines.append("\n---")
        lines.append("\n## 📊 History Availability Summary")
        lines.append("| Timeframe | Earliest Bar Date (UTC) | Latest Bar Date (UTC) | Total Bars | Timestamp Errors | Unusual Gaps |")
        lines.append("| :--- | :--- | :--- | :---: | :---: | :---: |")
        
        for tf_name, r in results.items():
            lines.append(
                f"| **{tf_name}** | **{r['earliest_utc'][:10]}** | {r['latest_utc'][:10]} | {r['total_bars']:,} | {r['reverse_timestamps']} | {r['unusual_gaps']} |"
            )
            
        lines.append("\n---")
        lines.append("\n## 🏛️ Verdict & Audit Insights")
        if "H1" in results:
            lines.append(f"1. **Xa nhất có thể (H1)**: Dữ liệu nến H1 của Vàng xa nhất là ngày **{results['H1']['earliest_utc'][:10]}** (Năm {results['H1']['earliest_year']}).")
            lines.append(f"2. **Độ tin cậy dữ liệu**: Tổng cộng **{results['H1']['total_bars']:,} nến H1** với **{results['H1']['reverse_timestamps']} lỗi mốc thời gian**.")
            lines.append(f"3. **Khoảng trống dữ liệu (Gaps)**: Phát hiện {results['H1']['unusual_gaps']} khoảng nghỉ lớn hơn 3 ngày (thường do kỳ nghỉ lễ dài ngày hoặc gián đoạn lịch sử từ sàn).")
            
        with open(report_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
            
        print(f"\n📄 Saved Deep History Report to: {report_path}")
        
    except Exception as e:
        print(f"❌ Error during probing: {e}")

if __name__ == "__main__":
    probe_gold_deep_history()
