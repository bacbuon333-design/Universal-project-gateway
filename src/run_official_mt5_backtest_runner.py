"""
OFFICIAL AUTOMATED MT5 BACKTEST RUNNER (REAL TICKS MODE - MODEL 0)
===================================================================
Runs MetaTrader 5 Strategy Tester in CLI mode with Model=0 (Every Tick Based on Real Ticks),
parses official generated HTML report, and extracts true MT5 execution metrics.
"""

import os, sys, time, subprocess
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None

TERMINAL_EXE = r"C:\Program Files\XM Global MT5\terminal64.exe"
DATA_DIR = r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05"
INI_PATH = os.path.join(DATA_DIR, "official_mt5_run.ini")
REPORT_PATH = os.path.join(DATA_DIR, "reports", "official_mt5_cp400_report.html")

os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)

def run_mt5_official_backtest():
    print("="*105)
    print("RUNNING OFFICIAL NATIVE MT5 STRATEGY TESTER (MODEL=0 EVERY TICK REAL TICKS)")
    print("Target EA   : Experts\\AlphaLab\\alphalab\\ALAB_CP400_MasterFlagshipEA.ex5")
    print("="*105)
    
    if os.path.exists(REPORT_PATH):
        try: os.remove(REPORT_PATH)
        except Exception: pass

    ini_content = f"""[Tester]
Expert=AlphaLab\\alphalab\\ALAB_CP400_MasterFlagshipEA.ex5
Symbol=GOLD
Period=M15
Deposit=1000
Currency=USD
Leverage=1:500
Model=0
ExecutionMode=0
Optimization=0
FromDate=2022.05.01
ToDate=2026.07.27
Report={REPORT_PATH}
ReplaceReport=1
ShutdownTerminal=1
"""
    with open(INI_PATH, 'w', encoding='utf-8') as f:
        f.write(ini_content)
        
    cmd = [TERMINAL_EXE, f"/config:{INI_PATH}"]
    print(f"Launching MT5 Terminal process... {cmd}")
    proc = subprocess.Popen(cmd)
    
    start_time = time.time()
    max_wait_seconds = 240
    
    print("Waiting for MT5 Strategy Tester process to complete real-tick backtest and output HTML report...")
    while time.time() - start_time < max_wait_seconds:
        if os.path.exists(REPORT_PATH) and proc.poll() is not None:
            print(f"MT5 Process completed. Report generated at: {REPORT_PATH}")
            break
        time.sleep(3)
        
    if proc.poll() is None:
        print("Waiting for process exit...")
        proc.wait()
        
    if not os.path.exists(REPORT_PATH):
        print(f"ERROR: HTML report file not found at {REPORT_PATH}")
        return None

    return parse_mt5_html_report(REPORT_PATH)

def parse_mt5_html_report(html_path):
    print("-" * 105)
    print(f"PARSING OFFICIAL MT5 GENERATED HTML REPORT: {html_path}")
    print("-" * 105)
    
    with open(html_path, 'r', encoding='utf-16-le', errors='ignore') as f:
        content = f.read()
        
    soup = BeautifulSoup(content, 'html.parser')
    rows = soup.find_all('tr')
    report_data = {}
    for r in rows:
        cols = [c.get_text().strip() for c in r.find_all(['td', 'th'])]
        if len(cols) >= 2:
            for i in range(0, len(cols) - 1, 2):
                key = cols[i].replace(':', '')
                val = cols[i+1]
                if key and val:
                    report_data[key] = val
                    
    print("OFFICIAL MT5 STRATEGY TESTER REPORT EXTRACTED DATA:")
    for k, v in report_data.items():
        print(f"  [MT5 REAL HTML REPORT] {k} -> {v}")
            
    return report_data

if __name__ == '__main__':
    run_mt5_official_backtest()
