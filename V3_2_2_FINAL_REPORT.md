# V3.2.2 FINAL SCIENTIFIC AUDIT REPORT: EXACT PRECOMMIT RECONCILIATION & REPRODUCTION

## 1. REPOSITORY & EXACT GIT COMMIT TOPOLOGY
* **Repository**: [`bacbuon333-design/Universal-project-gateway`](https://github.com/bacbuon333-design/Universal-project-gateway)
* **V3.2.1 Base Commit**: `fe6a08c6c3c83a28977a52330673f9ff9ff2529d`
* **Original Precommit Commit**: `f5be62deba702fd737149c64b5faca3599f0daca`
* **Audit & Reconciliation Plan Commit**: `4811e67e3df18aa0ebbb92e0132df6ff09a39f60`
* **Implementation Fix & Test Suite Commit**: `5f2f02c4fc7ae0caae04ea095c93c4dfc4069c1c`

---

## 2. PRECOMMIT RECONCILIATION SUMMARY

| Hypothesis | Precommitted Rules | Implementation Status in V3.2.1 | V3.2.2 Correction | Reconciliation Status |
| :--- | :--- | :--- | :--- | :--- |
| **`H-204`** | Squeeze $\ge 2$b, `EMA20 > EMA50`, TP=2.5x | Drifted (`c > ema20` added) | Removed extra close filter | **`EXACT REPRODUCTION`** |
| **`H-205`** | Vol Ratio $\le 0.80$, Donchian 10, TP=2.5x | Exact match | Retained | **`EXACT REPRODUCTION`** |
| **`H-206`** | Range $\le 0.65$ ATR, 3b Breakout + EMA50 | Drifted (3b EMA50 slope added) | Removed slope filter | **`EXACT REPRODUCTION`** |
| **`H-207`** | Squeeze $\ge 2$b, 07:00-17:00 UTC + EMA50 | Exact match | Retained | **`EXACT REPRODUCTION`** |
| **`H-208A`**| Long-Only Squeeze, EMA50 slope, TP=2.0x | Drifted (Inherited H-204 & TP=2.5x) | Decoupled, set TP=2.0x SL | **`EXACT REPRODUCTION`** |
| **`H-208B`**| Short-Only Squeeze, EMA50 slope, TP=3.0x | Drifted (Inherited H-204 & TP=2.5x) | Decoupled, set TP=3.0x SL | **`EXACT REPRODUCTION`** |
| **`H-208C`**| Symmetrical entries, Asymmetric TP (2x/3x) | Drifted (EMA50 slope added) | Removed slope, pure symmetrical | **`EXACT REPRODUCTION`** |

---

## 3. AUTHORITATIVE MACHINE-GENERATED EXACT REPRODUCTION RESULTS

| Hypothesis | Trades | Min/Q | Med/Q | Max/Q | Max Share | Max/Med | Gini | Top 3 Q PnL | Top 5 Q PnL | R4 Pos (%) | R4 PF $\ge 1.20$ (%) | PF | Expectancy ($) | Final Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`H-204`** | 311 | **4** | 9.0 | 19 | 6.1% | 2.11 | 0.217 | 102.1% | 121.8% | 73.3% | 53.3% | **1.256** | $+11.68 | **`VALIDLY REPRODUCED — REJECTED`** |
| **`H-205`** | 2545 | **50** | 79.0 | 98 | 3.9% | 1.24 | 0.100 | N/A (Loss) | N/A (Loss) | 6.7% | 3.3% | **0.962** | $-1.27 | **`VALIDLY REPRODUCED — REJECTED`** |
| **`H-206`** | 1623 | **32** | 49.0 | 63 | 3.9% | 1.29 | 0.076 | 178.7% | 206.0% | 40.0% | 10.0% | **1.087** | $+4.98 | **`VALIDLY REPRODUCED — REJECTED`** |
| **`H-207`** | 277 | **2** | 8.0 | 20 | 7.2% | 2.50 | 0.268 | 148.1% | 183.4% | 56.7% | 43.3% | **1.164** | $+7.10 | **`VALIDLY REPRODUCED — REJECTED`** |
| **`H-208A`** | 234 | **2** | 6.0 | 19 | 8.1% | 3.17 | 0.247 | 72.5% | 87.0% | 73.3% | 56.7% | **1.466** | $+17.09 | **`VALIDLY REPRODUCED — REJECTED`** |
| **`H-208B`** | 227 | **1** | 6.0 | 15 | 6.6% | 2.50 | 0.255 | N/A (Loss) | N/A (Loss) | 50.0% | 36.7% | **0.889** | $-6.07 | **`VALIDLY REPRODUCED — REJECTED`** |
| **`H-208C`** | 456 | **5** | 13.0 | 28 | 6.1% | 2.15 | 0.202 | 75.5% | 112.6% | 73.3% | 33.3% | **1.129** | $+5.89 | **`VALIDLY REPRODUCED — REJECTED`** |

---

## 4. PRECOMMITTED GATE AUDIT BREAKDOWN (BOOLEAN VERIFICATION)

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

## 5. NON-PRECOMMITTED INFORMATIVE DIAGNOSTICS (DIAGNOSTIC USE ONLY)

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

## 6. FINAL ACCEPTANCE STATEMENT & SCIENTIFIC CONCLUSION

Every single hypothesis from H-204 through H-208 has been reconciled against the original Git precommit, repaired of all implementation drift, verified through comprehensive multi-asset integration tests, and evaluated against the exact precommitted gates.

> ### **H-204 THROUGH H-208 EXACT REPRODUCTION CHAPTER CLOSED.**
> ### **NO HISTORICAL CANDIDATE PASSED V3.2 DISTRIBUTED EDGE STANDARD.**
