# OFFICIAL METATRADER 5 NATIVE BACKTEST STANDARD OPERATING PROCEDURE (SOP)

To guarantee 100% empirical validity and avoid unverified Python-only claims, every backtest must follow this exact pipeline:

## Step 1: Process Hygiene & Terminal Reset
- Before launching CLI backtests, terminate any running GUI terminal instance to release single-instance file locks:
  `taskkill /F /IM terminal64.exe /T`

## Step 2: MQL5 Compilation
- Always compile MQL5 source files using official MetaEditor CLI:
  `C:\Program Files\XM Global MT5\metaeditor64.exe /compile:<Path_To_MQ5> /log:<Path_To_Log>`
- Sync generated `.ex5` binary file to all terminal directories under `MQL5\Experts\AlphaLab\`.

## Step 3: INI Batch Configuration
- Create INI configuration file at terminal root:
  ```ini
  [Tester]
  Expert=AlphaLab\alphalab\<EA_NAME>.ex5
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
  Report=MQL5\Experts\AlphaLab\<REPORT_NAME>
  ReplaceReport=1
  ShutdownTerminal=1
  ```
- `Model=0` enforces **Every Tick Based on Real Ticks** (203M+ ticks).

## Step 4: Execution & HTML Report Parsing
- Launch CLI process: `C:\Program Files\XM Global MT5\terminal64.exe /config:<Path_To_INI>`
- Wait for process completion and read generated `MQL5\Experts\AlphaLab\<REPORT_NAME>.html` (encoded in `UTF-16-LE`).
- Extract exact rows from HTML report table:
  - `Total Net Profit`
  - `Total Trades` & `Win Rate %`
  - `Profit Factor`
  - `Balance Drawdown Maximal %`

---
*Preserved for AlphaLab Antigravity Systematic Research*
