"""
SEARCH ALL MT5 HTML REPORTS FOR TRUE PASSING CANDIDATES
======================================================
"""

import os, sys, glob
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None

DATA_DIR = r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05"

def audit_all():
    htms = glob.glob(os.path.join(DATA_DIR, "**", "*.htm*"), recursive=True)
    print(f"Auditing {len(htms)} HTML report files across terminal directory...\n")
    
    passed_reports = []
    
    for path in htms:
        try:
            with open(path, 'r', encoding='utf-16-le', errors='ignore') as f:
                content = f.read()
            if not content or len(content) < 100:
                with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
            soup = BeautifulSoup(content, 'html.parser')
            rows = soup.find_all('tr')
            
            expert = ""
            net_pnl = 0.0
            pf = 0.0
            max_dd_pct = 0.0
            trades = 0
            
            for r in rows[:35]:
                cols = [c.get_text().strip() for c in r.find_all(['td', 'th'])]
                if not cols: continue
                text = " ".join(cols)
                if 'Expert:' in text:
                    expert = cols[-1] if len(cols)>1 else text
                if 'Total Net Profit:' in text:
                    for i, c in enumerate(cols):
                        if c == 'Total Net Profit:':
                            try: net_pnl = float(cols[i+1].replace(' ', '').replace(',', ''))
                            except: pass
                if 'Profit Factor:' in text:
                    for i, c in enumerate(cols):
                        if c == 'Profit Factor:':
                            try: pf = float(cols[i+1].replace(' ', '').replace(',', ''))
                            except: pass
                if 'Equity Drawdown Relative:' in text or 'Balance Drawdown Relative:' in text:
                    for i, c in enumerate(cols):
                        if '%' in c:
                            try:
                                val = float(c.split('%')[0].split('(')[-1].strip())
                                if val > max_dd_pct: max_dd_pct = val
                            except: pass
                if 'Total Trades:' in text:
                    for i, c in enumerate(cols):
                        if c == 'Total Trades:':
                            try: trades = int(cols[i+1])
                            except: pass
                            
            if net_pnl > 1000.0:
                passed_reports.append({
                    'path': path,
                    'expert': expert,
                    'net_pnl': net_pnl,
                    'pf': pf,
                    'max_dd_pct': max_dd_pct,
                    'trades': trades
                })
        except Exception:
            pass
            
    print(f"FOUND {len(passed_reports)} REPORTS WITH NET PROFIT > $1,000.00 USD:")
    print("="*110)
    for rep in passed_reports:
        print(f"File: {os.path.basename(rep['path'])}")
        print(f"  Expert: {rep['expert']}")
        print(f"  Net Profit: ${rep['net_pnl']:.2f} USD | PF: {rep['pf']:.2f} | Max DD: {rep['max_dd_pct']:.2f}% | Trades: {rep['trades']}")
        print(f"  Path: {rep['path']}\n")

if __name__ == '__main__':
    audit_all()
