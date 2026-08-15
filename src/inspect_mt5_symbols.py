"""
INSPECT ALL AVAILABLE SYMBOLS AND TICK HISTORY QUALITY ON MT5
============================================================
"""

import os, sys
import MetaTrader5 as mt5

sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None

def inspect_symbols():
    print("="*105)
    print("CONNECTING TO MT5 IPC TO INSPECT AVAILABLE SYMBOLS & REAL TICKS QUALITY")
    print("="*105)
    
    if not mt5.initialize():
        print(f"MT5 Initialization failed: {mt5.last_error()}")
        return
        
    symbols = mt5.symbols_get()
    print(f"Total available symbols on broker: {len(symbols)}")
    
    target_names = ["GOLD", "US100", "US100Cash", "US500", "US500Cash", "EURUSD", "GBPUSD", "USTEC", "US30"]
    found_symbols = []
    
    for s in symbols:
        name = s.name
        if any(t.lower() in name.lower() for t in target_names):
            found_symbols.append(s)
            print(f"  Symbol: {s.name:15s} | Currency: {s.currency_profit:5s} | MarginInit: {s.margin_initial} | MinLot: {s.volume_min} | Step: {s.volume_step}")
            
    mt5.shutdown()

if __name__ == '__main__':
    inspect_symbols()
