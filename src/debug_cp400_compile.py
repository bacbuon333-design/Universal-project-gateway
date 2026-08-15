import os, sys, subprocess

sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None

METAEDITOR_EXE = r"C:\Program Files\XM Global MT5\metaeditor64.exe"
MQL5_SRC = r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05\MQL5\Experts\AlphaLab\alphalab\ALAB_CP400_MasterFlagshipEA.mq5"
LOG_PATH = r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05\MQL5\Experts\AlphaLab\alphalab\compile.log"

cmd = [METAEDITOR_EXE, f"/compile:{MQL5_SRC}", f"/log:{LOG_PATH}"]
subprocess.run(cmd, capture_output=True, text=True)

if os.path.exists(LOG_PATH):
    with open(LOG_PATH, 'r', encoding='utf-16-le', errors='ignore') as f:
        print(f.read())
else:
    print("No log generated.")
