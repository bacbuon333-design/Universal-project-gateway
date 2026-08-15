"""
DIAGNOSE EXACT TRADE-BY-TRADE MISMATCH FOR CP400
================================================
"""

import os, sys, glob, re
import pandas as pd
import numpy as np

sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None

AGENT_LOG = r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Tester\BB16F565FAAA6B23A20C26C49416FF05\Agent-127.0.0.1-3000\logs\20260801.log"

def parse_cp400_log_trades():
    print("="*105)
    print("PARSING CP400 TRADES FROM MT5 AGENT LOG...")
    print("="*105)
    
    cp400_trades = []
    with open(AGENT_LOG, 'r', encoding='utf-16-le', errors='ignore') as f:
        lines = f.readlines()
        
    # Find the last run section
    start_run_idx = 0
    for idx, l in enumerate(lines):
        if "test Experts\\AlphaLab\\ALAB_CP400_MasterFlagshipEA.ex5" in l:
            start_run_idx = idx
            
    print(f"Found CP400 run starting at line {start_run_idx} / {len(lines)}")
    
    for l in lines[start_run_idx:]:
        if "market buy" in l and "done" not in l and "failed" not in l:
            cp400_trades.append(l.strip())
            
    print(f"Total CP400 Trades Executed in Last MT5 Tester Run: {len(cp400_trades)}")
    for t in cp400_trades:
        print(f"  {t}")

if __name__ == '__main__':
    parse_cp400_log_trades()
