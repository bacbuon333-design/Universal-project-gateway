"""
BUILD AND EXECUTE ALPHALAB R25 M15 HIGH-DENSITY MASTER EA UNDER NATIVE MT5 MODEL=4 REAL-TICK PROTOCOL
====================================================================================================
"""

import os, sys, shutil, subprocess, hashlib, time
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None

TERMINAL_EXE = r"C:\Program Files\XM Global MT5\terminal64.exe"
METAEDITOR_EXE = r"C:\Program Files\XM Global MT5\metaeditor64.exe"
DATA_DIR = r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05"
MQL5_SRC = os.path.join(DATA_DIR, "MQL5", "Experts", "AlphaLab", "CleanRoom", "AlphaLabR25_M15HighDensityMasterEA.mq5")
LOG_PATH = MQL5_SRC.replace('.mq5', '.log')
INI_PATH = os.path.join(DATA_DIR, "generate_r25_gold_exec_report.ini")
TARGET_REPORT_PATH = os.path.join(DATA_DIR, "MQL5", "Experts", "AlphaLab", "r25_gold_exec_report.htm")

TERMINAL_ROOTS = [
    r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05",
    r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075",
    r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\F762D69EEEA9B4430D7F17C82167C844"
]

def run_protocol():
    print("="*115)
    print("STEP 1: TERMINATING RUNNING TERMINAL PROCESSES")
    print("="*115)
    subprocess.run(["taskkill", "/F", "/IM", "terminal64.exe", "/T"], capture_output=True)
    time.sleep(2)
    
    print("="*115)
    print("STEP 2: COMPILING AlphaLabR25_M15HighDensityMasterEA.mq5 VIA METAEDITOR CLI")
    print("="*115)
    
    cmd_compile = [METAEDITOR_EXE, f"/compile:{MQL5_SRC}", f"/log:{LOG_PATH}"]
    subprocess.run(cmd_compile, capture_output=True, text=True)
    
    ex5_src = MQL5_SRC.replace('.mq5', '.ex5')
    if not os.path.exists(ex5_src):
        print("COMPILATION FAILED! Check log.")
        return
        
    with open(LOG_PATH, 'r', encoding='utf-16-le', errors='ignore') as f:
        log_txt = f.read()
    print(f"MetaEditor Log Output:\n{log_txt[-300:]}")
    
    for root in TERMINAL_ROOTS:
        dest_dir = os.path.join(root, "MQL5", "Experts", "AlphaLab", "CleanRoom")
        os.makedirs(dest_dir, exist_ok=True)
        dest_file = os.path.join(dest_dir, "AlphaLabR25_M15HighDensityMasterEA.ex5")
        for attempt in range(5):
            try:
                shutil.copy2(ex5_src, dest_file)
                print(f"Synced EX5 -> {dest_file}")
                break
            except Exception:
                time.sleep(1)
                
    print("="*115)
    print("STEP 3: LAUNCHING NATIVE MT5 TESTER (MODEL=4 REAL TICKS)")
    print("="*115)
    
    if os.path.exists(TARGET_REPORT_PATH):
        try: os.remove(TARGET_REPORT_PATH)
        except Exception: pass
        
    ini_content = f"""[Tester]
Expert=AlphaLab\\CleanRoom\\AlphaLabR25_M15HighDensityMasterEA.ex5
Symbol=GOLD
Period=M15
Deposit=1000
Currency=USD
Leverage=1:500
Model=4
ExecutionMode=0
Optimization=0
FromDate=2022.05.01
ToDate=2026.07.27
Report=MQL5\\Experts\\AlphaLab\\r25_gold_exec_report
ReplaceReport=1
ShutdownTerminal=1

[TesterInputs]
InpBaseRiskPct=0.052
InpAccelStepMult=2.45
InpDDBrakeThreshPct=0.060
InpDDBrakeRiskMult=0.15
InpTakeProfitATRMult=3.60
InpStopLossATRMult=1.15
InpMaxDrawdownLimit=0.20
InpMagicNumber=202625001
InpTradeComment=ALAB_R25_M15_5K
"""
    with open(INI_PATH, 'w', encoding='utf-8') as f:
        f.write(ini_content)
        
    cmd_run = [TERMINAL_EXE, f"/config:{INI_PATH}"]
    print(f"Executing MT5 process: {cmd_run}")
    proc = subprocess.Popen(cmd_run)
    proc.wait()

if __name__ == '__main__':
    run_protocol()
