"""
TEST US100CASH NATIVE HISTORY QUALITY AND REAL TICKS
===================================================
"""

import os, sys, subprocess, time
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None

TERMINAL_EXE = r"C:\Program Files\XM Global MT5\terminal64.exe"
DATA_DIR = r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05"
INI_PATH = os.path.join(DATA_DIR, "generate_us100_quality.ini")
TARGET_REPORT_PATH = os.path.join(DATA_DIR, "MQL5", "Experts", "AlphaLab", "us100_quality_report.html")

def test_us100():
    print("="*105)
    print("TESTING NATIVE MT5 MODEL=4 HISTORY QUALITY FOR US100Cash")
    print("="*105)
    
    subprocess.run(["taskkill", "/F", "/IM", "terminal64.exe", "/T"], capture_output=True)
    time.sleep(1)
    
    if os.path.exists(TARGET_REPORT_PATH):
        try: os.remove(TARGET_REPORT_PATH)
        except Exception: pass
        
    ini_content = f"""[Tester]
Expert=AlphaLab\\ALAB_CP950_DiagnosticEA.ex5
Symbol=US100Cash
Period=M15
Deposit=1000
Currency=USD
Leverage=1:500
Model=4
ExecutionMode=0
Optimization=0
FromDate=2022.05.01
ToDate=2026.07.27
Report=MQL5\\Experts\\AlphaLab\\us100_quality_report
ReplaceReport=1
ShutdownTerminal=1
"""
    with open(INI_PATH, 'w', encoding='utf-8') as f:
        f.write(ini_content)
        
    cmd_run = [TERMINAL_EXE, f"/config:{INI_PATH}"]
    proc = subprocess.Popen(cmd_run)
    proc.wait()
    
    report_file = TARGET_REPORT_PATH.replace('.html', '.htm')
    if os.path.exists(report_file):
        print(f"REPORT FOUND AT: {report_file}")
        with open(report_file, 'r', encoding='utf-16-le', errors='ignore') as f:
            content = f.read()
        soup = BeautifulSoup(content, 'html.parser')
        rows = soup.find_all('tr')
        for r in rows[:25]:
            cols = [c.get_text().strip() for c in r.find_all(['td', 'th'])]
            if cols:
                print(f"  {' | '.join(cols)}")
    else:
        print(f"Report file not generated at {report_file}")

if __name__ == '__main__':
    test_us100()
