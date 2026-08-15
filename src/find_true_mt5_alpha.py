"""
FIND TRUE MT5 NATIVE ALPHA (SEARCHING FOR EA THAT PASSES REAL MT5 TESTER)
========================================================================
Compiles candidate MQL5 EAs and executes them directly in MT5 Strategy Tester (Model=0 Real Ticks).
Parses the agent log to find the exact performance on MT5 native engine.
"""

import os, sys, shutil, subprocess, glob

sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None

METAEDITOR = r"C:\Program Files\XM Global MT5\metaeditor64.exe"
TERMINAL = r"C:\Program Files\XM Global MT5\terminal64.exe"
DATA_DIR = r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05"
AGENT_LOG = os.path.join(DATA_DIR, "Tester", "Agent-127.0.0.1-3000", "logs", "20260801.log")

def test_mql5_candidate(name, mql5_code):
    print("\n" + "="*105)
    print(f"TESTING CANDIDATE EA ON NATIVE MT5 TESTER: {name}")
    print("="*105)
    
    mq5_path = os.path.join(DATA_DIR, "MQL5", "Experts", "AlphaLab", "alphalab", f"{name}.mq5")
    ex5_path = mq5_path.replace('.mq5', '.ex5')
    log_path = mq5_path.replace('.mq5', '.log')
    
    with open(mq5_path, 'w', encoding='utf-8') as f:
        f.write(mql5_code)
        
    cmd_compile = [METAEDITOR, f"/compile:{mq5_path}", f"/log:{log_path}"]
    subprocess.run(cmd_compile, capture_output=True, text=True)
    
    if not os.path.exists(ex5_path):
        print(f"Compilation failed for {name}")
        return None
        
    # Sync to Experts root
    sync_dest = os.path.join(DATA_DIR, "MQL5", "Experts", "AlphaLab", f"{name}.ex5")
    shutil.copy2(ex5_path, sync_dest)
    
    ini_path = os.path.join(DATA_DIR, f"run_{name}.ini")
    ini_content = f"""[Tester]
Expert=AlphaLab\\alphalab\\{name}.ex5
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
ShutdownTerminal=1
"""
    with open(ini_path, 'w', encoding='utf-8') as f:
        f.write(ini_content)
        
    cmd_run = [TERMINAL, f"/config:{ini_path}"]
    proc = subprocess.Popen(cmd_run)
    proc.wait()
    
    # Parse Agent Log for final balance
    if os.path.exists(AGENT_LOG):
        with open(AGENT_LOG, 'r', encoding='utf-16-le', errors='ignore') as f:
            lines = f.readlines()
        for l in reversed(lines[-200:]):
            if "final balance" in l:
                print(f"  --> NATIVE MT5 RESULT FOR {name}: {l.strip()}")
                return l.strip()
    return None

if __name__ == '__main__':
    print("MQL5 Candidate Testing Framework Ready.")
