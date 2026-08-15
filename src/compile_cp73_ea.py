import os, subprocess, sys

sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None

METAEDITOR_PATH = r"C:\Program Files\MetaTrader 5\metaeditor64.exe"
MQ5_PATH = r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\MQL5\Experts\AlphaLab\alphalab\ALAB_CP73_Strict1TradePerDayEngine.mq5"
LOG_PATH = r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\MQL5\Experts\AlphaLab\alphalab\compile_cp73.log"

def compile_cp73():
    cmd = [METAEDITOR_PATH, f"/compile:{MQ5_PATH}", f"/log:{LOG_PATH}"]
    print(f"Executing: {' '.join(cmd)}")
    res = subprocess.run(cmd, capture_output=True, text=True)
    
    if os.path.exists(LOG_PATH):
        with open(LOG_PATH, 'r', encoding='utf-16-le', errors='ignore') as f:
            content = f.read()
            print("--- COMPILATION LOG ---")
            print(content.encode('ascii', errors='ignore').decode('ascii'))
            print("-----------------------")
            if "0 errors, 0 warnings" in content:
                print("SUCCESS: 0 errors, 0 warnings!")
    else:
        print("Log file not found.")

if __name__ == '__main__':
    compile_cp73()
