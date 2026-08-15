import os, sys, subprocess, time

sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None

TERMINAL_DIR = r"C:\Program Files\XM Global MT5"
TERMINAL_EXE = os.path.join(TERMINAL_DIR, "terminal64.exe")
DATA_DIR = r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05"
INI_PATH = os.path.join(DATA_DIR, "direct_test_cp171_xm.ini")
REPORT_PATH = os.path.join(DATA_DIR, "MQL5", "Experts", "AlphaLab", "direct_cp171_xm_report.html")

def run_direct_xm_mt5_backtest():
    print("="*105)
    print("DIRECTLY INVOKING XM GLOBAL METATRADER 5 TERMINAL STRATEGY TESTER (WITH CORRECT CWD)")
    print("="*105)
    
    ini_content = f"""[Tester]
Expert=Experts\\AlphaLab\\ALAB_CP171_IndependentBBExpansion.ex5
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
    print(f"Target Report Path: {REPORT_PATH}")
    
    cmd = [TERMINAL_EXE, f"/config:{INI_PATH}"]
    print(f"Executing Command: {' '.join(cmd)} in CWD: {TERMINAL_DIR}")
    
    proc = subprocess.Popen(cmd, cwd=TERMINAL_DIR)
    print("XM MT5 Terminal Process launched with PID:", proc.pid)
    
    start_t = time.time()
    while proc.poll() is None:
        elapsed = int(time.time() - start_t)
        if elapsed % 5 == 0 and elapsed > 0:
            print(f"   Waiting for XM MT5 Strategy Tester execution... ({elapsed}s elapsed)")
        if elapsed > 180: # 3 minutes timeout
            print("   Timeout reached (180s). Terminating process.")
            proc.kill()
            break
        time.sleep(1)
        
    print(f"Process finished with exit code: {proc.returncode}")
    
    if os.path.exists(REPORT_PATH):
        print(f"SUCCESS! HTML Report generated: {REPORT_PATH}")
        with open(REPORT_PATH, 'r', encoding='utf-16-le', errors='ignore') as f:
            lines = f.readlines()
        print(f"Report File Size: {os.path.getsize(REPORT_PATH)} bytes, Lines: {len(lines)}")
    else:
        print("Report HTML file was not found after execution.")
        
    print("="*105)

if __name__ == '__main__':
    run_direct_xm_mt5_backtest()
