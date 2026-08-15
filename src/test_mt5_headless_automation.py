"""
MT5 AUTOMATED HEADLESS STRATEGY TESTER ENGINE (5-MINUTE WAIT FOR TICK BACKTEST)
=================================================================================
Launches XM Global MT5 in background, waiting up to 300s for 4-year Real-Tick backtest to finish.
"""

import os, sys, subprocess, time

sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None

TERMINAL_EXE = r"C:\Program Files\XM Global MT5\terminal64.exe"
DATA_DIR = r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05"
INI_PATH = os.path.join(DATA_DIR, "auto_test_cp171.ini")
REPORT_PATH = os.path.join(DATA_DIR, "MQL5", "Experts", "AlphaLab", "auto_cp171_report.html")

def test_headless_mt5_full():
    print("="*105)
    print("AUTOMATED MT5 STRATEGY TESTER EXECUTION (WAITING FOR 203M TICK BACKTEST TO FINISH)")
    print("="*105)
    
    ini_content = f"""[Common]
Server=XMGlobal-MT5

[Tester]
Expert=Experts\\AlphaLab\\alphalab\\ALAB_CP171_IndependentBBExpansion.ex5
Symbol=GOLD
Period=M15
Deposit=1000
Currency=USD
Leverage=1:500
Model=1
ExecutionMode=0
Optimization=0
FromDate=2022.05.01
ToDate=2026.07.27
Report={REPORT_PATH}
ReplaceReport=1
ShutdownTerminal=1
"""
    with open(INI_PATH, 'w', encoding='utf-16-le') as f:
        f.write(ini_content)
        
    print(f"Created Config INI: {INI_PATH}")
    print(f"Report Target Path: {REPORT_PATH}")
    
    ps_command = f'Start-Process -FilePath "{TERMINAL_EXE}" -ArgumentList "/config:`"{INI_PATH}`"" -PassThru'
    res = subprocess.run(["powershell", "-Command", ps_command], capture_output=True, text=True)
    print("PowerShell Process Launched:", res.stdout.strip())
    
    print("Waiting for MT5 Strategy Tester execution (up to 300s)...")
    start_t = time.time()
    found = False
    
    for sec in range(1, 301):
        if os.path.exists(REPORT_PATH) and os.path.getsize(REPORT_PATH) > 500:
            found = True
            print(f"-> HTML Report generated successfully at t={sec}s!")
            break
        if sec % 10 == 0:
            print(f"   [{sec}s] Backtesting 203M Ticks in progress...")
        time.sleep(1)
        
    if found:
        print(f"\nSUCCESS! MT5 Strategy Tester generated HTML report ({os.path.getsize(REPORT_PATH)} bytes):")
        print(f"File Path: {REPORT_PATH}")
    else:
        print("\n[NOTE] Check if MT5 is currently open in background or requires user login.")
        
    print("="*105)

if __name__ == '__main__':
    test_headless_mt5_full()
