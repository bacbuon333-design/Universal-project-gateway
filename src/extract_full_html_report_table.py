"""
EXTRACT COMPLETE MT5 HTML REPORT TABLE
======================================
"""

import os, sys, glob
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None

REPORT_PATH = r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05\MQL5\Experts\AlphaLab\r39_gold_exec_report.htm"

def print_full():
    if not os.path.exists(REPORT_PATH):
        print("Report file not found.")
        return
        
    with open(REPORT_PATH, 'r', encoding='utf-16-le', errors='ignore') as f:
        content = f.read()
    if not content or len(content) < 100:
        with open(REPORT_PATH, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            
    soup = BeautifulSoup(content, 'html.parser')
    rows = soup.find_all('tr')
    
    print("FULL MT5 STRATEGY TESTER REPORT TABLE:")
    print("="*100)
    for r in rows:
        cols = [c.get_text().strip() for c in r.find_all(['td', 'th'])]
        if cols:
            print(" | ".join(cols))

if __name__ == '__main__':
    print_full()
