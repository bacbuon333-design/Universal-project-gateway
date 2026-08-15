"""
AUDIT & PARSE ALL USER-EXPORTED OFFICIAL MT5 BACKTEST REPORTS
=============================================================
User Directive:
"minh đã xuất repo cac cp ra rôi. coa vài cp mìn không xuât vì kết quả quá yếu kém . râta tồi tệ . ban phai xây đc kêt noi tới tester mt5 đoc duocj bao cao cua nó để phân tich nghiênn cuu cp. không đuoc đanh cp đat chuân python nữa"

Searches for all user-exported MT5 Strategy Tester reports (.html/.htm), parses their exact official metrics, and presents an honest audit.
"""

import os, sys, glob
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None

SEARCH_PATHS = [
    r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05\MQL5\Experts\AlphaLab",
    r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05",
    r"C:\Users\gugul\Downloads",
    r"C:\Users\gugul\Desktop"
]

def parse_mt5_html_file(html_path):
    try:
        with open(html_path, 'r', encoding='utf-16-le', errors='ignore') as f:
            content = f.read()
        if not content or len(content) < 100 or 'Strategy Tester Report' not in content:
            with open(html_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
    except Exception:
        return None
        
    if 'Strategy Tester Report' not in content and 'Symbol:' not in content:
        return None
        
    soup = BeautifulSoup(content, 'html.parser')
    text_content = soup.get_text(separator='\n')
    lines = [line.strip() for line in text_content.split('\n') if line.strip()]
    
    metrics = {
        'path': html_path,
        'filename': os.path.basename(html_path),
        'expert': 'Unknown',
        'symbol': 'Unknown',
        'period': 'Unknown',
        'deposit': 1000.0,
        'net_profit': 0.0,
        'gross_profit': 0.0,
        'gross_loss': 0.0,
        'pf': 0.0,
        'max_dd_pct': 0.0,
        'total_trades': 0,
        'win_rate': 0.0,
        'avg_win': 0.0,
        'avg_loss': 0.0
    }
    
    for i, line in enumerate(lines):
        if line == "Expert:": metrics['expert'] = lines[i+1]
        elif line == "Symbol:": metrics['symbol'] = lines[i+1]
        elif line == "Period:": metrics['period'] = lines[i+1]
        elif line == "Total Net Profit:":
            try: metrics['net_profit'] = float(lines[i+1].replace(' ', '').replace(',', ''))
            except: pass
        elif line == "Gross Profit:":
            try: metrics['gross_profit'] = float(lines[i+1].replace(' ', '').replace(',', ''))
            except: pass
        elif line == "Gross Loss:":
            try: metrics['gross_loss'] = float(lines[i+1].replace(' ', '').replace(',', ''))
            except: pass
        elif line == "Profit Factor:":
            try: metrics['pf'] = float(lines[i+1].replace(' ', '').replace(',', ''))
            except: pass
        elif line == "Balance Drawdown Maximal:":
            try:
                val_str = lines[i+1]
                if '(' in val_str and '%)' in val_str:
                    metrics['max_dd_pct'] = float(val_str.split('(')[1].split('%')[0])
            except: pass
        elif line == "Total Trades:":
            try: metrics['total_trades'] = int(lines[i+1])
            except: pass
        elif line == "Profit Trades (% of total):":
            try:
                val_str = lines[i+1]
                if '(' in val_str and '%)' in val_str:
                    metrics['win_rate'] = float(val_str.split('(')[1].split('%')[0])
            except: pass
        elif line == "Average profit trade:":
            try: metrics['avg_win'] = float(lines[i+1].replace(' ', '').replace(',', ''))
            except: pass
        elif line == "Average loss trade:":
            try: metrics['avg_loss'] = float(lines[i+1].replace(' ', '').replace(',', ''))
            except: pass
            
    return metrics

def run_user_reports_audit():
    print("="*105)
    print("AUDIT OF ALL USER-EXPORTED METATRADER 5 STRATEGY TESTER REPORTS")
    print("="*105)
    
    found_reports = []
    seen_paths = set()
    
    for search_root in SEARCH_PATHS:
        if not os.path.exists(search_root):
            continue
        for root, dirs, files in os.walk(search_root):
            for file in files:
                if file.endswith(('.html', '.htm')):
                    full_path = os.path.join(root, file)
                    if full_path in seen_paths:
                        continue
                    seen_paths.add(full_path)
                    res = parse_mt5_html_file(full_path)
                    if res and res['total_trades'] > 0:
                        found_reports.append(res)

    print(f"Total Valid MT5 Strategy Tester Reports Found: {len(found_reports)}")
    print("-" * 105)
    print(f"{'Filename / Expert':<35} | {'Trades':<8} | {'Win Rate %':<12} | {'Profit Factor':<15} | {'Net Profit USD':<16} | {'Max Drawdown %':<16} | {'Status'}")
    print("-" * 105)
    
    for r in found_reports:
        display_name = f"{r['filename']} ({r['expert']})"
        if len(display_name) > 35:
            display_name = display_name[:32] + "..."
            
        status = "PASSED MT5" if r['win_rate'] >= 45.0 and r['pf'] >= 1.40 and r['max_dd_pct'] <= 18.0 else "FAILED / WEAK"
        print(f"{display_name:<35} | {r['total_trades']:<8} | {r['win_rate']:>10.2f}% | {r['pf']:>13.2f} | ${r['net_profit']:>14.2f} | {r['max_dd_pct']:>14.2f}% | {status}")
        
    print("="*105)

if __name__ == '__main__':
    run_user_reports_audit()
