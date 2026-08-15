"""
FIND ALL RECENT MT5 STRATEGY TESTER REPORTS AND DIAGNOSE CLI EXECUTION
========================================================================
"""

import os, sys, glob, subprocess

sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None

DATA_DIR = r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05"

def find_reports():
    print("="*105)
    print(f"SEARCHING FOR MT5 REPORTS IN: {DATA_DIR}")
    print("="*105)
    
    htm_files = glob.glob(os.path.join(DATA_DIR, "**", "*.htm*"), recursive=True)
    xml_files = glob.glob(os.path.join(DATA_DIR, "**", "*.xml"), recursive=True)
    
    all_files = htm_files + xml_files
    print(f"Found {len(all_files)} report candidate files:")
    for f in all_files:
        size = os.path.getsize(f)
        mtime = os.path.getmtime(f)
        print(f"  {f} | Size: {size:,} bytes | MTime: {mtime}")
        
if __name__ == '__main__':
    find_reports()
