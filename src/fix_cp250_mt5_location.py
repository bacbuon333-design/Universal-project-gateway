"""
FIX CP250 MT5 EXPERT FOLDER LOCATION
====================================
User Directive:
"không thây cp250 ở cung với cac cp khac trinh tét mt5 để tét kiêm nghiêm"

Copies ALAB_CP250_HyperGrowthEA.ex5 directly to MQL5\\Experts\\AlphaLab\\ across all MT5 terminals.
"""

import os, sys, shutil, glob

sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None

TERMINAL_ROOTS = [
    r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05",
    r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075",
    r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\F762D69EEEA9B4430D7F17C82167C844"
]

SRC_CP250_EX5 = r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05\MQL5\Experts\AlphaLab\alphalab\ALAB_CP250_HyperGrowthEA.ex5"

def fix_cp250_location():
    print("="*105)
    print("COPYING ALAB_CP250_HyperGrowthEA.ex5 DIRECTLY TO MQL5\\Experts\\AlphaLab\\ FOR ALL TERMINALS")
    print("="*105)
    
    if not os.path.exists(SRC_CP250_EX5):
        print(f"Source file not found: {SRC_CP250_EX5}")
        return
        
    for root in TERMINAL_ROOTS:
        target_dir = os.path.join(root, "MQL5", "Experts", "AlphaLab")
        os.makedirs(target_dir, exist_ok=True)
        
        dest_ex5 = os.path.join(target_dir, "ALAB_CP250_HyperGrowthEA.ex5")
        shutil.copy2(SRC_CP250_EX5, dest_ex5)
        print(f"COPIED DIRECTLY -> {dest_ex5}")
        
    print("="*105)
    print("CP-250 IS NOW INSTANTLY VISIBLE DIRECTLY IN MT5 STRATEGY TESTER DROPDOWN!")

if __name__ == '__main__':
    fix_cp250_location()
