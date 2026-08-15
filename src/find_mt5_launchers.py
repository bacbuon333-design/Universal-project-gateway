"""
FIND ALL PREVIOUS MT5 LAUNCHER SCRIPTS
======================================
"""

import os, sys, glob

sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None

DATA_DIR = r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05"

def find_launchers():
    py_files = glob.glob(os.path.join(DATA_DIR, "**", "*.py"), recursive=True)
    print(f"Searching {len(py_files)} python files for MT5 runner logic...")
    for pf in py_files:
        try:
            with open(pf, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                if "run_mt5" in content or "terminal64" in content or "official_backtest" in content:
                    print(f"Launcher script: {pf}")
        except Exception:
            pass

if __name__ == '__main__':
    find_launchers()
