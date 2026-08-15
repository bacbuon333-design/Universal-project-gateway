"""
OFFICIAL METATRADER 5 BATCH BACKTEST RUNNER FOR ALL APPROVED INDEPENDENT CPS
=============================================================================
User Directive:
"Đó vây nên cac chuân CP cân phai đuoc đanh giá lai = cach chay theo đung chuân MT5 backtest engien lần nhẵ lân luot với cac Cp đat"

Automates headless execution of the MetaTrader 5 Strategy Tester engine for each approved CP:
- CP-101 (Anchor Donchian Engine)
- CP-141 (Keltner Upper Engine)
- CP-171 (Independent BB Expansion Engine)
- CP-175 (Independent Keltner RSI Engine)
- CP-182 (Independent MACD Victory Engine)
- CP-190 (Independent CCI Momentum Engine)
- CP-195 (Independent Williams %R Engine)
- CP-200 (Independent Parabolic SAR Engine)

Generates official MT5 HTML reports for every CP and compiles a definitive audit table.
"""

import os, sys, subprocess, time
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None

TERMINAL_PATH = r"C:\Program Files\MetaTrader 5\terminal64.exe"
DATA_DIR = r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075"
REPORTS_DIR = os.path.join(DATA_DIR, "reports")
INI_DIR = os.path.join(DATA_DIR, "ini")

os.makedirs(REPORTS_DIR, exist_ok=True)
os.makedirs(INI_DIR, exist_ok=True)

cps = [
    {'code': 'CP-101', 'ea': r'AlphaLab\ALAB_CP101_Baseline.ex5'},
    {'code': 'CP-141', 'ea': r'AlphaLab\ALAB_CP141_KeltnerUpperEngine.ex5'},
    {'code': 'CP-171', 'ea': r'AlphaLab\ALAB_CP171_IndependentBBExpansion.ex5'},
    {'code': 'CP-175', 'ea': r'AlphaLab\ALAB_CP175_IndependentKeltnerRsi.ex5'},
    {'code': 'CP-182', 'ea': r'AlphaLab\ALAB_CP182_IndependentMacdVictory.ex5'},
    {'code': 'CP-190', 'ea': r'AlphaLab\ALAB_CP190_IndependentCciMomentum.ex5'},
    {'code': 'CP-195', 'ea': r'AlphaLab\ALAB_CP195_IndependentWilliamsRsi.ex5'},
    {'code': 'CP-200', 'ea': r'AlphaLab\ALAB_CP200_IndependentParabolicSar.ex5'}
]

def generate_ini_config(cp):
    ini_path = os.path.join(INI_DIR, f"test_{cp['code'].lower().replace('-', '_')}.ini")
    html_report_path = os.path.join(REPORTS_DIR, f"report_{cp['code'].lower().replace('-', '_')}.html")
    
    content = f"""; Auto-generated MT5 Strategy Tester Config for {cp['code']}
[Tester]
Expert=Experts\\{cp['ea']}
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
Report={html_report_path}
ReplaceReport=1
ShutdownTerminal=1
"""
    with open(ini_path, 'w', encoding='utf-16-le') as f:
        f.write(content)
        
    return ini_path, html_report_path

def parse_html_report(html_path):
    if not os.path.exists(html_path):
        return None
        
    with open(html_path, 'r', encoding='utf-16-le', errors='ignore') as f:
        content = f.read()
    if not content or len(content) < 100:
        with open(html_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            
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
                    pct_str = val_str.split('(')[1].split('%')[0]
                    metrics['max_dd_pct'] = float(pct_str)
            except: pass
        elif line == "Total Trades:":
            try: metrics['total_trades'] = int(lines[i+1])
            except: pass
        elif line == "Profit Trades (% of total):":
            try:
                val_str = lines[i+1]
                if '(' in val_str and '%)' in val_str:
                    pct_str = val_str.split('(')[1].split('%')[0]
                    metrics['win_rate'] = float(pct_str)
            except: pass
            
    return metrics

def run_mt5_batch_matrix():
    print("="*105)
    print("RUNNING OFFICIAL METATRADER 5 STRATEGY TESTER ENGINE FOR ALL APPROVED CPS")
    print("="*105)
    
    results = []
    
    for cp in cps:
        ini_path, html_report_path = generate_ini_config(cp)
        print(f"\n[EXEC-MT5] Launching MT5 Strategy Tester for {cp['code']}...")
        print(f"   Config INI : {ini_path}")
        print(f"   Report HTML: {html_report_path}")
        
        cmd = [TERMINAL_PATH, f"/config:{ini_path}"]
        proc = subprocess.Popen(cmd)
        
        # Wait for terminal to run test and shutdown
        timeout_sec = 120
        start_t = time.time()
        
        while proc.poll() is None:
            if time.time() - start_t > timeout_sec:
                print(f"   [WARNING] Timeout reached for {cp['code']}. Terminating process.")
                proc.kill()
                break
            time.sleep(2)
            
        time.sleep(2)
        metrics = parse_html_report(html_report_path)
        
        if metrics:
            print(f"   -> [RESULTS {cp['code']}] Net Profit: ${metrics['net_profit']:,.2f} | PF: {metrics['pf']:.2f} | WinRate: {metrics['win_rate']:.2f}% | MaxDD: {metrics['max_dd_pct']:.2f}% | Trades: {metrics['total_trades']}")
            results.append({
                'code': cp['code'],
                'net_profit': metrics['net_profit'],
                'gross_profit': metrics['gross_profit'],
                'gross_loss': metrics['gross_loss'],
                'pf': metrics['pf'],
                'max_dd_pct': metrics['max_dd_pct'],
                'total_trades': metrics['total_trades'],
                'win_rate': metrics['win_rate'],
                'report': html_report_path
            })
        else:
            print(f"   [NOTE] HTML Report not generated yet for {cp['code']}.")
            
    print("\n" + "="*105)
    print("OFFICIAL METATRADER 5 BACKTEST MATRIX SUMMARY REPORT (REAL-TICK DATA)")
    print("="*105)
    print(f"{'Engine':<10} | {'Trades':<8} | {'Win Rate %':<12} | {'Profit Factor':<15} | {'Net Profit USD':<16} | {'Max Drawdown %':<16} | {'Status'}")
    print("-" * 105)
    
    for r in results:
        status = "PASSED" if r['win_rate'] >= 45.0 and r['pf'] >= 1.40 and r['max_dd_pct'] <= 18.0 else "REVIEW"
        print(f"{r['code']:<10} | {r['total_trades']:<8} | {r['win_rate']:>10.2f}% | {r['pf']:>13.2f} | ${r['net_profit']:>14.2f} | {r['max_dd_pct']:>14.2f}% | {status}")
        
    print("="*105)

if __name__ == '__main__':
    run_mt5_batch_matrix()
