import os, sys
import pandas as pd
from collections import Counter

sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None

from checkpoint_v95_400trades_flawless_victory import run_cp95_400trades_flawless_master

# We will modify the engine to track bar indices of trades
DATA_PATH = r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05\AlphaLab_Antigravity\data\GOLD_M15.csv"

def audit_cp95_same_candle_trades():
    df_m15 = pd.read_csv(DATA_PATH)
    df_m15['datetime'] = pd.to_datetime(df_m15['datetime_str'])
    df_m15.set_index('datetime', inplace=True)
    
    h1 = df_m15.resample('1h').agg({'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'tick_volume': 'sum'}).dropna()
    
    c = h1['close'].values
    times = h1.index.astype(str).values
    n = len(c)
    
    # Run CP95 logic
    from checkpoint_v95_400trades_flawless_victory import (
        ema9, ema20, ema55, ema200, rsi, adx, atr14, atr50, kelt_upper,
        don_hi20, don_hi15, don_hi10, don_hi7, don_hi5, don_hi3, don_hi12,
        vol_zscore, macd_hist, o, h, l
    )
