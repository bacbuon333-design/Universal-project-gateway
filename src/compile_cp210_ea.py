import os, sys, subprocess

sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None

METAEDITOR_EXE = r"C:\Program Files\XM Global MT5\metaeditor64.exe"
MQL5_PATH = r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05\MQL5\Experts\AlphaLab\alphalab\ALAB_CP210_SpreadResilientTrend.mq5"
LOG_PATH = MQL5_PATH.replace('.mq5', '.log')

def compile_cp210():
    print("Compiling CP-210 MQL5 EA...")
    cmd = [METAEDITOR_EXE, f"/compile:{MQL5_PATH}", f"/log:{LOG_PATH}"]
    res = subprocess.run(cmd, capture_output=True, text=True)
    
    ex5_path = MQL5_PATH.replace('.mq5', '.ex5')
    if os.path.exists(ex5_path):
        print(f"SUCCESS! Compiled: {ex5_path}")
    else:
        print(f"Compilation Failed. Check log: {LOG_PATH}")

if __name__ == '__main__':
    compile_cp210()
