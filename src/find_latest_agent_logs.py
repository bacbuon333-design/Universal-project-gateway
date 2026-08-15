"""
FIND AND READ LATEST AGENT LOGS FOR DETAILED DIAGNOSTIC INFO
=============================================================
"""

import os, sys, glob

sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None

AGENT_ROOT = r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Tester\BB16F565FAAA6B23A20C26C49416FF05"

def read_agent_logs():
    print("="*105)
    print("SEARCHING FOR AGENT LOG FILES...")
    print("="*105)
    
    logs = glob.glob(os.path.join(AGENT_ROOT, "Agent-*", "logs", "*.log"), recursive=True)
    logs.sort(key=os.path.getmtime, reverse=True)
    
    if logs:
        latest = logs[0]
        print(f"Latest Agent Log File: {latest}")
        with open(latest, 'r', encoding='utf-16-le', errors='ignore') as f:
            lines = f.readlines()
            for l in lines[-120:]:
                if "DIAGNOSTIC" in l or "error" in l or "failed" in l or "failed to" in l:
                    print(l.strip())
                elif "GOLD" in l:
                    print(l.strip())
    else:
        print("No agent log files found.")

if __name__ == '__main__':
    read_agent_logs()
