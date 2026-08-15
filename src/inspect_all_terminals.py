"""
INSPECT ALL TERMINAL DIRECTORIES AND COMPILE CP400 EVERYWHERE
=============================================================
"""

import os, sys, glob, shutil, subprocess

sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None

METAEDITOR_EXE = r"C:\Program Files\XM Global MT5\metaeditor64.exe"
TERMINAL_BASE = r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal"

def inspect_and_force_compile():
    print("="*105)
    print("SEARCHING FOR ALL MT5 TERMINALS IN APPDATA...")
    print("="*105)
    
    term_dirs = glob.glob(os.path.join(TERMINAL_BASE, "*"))
    print(f"Found {len(term_dirs)} terminal directories:")
    for d in term_dirs:
        if os.path.isdir(d) and len(os.path.basename(d)) == 32: # MT5 hash dir
            print(f"  Terminal Dir: {d}")
            
            # Check Experts folder
            exp_dir = os.path.join(d, "MQL5", "Experts", "AlphaLab")
            os.makedirs(exp_dir, exist_ok=True)
            
            sub_exp_dir = os.path.join(exp_dir, "alphalab")
            os.makedirs(sub_exp_dir, exist_ok=True)
            
            ex5_files = glob.glob(os.path.join(d, "**", "ALAB_CP400_MasterFlagshipEA.ex5"), recursive=True)
            mq5_files = glob.glob(os.path.join(d, "**", "ALAB_CP400_MasterFlagshipEA.mq5"), recursive=True)
            
            for f in ex5_files + mq5_files:
                print(f"    Found File: {f} | Size: {os.path.getsize(f)} | MTime: {os.path.getmtime(f)}")

if __name__ == '__main__':
    inspect_and_force_compile()
