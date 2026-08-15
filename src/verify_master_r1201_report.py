"""
Parse and verify R1201 Native MT5 HTML Report
"""

import os, sys
from bs4 import BeautifulSoup

report_path = r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05\MQL5\Experts\AlphaLab\r1201_gold_exec_report.htm"

def parse():
    with open(report_path, 'r', encoding='utf-16-le', errors='ignore') as f:
        content = f.read()
    if not content or len(content) < 100:
        with open(report_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            
    soup = BeautifulSoup(content, 'html.parser')
    rows = soup.find_all('tr')
    
    print("="*80)
    print("NATIVE MT5 REPORT PARSED VERIFICATION (R1201 GOLD M15)")
    print("="*80)
    
    for r in rows[:40]:
        cols = [c.get_text().strip() for c in r.find_all(['td', 'th'])]
        if not cols: continue
        line = " | ".join(cols)
        if any(k in line for k in ['Total Net Profit', 'Profit Factor', 'Equity Drawdown', 'Total Trades', 'Deposit', 'Symbol', 'Period', 'Bars', 'Ticks']):
            print(line)
            
if __name__ == '__main__':
    parse()
