import os, sys

sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None

REPORTS_DIR = r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05\MQL5\Experts\AlphaLab\loop_reports"

def check_reports():
    print("="*105)
    print("CHECKING AUTOMATED RESEARCH LOOP REPORTS DIRECTORY")
    print("="*105)
    
    if os.path.exists(REPORTS_DIR):
        files = os.listdir(REPORTS_DIR)
        print(f"Files found in {REPORTS_DIR}: {len(files)}")
        for f in files:
            p = os.path.join(REPORTS_DIR, f)
            print(f"   -> {f} ({os.path.getsize(p)} bytes)")
    else:
        print("Reports directory does not exist yet.")
        
    print("="*105)

if __name__ == '__main__':
    check_reports()
