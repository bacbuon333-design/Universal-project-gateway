"""
READ LATEST MT5 TERMINAL AND TESTER LOGS
========================================
"""

import os, sys, glob

sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None

DATA_DIR = r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05"

def read_latest_logs():
    print("="*105)
    print("CHECKING MT5 TESTER LOGS")
    print("="*105)
    
    logs = glob.glob(os.path.join(DATA_DIR, "Tester", "logs", "*.log"))
    logs.sort(key=os.path.getmtime, reverse=True)
    
    if logs:
        latest_log = logs[0]
        print(f"Latest Tester Log: {latest_log}")
        with open(latest_log, 'r', encoding='utf-16-le', errors='ignore') as f:
            lines = f.readlines()
            for l in lines[-30:]:
                print(l.strip())
    else:
        print("No tester logs found in Tester/logs/")

if __name__ == '__main__':
    read_latest_logs()
