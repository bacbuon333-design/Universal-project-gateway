# V3.2 TEMPORAL DISTRIBUTION SUMMARY & CANDIDATE EVALUATION

This report summarizes the multi-stage evaluation of hypotheses H-204 through H-208 against the V3.2 Hard Temporal Distribution Standard across the 33 complete historical quarters of Gold M30 (`2018Q2` to `2026Q2`).

---

## 1. COMPREHENSIVE V3.2 DISCOVERY RESULTS MATRIX

| Hypothesis | Core Mechanism | Total Trades | Min Trades/Q | Max/Med Ratio | Trade Gini | Zero-Trade Qs | Profitable Full Years (%) | Rolling 4Q Pos (%) | Rolling 4Q PF $\ge$ 1.20 (%) | Top 3 Q PnL Share | Profit Factor | 100-Pip Stress PF | V3.2 Final Classification |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`H-204`** | Light Trend Squeeze (EMA 20/50) | 235 | **3** (FAIL) | 1.86 | 0.183 | **0** | 71.4% (5/7) | 63.3% | 50.0% | 78.4% | 1.173 | 0.985 | **`REJECTED`** |
| **`H-205`** | Volatility Ratio Contraction (0.80) | 641 | **15** (PASS) | 1.05 | **0.037** | **0** | 28.6% (2/7) | 36.7% | 13.3% | 94.2% | **0.860** (FAIL) | 0.724 | **`REJECTED`** |
| **`H-206`** | Range Compression ($0.65\times\text{ATR}$) | 601 | **16** (PASS) | 1.11 | **0.033** | **0** | 57.1% (4/7) | 63.3% | 40.0% | 61.2% | **1.134** (FAIL) | 0.942 | **`REJECTED`** |
| **`H-207`** | Session Squeeze (07:00–17:00 UTC) | 195 | **2** (FAIL) | 2.00 | 0.230 | **0** | 71.4% (5/7) | 60.0% | 50.0% | 82.1% | 1.392 | 1.140 | **`REJECTED`** |
| **`H-208A`**| Long-Only Squeeze | 134 | **1** (FAIL) | 2.25 | 0.284 | **0** | 57.1% (4/7) | 66.7% | 60.0% | 84.6% | 1.301 | 1.082 | **`REJECTED`** |
| **`H-208B`**| Short-Only Squeeze | 126 | **1** (FAIL) | 2.00 | 0.294 | **0** | 71.4% (5/7) | 63.3% | 56.7% | 81.2% | 1.389 | 1.175 | **`REJECTED`** |
| **`H-208C`**| Asymmetric Squeeze (Long 2x, Short 3x) | 289 | **5** (PASS) | 1.88 | 0.157 | **0** | 71.4% (5/7) | **73.3% (PASS)**| **40.0% (FAIL)**| **89.1% (FAIL)** | 1.255 | 1.052 | **`REJECTED`** |

---

## 2. SCIENTIFIC DIAGNOSIS & MANDATE COMPLIANCE

1. **Trade-Frequency vs Economic Edge Trade-Off**:
   - High-frequency range/volatility contraction breakouts (`H-205`, `H-206`) produce exceptionally uniform trade frequency (Gini $\sim 0.03$, Min/Q $\ge 15$), but fail to overcome the 25-pip spread friction on M30, producing unviable Profit Factors ($0.860$ and $1.134$).
   - Squeeze-based breakout systems (`H-204`, `H-207`, `H-208A`, `H-208B`) generate profitable Profit Factors ($1.30–1.39$), but fail Gate 12A because 1–3 quieter quarters dip below the mandatory $\ge 5$ trades threshold.
   - Asymmetric Squeeze (`H-208C`) achieves $\ge 5$ trades in 100% of quarters (Min = 5), but fails the strict profit distribution standard ($89.1\%$ of total profit generated in just 3 quarters) and rolling consistency ($40\% < 65\%$).

---

## 3. FINAL V3.2 SCIENTIFIC VERDICT

### **NO HISTORICAL CANDIDATE PASSED V3.2 DISTRIBUTED EDGE STANDARD**
*(Every tested hypothesis either fails the $\ge 5$ trades per complete quarter gate, fails the cost-adjusted economic profitability threshold, or fails the rolling window / profit concentration gate).*
