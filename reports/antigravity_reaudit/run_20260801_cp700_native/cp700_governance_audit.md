# AGY CLI GOVERNANCE AUDIT REPORT: CP-700 MULTI-REGIME EA

> [!IMPORTANT]
> **FINAL DECISION**: `NO_SAFE_TARGET_CANDIDATE`  
> **CLASSIFICATION**: `REJECTED_LOW_REAL_TICK_QUALITY`  
> **LIVE TRADING AUTHORITY**: **NOT GRANTED**

---

## 1. EVIDENCE LIFECYCLE & CRYPTOGRAPHIC HASHES

| Component | File Path | SHA-256 Hash |
| :--- | :--- | :--- |
| **Governance Manifest** | [cp700_causal_multi_regime_v1.json](file:///C:/Users/gugul/AppData/Roaming/MetaQuotes/Terminal/BB16F565FAAA6B23A20C26C49416FF05/governance/cp700_causal_multi_regime_v1.json) | `8f2210111d70ea6547608fbadcc4e82e86db8e9ec50cb07a578949f8faf109ed` |
| **MQL5 Source Code** | [ALAB_CP700_MultiRegimeEA.mq5](file:///C:/Users/gugul/AppData/Roaming/MetaQuotes/Terminal/BB16F565FAAA6B23A20C26C49416FF05/MQL5/Experts/AlphaLab/alphalab/ALAB_CP700_MultiRegimeEA.mq5) | `035cba575ae1e64b3cc290225f56c70ffd93c949e23cb7a5e68c06dd01cc8ff5` |
| **Compiled Binary EX5** | [ALAB_CP700_MultiRegimeEA.ex5](file:///C:/Users/gugul/AppData/Roaming/MetaQuotes/Terminal/BB16F565FAAA6B23A20C26C49416FF05/MQL5/Experts/AlphaLab/ALAB_CP700_MultiRegimeEA.ex5) | `17c9343231807501c0a503651f66b7593ab69d2e66adbbf821060b9ae629bc77` |
| **INI Config File** | [generate_cp700_report.ini](file:///C:/Users/gugul/AppData/Roaming/MetaQuotes/Terminal/BB16F565FAAA6B23A20C26C49416FF05/generate_cp700_report.ini) | `4b13b14e9a7cc2f083fafb6a5a77abf6f2a668ed9675641538419471c5ed10c5` |

---

## 2. NATIVE TESTER CONTRACT & REAL TICK METRICS

- **Terminal Process**: `C:\Program Files\XM Global MT5\terminal64.exe`
- **Compiler Process**: `C:\Program Files\XM Global MT5\metaeditor64.exe`
- **Tester Model**: `Model=4` (MT5 Real Ticks)
- **Symbol & Period**: `GOLD M15`
- **Window**: `2022.05.01 to 2026.07.27`
- **Ticks Processed**: `225,125,541 Ticks`
- **History Quality**: `63.0%` (Target: $\ge 99.0\%$)

---

## 3. MANDATORY TARGET GATES EVALUATION

| Mandatory Gate | Required Target | Observed Value | Gate Status |
| :--- | :--- | :--- | :--- |
| **Net Profit** | `> $5,000.00 USD` | `$0.00 USD` | **FAILED** |
| **Profit Factor** | `>= 1.50` | `0.00` | **FAILED** |
| **Win Rate %** | `> 45.0%` | `0.00%` | **FAILED** |
| **Max Equity DD** | `<= 20.0%` | `0.00%` | **PASSED** |
| **History Quality** | `>= 99.0%` | `63.0%` | **FAILED** |
| **Model=4 Real Ticks** | `True` | `True` | **PASSED** |

---

## 4. SCIENTIFIC DIAGNOSIS & NEXT VALID RESEARCH STAGE

1. **History Quality Gate Violation**: The native MT5 server data for GOLD M15 from 2022 to 2026 exhibits only 63% history quality due to missing/discarded tick intervals. Under `AGY_CLI_NATIVE_MT5_DEVELOPMENT_PROTOCOL.md` Section 9, any dataset with history quality < 99% is strictly classified as diagnostic only and cannot be used for promotion.
2. **Conjunction Filter Overshoot**: The 7-layer conjunction filter (Quad H1 EMAs + M15 EMAs + BB breakout + RSI + wick ratio + 2 green bars) resulted in 0 trades over 225M real ticks.
3. **Next Valid Stage**: Shift to a cleaner native dataset (e.g. `US100Cash` / `US500Cash`) with confirmed $\ge 99\%$ history quality and test a preregistered two-sided causal architecture.

---
*Reported under AGY CLI Governance Standard. Backtests are research evidence, not a guarantee of future profit.*
