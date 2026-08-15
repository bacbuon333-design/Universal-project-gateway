"""
AUTONOMOUS RESEARCH LOOP V40 - HIGH-ACCEL SMOOTH DIAGONAL ENGINE
================================================================
Based on V39 proven signal. Higher base risk, higher acceleration, higher cap.
"""
import os, sys, shutil, subprocess, time
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None

TERMINAL_EXE = r"C:\Program Files\XM Global MT5\terminal64.exe"
METAEDITOR_EXE = r"C:\Program Files\XM Global MT5\metaeditor64.exe"
DATA_DIR = r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05"
CLEAN_ROOM = os.path.join(DATA_DIR, "MQL5", "Experts", "AlphaLab", "CleanRoom")
TERMINAL_ROOTS = [
    r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05",
    r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075",
    r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\F762D69EEEA9B4430D7F17C82167C844"
]

def kill_terminal():
    subprocess.run(["taskkill", "/F", "/IM", "terminal64.exe", "/T"], capture_output=True)
    time.sleep(2)

# Reuse V39 EA code generator (same file, just different params)
exec(open(os.path.join(DATA_DIR, "src", "autonomous_research_loop_v39.py")).read().split("def run_loop")[0])

def parse_report(report_path):
    if not os.path.exists(report_path): return None
    try:
        with open(report_path, 'r', encoding='utf-16-le', errors='ignore') as f:
            content = f.read()
        if len(content) < 100:
            with open(report_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
        soup = BeautifulSoup(content, 'html.parser')
        pnl=0; pf=0; dd=0; trades=0
        for r in soup.find_all('tr'):
            cols = [c.get_text(strip=True) for c in r.find_all(['td','th'])]
            txt = ' '.join(cols)
            if 'Total Net Profit:' in txt:
                try: pnl = float(cols[cols.index('Total Net Profit:')+1].replace(' ','').replace(',',''))
                except: pass
            if 'Profit Factor:' in txt:
                try: pf = float(cols[cols.index('Profit Factor:')+1].replace(' ','').replace(',',''))
                except: pass
            if 'Equity Drawdown Relative:' in txt:
                for c in cols:
                    if '%' in c and '(' in c:
                        try: dd = float(c.split('%')[0])
                        except: pass
            if 'Total Trades:' in txt:
                try: trades = int(cols[cols.index('Total Trades:')+1])
                except: pass
        return {'net_pnl': pnl, 'pf': pf, 'max_dd_pct': dd, 'trades': trades}
    except: return None

def run():
    print("="*100)
    print("V40: HIGH-ACCEL SMOOTH DIAGONAL ENGINE (Proven Signal + Aggressive Smooth Lot Scaling)")
    print("="*100)

    configs = [
        # Best V39 was R6005: Risk=5.5%, Accel=2.0, Cap=4.0 → PnL=$1116, PF=3.91, DD=19.69%
        # Now: higher risk, higher accel, higher cap, higher DD brake threshold
        # (ver, base_risk, accel_mult, dd_brake_thresh, dd_brake_mult, tp_atr, cap)
        (6101, 0.068, 3.50, 0.080, 0.12, 4.00, 8.0),   # High accel like R1201
        (6102, 0.072, 4.00, 0.085, 0.12, 4.00, 10.0),  # Very high accel
        (6103, 0.065, 3.00, 0.075, 0.14, 3.80, 7.0),   # Moderate high accel
        (6104, 0.060, 2.50, 0.070, 0.15, 3.60, 6.0),   # Conservative high accel
        (6105, 0.075, 4.50, 0.090, 0.10, 4.00, 12.0),  # Ultra aggressive
        (6106, 0.058, 2.20, 0.065, 0.14, 3.50, 5.0),   # R6005-based + boost
        (6107, 0.070, 3.80, 0.080, 0.11, 3.80, 9.0),   # High balanced
        (6108, 0.062, 2.80, 0.072, 0.13, 3.60, 6.5),   # Mid-range
    ]

    best = None
    for cfg in configs:
        ver, br, am, dbt, dbm, tp, cap = cfg
        print(f"\n--- R{ver}: Risk={br*100:.1f}%, Accel={am:.1f}x, Cap={cap:.0f}, DDBrake={dbt*100:.1f}%/{dbm:.2f}x, TP={tp}x ---")
        kill_terminal()

        mql5_file = os.path.join(CLEAN_ROOM, f"AlphaLabR{ver}_SmoothDiagonalMasterEA.mq5")
        ini_file = os.path.join(DATA_DIR, f"generate_r{ver}_gold_exec_report.ini")
        report_path = os.path.join(DATA_DIR, "MQL5", "Experts", "AlphaLab", f"r{ver}_gold_exec_report.htm")

        code = generate_ea_code(ver, br, am, dbt, dbm, tp, cap)
        with open(mql5_file, 'w', encoding='utf-8') as f: f.write(code)
        subprocess.run([METAEDITOR_EXE, f"/compile:{mql5_file}", f"/log:{mql5_file.replace('.mq5','.log')}"], capture_output=True)

        ex5 = mql5_file.replace('.mq5', '.ex5')
        if not os.path.exists(ex5): print("  COMPILE FAILED"); continue

        for root in TERMINAL_ROOTS:
            d = os.path.join(root, "MQL5", "Experts", "AlphaLab", "CleanRoom")
            os.makedirs(d, exist_ok=True)
            try: shutil.copy2(ex5, os.path.join(d, os.path.basename(ex5)))
            except: pass

        with open(ini_file, 'w', encoding='utf-8') as f:
            f.write(f"""[Tester]
Expert=AlphaLab\\CleanRoom\\AlphaLabR{ver}_SmoothDiagonalMasterEA.ex5
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
Report=MQL5\\Experts\\AlphaLab\\r{ver}_gold_exec_report
ReplaceReport=1
ShutdownTerminal=1
""")
        print(f"  Launching MT5 Model=4...")
        subprocess.run([TERMINAL_EXE, f"/config:{ini_file}"], capture_output=True)

        res = parse_report(report_path)
        if not res: print("  PARSE FAILED"); continue

        passed = res['net_pnl'] > 4000 and res['pf'] >= 1.50 and res['max_dd_pct'] <= 20.00
        flag = "*** PASS ***" if passed else "FAIL"
        print(f"  PnL=${res['net_pnl']:.2f} PF={res['pf']:.2f} DD={res['max_dd_pct']:.2f}% Trades={res['trades']} [{flag}]")

        if passed:
            best = (ver, res); break

    if best:
        print(f"\nWINNER: R{best[0]} PnL=${best[1]['net_pnl']:.2f}")
    else:
        print("\nNo winner. Need further tuning.")

if __name__ == '__main__':
    run()
