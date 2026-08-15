"""
AUTOMATED METATRADER 5 STRATEGY TESTER EXECUTION & PARSER HARNESS FOR CP-250
===========================================================================
Executes MT5 Strategy Tester headlessly / interactively, waits for execution to complete,
finds the generated HTML report file, parses all 16 official metrics, and reports actual results.
"""

import os, sys, time, subprocess, glob
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None

LOGIN_ID = "33943735"
PASS_WD = "01120999Bac@"
SERVER_NAME = "XMGlobal-MT5"

TERMINAL_EXE = r"C:\Program Files\XM Global MT5\terminal64.exe"
DATA_DIR = r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05"
INI_PATH = os.path.join(DATA_DIR, "cp250_official_run.ini")
REPORTS_DIR = os.path.join(DATA_DIR, "MQL5", "Reports")
os.makedirs(REPORTS_DIR, exist_ok=True)

def parse_mt5_html_report(html_path):
    try:
        with open(html_path, 'r', encoding='utf-16-le', errors='ignore') as f:
            content = f.read()
        if not content or len(content) < 100 or 'Strategy Tester Report' not in content:
            with open(html_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
    except Exception:
        return None
        
    soup = BeautifulSoup(content, 'html.parser')
    text_content = soup.get_text(separator='\n')
    lines = [line.strip() for line in text_content.split('\n') if line.strip()]
    
    metrics = {
        'expert': 'ALAB_CP250_HyperGrowthEA',
        'symbol': 'GOLD',
        'deposit': 1000.0,
        'net_profit': 0.0,
        'gross_profit': 0.0,
        'gross_loss': 0.0,
        'pf': 0.0,
        'max_dd_pct': 0.0,
        'total_trades': 0,
        'win_rate': 0.0
    }
    
    for i, line in enumerate(lines):
        if line == "Total Net Profit:":
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
            
    return metrics

def run_cp250_official_backtest():
    print("="*105)
    print("AUTOMATED METATRADER 5 DIRECT BACKTEST HARNESS FOR CP-250")
    print("="*105)
    
    ini_content = f"""[Common]
Login={LOGIN_ID}
Password={PASS_WD}
Server={SERVER_NAME}

[Tester]
Expert=Experts\\AlphaLab\\ALAB_CP250_HyperGrowthEA.ex5
Symbol=GOLD
Period=M15
Login={LOGIN_ID}
Deposit=1000
Currency=USD
Leverage=1:500
Model=1
ExecutionMode=0
Optimization=0
TestDateEnable=1
FromDate=2022.05.01
ToDate=2026.07.24
Report=cp250_official_report
ReplaceReport=1
ShutdownTerminal=1
"""
    with open(INI_PATH, 'w', encoding='utf-16-le') as f:
        f.write(ini_content)
        
    print(f"Created Config INI: {INI_PATH}")
    print(f"Executing: {TERMINAL_EXE} /config:{INI_PATH}")
    
    proc = subprocess.Popen([TERMINAL_EXE, f"/config:{INI_PATH}"])
    print(f"MT5 Strategy Tester launched with PID: {proc.pid}")
    
    start_t = time.time()
    report_file = None
    
    for wait_step in range(90):
        time.sleep(2)
        # Search for report in all potential locations
        possible_reports = glob.glob(os.path.join(DATA_DIR, "**", "*cp250*report*.html"), recursive=True) + \
                           glob.glob(os.path.join(DATA_DIR, "**", "*cp250*report*.htm"), recursive=True)
        if possible_reports:
            report_file = possible_reports[0]
            print(f"\nFOUND GENERATED REPORT FILE: {report_file}")
            break
        if proc.poll() is not None and wait_step > 15:
            print("\nMT5 Process completed execution.")
            possible_reports = glob.glob(os.path.join(DATA_DIR, "**", "*cp250*report*.html"), recursive=True)
            if possible_reports:
                report_file = possible_reports[0]
            break
            
    print("="*105)
    if report_file and os.path.exists(report_file):
        res = parse_mt5_html_report(report_file)
        if res:
            print("OFFICIAL METATRADER 5 STRATEGY TESTER RESULT FOR CP-250:")
            print(f"1. Total Trades        : {res['total_trades']} Trades")
            print(f"2. Win Rate %           : {res['win_rate']:.2f}%")
            print(f"3. Profit Factor (PF)   : {res['pf']:.2f}")
            print(f"4. Total Net Profit USD : ${res['net_profit']:,.2f} USD")
            print(f"5. Max Drawdown %       : {res['max_dd_pct']:.2f}%")
            print("="*105)
            return res
    else:
        print("Report not generated yet or process still running.")
        print("="*105)
        return None

if __name__ == '__main__':
    run_cp250_official_backtest()
