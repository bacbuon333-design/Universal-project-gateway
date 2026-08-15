"""
NATIVE METATRADER 5 PYTHON API IPC CONNECTION TEST
===================================================
User Directive:
"ban có thể từ cưa sổ mở săn tiên hanh tét mt5 đc mà đâu nhâta thiêt phải mở lãi hoan toan muơn trinh testecuar mt5 ở câp độ mã nguôn ây"

Connects directly to the ALREADY OPEN MT5 terminal window using native MetaTrader5 Python IPC.
"""

import os, sys
import MetaTrader5 as mt5

sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None

def test_mt5_native_ipc():
    print("="*105)
    print("CONNECTING DIRECTLY TO ALREADY OPEN MT5 TERMINAL VIA NATIVE PYTHON IPC")
    print("="*105)
    
    if not mt5.initialize(path=r"C:\Program Files\XM Global MT5\terminal64.exe"):
        print("mt5.initialize() failed! Error:", mt5.last_error())
        return
        
    print("SUCCESSFULLY CONNECTED TO RUNNING MT5 TERMINAL!")
    term_info = mt5.terminal_info()
    acc_info = mt5.account_info()
    
    if term_info:
        print(f"Terminal Name   : {term_info.name}")
        print(f"Terminal Company: {term_info.company}")
        print(f"Build Version   : {term_info.build}")
        print(f"Data Path       : {term_info.data_path}")
        print(f"Connected Server: {term_info.connected}")
        
    if acc_info:
        print(f"Account Login   : {acc_info.login}")
        print(f"Account Server  : {acc_info.server}")
        print(f"Account Balance : ${acc_info.balance:,.2f} {acc_info.currency}")
        print(f"Account Equity  : ${acc_info.equity:,.2f} {acc_info.currency}")
        
    mt5.shutdown()
    print("="*105)

if __name__ == '__main__':
    test_mt5_native_ipc()
