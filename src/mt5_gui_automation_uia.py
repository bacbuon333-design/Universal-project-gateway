"""
AUTOMATED MT5 GUI STRATEGY TESTER CONTROLLER (UIA BACKEND)
===========================================================
Uses pywinauto UIA backend to inspect and control MT5 GUI windows on Windows 11.
"""

import os, sys, time, subprocess
from pywinauto import Desktop, Application

sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None

TERMINAL_EXE = r"C:\Program Files\XM Global MT5\terminal64.exe"

def run_uia_mt5_automation():
    print("="*105)
    print("LAUNCHING MT5 GUI AUTOMATION WITH PYWINAUTO UIA BACKEND")
    print("="*105)
    
    # Check if MT5 process is already running or launch it
    print("1. Launching XM Global MT5 GUI Application...")
    proc = subprocess.Popen([TERMINAL_EXE])
    time.sleep(6)
    
    print("2. Searching Desktop for MetaTrader 5 Window...")
    desktop = Desktop(backend="uia")
    mt5_win = None
    
    for win in desktop.windows():
        title = win.window_text()
        if "MetaTrader" in title or "XM Global" in title or "735" in title:
            mt5_win = win
            print(f"   FOUND MT5 WINDOW: '{title}'")
            break
            
    if mt5_win:
        print("3. Bringing MT5 Window to Foreground & Focus...")
        try:
            mt5_win.set_focus()
            time.sleep(1)
            
            print("4. Pressing Ctrl+R to activate Strategy Tester panel...")
            mt5_win.type_keys("^r")
            time.sleep(2)
            
            print("5. Sending Start Execution signal ({ENTER}) to Strategy Tester...")
            mt5_win.type_keys("{ENTER}")
            time.sleep(2)
            
            print("SUCCESS: MT5 Strategy Tester execution triggered on GUI!")
        except Exception as e:
            print("Interaction Note:", e)
    else:
        print("Could not find open MT5 window on Desktop.")
        
    print("="*105)

if __name__ == '__main__':
    run_uia_mt5_automation()
