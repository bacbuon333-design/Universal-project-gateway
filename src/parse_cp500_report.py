"""
PARSE SPECIFIC CP500 MT5 REPORT
===============================
"""

import os, sys, glob
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None

REPORT_PATH = r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05\official_mt5_cp500_report.htm"

def parse_cp500_report():
    if not os.path.exists(REPORT_PATH):
        print(f"Report not found at {REPORT_PATH}")
        return
        
    print("="*105)
    print(f"PARSING NATIVE MT5 GENERATED HTML REPORT: {REPORT_PATH}")
    print("="*105)
    
    with open(REPORT_PATH, 'r', encoding='utf-16-le', errors='ignore') as f:
        content = f.read()
    if not content or len(content) < 100:
        with open(REPORT_PATH, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            
    soup = BeautifulSoup(content, 'html.parser')
    rows = soup.find_all('tr')
    for r in rows:
        cols = [c.get_text().strip() for c in r.find_all(['td', 'th'])]
        if len(cols) >= 2:
            for i in range(0, len(cols) - 1, 2):
                k = cols[i].replace(':', '')
                v = cols[i+1]
                print(f"  {k:35s} -> {v}")

if __name__ == '__main__':
    parse_cp500_report()
