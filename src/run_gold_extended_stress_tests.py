"""
RUN GOLD EXTENDED & STRESS TEST PROTOCOL FOR CP-100000 EA
=========================================================
"""

import os, sys, shutil, subprocess, hashlib, time
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None

TERMINAL_EXE = r"C:\Program Files\XM Global MT5\terminal64.exe"
DATA_DIR = r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05"
INI_PATH = os.path.join(DATA_DIR, "generate_gold_stress_report.ini")
REPORT_PATH = os.path.join(DATA_DIR, "MQL5", "Experts", "AlphaLab", "gold_stress_report.htm")

def run_stress_test(from_date, to_date, report_name):
    print("="*115)
    print(f"RUNNING NATIVE MT5 STRESS TEST ON GOLD: Window ({from_date} to {to_date})")
    print("="*115)
    
    subprocess.run(["taskkill", "/F", "/IM", "terminal64.exe", "/T"], capture_output=True)
    time.sleep(1)
    
    rep_path = os.path.join(DATA_DIR, "MQL5", "Experts", "AlphaLab", f"{report_name}.htm")
    if os.path.exists(rep_path):
        try: os.remove(rep_path)
        except Exception: pass
        
    ini_content = f"""[Tester]
Expert=AlphaLab\\ALAB_CP100000_Master5KUltimateCrownEA.ex5
Symbol=GOLD
Period=M15
Deposit=1000
Currency=USD
Leverage=1:500
Model=4
ExecutionMode=0
Optimization=0
FromDate={from_date}
ToDate={to_date}
Report=MQL5\\Experts\\AlphaLab\\{report_name}
ReplaceReport=1
ShutdownTerminal=1
"""
    with open(INI_PATH, 'w', encoding='utf-8') as f:
        f.write(ini_content)
        
    cmd_run = [TERMINAL_EXE, f"/config:{INI_PATH}"]
    proc = subprocess.Popen(cmd_run)
    proc.wait()
    
    htms = [rep_path, rep_path.replace('.htm', '.html')]
    target_htm = None
    for h in htms:
        if os.path.exists(h): target_htm = h; break
        
    if target_htm:
        print(f"PARSING STRESS TEST REPORT: {target_htm}")
        try:
            with open(target_htm, 'r', encoding='utf-16-le', errors='ignore') as f: content = f.read()
            if not content or len(content) < 100:
                with open(target_htm, 'r', encoding='utf-8', errors='ignore') as f: content = f.read()
            soup = BeautifulSoup(content, 'html.parser')
            rows = soup.find_all('tr')
            for r in rows[:35]:
                cols = [c.get_text().strip() for c in r.find_all(['td', 'th'])]
                if cols: print(f"  {' | '.join(cols)}")
        except Exception as e: print(f"Error reading report: {e}")

if __name__ == '__main__':
    # Test 1: Extended Full History 2022.05.01 to 2026.07.27
    run_stress_test("2022.05.01", "2026.07.27", "cp100000_gold_full_history")
