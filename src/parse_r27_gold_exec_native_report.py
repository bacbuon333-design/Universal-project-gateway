"""
PARSE R27 GOLD EXEC NATIVE MODEL=4 HTML REPORT SOURCE
=====================================================
"""

import os, sys, glob
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None

DATA_DIR = r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05"

def parse_report():
    htms = glob.glob(os.path.join(DATA_DIR, "**", "*r27_gold_exec*.htm*"), recursive=True)
    if not htms:
        htms = glob.glob(os.path.join(DATA_DIR, "**", "*.htm*"), recursive=True)
        htms.sort(key=os.path.getmtime, reverse=True)
        
    print(f"Found {len(htms)} HTML report files. Parsing latest...")
    
    if htms:
        latest = htms[0]
        print("="*105)
        print(f"PARSING NATIVE MT5 MODEL=4 HTML REPORT: {latest}")
        print("="*105)
        
        try:
            with open(latest, 'r', encoding='utf-16-le', errors='ignore') as f:
                content = f.read()
            if not content or len(content) < 100:
                with open(latest, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    
            soup = BeautifulSoup(content, 'html.parser')
            rows = soup.find_all('tr')
            for r in rows[:35]:
                cols = [c.get_text().strip() for c in r.find_all(['td', 'th'])]
                if cols:
                    print(f"  {' | '.join(cols)}")
        except Exception as e:
            print(f"Error reading report: {e}")

if __name__ == '__main__':
    parse_report()
