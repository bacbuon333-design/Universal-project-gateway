"""
COMPILE AND DEPLOY CP-350 TO ALL MT5 TERMINALS
================================================
Compiles ALAB_CP350_MT5HyperGrowth.mq5 via MetaEditor
and copies ALAB_CP350_MT5HyperGrowth.ex5 directly to MQL5\\Experts\\AlphaLab\\ across all MT5 terminals.
"""

import os, sys, shutil, subprocess

sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None

METAEDITOR_EXE = r"C:\Program Files\XM Global MT5\metaeditor64.exe"
MQL5_SRC = r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05\MQL5\Experts\AlphaLab\alphalab\ALAB_CP350_MT5HyperGrowth.mq5"
LOG_PATH = MQL5_SRC.replace('.mq5', '.log')

TERMINAL_ROOTS = [
    r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05",
    r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075",
    r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\F762D69EEEA9B4430D7F17C82167C844"
]

def compile_and_deploy():
    print("="*105)
    print("COMPILING AND DEPLOYING CP-350 TO ALL MT5 TERMINALS")
    print("="*105)
    
    cmd = [METAEDITOR_EXE, f"/compile:{MQL5_SRC}", f"/log:{LOG_PATH}"]
    subprocess.run(cmd, capture_output=True, text=True)
    
    ex5_src = MQL5_SRC.replace('.mq5', '.ex5')
    if not os.path.exists(ex5_src):
        print(f"Compilation failed. Log: {LOG_PATH}")
        return
        
    print(f"SUCCESSFULLY COMPILED EX5: {ex5_src}")
    
    for root in TERMINAL_ROOTS:
        dest_dir = os.path.join(root, "MQL5", "Experts", "AlphaLab")
        os.makedirs(dest_dir, exist_ok=True)
        dest_ex5 = os.path.join(dest_dir, "ALAB_CP350_MT5HyperGrowth.ex5")
        shutil.copy2(ex5_src, dest_ex5)
        print(f"DEPLOYED DIRECTLY -> {dest_ex5}")
        
    print("="*105)
    print("CP-350 IS NOW INSTANTLY VISIBLE IN MT5 STRATEGY TESTER!")

if __name__ == '__main__':
    compile_and_deploy()
