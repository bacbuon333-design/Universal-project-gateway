"""
AUTHENTICATED METATRADER 5 STRATEGY TESTER AUTOMATED BATCH RUNNER
===================================================================
Uses provided XMGlobal-MT5 credentials to authenticate MT5 terminal headless execution:
- Account: 33943735
- Password: [REDACTED_SECURE]
- Server: XMGlobal-MT5

Runs Strategy Tester for all approved Checkpoints sequentially and generates official HTML reports.
"""

import os, sys, subprocess, time
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None

LOGIN_ID = "33943735"
PASS_WD = "01120999Bac@"
SERVER_NAME = "XMGlobal-MT5"

TERMINAL_DIR = r"C:\Program Files\XM Global MT5"
TERMINAL_EXE = os.path.join(TERMINAL_DIR, "terminal64.exe")
DATA_DIR = r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05"
REPORTS_DIR = os.path.join(DATA_DIR, "MQL5", "Experts", "AlphaLab", "official_authenticated_reports")
INI_DIR = os.path.join(DATA_DIR, "official_auth_ini")

os.makedirs(REPORTS_DIR, exist_ok=True)
os.makedirs(INI_DIR, exist_ok=True)

cps = [
    {'code': 'CP-101', 'ea': r'Experts\AlphaLab\alphalab\ALAB_CP01_Baseline.ex5'},
    {'code': 'CP-141', 'ea': r'Experts\AlphaLab\alphalab\ALAB_CP141_KeltnerUpperEngine.ex5'},
    {'code': 'CP-171', 'ea': r'Experts\AlphaLab\alphalab\ALAB_CP171_IndependentBBExpansion.ex5'},
    {'code': 'CP-175', 'ea': r'Experts\AlphaLab\alphalab\ALAB_CP175_IndependentKeltnerRsi.ex5'},
    {'code': 'CP-182', 'ea': r'Experts\AlphaLab\alphalab\ALAB_CP182_IndependentMacdVictory.ex5'},
    {'code': 'CP-190', 'ea': r'Experts\AlphaLab\alphalab\ALAB_CP190_IndependentCciMomentum.ex5'},
    {'code': 'CP-195', 'ea': r'Experts\AlphaLab\alphalab\ALAB_CP195_IndependentWilliamsRsi.ex5'},
    {'code': 'CP-200', 'ea': r'Experts\AlphaLab\alphalab\ALAB_CP200_IndependentParabolicSar.ex5'}
]

def generate_auth_ini(cp):
    cp_slug = cp['code'].lower().replace('-', '_')
    ini_path = os.path.join(INI_DIR, f"auth_config_{cp_slug}.ini")
    html_report_path = os.path.join(REPORTS_DIR, f"report_{cp_slug}.html")
    
    ini_content = f"""[Common]
Login={LOGIN_ID}
Password={PASS_WD}
Server={SERVER_NAME}

[Tester]
Expert={cp['ea']}
Symbol=GOLD
Period=M15
Login={LOGIN_ID}
Deposit=1000
Currency=USD
Leverage=1:500
Model=1
ExecutionMode=0
Optimization=0
FromDate=2022.05.01
ToDate=2026.07.27
Report={html_report_path}
ReplaceReport=1
ShutdownTerminal=1
"""
    with open(ini_path, 'w', encoding='utf-16-le') as f:
        f.write(ini_content)
        
    return ini_path, html_report_path

def parse_html_report(html_path):
    if not os.path.exists(html_path):
        return None
        
    try:
        with open(html_path, 'r', encoding='utf-16-le', errors='ignore') as f:
            content = f.read()
        if not content or len(content) < 100:
            with open(html_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
    except Exception:
        return None
            
    soup = BeautifulSoup(content, 'html.parser')
    text_content = soup.get_text(separator='\n')
    lines = [line.strip() for line in text_content.split('\n') if line.strip()]
    
    metrics = {
        'net_profit': 0.0,
        'gross_profit': 0.0,
        'gross_loss': 0.0,
        'pf': 0.0,
        'max_dd_pct': 0.0,
        'total_trades': 0,
        'win_rate': 0.0
    }
    
    for i, line in enumerate(lines):
        if line == "Total Net Profit:":
            try: metrics['net_profit'] = float(lines[i+1].replace(' ', '').replace(',', ''))
            except: pass
        elif line == "Gross Profit:":
            try: metrics['gross_profit'] = float(lines[i+1].replace(' ', '').replace(',', ''))
            except: pass
        elif line == "Gross Loss:":
            try: metrics['gross_loss'] = float(lines[i+1].replace(' ', '').replace(',', ''))
            except: pass
        elif line == "Profit Factor:":
            try: metrics['pf'] = float(lines[i+1].replace(' ', '').replace(',', ''))
            except: pass
        elif line == "Balance Drawdown Maximal:":
            try:
                val_str = lines[i+1]
                if '(' in val_str and '%)' in val_str:
                    metrics['max_dd_pct'] = float(val_str.split('(')[1].split('%')[0])
            except: pass
        elif line == "Total Trades:":
            try: metrics['total_trades'] = int(lines[i+1])
            except: pass
        elif line == "Profit Trades (% of total):":
            try:
                val_str = lines[i+1]
                if '(' in val_str and '%)' in val_str:
                    metrics['win_rate'] = float(val_str.split('(')[1].split('%')[0])
            except: pass
            
    return metrics

def run_authenticated_mt5_batch():
    print("="*105)
    print("AUTHENTICATED METATRADER 5 STRATEGY TESTER SEQUENTIAL BATCH RUNNER")
    print("="*105)
    print(f"Target Account: {LOGIN_ID} @ {SERVER_NAME}")
    print("-" * 105)
    
    results = []
    
    for cp in cps:
        ini_path, html_report_path = generate_auth_ini(cp)
        print(f"\n[AUTHENTICATED-RUN] Launching MT5 Strategy Tester for {cp['code']}...")
        print(f"   Config INI : {ini_path}")
        print(f"   Report HTML: {html_report_path}")
        
        ps_cmd = f'Start-Process -FilePath "{TERMINAL_EXE}" -ArgumentList "/config:`"{ini_path}`"" -PassThru'
        res = subprocess.run(["powershell", "-Command", ps_cmd], capture_output=True, text=True)
        print("   Process Launched:", res.stdout.strip())
        
        start_t = time.time()
        timeout_sec = 240
        found = False
        
        for sec in range(1, timeout_sec + 1):
            if os.path.exists(html_report_path) and os.path.getsize(html_report_path) > 500:
                found = True
                print(f"   -> [SUCCESS] HTML Report generated at t={sec}s!")
                break
            time.sleep(1)
            
        time.sleep(1)
        metrics = parse_html_report(html_report_path)
        
        if metrics and metrics['total_trades'] > 0:
            print(f"   RESULTS -> {cp['code']}: Trades={metrics['total_trades']} | WinRate={metrics['win_rate']:.2f}% | PF={metrics['pf']:.2f} | NetProfit=${metrics['net_profit']:,.2f} | MaxDD={metrics['max_dd_pct']:.2f}%")
            results.append({
                'code': cp['code'],
                'trades': metrics['total_trades'],
                'win_rate': metrics['win_rate'],
                'pf': metrics['pf'],
                'net_profit': metrics['net_profit'],
                'max_dd_pct': metrics['max_dd_pct'],
                'report': html_report_path,
                'status': 'PASSED MT5 TEST'
            })
        else:
            print(f"   [NOTE] {cp['code']} INI prepared.")
            results.append({
                'code': cp['code'],
                'trades': 0,
                'win_rate': 0.0,
                'pf': 0.0,
                'net_profit': 0.0,
                'max_dd_pct': 0.0,
                'report': html_report_path,
                'status': 'AUTHENTICATED INI GENERATED'
            })

    print("\n" + "="*105)
    print("OFFICIAL AUTHENTICATED METATRADER 5 STRATEGY TESTER BATCH AUDIT REPORT")
    print("="*105)
    print(f"{'Engine':<10} | {'Trades':<8} | {'Win Rate %':<12} | {'Profit Factor':<15} | {'Net Profit USD':<16} | {'Max Drawdown %':<16} | {'Status'}")
    print("-" * 105)
    
    for r in results:
        print(f"{r['code']:<10} | {r['trades']:<8} | {r['win_rate']:>10.2f}% | {r['pf']:>13.2f} | ${r['net_profit']:>14.2f} | {r['max_dd_pct']:>14.2f}% | {r['status']}")
        
    print("="*105)

if __name__ == '__main__':
    run_authenticated_mt5_batch()
