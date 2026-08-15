import os, sys

sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None

LOG_PATH = r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Tester\BB16F565FAAA6B23A20C26C49416FF05\Agent-127.0.0.1-3000\logs\20260801.log"

def inspect_mt5_log():
    if not os.path.exists(LOG_PATH):
        print(f"File not found: {LOG_PATH}")
        # Search for any logs in the Tester directory
        tester_root = r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Tester"
        for root, dirs, files in os.walk(tester_root):
            for file in files:
                if file.endswith(".log"):
                    print("Found log:", os.path.join(root, file))
        return

    with open(LOG_PATH, 'r', encoding='utf-16-le', errors='ignore') as f:
        lines = f.readlines()
        print("Total log lines:", len(lines))
        print("--- FIRST 30 LINES ---")
        for line in lines[:30]:
            print(line.strip())
        print("\n--- LAST 50 LINES ---")
        for line in lines[-50:]:
            print(line.strip())

if __name__ == '__main__':
    inspect_mt5_log()
