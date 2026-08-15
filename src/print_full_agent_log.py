"""
PRINT COMPLETE LATEST AGENT LOG CONTENT
=======================================
"""

import os, sys, glob

sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None

AGENT_ROOT = r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Tester\BB16F565FAAA6B23A20C26C49416FF05"

def print_full_log():
    logs = glob.glob(os.path.join(AGENT_ROOT, "Agent-*", "logs", "*.log"), recursive=True)
    logs.sort(key=os.path.getmtime, reverse=True)
    
    if logs:
        latest = logs[0]
        print(f"Latest Agent Log: {latest} | Size: {os.path.getsize(latest)} bytes")
        with open(latest, 'r', encoding='utf-16-le', errors='ignore') as f:
            lines = f.readlines()
        print(f"Total lines: {len(lines)}")
        for l in lines[-60:]:
            print(l.strip())
    else:
        print("No logs found.")

if __name__ == '__main__':
    print_full_log()
