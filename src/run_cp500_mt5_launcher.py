"""
LAUNCH MT5 STRATEGY TESTER FOR CP-500 MASTER FLAGSHIP
======================================================
"""

import os, sys, subprocess

sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None

TERMINAL_EXE = r"C:\Program Files\XM Global MT5\terminal64.exe"
DATA_DIR = r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05"
INI_PATH = os.path.join(DATA_DIR, "run_cp500_gui.ini")

ini_content = f"""[Tester]
Expert=AlphaLab\\ALAB_CP500_MasterFlagshipEA.ex5
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
Visual=1
"""

def launch_cp500_gui():
    with open(INI_PATH, 'w', encoding='utf-8') as f:
        f.write(ini_content)
    cmd = [TERMINAL_EXE, f"/config:{INI_PATH}"]
    subprocess.Popen(cmd)
    print("MT5 Strategy Tester window launched on desktop with CP-500 Master Flagship pre-loaded!")

if __name__ == '__main__':
    launch_cp500_gui()
