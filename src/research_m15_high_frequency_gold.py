"""
RESEARCH M15 HIGH-FREQUENCY MULTI-LEG GOLD ENGINE (2022 - 2026)
================================================================
"""

import os, sys, pandas as pd, numpy as np

sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None

CSV_PATH = r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05\AlphaLab_Antigravity\data\GOLD_M15.csv"

def run_m15_hf_research():
    print("="*115)
    print("RUNNING M15 HIGH-FREQUENCY MULTI-LEG GOLD ALPHA ENGINE RESEARCH")
    print("="*115)
    
    if not os.path.exists(CSV_PATH):
        print(f"Data file missing at {CSV_PATH}")
        return
        
    df = pd.read_csv(CSV_PATH)
    print(f"Loaded {len(df)} M15 bars from CSV.")
    
    # Calculate indicators
    df['ema9'] = df['close'].ewm(span=9, adjust=False).mean()
    df['ema20'] = df['close'].ewm(span=20, adjust=False).mean()
    df['ema55'] = df['close'].ewm(span=55, adjust=False).mean()
    df['ema200'] = df['close'].ewm(span=200, adjust=False).mean()
    
    df['tr'] = np.maximum(df['high'] - df['low'], 
                          np.maximum(abs(df['high'] - df['close'].shift(1)), 
                                     abs(df['low'] - df['close'].shift(1))))
    df['atr14'] = df['tr'].rolling(14).mean()
    df['atr50'] = df['tr'].rolling(50).mean()
    
    # Donchian channels (causal: shift 1)
    df['donchian_high'] = df['high'].shift(1).rolling(20).max()
    df['donchian_low'] = df['low'].shift(1).rolling(20).min()
    
    # RSI
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / (loss + 1e-8)
    df['rsi'] = 100 - (100 / (1 + rs))
    
    # Signals
    # Leg 1: Donchian Breakout
    df['sig_donchian_buy'] = (df['close'] > df['donchian_high']) & (df['ema9'] > df['ema20'])
    df['sig_donchian_sell'] = (df['close'] < df['donchian_low']) & (df['ema9'] < df['ema20'])
    
    # Leg 2: EMA Pullback Re-entry
    df['sig_pullback_buy'] = (df['ema20'] > df['ema55']) & (df['low'] <= df['ema20']) & (df['close'] > df['ema20']) & (df['rsi'] > 50)
    df['sig_pullback_sell'] = (df['ema20'] < df['ema55']) & (df['high'] >= df['ema20']) & (df['close'] < df['ema20']) & (df['rsi'] < 50)
    
    # Leg 3: Volatility Impulse Breakout
    df['sig_vol_buy'] = (df['atr14'] > df['atr50'] * 1.05) & (df['close'] > df['ema9']) & (df['ema9'] > df['ema20']) & (df['rsi'] > 55)
    df['sig_vol_sell'] = (df['atr14'] > df['atr50'] * 1.05) & (df['close'] < df['ema9']) & (df['ema9'] < df['ema20']) & (df['rsi'] < 45)
    
    df['buy_signal'] = df['sig_donchian_buy'] | df['sig_pullback_buy'] | df['sig_vol_buy']
    df['sell_signal'] = df['sig_donchian_sell'] | df['sig_pullback_sell'] | df['sig_vol_sell']
    
    print(f"Total Buy Signal Triggers : {df['buy_signal'].sum()}")
    print(f"Total Sell Signal Triggers: {df['sell_signal'].sum()}")
    print(f"Total Potential Signal Entries: {df['buy_signal'].sum() + df['sell_signal'].sum()}")

if __name__ == '__main__':
    run_m15_hf_research()
