# V3 TEMPORAL ROBUSTNESS & WINDOW ANALYSIS

This document analyzes the quarter-level, multi-quarter rolling, and calendar coverage robustness of **CAND-001** and **H-105** across 25 years of Gold H1 data.

---

## 1. COMPLETE VS PARTIAL QUARTER RECONCILIATION

* **Total Recorded Calendar Quarters**: 102 (from `2001Q2` to `2026Q3`).
* **Partial Boundary Quarters**:
  1. `2001Q2` (June 4 – June 30, 2001): 27 days only (Partial).
  2. `2026Q3` (July 1 – July 24, 2026): 24 days only (Partial).
* **Complete Calendar Quarters**: **100 Quarters** (from `2001Q3` through `2026Q2`).

---

## 2. QUARTER-LEVEL ACTIVITY & PASS DISTRIBUTION

| Metric | CAND-001 Benchmark | H-105 Minimalist | Interpretation |
| :--- | :--- | :--- | :--- |
| **Total Complete Quarters** | 100 | 100 | Full 25-year calendar |
| **No-Trade Quarters (0 trades)** | 50 (50.0%) | 49 (49.0%) | Low H1 trade frequency |
| **Low-Trade Quarters (1–2 trades)**| 31 (31.0%) | 31 (31.0%) | Sparse statistical sample |
| **Active Quarters ($\ge 3$ trades)** | 19 (19.0%) | 20 (20.0%) | Sufficient sample quarters |
| **PASS Quarters ($PF \ge 1.25, PnL > 0$)**| 9 | 9 | Consistently profitable |
| **FAIL Quarters ($PF < 0.90, PnL < 0$)**| 9 | 9 | Losing quarters |
| **INCONCLUSIVE Quarters** | 32 | 33 | Sample $< 3$ trades |
| **Active Quarter Pass Rate** | **47.4%** (9 / 19) | **45.0%** (9 / 20) | Active quarter consistency |
| **Full Calendar Pass Rate** | **9.0%** (9 / 100) | **9.0%** (9 / 100) | Full calendar coverage |

---

## 3. ROLLING MULTI-QUARTER WINDOW ANALYSIS

Because H1 trade frequency is low (~5.3 trades/year), individual quarterly pass rates underestimate temporal continuity. Multi-quarter rolling windows capture multi-year economic performance:

| Rolling Window Length | Total Windows | Profitable Windows ($\text{PnL} > 0$) | Windows with $PF \ge 1.20$ | Max Window Drawdown |
| :--- | :--- | :--- | :--- | :--- |
| **Rolling 4-Quarter (1-Year) CAND-001** | 97 | **35.1%** | 28.9% | $1,248.00 USD |
| **Rolling 4-Quarter (1-Year) H-105** | 97 | **34.0%** | 28.9% | $1,248.00 USD |
| **Rolling 8-Quarter (2-Year) CAND-001** | 93 | **35.5%** | 26.9% | $1,520.00 USD |
| **Rolling 8-Quarter (2-Year) H-105** | 93 | **36.6%** | 29.0% | $1,520.00 USD |

* **Temporal Clustering Insight**:
  - Between 2001 and 2011, Gold experienced lower intraday volatility, resulting in only 3 trades total across 40 calendar quarters. This produces a large cluster of $0.00 PnL zero-trade rolling windows.
  - From 2012 to 2026 (58 active quarters), rolling 4-quarter profitability rises to **62.1%**.
