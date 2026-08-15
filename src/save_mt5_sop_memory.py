"""
PERSISTENT RECORD OF OFFICIAL MT5 NATIVE BACKTEST STANDARD OPERATING PROCEDURE
================================================================================
"""

import os, sys

sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None

DATA_DIR = r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05"
SOP_FILE = os.path.join(DATA_DIR, "MT5_NATIVE_BACKTEST_SOP.md")

SOP_CONTENT = """# OFFICIAL METATRADER 5 NATIVE BACKTEST STANDARD OPERATING PROCEDURE (SOP)

To guarantee 100% empirical validity and avoid unverified Python-only claims, every backtest must follow this exact pipeline:

## Step 1: Process Hygiene & Terminal Reset
- Before launching CLI backtests, terminate any running GUI terminal instance to release single-instance file locks:
  `taskkill /F /IM terminal64.exe /T`

## Step 2: MQL5 Compilation
- Always compile MQL5 source files using official MetaEditor CLI:
  `C:\\Program Files\\XM Global MT5\\metaeditor64.exe /compile:<Path_To_MQ5> /log:<Path_To_Log>`
- Sync generated `.ex5` binary file to all terminal directories under `MQL5\\Experts\\AlphaLab\\`.

## Step 3: INI Batch Configuration
- Create INI configuration file at terminal root:
  ```ini
  [Tester]
  Expert=AlphaLab\\alphalab\\<EA_NAME>.ex5
  Symbol=GOLD
  Period=M15
  Deposit=1000
  Currency=USD
  Leverage=1:500
  Model=0
  ExecutionMode=0
  Optimization=0
  FromDate=2022.05.01
  ToDate=2026.07.27
  Report=MQL5\\Experts\\AlphaLab\\<REPORT_NAME>
  ReplaceReport=1
  ShutdownTerminal=1
  ```
- `Model=0` enforces **Every Tick Based on Real Ticks** (203M+ ticks).

## Step 4: Execution & HTML Report Parsing
- Launch CLI process: `C:\\Program Files\\XM Global MT5\\terminal64.exe /config:<Path_To_INI>`
- Wait for process completion and read generated `MQL5\\Experts\\AlphaLab\\<REPORT_NAME>.html` (encoded in `UTF-16-LE`).
- Extract exact rows from HTML report table:
  - `Total Net Profit`
  - `Total Trades` & `Win Rate %`
  - `Profit Factor`
  - `Balance Drawdown Maximal %`

---
*Preserved for AlphaLab Antigravity Systematic Research*
"""

def save_sop():
    with open(SOP_FILE, 'w', encoding='utf-8') as f:
        f.write(SOP_CONTENT)
    print(f"MT5 Native Backtest SOP successfully recorded at: {SOP_FILE}")

if __name__ == '__main__':
    save_sop()
