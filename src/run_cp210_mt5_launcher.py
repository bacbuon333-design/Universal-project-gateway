"""
AUTOMATED MT5 STRATEGY TESTER LAUNCHER FOR CP-210
===============================================
Launches XM Global MT5 Strategy Tester pre-configured with CP-210 INI file.
"""

import os, sys, subprocess, time

sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None

LOGIN_ID = "33943735"
PASS_WD = "01120999Bac@"
SERVER_NAME = "XMGlobal-MT5"

TERMINAL_DIR = r"C:\Program Files\XM Global MT5"
TERMINAL_EXE = os.path.join(TERMINAL_DIR, "terminal64.exe")
DATA_DIR = r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05"
INI_PATH = os.path.join(DATA_DIR, "cp210_test.ini")
REPORT_PATH = os.path.join(DATA_DIR, "MQL5", "Experts", "AlphaLab", "cp210_mt5_report.html")

def launch_cp210_mt5():
    print("="*105)
    print("LAUNCHING METATRADER 5 STRATEGY TESTER FOR CP-210")
    print("="*105)
    
    ini_content = f"""[Common]
Login={LOGIN_ID}
Password={PASS_WD}
Server={SERVER_NAME}

[Tester]
Expert=Experts\\AlphaLab\\alphalab\\ALAB_CP210_SpreadResilientTrend.ex5
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
Report=cp210_mt5_report
ReplaceReport=1
ShutdownTerminal=1
"""
    with open(INI_PATH, 'w', encoding='utf-16-le') as f:
        f.write(ini_content)
        
    print(f"Created Config INI: {INI_PATH}")
    print(f"Executing: {TERMINAL_EXE} /config:{INI_PATH}")
    
    # Launch via Windows cmd start to open interactive window
    cmd_str = f'cmd.exe /c start "" "{TERMINAL_EXE}" /config:"{INI_PATH}"'
    subprocess.run(cmd_str, shell=True)
    
    print("\nMT5 Application window launched on your desktop screen!")
    print("="*105)

if __name__ == '__main__':
    launch_cp210_mt5()
