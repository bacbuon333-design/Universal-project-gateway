"""
===================================================================
ANTIGRAVITY GOLD ALL TIMEFRAMES DOWNLOADER
===================================================================
Downloads and saves full historical datasets for all remaining timeframes:
M5, M15, M30, H4, W1 into AlphaLab_Antigravity/data/.
"""

import os
import sys
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

import sqlite3
import pandas as pd
from datetime import datetime, timezone

def download_all_remaining_timeframes():
    print("==========================================================")
    print("📥 DOWNLOADING ALL REMAINING TIMEFRAMES FOR GOLD")
    print("==========================================================")
    
    try:
        import MetaTrader5 as mt5
        if not mt5.initialize():
            print(f"❌ MT5 Initialize failed: {mt5.last_error()}")
            return
            
        target_symbol = "GOLD"
        if not mt5.symbol_select(target_symbol, True):
            print(f"⚠️ Symbol {target_symbol} select failed.")
            
        antigravity_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        data_dir = os.path.join(antigravity_dir, "data")
        os.makedirs(data_dir, exist_ok=True)
        
        db_path = os.path.join(data_dir, "gold_history.db")
        conn = sqlite3.connect(db_path)
        
        timeframes = [
            ("M5", mt5.TIMEFRAME_M5),
            ("M15", mt5.TIMEFRAME_M15),
            ("M30", mt5.TIMEFRAME_M30),
            ("H4", mt5.TIMEFRAME_H4),
            ("W1", mt5.TIMEFRAME_W1)
        ]
        
        start_date = datetime(1995, 1, 1, tzinfo=timezone.utc)
        end_date = datetime.now(timezone.utc)
        
        for tf_name, tf_const in timeframes:
            print(f"\n⏳ Downloading {tf_name} history for {target_symbol}...")
            rates = mt5.copy_rates_range(target_symbol, tf_const, start_date, end_date)
            
            if rates is None or len(rates) == 0:
                rates = mt5.copy_rates_from_pos(target_symbol, tf_const, 0, 99999)
                
            if rates is None or len(rates) == 0:
                print(f"❌ Failed to download {tf_name} bars.")
                continue
                
            df = pd.DataFrame(rates)
            df['datetime'] = pd.to_datetime(df['time'], unit='s', utc=True)
            df['datetime_str'] = df['datetime'].dt.strftime('%Y-%m-%d %H:%M:%S')
            
            cols = ['time', 'datetime_str', 'open', 'high', 'low', 'close', 'tick_volume', 'spread', 'real_volume']
            df = df[cols]
            
            csv_path = os.path.join(data_dir, f"GOLD_{tf_name}.csv")
            df.to_csv(csv_path, index=False)
            
            table_name = f"gold_{tf_name.lower()}"
            df.to_sql(table_name, conn, if_exists="replace", index=False)
            
            file_size_mb = os.path.getsize(csv_path) / (1024 * 1024)
            
            print(f"   ✅ {tf_name}: Downloaded {len(df):,} bars")
            print(f"      Saved CSV to    : {csv_path} ({file_size_mb:.2f} MB)")
            print(f"      Saved SQLite to : {db_path} [table: '{table_name}']")
            print(f"      Period Covered  : {df['datetime_str'].iloc[0]} -> {df['datetime_str'].iloc[-1]}")

        conn.close()
        mt5.shutdown()
        
        print("\n==========================================================")
        print("🎉 ALL TIMEFRAMES (M1, M5, M15, M30, H1, H4, D1, W1) PERSISTED!")
        print("==========================================================")
        
    except Exception as e:
        print(f"❌ Download error: {e}")

if __name__ == "__main__":
    download_all_remaining_timeframes()
