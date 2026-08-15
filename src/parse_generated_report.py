"""
PARSE MT5 GENERATED HTML REPORT SUMMARY
=======================================
"""

import os, sys, glob
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None

DATA_DIR = r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05"

def parse_summary():
    htms = glob.glob(os.path.join(DATA_DIR, "**", "*.htm*"), recursive=True)
    htms.sort(key=os.path.getmtime, reverse=True)
    print(f"Found {len(htms)} htm/html files. Inspecting latest...")
    
    for h in htms[:3]:
        print("\n" + "="*105)
        print(f"FILE: {h} | Size: {os.path.getsize(h)} bytes")
        print("="*105)
        try:
            with open(h, 'r', encoding='utf-16-le', errors='ignore') as f:
                content = f.read()
            if not content or len(content) < 100:
                with open(h, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    
            soup = BeautifulSoup(content, 'html.parser')
            rows = soup.find_all('tr')
            for r in rows:
                cols = [c.get_text().strip() for c in r.find_all(['td', 'th'])]
                if len(cols) >= 2:
                    for i in range(0, len(cols) - 1, 2):
                        k = cols[i].replace(':', '')
                        v = cols[i+1]
                        if any(term in k.lower() for term in ['profit', 'drawdown', 'trades', 'factor', 'payoff', 'deposit', 'balance']):
                            print(f"  {k:30s} -> {v}")
        except Exception as e:
            print(f"Error parsing {h}: {e}")

if __name__ == '__main__':
    parse_summary()
