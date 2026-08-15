"""
SEARCH ALL CP400 RUNS IN MT5 AGENT LOG
======================================
"""

import os, sys, glob

sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None

AGENT_LOG = r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Tester\BB16F565FAAA6B23A20C26C49416FF05\Agent-127.0.0.1-3000\logs\20260801.log"

def search_all_cp400_runs():
    with open(AGENT_LOG, 'r', encoding='utf-16-le', errors='ignore') as f:
        lines = f.readlines()
        
    print(f"Total log lines: {len(lines)}")
    indices = [idx for idx, l in enumerate(lines) if "ALAB_CP400_MasterFlagshipEA" in l]
    print(f"Found {len(indices)} lines mentioning ALAB_CP400_MasterFlagshipEA:")
    for idx in indices[:20]:
        print(f"  Line {idx}: {lines[idx].strip()}")

if __name__ == '__main__':
    search_all_cp400_runs()
