"""
FIND AND DISPLAY ALL MT5 HTML REPORTS
====================================
"""

import os, sys, glob, subprocess
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None

DATA_DIR = r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05"

def list_and_open():
    htms = glob.glob(os.path.join(DATA_DIR, "**", "*.htm*"), recursive=True)
    print(f"Found {len(htms)} total HTML reports in terminal directory:")
    for i, path in enumerate(htms):
        print(f"[{i+1}] {path}")
        try:
            with open(path, 'r', encoding='utf-16-le', errors='ignore') as f:
                content = f.read()
            if not content or len(content) < 100:
                with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
            soup = BeautifulSoup(content, 'html.parser')
            rows = soup.find_all('tr')
            for r in rows[:15]:
                cols = [c.get_text().strip() for c in r.find_all(['td', 'th'])]
                if cols and ('Total Net Profit:' in cols or 'Profit Factor:' in cols or 'Expert:' in cols):
                    print(f"     {' | '.join(cols)}")
        except Exception as e:
            print(f"     Error: {e}")

if __name__ == '__main__':
    list_and_open()
