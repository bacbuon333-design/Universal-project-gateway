import os, sys
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None

SEARCH_DIRS = [
    r"C:\Users\gugul\AppData\Roaming\MetaQuotes",
    r"C:\Users\gugul\Downloads",
    r"C:\Users\gugul\Desktop"
]

def find_and_parse_all_mt5_reports():
    print("="*105)
    print("SEARCHING AND PARSING ALL OFFICIAL MT5 STRATEGY TESTER HTML REPORTS")
    print("="*105)
    
    found_reports = []
    
    for search_root in SEARCH_DIRS:
        if not os.path.exists(search_root):
            continue
        for root, dirs, files in os.walk(search_root):
            for file in files:
                if file.endswith(('.html', '.htm')):
                    full_path = os.path.join(root, file)
                    try:
                        with open(full_path, 'r', encoding='utf-16-le', errors='ignore') as f:
                            content = f.read()
                        if 'Strategy Tester Report' in content or 'Symbol:' in content:
                            found_reports.append((full_path, content))
                        else:
                            with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                                content = f.read()
                            if 'Strategy Tester Report' in content or 'Symbol:' in content:
                                found_reports.append((full_path, content))
                    except Exception as e:
                        pass

    print(f"Found {len(found_reports)} official MT5 Strategy Tester report files.")
    print("-" * 105)
    
    for path, content in found_reports:
        soup = BeautifulSoup(content, 'html.parser')
        text_content = soup.get_text(separator='\n')
        lines = [line.strip() for line in text_content.split('\n') if line.strip()]
        
        ea_name = "Unknown"
        profit = 0.0
        pf = 0.0
        win_rate = 0.0
        max_dd = 0.0
        trades = 0
        
        for i, line in enumerate(lines):
            if line == "Expert:": ea_name = lines[i+1]
            elif line == "Total Net Profit:":
                try: profit = float(lines[i+1].replace(' ', '').replace(',', ''))
                except: pass
            elif line == "Profit Factor:":
                try: pf = float(lines[i+1].replace(' ', '').replace(',', ''))
                except: pass
            elif line == "Balance Drawdown Maximal:":
                try:
                    val_str = lines[i+1]
                    if '(' in val_str and '%)' in val_str:
                        max_dd = float(val_str.split('(')[1].split('%')[0])
                except: pass
            elif line == "Total Trades:":
                try: trades = int(lines[i+1])
                except: pass
            elif line == "Profit Trades (% of total):":
                try:
                    val_str = lines[i+1]
                    if '(' in val_str and '%)' in val_str:
                        win_rate = float(val_str.split('(')[1].split('%')[0])
                except: pass
                
        print(f"File Path   : {path}")
        print(f"Expert Name : {ea_name}")
        print(f"Total Trades: {trades} trades | Win Rate: {win_rate:.2f}% | Profit Factor: {pf:.2f} | Net Profit: ${profit:,.2f} | MaxDD: {max_dd:.2f}%")
        print("-" * 105)

if __name__ == '__main__':
    find_and_parse_all_mt5_reports()
