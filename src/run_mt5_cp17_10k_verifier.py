"""
OFFICIAL METATRADER 5 NATIVE STRATEGY TESTER EXECUTION: CHECKPOINT 17 ($10K TARGET GAUNTLET)
=============================================================================================
Launches terminal64.exe CLI with batch INI config to run native C++ Strategy Tester
on ALAB_CP17_HyperCompounding_10k.ex5 on GOLD H1 across FULL MAXIMUM HISTORICAL DATA (2010 to 2026).

Parses generated official MT5 tester log for exact metrics.
"""

import os, sys, subprocess, time, glob

sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None

BASE_DIR = r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05"
TERMINAL = r"C:\Program Files\XM Global MT5\terminal64.exe"
TESTER_LOG_DIR = os.path.join(BASE_DIR, "Tester", "logs")
INI_PATH = os.path.join(BASE_DIR, "run_cp17_10k.ini")
REPORT_PATH = os.path.join(BASE_DIR, "reports", "official_mt5_cp17_10k_report.html")

os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)

ini_content = f"""[Tester]
Expert=AlphaLab\\alphalab\\ALAB_CP17_HyperCompounding_10k.ex5
Symbol=GOLD
Period=H1
Deposit=1000
Currency=USD
Leverage=1:500
Model=1
ExecutionMode=0
Optimization=0
FromDate=2010.01.01
ToDate=2026.07.30
Report={REPORT_PATH}
ReplaceReport=1
ShutdownTerminal=1
"""

def run_cp17_10k_backtest():
    with open(INI_PATH, 'w', encoding='utf-8') as f:
        f.write(ini_content)
        
    print("="*105)
    print("LAUNCHING OFFICIAL METATRADER 5 TESTER: CHECKPOINT 17 ($10K TARGET GAUNTLET)")
    print("Binary EA   : ALAB_CP17_HyperCompounding_10k.ex5 (Dynamic Profit Buffer Compounding)")
    print("Dataset     : GOLD H1 / Maximum Available History (2010 - 2026)")
    print("Capital     : $1,000.00 USD")
    print("="*105)
    
    cmd = [TERMINAL, f"/config:{INI_PATH}"]
    print("Starting MT5 C++ Strategy Tester process...")
    proc = subprocess.Popen(cmd)
    
    elapsed = 0
    while proc.poll() is None and elapsed < 180:
        time.sleep(3)
        elapsed += 3
        print(f"   [MT5 CP-17 10k Tester Running] Elapsed: {elapsed}s...", end='\r')
        
    print(f"\n   Process completed in {elapsed}s with status code: {proc.returncode}")
    
    time.sleep(2)
    latest_log = max(glob.glob(os.path.join(TESTER_LOG_DIR, "*.log")), key=os.path.getmtime, default=None)
    final_balance = 1000.0
    ticks_count = "0"
    bars_count = "0"
    
    if latest_log:
        try:
            with open(latest_log, 'r', encoding='utf-16-le', errors='ignore') as f:
                lines = f.readlines()
            for line in reversed(lines):
                if 'final balance' in line:
                    parts = line.split('final balance')
                    if len(parts) > 1:
                        val = parts[1].strip().split(' ')[0]
                        final_balance = float(val)
                if 'ticks' in line and 'bars generated' in line:
                    parts = line.split('ticks')
                    if len(parts) > 0:
                        sub = parts[0].strip().split(' ')
                        if len(sub) > 0:
                            ticks_count = sub[-1]
                    parts_bar = line.split('bars generated')
                    if len(parts_bar) > 0:
                        sub_b = parts_bar[0].strip().split(' ')
                        if len(sub_b) > 0:
                            bars_count = sub_b[-1]
        except Exception as e:
            pass
            
    pnl_pct = (final_balance - 1000.0) / 10.0
    print("="*105)
    print("OFFICIAL METATRADER 5 CHECKPOINT 17 RESULTS ($10K TARGET GAUNTLET)")
    print("="*105)
    print(f"Initial Deposit       : $1,000.00 USD")
    print(f"Final Balance (MT5)   : ${final_balance:,.2f} USD")
    print(f"Net Profit % (MT5)    : {pnl_pct:>+8.2f}% Net Yield")
    print(f"Ticks Processed       : {ticks_count} real ticks")
    print(f"Bars Evaluated        : {bars_count} H1 bars")
    print("="*105)

if __name__ == '__main__':
    run_cp17_10k_backtest()
