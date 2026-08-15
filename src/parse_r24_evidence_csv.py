"""
PARSE R24 EVIDENCE CSV LOG
==========================
"""

import os, sys, glob

sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None

COMMON_FILES = r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\Common\Files"
TERMINAL_FILES = r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05\MQL5\Files"

def parse_csv():
    csvs = glob.glob(os.path.join(COMMON_FILES, "*R24*.csv")) + glob.glob(os.path.join(TERMINAL_FILES, "*R24*.csv"))
    print(f"Found {len(csvs)} R24 evidence CSV files.")
    
    for c in csvs:
        print("="*105)
        print(f"READING EVIDENCE CSV: {c}")
        print("="*105)
        with open(c, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        for l in lines:
            print(f"  {l.strip()}")

if __name__ == '__main__':
    parse_csv()
