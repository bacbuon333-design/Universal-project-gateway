"""
CHECK MAX HISTORICAL DEPTH FOR M5 / M15 / REALTIME TICK DATA IN MT5
===================================================================
Checks the maximum available historical bars and date range for:
1. M5 Bars from MT5 Terminal
2. M15 Bars from MT5 Terminal & Local CSV
3. H1 Bars from MT5 Terminal & Local CSV
"""

import os, sys
sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None
import pandas as pd
import MetaTrader5 as mt5

BASE_DIR = r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05\AlphaLab_Antigravity"

def check_depth():
    print("="*95)
    print("METATRADER 5 & LOCAL DATASET MAXIMUM HISTORICAL DEPTH AUDIT")
    print("="*95)
    
    # Check local CSV files
    m15_path = os.path.join(BASE_DIR, "data", "GOLD_M15.csv")
    h1_path  = os.path.join(BASE_DIR, "data", "GOLD_H1_2010_2026.csv")
    
    if os.path.exists(m15_path):
        df_m15 = pd.read_csv(m15_path)
        col = 'datetime_str' if 'datetime_str' in df_m15.columns else df_m15.columns[0]
        dt_m15 = pd.to_datetime(df_m15[col])
        print(f"📁 Local M15 File (`data/GOLD_M15.csv`):")
        print(f"   - Total Bars : {len(df_m15):,} bars")
        print(f"   - Date Range : {dt_m15.iloc[0]} to {dt_m15.iloc[-1]} ({len(df_m15)*15/60/24/365:.2f} Years)")
        
    if os.path.exists(h1_path):
        df_h1 = pd.read_csv(h1_path)
        col = 'datetime_str' if 'datetime_str' in df_h1.columns else df_h1.columns[0]
        dt_h1 = pd.to_datetime(df_h1[col])
        print(f"\n📁 Local H1 File (`data/GOLD_H1_2010_2026.csv`):")
        print(f"   - Total Bars : {len(df_h1):,} bars")
        print(f"   - Date Range : {dt_h1.iloc[0]} to {dt_h1.iloc[-1]} ({len(df_h1)/24/365:.2f} Years)")

    # Check MT5 connection and maximum copy_rates capability
    if mt5.initialize():
        print(f"\n🔌 MetaTrader 5 Terminal Direct API Connection:")
        account = mt5.account_info()
        if account:
            print(f"   - Connected Broker Account: {account.login} ({account.company})")
            
        symbols = ['XAUUSD', 'GOLD']
        found_sym = None
        for s in symbols:
            info = mt5.symbol_info(s)
            if info is not None:
                found_sym = s
                break
                
        if found_sym:
            print(f"   - Target Symbol: {found_sym}")
            
            # Fetch max M5 bars
            rates_m5 = mt5.copy_rates_from_pos(found_sym, mt5.TIMEFRAME_M5, 0, 100000)
            if rates_m5 is not None and len(rates_m5) > 0:
                dt_m5_start = pd.to_datetime(rates_m5[0]['time'], unit='s')
                dt_m5_end   = pd.to_datetime(rates_m5[-1]['time'], unit='s')
                days_m5 = (dt_m5_end - dt_m5_start).days
                print(f"   - M5 Maximum Depth : {len(rates_m5):,} bars ({dt_m5_start.strftime('%Y-%m-%d')} to {dt_m5_end.strftime('%Y-%m-%d')}, ~{days_m5/365:.2f} Years / {days_m5} Days)")
                
            # Fetch max M1 bars
            rates_m1 = mt5.copy_rates_from_pos(found_sym, mt5.TIMEFRAME_M1, 0, 100000)
            if rates_m1 is not None and len(rates_m1) > 0:
                dt_m1_start = pd.to_datetime(rates_m1[0]['time'], unit='s')
                dt_m1_end   = pd.to_datetime(rates_m1[-1]['time'], unit='s')
                days_m1 = (dt_m1_end - dt_m1_start).days
                print(f"   - M1 Maximum Depth : {len(rates_m1):,} bars ({dt_m1_start.strftime('%Y-%m-%d')} to {dt_m1_end.strftime('%Y-%m-%d')}, ~{days_m1/365:.2f} Years / {days_m1} Days)")
                
            # Fetch max Ticks
            ticks = mt5.copy_ticks_from(found_sym, pd.to_datetime('2026-07-01'), 100000, mt5.COPY_TICKS_ALL)
            if ticks is not None and len(ticks) > 0:
                dt_tick_start = pd.to_datetime(ticks[0]['time'], unit='s')
                dt_tick_end   = pd.to_datetime(ticks[-1]['time'], unit='s')
                print(f"   - Realtime Tick Depth: {len(ticks):,} raw ticks fetched ({dt_tick_start.strftime('%Y-%m-%d %H:%M')} to {dt_tick_end.strftime('%Y-%m-%d %H:%M')})")
        mt5.shutdown()

if __name__ == '__main__':
    check_depth()
