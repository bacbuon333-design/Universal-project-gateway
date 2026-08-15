import os, subprocess, sys

sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None

editor = r"C:\Program Files\XM Global MT5\metaeditor64.exe"
mq5 = r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05\MQL5\Experts\AlphaLab\alphalab\ALAB_CP24_HighWinRateMaster.mq5"
log = r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05\MQL5\Experts\AlphaLab\alphalab\compile_cp24.log"

cmd = [editor, f"/compile:{mq5}", f"/log:{log}"]
print("Executing:", cmd)
res = subprocess.run(cmd, capture_output=True, text=True)
print("Exit code:", res.returncode)

if os.path.exists(log):
    with open(log, 'r', encoding='utf-16', errors='ignore') as f:
        print("Compile log content:\n", f.read())
else:
    print("Log file not found.")

ex5 = mq5.replace('.mq5', '.ex5')
print("EX5 exists:", os.path.exists(ex5))
