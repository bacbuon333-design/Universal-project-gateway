"""
ALPHA LAB AUTOMATED MT5 RESEARCH & TESTING LOOP HARNESS
======================================================
User Mandate:
"minh cân là ban thực hiên thanh lập đc quy trinh vong lăp nghien cứ xong r tự dông đưa lên mt5 tester để thực nghiêm xem bao cao cua mt5 và dung đó để bao cao cho minh"

Automated Pipeline Architecture:
1. Strategy Hypothesis & Python Simulation
2. MQL5 Code Generation (.mq5)
3. MetaEditor Compilation (.ex5)
4. MT5 Strategy Tester Headless Execution
5. Parsing Official MT5 Strategy Tester HTML Report
6. Reporting Verified MT5 Empirical Results to User
"""

import os, sys, subprocess, time, json
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None

LOGIN_ID = "33943735"
PASS_WD = "01120999Bac@"
SERVER_NAME = "XMGlobal-MT5"

TERMINAL_DIR = r"C:\Program Files\XM Global MT5"
TERMINAL_EXE = os.path.join(TERMINAL_DIR, "terminal64.exe")
METAEDITOR_EXE = os.path.join(TERMINAL_DIR, "metaeditor64.exe")

DATA_DIR = r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05"
MQL5_DIR = os.path.join(DATA_DIR, "MQL5", "Experts", "AlphaLab")
REPORTS_DIR = os.path.join(DATA_DIR, "MQL5", "Experts", "AlphaLab", "loop_reports")
INI_DIR = os.path.join(DATA_DIR, "loop_ini")

os.makedirs(MQL5_DIR, exist_ok=True)
os.makedirs(REPORTS_DIR, exist_ok=True)
os.makedirs(INI_DIR, exist_ok=True)

def step1_compile_mql5(mq5_path, ex5_path):
    print(f"[STEP 2/5] Compiling MQL5 EA using MetaEditor...")
    log_path = mq5_path.replace('.mq5', '.log')
    cmd = [METAEDITOR_EXE, f"/compile:{mq5_path}", f"/log:{log_path}"]
    
    res = subprocess.run(cmd, capture_output=True, text=True)
    time.sleep(1)
    
    if os.path.exists(ex5_path):
        print(f"   -> Compilation SUCCESSFUL: {ex5_path}")
        return True
    else:
        print(f"   -> Compilation FAILED! Log: {log_path}")
        return False

def step2_generate_ini(ea_rel_path, cp_code):
    ini_path = os.path.join(INI_DIR, f"run_{cp_code.lower().replace('-', '_')}.ini")
    html_report_path = os.path.join(REPORTS_DIR, f"report_{cp_code.lower().replace('-', '_')}.html")
    
    content = f"""[Common]
Login={LOGIN_ID}
Password={PASS_WD}
Server={SERVER_NAME}

[Tester]
Expert={ea_rel_path}
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
        f.write(content)
        
    return ini_path, html_report_path

def step3_execute_mt5_tester(ini_path, html_report_path, timeout_sec=240):
    print(f"[STEP 3/5] Executing MT5 Strategy Tester via Command Line...")
    print(f"   Config INI: {ini_path}")
    print(f"   Output Report: {html_report_path}")
    
    cmd_str = f'cmd.exe /c start "" "{TERMINAL_EXE}" /config:"{ini_path}"'
    subprocess.run(cmd_str, shell=True)
    
    print("   Waiting for MT5 Strategy Tester execution and report generation...")
    start_t = time.time()
    
    for sec in range(1, timeout_sec + 1):
        if os.path.exists(html_report_path) and os.path.getsize(html_report_path) > 1000:
            print(f"   -> MT5 Backtest Complete! HTML Report created at t={sec}s ({os.path.getsize(html_report_path)} bytes)")
            return True
        if sec % 15 == 0:
            print(f"   [{sec}s elapsed] MT5 Backtesting in progress...")
        time.sleep(1)
        
    print(f"   [NOTE] INI Config created at: {ini_path}")
    return False

def step4_parse_mt5_html(html_path):
    print(f"[STEP 4/5] Parsing MT5 Strategy Tester Official HTML Output...")
    if not os.path.exists(html_path):
        return None
        
    try:
        with open(html_path, 'r', encoding='utf-16-le', errors='ignore') as f:
            content = f.read()
        if not content or len(content) < 100:
            with open(html_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
    except Exception as e:
        print("Parse error:", e)
        return None
        
    soup = BeautifulSoup(content, 'html.parser')
    text_content = soup.get_text(separator='\n')
    lines = [line.strip() for line in text_content.split('\n') if line.strip()]
    
    metrics = {
        'expert': 'Unknown',
        'symbol': 'Unknown',
        'deposit': 1000.0,
        'net_profit': 0.0,
        'gross_profit': 0.0,
        'gross_loss': 0.0,
        'pf': 0.0,
        'max_dd_pct': 0.0,
        'total_trades': 0,
        'win_rate': 0.0,
        'avg_win': 0.0,
        'avg_loss': 0.0
    }
    
    for i, line in enumerate(lines):
        if line == "Expert:": metrics['expert'] = lines[i+1]
        elif line == "Symbol:": metrics['symbol'] = lines[i+1]
        elif line == "Total Net Profit:":
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
        elif line == "Average profit trade:":
            try: metrics['avg_win'] = float(lines[i+1].replace(' ', '').replace(',', ''))
            except: pass
        elif line == "Average loss trade:":
            try: metrics['avg_loss'] = float(lines[i+1].replace(' ', '').replace(',', ''))
            except: pass
            
    return metrics

def run_automated_research_loop(cp_code, mq5_filename):
    print("="*105)
    print(f"AUTOMATED MT5 RESEARCH & VERIFICATION LOOP FOR ENGINE: {cp_code}")
    print("="*105)
    
    mq5_path = os.path.join(MQL5_DIR, mq5_filename)
    ex5_path = mq5_path.replace('.mq5', '.ex5')
    ea_rel_path = rf"Experts\AlphaLab\{mq5_filename.replace('.mq5', '.ex5')}"
    
    if not os.path.exists(mq5_path):
        print(f"Error: Source file {mq5_path} does not exist!")
        return
        
    if not step1_compile_mql5(mq5_path, ex5_path):
        return
        
    ini_path, html_report_path = step2_generate_ini(ea_rel_path, cp_code)
    success = step3_execute_mt5_tester(ini_path, html_report_path, timeout_sec=120)
    
    if success or os.path.exists(html_report_path):
        metrics = step4_parse_mt5_html(html_report_path)
        if metrics:
            print("\n" + "="*105)
            print(f"OFFICIAL MT5 STRATEGY TESTER VERIFIED REPORT FOR {cp_code}")
            print("="*105)
            print(f"Robot EA Name            : {metrics['expert']}")
            print(f"Symbol / Period           : {metrics['symbol']} M15")
            print(f"Initial Deposit           : ${metrics['deposit']:,.2f} USD")
            print(f"Total Net Profit          : +${metrics['net_profit']:,.2f} USD")
            print(f"Gross Profit / Gross Loss : +${metrics['gross_profit']:,.2f} USD / -${metrics['gross_loss']:,.2f} USD")
            print(f"Profit Factor (PF)        : {metrics['pf']:.2f}")
            print(f"Win Rate %                : {metrics['win_rate']:.2f}% ({metrics['total_trades']} Total Trades)")
            print(f"Max Drawdown (MaxDD %)   : {metrics['max_dd_pct']:.2f}%")
            print(f"Avg Win / Avg Loss        : +${metrics['avg_win']:,.2f} USD / -${metrics['avg_loss']:,.2f} USD")
            print(f"HTML Report Location     : {html_report_path}")
            print("="*105)
        else:
            print("Could not parse HTML metrics.")

if __name__ == '__main__':
    run_automated_research_loop('CP-171', 'ALAB_CP171_IndependentBBExpansion.mq5')
