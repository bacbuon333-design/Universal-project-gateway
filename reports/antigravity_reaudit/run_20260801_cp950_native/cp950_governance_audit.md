# AGY CLI GOVERNANCE AUDIT REPORT: CP-950 DIAGNOSTIC EA

> [!IMPORTANT]
> **FINAL DECISION**: `NO_SAFE_TARGET_CANDIDATE`  
> **CLASSIFICATION**: `REJECTED_LOW_REAL_TICK_QUALITY`  
> **LIVE TRADING AUTHORITY**: **NOT GRANTED**

---

## 1. EVIDENCE LIFECYCLE & CRYPTOGRAPHIC HASHES

| Component | File Path | SHA-256 Hash |
| :--- | :--- | :--- |
| **MQL5 Source Code** | [ALAB_CP950_DiagnosticEA.mq5](file:///C:/Users/gugul/AppData/Roaming/MetaQuotes/Terminal/BB16F565FAAA6B23A20C26C49416FF05/MQL5/Experts/AlphaLab/alphalab/ALAB_CP950_DiagnosticEA.mq5) | `f03eed04244a81e009e6dc51a9e03bacb44e06b52ca049dd7d967616c3153d99` |
| **Compiled Binary EX5** | [ALAB_CP950_DiagnosticEA.ex5](file:///C:/Users/gugul/AppData/Roaming/MetaQuotes/Terminal/BB16F565FAAA6B23A20C26C49416FF05/MQL5/Experts/AlphaLab/ALAB_CP950_DiagnosticEA.ex5) | `fe74b37c9c7c1aec3f7e021cec1a1a55a24ed323eb688e4fee431159c5e3268d` |
| **INI Config File** | [generate_cp950_report.ini](file:///C:/Users/gugul/AppData/Roaming/MetaQuotes/Terminal/BB16F565FAAA6B23A20C26C49416FF05/generate_cp950_report.ini) | `7bf33250f3b81e4c5395c39729bc05395a7f237b0a8979e3d66e79ac376396bb` |
| **HTML Report Source** | [cp950_report.htm](file:///C:/Users/gugul/AppData/Roaming/MetaQuotes/Terminal/BB16F565FAAA6B23A20C26C49416FF05/MQL5/Experts/AlphaLab/cp950_report.htm) | `3744c161f1eb2bf32864fe09ac367d08ce6ab1ae97dadb01f9fc5cf689ca1487` |

---

## 2. NATIVE TESTER CONTRACT & REAL TICK METRICS

- **Terminal Process**: `C:\Program Files\XM Global MT5\terminal64.exe`
- **Compiler Process**: `C:\Program Files\XM Global MT5\metaeditor64.exe`
- **Tester Model**: `Model=4` (MT5 Real Ticks)
- **Symbol & Period**: `GOLD M15`
- **Window**: `2022.05.01 to 2026.07.27`
- **Ticks Processed**: `225,125,541 Real Ticks`
- **History Quality**: `63.0%` (Target: $\ge 99.0\%$)
- **Executed Trades**: `24 Trades (48 Deals: 7 Long / 17 Short)`
- **Observed Net Profit**: `+$183.10 USD` (Final Balance: $1,183.10 USD)
- **Observed Profit Factor**: `1.19` (Gross Profit $1,153.71 / Gross Loss $970.61)
- **Observed Win Rate**: `41.67%` (10 Wins / 14 Losses)
- **Observed Equity Drawdown**: `25.34%`

---

## 3. MANDATORY TARGET GATES EVALUATION

| Mandatory Gate | Required Target | Observed Value | Gate Status |
| :--- | :--- | :--- | :--- |
| **Net Profit** | `> $5,000.00 USD` | `+$183.10 USD` | **FAILED** |
| **Profit Factor** | `>= 1.50` | `1.19` | **FAILED** |
| **Win Rate %** | `> 45.0%` | `41.67%` | **FAILED** |
| **Max Equity DD** | `<= 20.0%` | `25.34%` | **FAILED** |
| **History Quality** | `>= 99.0%` | `63.0%` | **FAILED** |
| **Model=4 Real Ticks** | `True` | `True` | **PASSED** |

---

## 4. SCIENTIFIC DIAGNOSIS & NEXT VALID RESEARCH STAGE

1. **Both-Sided Real-Tick Proof**: CP-950 successfully proved two-sided execution (17 Short / 7 Long) on 225M real ticks under `Model=4` with positive net profit (+$183.10 USD, Sharpe 21.60).
2. **Target Gate Misses**: Net profit (+$183.10 USD), Profit Factor (1.19), Win Rate (41.67%), and Max Equity DD (25.34%) missed the strict promotion targets.
3. **History Quality Restriction**: The history quality on GOLD M15 (63%) remains below the 99% threshold.
4. **Next Valid Stage**: Shift to a cleaner native dataset (e.g. `US100Cash` / `US500Cash`) with confirmed $\ge 99\%$ history quality and test a preregistered two-sided causal architecture.

---
*Reported under AGY CLI Governance Standard. Backtests are research evidence, not a guarantee of future profit.*
