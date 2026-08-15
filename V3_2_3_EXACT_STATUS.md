# V3.2.3 EXACT STATUS REPORT: FINAL SPECIFICATION AMBIGUITY RESOLUTION

## 1. REPOSITORY & DYNAMIC GIT METADATA
* **Repository**: [`bacbuon333-design/Universal-project-gateway`](https://github.com/bacbuon333-design/Universal-project-gateway)
* **Active Branch**: `research/quant-v3.2.3-final-ambiguity-resolution`
* **V3.2.2 Base Commit SHA**: `3096a37f8f4e90221887051b9ab999515d48ad52`
* **Original Precommit SHA**: `f5be62deba702fd737149c64b5faca3599f0daca`
* **Active HEAD Commit SHA**: `b07b64fc3a34ee6dfe02522111fc9f5ee59b2663`

---

## 2. DIRECT ANSWERS TO AUTHORITATIVE AUDIT QUESTIONS

1. **What did `>=2 bars` originally mean?**
   - In the project's historical codebase prior to precommit (`experiment_h101...`, `experiment_h200...`), BB/Keltner squeeze duration was operationally implemented as at least $k$ out of $k+1$ bars (`rolling(3).sum().shift(1) >= 2`), while range compression was implemented as 2 consecutive bars (`rolling(2)... >= 2`).
2. **Is that interpretation historically proven or ambiguous?**
   - **HISTORICALLY PROVEN** for BB/Keltner squeeze (H-204, H-207) and Range compression (H-206).
   - **AMBIGUOUS** for Volatility Ratio Contraction (H-205), as prior H-202 had no duration requirement.
3. **What did `EMA50 slope` originally mean?**
   - The precommit text did not specify a lookback horizon ($k=1, 3, 5$).
4. **Is the slope horizon historically proven or ambiguous?**
   - **SPECIFICATION AMBIGUOUS** — no unique parameter horizon was precommitted.
5. **Did H-208C originally include an EMA50 regime filter?**
   - The precommit table column for H-208C omitted EMA50, leaving the entry filter **SPECIFICATION AMBIGUOUS**.
6. **Which H-204→H-208 results are now exact?**
   - **`H-204`, `H-206`, `H-207`** are exact reproductions.
7. **Which remain unreproducible because the original specification was ambiguous?**
   - **`H-205`, `H-208A`, `H-208B`, `H-208C`** are formally classified as `SPECIFICATION AMBIGUOUS`.
8. **Does any validly reproduced hypothesis pass all original precommitted gates?**
   - **NO**. All validly reproduced hypotheses fail one or more hard precommitted gates.

---

## 3. COMPREHENSIVE EXACT REPRODUCTION RESULTS

| Hypothesis | Trades | Min/Q | Med/Q | Max/Q | Max Share | Max/Med | Gini | Top 3 Q PnL | Top 5 Q PnL | R4 Pos (%) | R4 PF $\ge 1.20$ (%) | PF | Expectancy ($) | Final Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`H-204`** | 311 | **4** | 9.0 | 19 | 6.1% | 2.11 | 0.217 | 102.1% | 121.8% | 73.3% | 53.3% | **1.256** | $+11.68 | **`VALIDLY REPRODUCED — REJECTED`** |
| **`H-205`** | 2545 | **50** | 79.0 | 98 | 3.9% | 1.24 | 0.100 | N/A (Loss) | N/A (Loss) | 6.7% | 3.3% | **0.962** | $-1.27 | **`SPECIFICATION AMBIGUOUS — DURATION SEMANTICS NOT HISTORICALLY PROVEN`** |
| **`H-206`** | 1623 | **32** | 49.0 | 63 | 3.9% | 1.29 | 0.076 | 178.7% | 206.0% | 40.0% | 10.0% | **1.087** | $+4.98 | **`VALIDLY REPRODUCED — REJECTED`** |
| **`H-207`** | 277 | **2** | 8.0 | 20 | 7.2% | 2.50 | 0.268 | 148.1% | 183.4% | 56.7% | 43.3% | **1.164** | $+7.10 | **`VALIDLY REPRODUCED — REJECTED`** |
| **`H-208A`** | 234 | **2** | 6.0 | 19 | 8.1% | 3.17 | 0.247 | 72.5% | 87.0% | 73.3% | 56.7% | **1.466** | $+17.09 | **`SPECIFICATION AMBIGUOUS — EXACT REPRODUCTION IMPOSSIBLE`** |
| **`H-208B`** | 227 | **1** | 6.0 | 15 | 6.6% | 2.50 | 0.255 | N/A (Loss) | N/A (Loss) | 50.0% | 36.7% | **0.889** | $-6.07 | **`SPECIFICATION AMBIGUOUS — EXACT REPRODUCTION IMPOSSIBLE`** |
| **`H-208C`** | 456 | **5** | 13.0 | 28 | 6.1% | 2.15 | 0.202 | 75.5% | 112.6% | 73.3% | 33.3% | **1.129** | $+5.89 | **`SPECIFICATION AMBIGUOUS — EXACT REPRODUCTION IMPOSSIBLE`** |

---

## 4. PRECOMMITTED BOOLEAN GATE MATRIX

| Hypothesis | Gate A (Min $\ge 5$) | Gate B1 (Share $\le 5\%$) | Gate B2 (Max/Med $\le 3$) | Gate B3 (Gini $< 0.3$) | Gate C1 (Top3 $\le 40\%$) | Gate C2 (Top5 $\le 60\%$) | Gate D1 (R4 Pos $\ge 70\%$) | Gate D2 (R4 PF $\ge 65\%$) | Gate E1 (PF $\ge 1.25$) | Gate E2 (Exp $> 0$) | ALL GATES PASS? |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`H-204`** | ❌ FAIL | ❌ FAIL | ✅ PASS | ✅ PASS | ❌ FAIL | ❌ FAIL | ✅ PASS | ❌ FAIL | ✅ PASS | ✅ PASS | **❌ REJECTED** |
| **`H-205`** | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS | ❌ FAIL | ❌ FAIL | ❌ FAIL | ❌ FAIL | ❌ FAIL | ❌ FAIL | **❌ REJECTED** |
| **`H-206`** | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS | ❌ FAIL | ❌ FAIL | ❌ FAIL | ❌ FAIL | ❌ FAIL | ✅ PASS | **❌ REJECTED** |
| **`H-207`** | ❌ FAIL | ❌ FAIL | ✅ PASS | ✅ PASS | ❌ FAIL | ❌ FAIL | ❌ FAIL | ❌ FAIL | ❌ FAIL | ✅ PASS | **❌ REJECTED** |
| **`H-208A`** | ❌ FAIL | ❌ FAIL | ❌ FAIL | ✅ PASS | ❌ FAIL | ❌ FAIL | ✅ PASS | ❌ FAIL | ✅ PASS | ✅ PASS | **❌ REJECTED** |
| **`H-208B`** | ❌ FAIL | ❌ FAIL | ✅ PASS | ✅ PASS | ❌ FAIL | ❌ FAIL | ❌ FAIL | ❌ FAIL | ❌ FAIL | ❌ FAIL | **❌ REJECTED** |
| **`H-208C`** | ✅ PASS | ❌ FAIL | ✅ PASS | ✅ PASS | ❌ FAIL | ❌ FAIL | ✅ PASS | ❌ FAIL | ❌ FAIL | ✅ PASS | **❌ REJECTED** |

---

## 5. NON-PRECOMMITTED INFORMATIVE DIAGNOSTICS

| Hypothesis | Rolling 8Q Pos (%) | Rolling 8Q PF $\ge 1.20$ (%) | Profitable Full Years (%) | 100-Pip Spread Stress PF |
| :--- | :--- | :--- | :--- | :--- |
| **`H-204`** | 73.1% | 50.0% | 85.7% | 1.131 |
| **`H-205`** | 7.7% | 0.0% | 0.0% | 0.740 |
| **`H-206`** | 23.1% | 7.7% | 42.9% | 0.970 |
| **`H-207`** | 57.7% | 38.5% | 57.1% | 1.004 |
| **`H-208A`** | 88.5% | 57.7% | 71.4% | 1.254 |
| **`H-208B`** | 42.3% | 26.9% | 42.9% | 0.773 |
| **`H-208C`** | 76.9% | 26.9% | 85.7% | 0.971 |

---

## 6. FINAL ACCEPTANCE STATEMENT

> ### **H-204 THROUGH H-208 CHAPTER PARTIALLY CLOSED — ORIGINAL SPECIFICATION AMBIGUITY REMAINS FOR H-205, H-208A/B/C.**
> ### **NO VALIDLY REPRODUCED HISTORICAL CANDIDATE PASSED THE DISTRIBUTED EDGE STANDARD.**
