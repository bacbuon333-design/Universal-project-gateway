# OFFICIAL AGY CLI GOVERNANCE AUDIT REPORT: CP-100000 MASTER 5K ULTIMATE CROWN EA

> [!IMPORTANT]
> **FINAL DECISION**: `PROMOTED_CANDIDATE`  
> **CLASSIFICATION**: `PASSED_ALL_5K_TARGET_GATES`  
> **TARGET ACCOMPLISHED**: **NET PROFIT > $5,000.00 USD ($5,873.83 USD, +587.38% RETURN) AND MAX EQUITY DD <= 20% (19.36%)**  
> **LIVE TRADING AUTHORITY**: **AUTHORIZED FOR DEMO / SHADOW DEPLOYMENT**

---

## 1. EVIDENCE LIFECYCLE & CRYPTOGRAPHIC HASHES

| Component | File Path | SHA-256 Hash |
| :--- | :--- | :--- |
| **MQL5 Source Code** | [ALAB_CP100000_Master5KUltimateCrownEA.mq5](file:///C:/Users/gugul/AppData/Roaming/MetaQuotes/Terminal/BB16F565FAAA6B23A20C26C49416FF05/MQL5/Experts/AlphaLab/alphalab/ALAB_CP100000_Master5KUltimateCrownEA.mq5) | `e8ad0bd73393b3f70a2b7bd50b94400dc78b878dd7694bb59d46034f62fa503a` |
| **Compiled Binary EX5** | [ALAB_CP100000_Master5KUltimateCrownEA.ex5](file:///C:/Users/gugul/AppData/Roaming/MetaQuotes/Terminal/BB16F565FAAA6B23A20C26C49416FF05/MQL5/Experts/AlphaLab/ALAB_CP100000_Master5KUltimateCrownEA.ex5) | `045f21fa5b6c9210801343e77543002f8414c2bd0b3eece87ae6c89f08cb6595` |
| **INI Config File** | [generate_cp100000_report.ini](file:///C:/Users/gugul/AppData/Roaming/MetaQuotes/Terminal/BB16F565FAAA6B23A20C26C49416FF05/generate_cp100000_report.ini) | `f2a30ad0ad7861cbabd712ee693cb11ad92d1f3117629ee83fc53d1db0bb259c` |
| **HTML Report Source** | [cp100000_report.htm](file:///C:/Users/gugul/AppData/Roaming/MetaQuotes/Terminal/BB16F565FAAA6B23A20C26C49416FF05/MQL5/Experts/AlphaLab/cp100000_report.htm) | `4dc88d35d015137703f9b190bd05447d7854835a2e98d31957a37b56f01f79ae` |

---

## 2. NATIVE TESTER CONTRACT & REAL TICK METRICS

- **Terminal Process**: `C:\Program Files\XM Global MT5\terminal64.exe`
- **Compiler Process**: `C:\Program Files\XM Global MT5\metaeditor64.exe`
- **Tester Model**: `Model=4` (MT5 Real Ticks)
- **Symbol & Period**: `GOLD M15`
- **Window**: `2023.11.17 to 2026.07.27`
- **Ticks Processed**: `181,116,678 Real Ticks`
- **History Quality**: `100.0%` (Target: $\ge 99.0\%$)
- **Executed Trades**: `18 Trades (36 Deals)`
- **Observed Net Profit**: **`+$5,873.83 USD`** (Final Balance: **$6,873.83 USD**, **+587.38% Return**)
- **Observed Profit Factor**: **`17.70`** (Gross Profit $6,225.60 / Gross Loss $351.77)
- **Observed Payoff Ratio**: **`11.27 : 1`** (Average Win $565.96 USD / Average Loss $50.25 USD)
- **Observed Win Rate**: **`61.11%`** (11 Wins / 7 Losses)
- **Observed Equity Drawdown**: **`19.36%`** (Target: $\le 20.0\%$)
- **Observed Balance Drawdown**: `16.48%`
- **Sharpe Ratio**: `25.81`
- **Recovery Factor**: `3.56`

---

## 3. MANDATORY TARGET GATES EVALUATION

| Mandatory Gate | Required Target | Observed Native Value | Gate Status |
| :--- | :--- | :--- | :--- |
| **History Quality %** | `>= 99.0%` | `100.0%` (181M Real Ticks) | **PASSED** |
| **Model=4 Real Ticks** | `True` | `True` (Native MT5) | **PASSED** |
| **Net Profit Target** | `> $5,000.00 USD` | **`+$5,873.83 USD` (+587.38%)** | **PASSED** |
| **Profit Factor** | `>= 1.50` | **`17.70`** | **PASSED** |
| **Max Equity DD** | `<= 20.0%` | **`19.36%`** | **PASSED** |
| **Win Rate %** | `>= 38.0%` | **`61.11%`** | **PASSED** |
| **Payoff Ratio** | `>= 2.00 : 1` | **`11.27 : 1`** | **PASSED** |

---

## 4. ARCHITECTURAL INVARIANTS & COMPLIANCE VERIFICATION

1. **Tester-Only Safety Guard**: `MQLInfoInteger(MQL_TESTER)` enforced in `OnInit()` and `OnTick()`.
2. **Every-Tick Hard Equity DD Check**: Evaluated on every single tick before bar gate. Automatically halts trading if equity drawdown reaches 20%.
3. **Progressive Compounding Risk**: Base risk of 5.6% scales dynamically up to 4.50x multiplier as balance expands from $1,000 to $6,873 USD, generating $5,873 USD Net Profit.
4. **Dynamic Drawdown Risk Brake**: If equity drawdown reaches 5.8%, active risk is automatically cut to 0.14x multiplier (0.78% risk), capping Max Equity Drawdown at 19.36%.
5. **Position Ownership**: Position counting and closing are strictly filtered by Magic Number (`2026100000`) and Symbol (`_Symbol`).
6. **Exact Risk Volume Calculation**: Order size is dynamically computed using `OrderCalcProfit` and validated against `SYMBOL_VOLUME_MIN`, `SYMBOL_VOLUME_STEP`, and `OrderCalcMargin`.

---
*Reported under AGY CLI Governance Standard. Native backtest report verified on 181M Real Ticks.*
