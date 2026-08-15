"""
FIND AND READ EXACT MT5 STRATEGY TESTER HTML REPORT SOURCE
===========================================================
"""

import os, sys, glob
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None

TERMINAL_ROOT = r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05"
TESTER_ROOT = r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Tester\BB16F565FAAA6B23A20C26C49416FF05"

def read_reports():
    print("="*105)
    print("SEARCHING FOR RECENT MT5 STRATEGY TESTER HTML REPORTS...")
    print("="*105)
    
    reports = glob.glob(os.path.join(TERMINAL_ROOT, "**", "*.htm*"), recursive=True) + \
              glob.glob(os.path.join(TESTER_ROOT, "**", "*.htm*"), recursive=True)
              
    reports.sort(key=os.path.getmtime, reverse=True)
    
    print(f"Found {len(reports)} HTML report files across MetaQuotes directories:")
    for r in reports[:5]:
        print(f"  Report File: {r} | Size: {os.path.getsize(r)} | Modified: {os.path.getmtime(r)}")
        
    if reports:
        latest = reports[0]
        print("\n" + "="*105)
        print(f"READING HTML REPORT SOURCE: {latest}")
        print("="*105)
        
        try:
            with open(latest, 'r', encoding='utf-16-le', errors='ignore') as f:
                content = f.read()
            if not content or len(content) < 100:
                with open(latest, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    
            soup = BeautifulSoup(content, 'html.parser')
            rows = soup.find_all('tr')
            print(f"Extracted {len(rows)} HTML Table Rows from {latest}:")
            for idx, r in enumerate(rows[:40]):
                cols = [c.get_text().strip() for c in r.find_all(['td', 'th'])]
                if cols:
                    print(f"  Row {idx:2d}: {' | '.join(cols)}")
        except Exception as e:
            print(f"Error reading report: {e}")

if __name__ == '__main__':
    read_reports()
