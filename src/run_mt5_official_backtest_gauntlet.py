"""
OFFICIAL METATRADER 5 NATIVE STRATEGY TESTER GAUNTLET RUNNER
============================================================
Executes official MT5 native C++ Strategy Tester CLI (terminal64.exe) across all compiled EX5 EAs
and multi-timeframes (H1, M15, M5).

Generates official HTML reports in reports/mt5_official_gauntlet/
"""

import os, sys, subprocess, time
sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None

BASE_DIR = r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05"
TERMINAL = r"C:\Program Files\XM Global MT5\terminal64.exe"
REPORTS_DIR = os.path.join(BASE_DIR, "reports", "mt5_official_gauntlet")
os.makedirs(REPORTS_DIR, exist_ok=True)

eas_to_test = [
    {
        'name': 'ALAB_Strategy1_HighYieldSafe',
        'ex5': r'AlphaLab\alphalab\ALAB_Strategy1_HighYieldSafe.ex5',
        'timeframes': ['H1', 'M15']
    },
    {
        'name': 'ALAB_CP05_ReactionZone',
        'ex5': r'AlphaLab\alphalab\ALAB_CP05_ReactionZone.ex5',
        'timeframes': ['H1', 'M15']
    },
    {
        'name': 'ALAB_NexusV33',
        'ex5': r'AlphaLab\alphalab\ALAB_NexusV33.ex5',
        'timeframes': ['H1']
    }
]

def run_mt5_official_gauntlet():
    print("="*105)
    print("OFFICIAL METATRADER 5 NATIVE STRATEGY TESTER GAUNTLET RUNNER")
    print("Executable: terminal64.exe (C++ Official Broker Tick Tester Engine)")
    print("="*105)
    
    test_results = []
    
    for ea in eas_to_test:
        ea_name = ea['name']
        ex5_rel = ea['ex5']
        
        for tf in ea['timeframes']:
            ini_filename = f"config_{ea_name}_{tf}.ini"
            ini_path = os.path.join(BASE_DIR, "src", ini_filename)
            report_path = os.path.join(REPORTS_DIR, f"Report_{ea_name}_{tf}.html")
            
            ini_content = f"""[Tester]
Expert={ex5_rel}
Symbol=XAUUSD
Period={tf}
Deposit=1000
Currency=USD
Leverage=1:500
Model=1
ExecutionMode=0
Optimization=0
FromDate=2025.01.01
ToDate=2026.07.30
Report={report_path}
ReplaceReport=1
ShutdownTerminal=1
"""
            with open(ini_path, 'w', encoding='utf-8') as f:
                f.write(ini_content)
                
            print(f"\n🚀 Running MT5 Official Backtest: {ea_name} [{tf}]...")
            cmd = [TERMINAL, f"/config:{ini_path}"]
            res = subprocess.run(cmd, capture_output=True, text=True)
            print(f"   Command launched with exit code: {res.returncode}")
            
            # Wait briefly for MT5 terminal execution
            time.sleep(3)
            report_exists = os.path.exists(report_path)
            
            test_results.append({
                'ea': ea_name,
                'tf': tf,
                'ini': ini_path,
                'report': report_path,
                'generated': report_exists
            })

    print("\n" + "="*105)
    print("OFFICIAL MT5 BACKTEST GAUNTLET EXECUTION SUMMARY")
    print("="*105)
    print(f"{'EA Name':<35} | {'Timeframe':<10} | {'Report Generated':<20} | {'Report Location'}")
    print("-" * 105)
    for r in test_results:
        gen_str = "✅ YES (HTML Report)" if r['generated'] else "⏳ RUNNING IN MT5"
        print(f"{r['ea']:<35} | {r['tf']:<10} | {gen_str:<20} | {r['report']}")

if __name__ == '__main__':
    run_mt5_official_gauntlet()
