"""
OFFICIAL METATRADER 5 COMMAND LINE BACKTEST RUNNER (BASED ON MQL5 OFFICIAL DOCS)
==================================================================================
Key discovery from official MQL5 documentation:
1. Report=filename (WITHOUT extension and WITHOUT directory path!)
2. TestDateEnable=1 must be set for date filtering to apply.
3. ShutdownTerminal=1 shuts down MT5 after report is saved to MQL5/Reports/.
"""

import os, sys, subprocess, time
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None

LOGIN_ID = "33943735"
PASS_WD = "01120999Bac@"
SERVER_NAME = "XMGlobal-MT5"

TERMINAL_DIR = r"C:\Program Files\XM Global MT5"
TERMINAL_EXE = os.path.join(TERMINAL_DIR, "terminal64.exe")
DATA_DIR = r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05"
INI_PATH = os.path.join(DATA_DIR, "mql5_official_cp171.ini")

def run_official_mql5_cli():
    print("="*105)
    print("EXECUTING OFFICIAL METATRADER 5 COMMAND-LINE BACKTEST (MQL5 DOCS COMPLIANT)")
    print("="*105)
    
    # Report name MUST BE A SIMPLE FILENAME WITHOUT EXTENSION according to MQL5 Docs
    report_name = "official_cp171_test_result"
    
    ini_content = f"""[Common]
Login={LOGIN_ID}
Password={PASS_WD}
Server={SERVER_NAME}

[Tester]
Expert=Experts\\AlphaLab\\alphalab\\ALAB_CP171_IndependentBBExpansion.ex5
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
ToDate=2026.07.27
Report={report_name}
ReplaceReport=1
ShutdownTerminal=1
"""
    with open(INI_PATH, 'w', encoding='utf-16-le') as f:
        f.write(ini_content)
        
    print(f"Created Config INI: {INI_PATH}")
    print(f"Target Report Name: {report_name}")
    
    # Execute MT5 terminal using official syntax
    cmd = [TERMINAL_EXE, f"/config:{INI_PATH}"]
    print(f"Executing: {' '.join(cmd)}")
    
    proc = subprocess.Popen(cmd, cwd=TERMINAL_DIR)
    print("MT5 Process launched with PID:", proc.pid)
    
    # Monitor for generated report file in MT5 data folder or reports folder
    print("Waiting for MT5 Strategy Tester execution...")
    start_t = time.time()
    found_path = None
    
    for sec in range(1, 180):
        # Search for report_name.html or report_name.htm in DATA_DIR
        for root, dirs, files in os.walk(DATA_DIR):
            for file in files:
                if report_name in file and file.endswith(('.html', '.htm')):
                    found_path = os.path.join(root, file)
                    print(f"-> [SUCCESS] Found MT5 HTML Report at t={sec}s: {found_path}")
                    break
            if found_path:
                break
        if found_path:
            break
        if sec % 10 == 0:
            print(f"   [{sec}s elapsed] MT5 Backtesting in progress...")
        time.sleep(1)
        
    if found_path:
        print(f"\nParsing Report File: {found_path} ({os.path.getsize(found_path)} bytes)...")
        with open(found_path, 'r', encoding='utf-16-le', errors='ignore') as f:
            content = f.read()
        soup = BeautifulSoup(content, 'html.parser')
        text_content = soup.get_text(separator='\n')
        lines = [line.strip() for line in text_content.split('\n') if line.strip()]
        for i, line in enumerate(lines[:40]):
            print(f"   {i+1:02d}: {line}")
    else:
        print("\nReport file not generated within 180s timeout.")
        
    print("="*105)

if __name__ == '__main__':
    run_official_mql5_cli()
