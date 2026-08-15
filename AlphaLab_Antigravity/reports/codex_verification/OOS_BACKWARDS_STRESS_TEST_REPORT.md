# 🔍 OUT-OF-SAMPLE (OOS) BACKWARDS STRESS TEST REPORT
**Timestamp**: 2026-07-26T18:04:57.311693+00:00 UTC
**Counter-Audit Focus**: Testing identical configuration on Out-Of-Sample historical years

---

## 📊 Multi-Year OOS Audit Matrix
| Historical Window | Sample Type | Initial Balance | FINAL BALANCE | Net Profit ($) | PROFIT FACTOR | Max Drawdown | Total Trades | Win Rate | Verdict |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **2024-05-01 -> 2025-05-01** | In-Sample (IS) | $1,000.00 | **$3,548.32** | **$+2,548.32** | **2.093** | 16.65% | 82 | 34.1% | 🏆 **Baseline Champion** |
| **2023-05-01 -> 2024-05-01** | Previous OOS 1 | $1,000.00 | **$1,009.97** | **$+9.97** | **1.010** | 31.54% | 60 | 18.3% | 🏆 **PASSED** |
| **2022-05-02 -> 2023-05-01** | Previous OOS 2 | $1,000.00 | **$1,193.08** | **$+193.08** | **1.162** | 25.14% | 69 | 24.6% | 🏆 **PASSED** |
| **2025-05-01 -> 2026-07-24** | Forward OOS 3 | $1,000.00 | **$763.68** | **$-236.32** | **0.753** | 30.70% | 79 | 19.0% | ❌ Sụt giảm |