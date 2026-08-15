"""
FIND ALL RECENTLY CREATED HTML REPORTS
======================================
"""

import os, sys, glob

sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None

DATA_DIR = r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05"

def find_recent():
    htms = glob.glob(os.path.join(DATA_DIR, "**", "*.htm*"), recursive=True)
    htms.sort(key=os.path.getmtime, reverse=True)
    print(f"Total htm files: {len(htms)}")
    for h in htms[:10]:
        print(f"  Report File: {h} | Size: {os.path.getsize(h)} | MTime: {os.path.getmtime(h)}")

if __name__ == '__main__':
    find_recent()
