# V3.1 HARD TEMPORAL DISTRIBUTION AUDIT REPORT

This report audits **CAND-001** and **CAND-002** against the V3.1 Hard Temporal Distribution Standard across the 100 complete historical quarters (`2001Q3` to `2026Q2`).

---

## 1. HARD TEMPORAL DISTRIBUTION GATES EVALUATION

| Requirement / Standard | Precommitted Hard Threshold | CAND-001 Benchmark | CAND-002 Minimalist | Audit Verdict |
| :--- | :--- | :--- | :--- | :--- |
| **Gate 12A: Min Trades per Quarter** | $\ge 5$ trades in **EVERY** complete quarter (100/100) | **8 / 100** ($92$ failed quarters, $48$ zero-trade) | **8 / 100** ($92$ failed quarters, $47$ zero-trade) | **FAILED (REJECTED)** |
| **Gate 12B: Min Trades per Year** | $\ge 20$ trades in **EVERY** full year (24/24) | **1 / 24** (4.2% compliance) | **1 / 24** (4.2% compliance) | **FAILED (REJECTED)** |
| **Gate 12C: Min Historical Sample** | $\approx \ge 500$ trades over 100 quarters | **136 trades** | **144 trades** | **FAILED (REJECTED)** |
| **Gate 14: Trade Concentration** | No quarter $> 5\%$, $\text{Max}/\text{Median} \le 3.0$ | Max/Med = **8.00**, Gini = **0.665** | Max/Med = **8.00**, Gini = **0.656** | **FAILED (REJECTED)** |
| **Gate 15: Profit Distribution** | Top 3 Quarters $\le 40\%$, Top 5 $\le 60\%$ | Top 3 = **80.9%**, Top 5 = **97.9%** | Top 3 = **84.5%**, Top 5 = **102.3%** | **FAILED (SEVERE)** |
| **Gate 16: Rolling 4Q Windows** | $\ge 70\%$ Profitable, $\ge 65\%$ with $PF \ge 1.20$ | **35.1%** Profitable, **28.9%** $PF \ge 1.20$ | **34.0%** Profitable, **28.9%** $PF \ge 1.20$ | **FAILED (REJECTED)** |
| **Gate 16: Rolling 8Q Windows** | $\ge 75\%$ Profitable, $\ge 70\%$ with $PF \ge 1.20$ | **35.5%** Profitable, **26.9%** $PF \ge 1.20$ | **36.6%** Profitable, **29.0%** $PF \ge 1.20$ | **FAILED (REJECTED)** |
| **Gate 17: Profitable Full Years** | $\ge 70\%$ of complete calendar years profitable | **29.2%** (7 / 24 years) | **29.2%** (7 / 24 years) | **FAILED (REJECTED)** |

---

## 2. SCIENTIFIC DIAGNOSIS & MANDATE COMPLIANCE

* **Both CAND-001 and CAND-002 are formally REJECTED for promotion under the V3.1 Hard Temporal Distribution Standard**.
* **Rationale**: Despite attractive full-history aggregate Profit Factors ($1.837$ and $1.752$), both strategies suffer from extreme temporal sparsity ($\sim 5.3$ trades/year), $47–48$ completely inactive quarters, and extreme profit concentration ($>80\%$ of 25-year profit generated in just 3 quarters).
* As per Section 19 and Section 41: **No retrofitting, no manufactured trades, and no quarter-specific hacks are allowed. They remain immutable historical benchmarks.**
