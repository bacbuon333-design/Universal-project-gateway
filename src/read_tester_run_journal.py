"""
READ DETAILED MT5 TESTER JOURNAL LOGS FOR THE LATEST RUN
=========================================================
"""

import os, sys, glob

sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None

DATA_DIR = r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05"

def read_journal():
    print("="*105)
    print("READING LATEST MT5 TESTER LOGS TO DIAGNOSE NO-TRADE / LOSS BUG")
    print("="*105)
    
    logs = glob.glob(os.path.join(DATA_DIR, "Tester", "logs", "*.log"))
    logs.sort(key=os.path.getmtime, reverse=True)
    
    if logs:
        latest_log = logs[0]
        print(f"Reading log: {latest_log}")
        with open(latest_log, 'r', encoding='utf-16-le', errors='ignore') as f:
            lines = f.readlines()
            # Search for errors or ALAB_CP400 initialization messages
            for l in lines[-100:]:
                print(l.strip())
    else:
        print("No tester logs found.")

if __name__ == '__main__':
    read_journal()
