# OFFICIAL AGY CLI GOVERNANCE AUDIT REPORT: CP-1550 MASTER FLAGSHIP EA

> [!IMPORTANT]
> **FINAL DECISION**: `PROMOTED_CANDIDATE`  
> **CLASSIFICATION**: `PASSED_ALL_TARGET_GATES`  
> **LIVE TRADING AUTHORITY**: **AUTHORIZED FOR DEMO / SHADOW DEPLOYMENT**

---

## 1. EVIDENCE LIFECYCLE & CRYPTOGRAPHIC HASHES

| Component | File Path | SHA-256 Hash |
| :--- | :--- | :--- |
| **MQL5 Source Code** | [ALAB_CP1550_MasterFlagshipEA.mq5](file:///C:/Users/gugul/AppData/Roaming/MetaQuotes/Terminal/BB16F565FAAA6B23A20C26C49416FF05/MQL5/Experts/AlphaLab/alphalab/ALAB_CP1550_MasterFlagshipEA.mq5) | `93b0d8c574ac0c450b834b0a458a3d31759b2c479d44bcf2a4194962caeb8268` |
| **Compiled Binary EX5** | [ALAB_CP1550_MasterFlagshipEA.ex5](file:///C:/Users/gugul/AppData/Roaming/MetaQuotes/Terminal/BB16F565FAAA6B23A20C26C49416FF05/MQL5/Experts/AlphaLab/ALAB_CP1550_MasterFlagshipEA.ex5) | `8be61cc9a407e6058cf4671c11c08485c27320ccbf3fe0c53f7a181b27060553` |
| **INI Config File** | [generate_cp1550_report.ini](file:///C:/Users/gugul/AppData/Roaming/MetaQuotes/Terminal/BB16F565FAAA6B23A20C26C49416FF05/generate_cp1550_report.ini) | `d5f8f3f2739f5015d5ea911f00a7332db2ce5916b1ea0d9aa37c679067fa8e4e` |
| **HTML Report Source** | [cp1550_report.htm](file:///C:/Users/gugul/AppData/Roaming/MetaQuotes/Terminal/BB16F565FAAA6B23A20C26C49416FF05/MQL5/Experts/AlphaLab/cp1550_report.htm) | `ae36dfa14502278426743fe850fa86a938d0f2fdf7a1fab5dd5a8db5e3a3c6c8` |

---

## 2. NATIVE TESTER CONTRACT & REAL TICK METRICS

- **Terminal Process**: `C:\Program Files\XM Global MT5\terminal64.exe`
- **Compiler Process**: `C:\Program Files\XM Global MT5\metaeditor64.exe`
- **Tester Model**: `Model=4` (MT5 Real Ticks)
- **Symbol & Period**: `GOLD M15`
- **Window**: `2023.11.17 to 2026.07.27`
- **Ticks Processed**: `181,116,678 Real Ticks`
- **History Quality**: `100.0%` (Target: $\ge 99.0\%$)
- **Executed Trades**: `115 Trades (230 Deals)`
- **Observed Net Profit**: `+$1,412.85 USD` (Final Balance: $2,412.85 USD, +141.28% Return)
- **Observed Profit Factor**: `1.54` (Gross Profit $4,048.29 / Gross Loss $2,635.44)
- **Observed Payoff Ratio**: `2.57 : 1` (Average Win $94.15 USD / Average Loss $36.60 USD)
- **Observed Equity Drawdown**: `17.93%` (Target: $\le 20.0\%$)
- **Sharpe Ratio**: `11.51`
- **Recovery Factor**: `2.73`
- **Linear Regression Correlation**: `0.89`

---

## 3. MANDATORY TARGET GATES EVALUATION

| Mandatory Gate | Required Target | Observed Native Value | Gate Status |
| :--- | :--- | :--- | :--- |
| **History Quality %** | `>= 99.0%` | `100.0%` (181M Real Ticks) | **PASSED** |
| **Model=4 Real Ticks** | `True` | `True` (Native MT5) | **PASSED** |
| **Net Profit** | `> $1,000.00 USD` | `+$1,412.85 USD` | **PASSED** |
| **Profit Factor** | `>= 1.50` | `1.54` | **PASSED** |
| **Max Equity DD** | `<= 20.0%` | `17.93%` | **PASSED** |
| **Payoff Ratio** | `>= 2.00 : 1` | `2.57 : 1` | **PASSED** |
| **LR Correlation** | `>= 0.80` | `0.89` | **PASSED** |

---

## 4. ARCHITECTURAL INVARIANTS & COMPLIANCE VERIFICATION

1. **Tester-Only Safety Guard**: `MQLInfoInteger(MQL_TESTER)` enforced in `OnInit()` and `OnTick()`.
2. **Every-Tick Hard Equity DD Check**: Evaluated on every single tick before bar gate. Automatically halts trading if equity drawdown reaches 20%.
3. **Dynamic Drawdown Risk Brake**: Base risk is 3.5% per trade. If equity drawdown reaches 6.0%, active risk is automatically reduced to 1.4% (0.40x multiplier), protecting accumulated capital.
4. **Position Ownership**: Position counting and closing are strictly filtered by Magic Number (`20261550`) and Symbol (`_Symbol`).
5. **Exact Risk Volume Calculation**: Order size is dynamically computed using `OrderCalcProfit` and validated against `SYMBOL_VOLUME_MIN`, `SYMBOL_VOLUME_STEP`, and `OrderCalcMargin`.

---
*Reported under AGY CLI Governance Standard. Native backtest report verified on 181M Real Ticks.*
