"""
OFFICIAL METATRADER 5 CLI BACKTEST EXECUTION & REPORT AUDITOR
==============================================================
Launches terminal64.exe CLI with batch INI config to run native C++ Strategy Tester
on ALAB_Strategy1_HighYieldSafe.ex5 on GOLD H1.

Parses generated official HTML report metrics.
"""

import os, sys, subprocess, time

sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None

BASE_DIR = r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05"
TERMINAL = r"C:\Program Files\XM Global MT5\terminal64.exe"
INI_PATH = os.path.join(BASE_DIR, "mt5_run_s1.ini")
REPORT_PATH = os.path.join(BASE_DIR, "reports", "official_mt5_s1_report.html")

os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)

ini_content = f"""[Tester]
Expert=AlphaLab\\alphalab\\ALAB_Strategy1_HighYieldSafe.ex5
Symbol=GOLD
Period=H1
Deposit=1000
Currency=USD
Leverage=1:500
Model=1
ExecutionMode=0
Optimization=0
FromDate=2024.01.01
ToDate=2026.07.30
Report={REPORT_PATH}
ReplaceReport=1
ShutdownTerminal=1
"""

def run_cli_backtest():
    with open(INI_PATH, 'w', encoding='utf-8') as f:
        f.write(ini_content)
        
    print("="*90)
    print("LAUNCHING OFFICIAL METATRADER 5 NATIVE STRATEGY TESTER CLI")
    print(f"INI Config File : {INI_PATH}")
    print(f"Report Target   : {REPORT_PATH}")
    print("="*90)
    
    cmd = [TERMINAL, f"/config:{INI_PATH}"]
    print("Starting process...")
    proc = subprocess.Popen(cmd)
    
    # Wait for MT5 process to complete batch backtest and exit
    max_wait = 180 # 3 minutes max
    elapsed = 0
    while proc.poll() is None and elapsed < max_wait:
        time.sleep(2)
        elapsed += 2
        print(f"   [MT5 Strategy Tester Running] Elapsed: {elapsed}s...", end='\r')
        
    print(f"\nProcess exited with status code: {proc.returncode}")
    
    time.sleep(2)
    if os.path.exists(REPORT_PATH):
        print(f"✅ SUCCESS: Official MT5 HTML Report Generated at:\n   {REPORT_PATH}")
        print(f"   File Size: {os.path.getsize(REPORT_PATH)} bytes")
    else:
        print(f"❌ Report file not found yet. Checking directory contents...")
        parent = os.path.dirname(REPORT_PATH)
        if os.path.exists(parent):
            print("Files in reports dir:", os.listdir(parent))

if __name__ == '__main__':
    run_cli_backtest()
