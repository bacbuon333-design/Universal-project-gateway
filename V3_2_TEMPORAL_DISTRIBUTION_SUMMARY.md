# V3.2 TEMPORAL DISTRIBUTION SUMMARY & CANDIDATE EVALUATION (REPAIRED V3.2.1)

This report summarizes the multi-stage evaluation of hypotheses H-204 through H-208 against the V3.2 Hard Temporal Distribution Standard across the 33 complete historical quarters of Gold M30 (`2018Q2` to `2026Q2`) following the V3.2.1 SL/TP distance interface repair.

---

## 1. COMPREHENSIVE REPAIRED DISCOVERY RESULTS MATRIX

| Hypothesis | Core Mechanism | Total Trades | Min Trades/Q | Max/Med Ratio | Trade Gini | Zero-Trade Qs | Profitable Full Years (%) | Rolling 4Q Pos (%) | Rolling 4Q PF $\ge$ 1.20 (%) | Top 3 Q PnL Share | Profit Factor | 100-Pip Stress PF | V3.2.1 Final Classification |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`H-204`** | Light Trend Squeeze (EMA 20/50) | 311 | **4** (FAIL) | 2.11 | 0.217 | **0** | 71.4% (5/7) | **73.3%** | **53.3% (FAIL)** | 71.4% | **1.256** | 1.012 | **`REJECTED`** |
| **`H-205`** | Volatility Ratio Contraction (0.80) | 2,545 | **50** (PASS) | 1.24 | **0.100** | **0** | 14.3% (1/7) | 6.7% | 3.3% (FAIL) | N/A | **0.962** (FAIL) | 0.814 | **`REJECTED`** |
| **`H-206`** | Range Compression ($0.65\times\text{ATR}$) | 1,492 | **30** (PASS) | 1.26 | **0.072** | **0** | 42.9% (3/7) | 43.3% | 16.7% (FAIL) | 68.9% | **1.117** (FAIL) | 0.938 | **`REJECTED`** |
| **`H-207`** | Session Squeeze (07:00–17:00 UTC) | 277 | **2** (FAIL) | 2.50 | 0.268 | **0** | 71.4% (5/7) | 56.7% | 43.3% (FAIL) | 79.4% | **1.164** (FAIL) | 0.952 | **`REJECTED`** |
| **`H-208A`**| Long-Only Squeeze | 161 | **1** (FAIL) | 3.25 | 0.312 | **0** | 71.4% (5/7) | 66.7% | 46.7% (FAIL) | 74.2% | **1.444** | 1.182 | **`REJECTED`** |
| **`H-208B`**| Short-Only Squeeze | 151 | **1** (FAIL) | 2.75 | 0.320 | **0** | 57.1% (4/7) | 66.7% | 56.7% (FAIL) | 88.5% | **1.081** (FAIL) | 0.894 | **`REJECTED`** |
| **`H-208C`**| Asymmetric Squeeze (Long 2x, Short 3x) | 420 | **5** (PASS) | 1.92 | 0.202 | **0** | 71.4% (5/7) | **73.3% (PASS)**| **40.0% (FAIL)**| **84.6% (FAIL)** | **1.070** (FAIL) | 0.891 | **`REJECTED`** |

---

## 2. SCIENTIFIC DIAGNOSIS & MANDATE COMPLIANCE

1. **Trade-Frequency vs Economic Edge Reality**:
   - Pure volatility/range contraction breakouts (`H-205`, `H-206`) generate massive, highly uniform event counts ($1,492$ to $2,545$ trades, Gini $\le 0.10$, Min/Q $\ge 30$), but when subjected to realistic bid-ask spread (25 pips) and commission ($7/lot), their gross edges are completely consumed ($PF = 0.962$ and $PF = 1.117$).
   - Squeeze-based setups (`H-204`, `H-208A`) generate legitimate positive expectancy ($PF = 1.256$ to $1.444$), but fail Gate 12A because 1–2 quiet market quarters drop below the mandatory 5 trades/quarter mark (e.g. H-204 Min/Q = 4).
   - Asymmetric sizing (`H-208C`) passes the trade frequency gate ($\ge 5$ in 100% of quarters, 420 trades), but fails the economic consistency gate ($PF = 1.070$, Rolling 4Q $PF \ge 1.20$ is only $40.0\% < 65\%$).

---

## 3. FINAL SCIENTIFIC VERDICT

### **NO HISTORICAL CANDIDATE PASSED V3.2 DISTRIBUTED EDGE STANDARD**
