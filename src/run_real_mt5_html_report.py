"""
RUN REAL NATIVE MT5 TESTER AND CAPTURE OFFICIAL HTML REPORT
===========================================================
"""

import os, sys, time, subprocess, glob
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None

TERMINAL_EXE = r"C:\Program Files\XM Global MT5\terminal64.exe"
DATA_DIR = r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05"
INI_PATH = os.path.join(DATA_DIR, "generate_mt5_report.ini")
TARGET_REPORT_PATH = os.path.join(DATA_DIR, "MQL5", "Experts", "AlphaLab", "cp500_report.html")

def generate_report():
    print("="*105)
    print("EXECUTING REAL NATIVE MT5 STRATEGY TESTER TO GENERATE OFFICIAL HTML REPORT")
    print("="*105)
    
    if os.path.exists(TARGET_REPORT_PATH):
        try: os.remove(TARGET_REPORT_PATH)
        except Exception: pass

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
Report=MQL5\\Experts\\AlphaLab\\cp500_report
ReplaceReport=1
ShutdownTerminal=1
"""
    with open(INI_PATH, 'w', encoding='utf-8') as f:
        f.write(ini_content)
        
    cmd = [TERMINAL_EXE, f"/config:{INI_PATH}"]
    print(f"Executing MT5 Terminal process... {cmd}")
    proc = subprocess.Popen(cmd)
    proc.wait()
    
    # Check if report generated
    if os.path.exists(TARGET_REPORT_PATH):
        print("="*105)
        print(f"OFFICIAL MT5 HTML REPORT GENERATED: {TARGET_REPORT_PATH}")
        print("="*105)
        
        with open(TARGET_REPORT_PATH, 'r', encoding='utf-16-le', errors='ignore') as f:
            content = f.read()
            
        soup = BeautifulSoup(content, 'html.parser')
        rows = soup.find_all('tr')
        report_data = {}
        for r in rows:
            cols = [c.get_text().strip() for c in r.find_all(['td', 'th'])]
            if len(cols) >= 2:
                for i in range(0, len(cols) - 1, 2):
                    key = cols[i].replace(':', '')
                    val = cols[i+1]
                    if key and val:
                        report_data[key] = val
                        
        print("\nOFFICIAL MT5 STRATEGY TESTER HTML REPORT METRICS:")
        for k, v in report_data.items():
            print(f"  [MT5 HTML REPORT] {k} -> {v}")
            
        return TARGET_REPORT_PATH
    else:
        print("ERROR: Native MT5 Report file not generated.")
        return None

if __name__ == '__main__':
    generate_report()
