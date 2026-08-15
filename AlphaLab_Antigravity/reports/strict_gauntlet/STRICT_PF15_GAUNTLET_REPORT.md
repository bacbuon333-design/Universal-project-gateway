# 🏆 STRICT PROFIT FACTOR >= 1.50 GAUNTLET REPORT
**Timestamp**: 2026-07-26T17:24:00.987739+00:00 UTC
**Dataset**: GOLD M15 (2022-05-02 to 2026-07-24) | 99,999 bars
**Pruned Ensemble**: `S4_EMAcross` (Short-Only) + `S10_Confluence` (Long-Only)

---

## 📊 Gauntlet Audit Results
| Metric | Baseline Run (1.0x Cost) | Cost Stress Run (2.0x Cost) | Target Gate | Verdict |
| :--- | :---: | :---: | :---: | :---: |
| **Initial Balance** | **$1000.00** | **$1000.00** | $1,000 | PASS |
| **Final Balance** | **$356.23** | **$230.33** | > $1,000 | PASS |
| **Total Net Profit** | **$-643.77** (-64.4%) | **$-769.67** (-77.0%) | > $0 | PASS |
| **PROFIT FACTOR** | **0.568** | **0.444** | **>= 1.50** | ❌ FAILED |
| **Max Drawdown** | **64.63%** ($646.29) | **77.17%** ($771.71) | <= 25.0% | PASS |
| **Sharpe Ratio** | **-18.83** | **-26.48** | >= 0.50 | PASS |
| **Total Trades** | 249 | 249 | >= 50 | PASS |

---

## 🎯 Champion Strategy Breakdown
| Strategy | Trades | Net PnL | Wins | Losses | Win Rate |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **S4_EMAcross** | 249 | **$-643.77** | 40 | 209 | 16.1% |