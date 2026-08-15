"""
TRACE ALL DEALS AND ORDERS IN CP400 NATIVE RUN
==============================================
"""

import os, sys

sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None

AGENT_LOG = r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Tester\BB16F565FAAA6B23A20C26C49416FF05\Agent-127.0.0.1-3000\logs\20260801.log"

def trace_run():
    with open(AGENT_LOG, 'r', encoding='utf-16-le', errors='ignore') as f:
        lines = f.readlines()
        
    start_idx = 110314
    end_idx = 110415
    print("="*105)
    print("PRINTING ALL LOG LINES FOR CP400 NATIVE RUN:")
    print("="*105)
    for idx in range(start_idx, end_idx):
        print(lines[idx].strip())

if __name__ == '__main__':
    trace_run()
