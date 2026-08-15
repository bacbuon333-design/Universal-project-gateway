"""
AUTOMATED MT5 STRATEGY TESTER LAUNCHER FOR CP-350
===============================================
Launches XM Global MT5 Strategy Tester pre-configured with CP-350.
"""

import os, sys, subprocess

sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None

LOGIN_ID = "33943735"
PASS_WD = "01120999Bac@"
SERVER_NAME = "XMGlobal-MT5"

TERMINAL_EXE = r"C:\Program Files\XM Global MT5\terminal64.exe"
DATA_DIR = r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05"
INI_PATH = os.path.join(DATA_DIR, "cp350_test.ini")

def launch_cp350_mt5():
    ini_content = f"""[Common]
Login={LOGIN_ID}
Password={PASS_WD}
Server={SERVER_NAME}

[Tester]
Expert=Experts\\AlphaLab\\ALAB_CP350_MT5HyperGrowth.ex5
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
Report=cp350_mt5_report
ReplaceReport=1
ShutdownTerminal=1
"""
    with open(INI_PATH, 'w', encoding='utf-16-le') as f:
        f.write(ini_content)
        
    cmd_str = f'cmd.exe /c start "" "{TERMINAL_EXE}" /config:"{INI_PATH}"'
    subprocess.run(cmd_str, shell=True)
    print("MT5 Strategy Tester window launched on desktop with CP-350 pre-loaded!")

if __name__ == '__main__':
    launch_cp350_mt5()
