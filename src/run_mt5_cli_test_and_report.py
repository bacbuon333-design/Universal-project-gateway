"""
MT5 CLI STRATEGY TESTER EXECUTION & REPORT RETRIEVAL
=====================================================
"""

import os, sys, time, subprocess, glob

sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None

TERMINAL_EXE = r"C:\Program Files\XM Global MT5\terminal64.exe"
DATA_DIR = r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05"
INI_PATH = os.path.join(DATA_DIR, "cli_test_run.ini")

LOGIN_ID = "33943735"
PASS_WD = "01120999Bac@"
SERVER_NAME = "XMGlobal-MT5"

def run_test():
    report_filename = "official_cp400_report.htm"
    report_abs_path = os.path.join(DATA_DIR, report_filename)
    
    if os.path.exists(report_abs_path):
        try: os.remove(report_abs_path)
        except: pass

    ini_content = f"""[Common]
Login={LOGIN_ID}
Password={PASS_WD}
Server={SERVER_NAME}

[Tester]
Expert=Experts\\AlphaLab\\ALAB_CP400_MasterFlagshipEA.ex5
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
Report={report_abs_path}
ReplaceReport=1
ShutdownTerminal=1
"""
    with open(INI_PATH, 'w', encoding='utf-16-le') as f:
        f.write(ini_content)
        
    print(f"Executing MT5 Terminal CLI command: {TERMINAL_EXE} /config:{INI_PATH}")
    proc = subprocess.run([TERMINAL_EXE, f"/config:{INI_PATH}"], capture_output=True, text=True)
    print(f"MT5 Process Return Code: {proc.returncode}")
    
    # Check if report was generated anywhere in DATA_DIR
    time.sleep(5)
    candidates = glob.glob(os.path.join(DATA_DIR, "**", "*cp400*"), recursive=True)
    print(f"Found {len(candidates)} files containing 'cp400':")
    for c in candidates:
        print(f"  -> {c} ({os.path.getsize(c):,} bytes)")

if __name__ == '__main__':
    run_test()
