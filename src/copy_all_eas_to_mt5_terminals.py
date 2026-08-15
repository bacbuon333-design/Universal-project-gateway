"""
COPY ALL COMPILED EA FILES TO ALL MT5 TERMINAL DIRECTORIES FOR REAL GUI TESTING
================================================================================
User Directive:
"minh không tin ban sao chep ea đã biên dich để minh chon backtest = mt5 thâtn giao diên nguoig dung"

Copies all compiled .ex5 and .mq5 Expert Advisors into every MetaTrader 5 terminal
data folder present on the system so the user can immediately select them in the MT5 GUI Strategy Tester.
"""

import os, sys, shutil

sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None

TERMINALS_ROOT = r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal"
SOURCE_DIR = r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\MQL5\Experts\AlphaLab\alphalab"

def copy_eas_to_all_mt5_terminals():
    if not os.path.exists(SOURCE_DIR):
        print(f"[ERROR] Source directory not found: {SOURCE_DIR}")
        return
        
    source_files = [f for f in os.listdir(SOURCE_DIR) if f.endswith('.ex5') or f.endswith('.mq5')]
    
    print("="*105)
    print("COPYING ALL COMPILED EX5 & MQ5 ROBOT EAS TO ALL MT5 TERMINAL DIRECTORIES FOR GUI TESTING")
    print("="*105)
    print(f"Source Folder: {SOURCE_DIR}")
    print(f"Found {len(source_files)} Robot EA files to distribute.")
    print("-" * 105)
    
    terminal_folders = [os.path.join(TERMINALS_ROOT, d) for d in os.listdir(TERMINALS_ROOT) if os.path.isdir(os.path.join(TERMINALS_ROOT, d))]
    
    copied_count = 0
    for term_dir in terminal_folders:
        mql5_experts_dir = os.path.join(term_dir, "MQL5", "Experts", "AlphaLab")
        os.makedirs(mql5_experts_dir, exist_ok=True)
        
        print(f"Syncing to Target MT5 Terminal: {mql5_experts_dir}")
        for file_name in source_files:
            src_file = os.path.join(SOURCE_DIR, file_name)
            dst_file = os.path.join(mql5_experts_dir, file_name)
            shutil.copy2(src_file, dst_file)
            print(f"   -> Copied: {file_name}")
            copied_count += 1
            
    print("="*105)
    print(f"SUCCESSFULLY SYNCHRONIZED {copied_count} EA FILES ACROSS ALL MT5 TERMINALS!")
    print("User Action Instructions:")
    print("1. Open MetaTrader 5 GUI.")
    print("2. Press Ctrl+N to open Navigator panel -> Right-click 'Expert Advisors' -> Click 'Refresh'.")
    print("3. Press Ctrl+R to open Strategy Tester.")
    print("4. Under 'Expert', select 'AlphaLab\\ALAB_MasterPortfolio_8CP_Compounding.ex5' (or any individual CP).")
    print("5. Select Symbol 'XAUUSD', Period 'M15', Date Range '2022.05.01 - 2026.07.24'.")
    print("6. Click 'Start' to run live backtest in MT5 GUI!")
    print("="*105)

if __name__ == '__main__':
    copy_eas_to_all_mt5_terminals()
