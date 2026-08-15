"""
FIND DOCUMENTATION FILES REFERRED TO BY USER
=============================================
"""

import os, sys, glob

sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None

def find_docs():
    print("Searching for user documentation files...")
    search_paths = [
        r"C:\Users\gugul",
        r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05"
    ]
    
    for sp in search_paths:
        matches = glob.glob(os.path.join(sp, "**", "00_READ_FIRST.md"), recursive=True)
        for m in matches:
            print(f"FOUND: {m}")
            
    matches_all = glob.glob(os.path.join(r"C:\Users\gugul", "**", "AGY_CLI_NATIVE_MT5_DEVELOPMENT_PROTOCOL.md"), recursive=True)
    for m in matches_all:
        print(f"FOUND PROTOCOL: {m}")

if __name__ == '__main__':
    find_docs()
