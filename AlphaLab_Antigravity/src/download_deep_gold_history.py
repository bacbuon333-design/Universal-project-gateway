"""
DOWNLOAD DEEP GOLD HISTORY (2010 - 2026) FROM MT5
===================================================
Fetches H1 historical data directly from MT5 terminal history cache
and saves it to data/GOLD_H1_2010_2026.csv
"""
import MetaTrader5 as mt5
import pandas as pd
import os, sys
from datetime import datetime

BASE_DIR = r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05\AlphaLab_Antigravity"
OUT_PATH = os.path.join(BASE_DIR, "data", "GOLD_H1_2010_2026.csv")

if not mt5.initialize():
    print("MT5 Init Failed:", mt5.last_error())
    sys.exit(1)

symbol = "GOLD"
mt5.symbol_select(symbol, True)

# Copy 99,999 H1 bars from current bar back
rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H1, 0, 99999)
mt5.shutdown()

if rates is None or len(rates) == 0:
    print("Failed to copy rates")
    sys.exit(1)

df = pd.DataFrame(rates)
df['datetime_str'] = pd.to_datetime(df['time'], unit='s')

# Filter >= 2010-01-01
df_2010 = df[df['datetime_str'] >= '2010-01-01'].copy()
df_2010.sort_values('datetime_str', inplace=True)
df_2010.reset_index(drop=True, inplace=True)

df_2010.to_csv(OUT_PATH, index=False)

print("============================================================")
print("DEEP GOLD HISTORY DOWNLOADED SUCCESSFULLY!")
print("============================================================")
print(f"File Path    : {OUT_PATH}")
print(f"Total H1 Bars: {len(df_2010):,}")
print(f"Start Date   : {df_2010['datetime_str'].min()}")
print(f"End Date     : {df_2010['datetime_str'].max()}")
print(f"Duration     : {(df_2010['datetime_str'].max() - df_2010['datetime_str'].min()).days / 365.25:.2f} years")
