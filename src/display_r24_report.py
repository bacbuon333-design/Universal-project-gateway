"""
READ AND DISPLAY SUMMARY OF R24 NATIVE REPORT HTML
==================================================
"""

import os, sys
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None

REPORT_PATH = r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05\MQL5\Experts\AlphaLab\r24_gold_exec_report.htm"

def read_report():
    if not os.path.exists(REPORT_PATH):
        print("Report path does not exist.")
        return
        
    with open(REPORT_PATH, 'r', encoding='utf-16-le', errors='ignore') as f:
        content = f.read()
        
    soup = BeautifulSoup(content, 'html.parser')
    rows = soup.find_all('tr')
    print("="*105)
    print("SUMMARY OF MT5 STRATEGY TESTER REPORT (r24_gold_exec_report.htm)")
    print("="*105)
    for r in rows[:35]:
        cols = [c.get_text().strip() for c in r.find_all(['td', 'th'])]
        if cols:
            print(f"  {' | '.join(cols)}")

if __name__ == '__main__':
    read_report()
