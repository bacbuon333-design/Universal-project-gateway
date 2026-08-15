# V3.2.3 SPECIFICATION RESOLUTION AUDIT REPORT
## RIGOROUS PRECOMMIT AMBIGUITY DECOMPOSITION & HISTORICAL EVIDENCE AUDIT

This document establishes the authoritative resolution of specification ambiguities for hypotheses H-204 through H-208 based strictly on historical artifacts predating the original precommit commit (`f5be62deba702fd737149c64b5faca3599f0daca`).

---

## 1. ISSUE #1: SEMANTICS OF ">= 2 BARS" COMPRESSION / SQUEEZE

### A. Historical Evidence Audit
1. **BB / Keltner Squeeze Duration (`H-204`, `H-207`)**:
   - In V3 (`experiment_h101_directionality_and_trigger_study.py` at `b983d57`): Squeeze duration was implemented as $\ge 4$ of previous 5 bars (`rolling(5).sum().shift(1) >= 4`).
   - In V3.1 (`experiment_h200_to_h203_high_frequency.py` at `ee40ec8`): Squeeze duration was implemented as $\ge 2$ of previous 3 bars (`rolling(3).sum().shift(1) >= 2`).
   - *Conclusion*: **HISTORICALLY PROVEN CONVENTION** for BB/Keltner squeeze mechanisms.
2. **Range Compression Duration (`H-206`)**:
   - In V3.1 (`make_h201_signals` / `make_h206_signals`): Range compression $(H-L) \le k\times\text{ATR}$ was implemented as 2 consecutive bars (`rolling(2)... >= 2`).
   - *Conclusion*: **HISTORICALLY PROVEN CONVENTION** for bar range compression.
3. **Volatility Ratio Contraction Duration (`H-205`)**:
   - In V3.1 (`H-202` in `experiment_h200_to_h203_high_frequency.py`): The ratio $\text{ATR}(14)/\text{ATR}(50) \le 0.85$ had NO duration requirement (`is_contracted = atr_ratio <= 0.85`).
   - The precommit text `V3_2_PRECOMMIT_H204_PLUS.md` introduced "$\ge 2$ bars" for the ATR ratio for the first time without prior code precedent.
   - *Conclusion*: Inferring `2-of-3` for volatility ratio contraction was an unproven extrapolation. Hence, **`H-205: SPECIFICATION AMBIGUOUS — DURATION SEMANTICS NOT HISTORICALLY PROVEN`**.

---

## 2. ISSUE #2: EMA50 SLOPE HORIZON FOR H-208A & H-208B

- The precommit text `V3_2_PRECOMMIT_H204_PLUS.md` never specified a lookback horizon ($k=1, 3, 5$) for the EMA50 slope.
- *Conclusion*: **`SPECIFICATION AMBIGUOUS — EXACT REPRODUCTION IMPOSSIBLE`**.

---

## 3. ISSUE #3: H-208C DIRECTIONAL / REGIME FILTER

- The precommit table column for `H-208C` omitted any reference to `EMA(50)`, leaving the entry filter ambiguous between pure breakout and filtered breakout.
- *Conclusion*: **`SPECIFICATION AMBIGUOUS — EXACT REPRODUCTION IMPOSSIBLE`**.

---

## 4. FINAL RECONCILIATION SUMMARY TABLE

| Hypothesis | Precommit Description | Operational Semantics Used | Ambiguity Status | Final V3.2.3 Status |
| :--- | :--- | :--- | :--- | :--- |
| **`H-204`** | Squeeze $\ge 2$b, `EMA20 > EMA50`, TP=2.5x | 2-of-3 Squeeze, pure EMA20/50, TP=2.5x | Unambiguous | **`VALIDLY REPRODUCED — REJECTED`** |
| **`H-205`** | Vol Ratio $\le 0.80$, Donchian 10, TP=2.5x | Volatility ratio duration unproven | **Ambiguous Duration** | **`SPECIFICATION AMBIGUOUS — DURATION SEMANTICS NOT HISTORICALLY PROVEN`** |
| **`H-206`** | Range $\le 0.65$ ATR, 3b Breakout + EMA50 | 2 cons. Range, 3b Breakout + EMA50, TP=2.5x | Unambiguous | **`VALIDLY REPRODUCED — REJECTED`** |
| **`H-207`** | Squeeze $\ge 2$b, 07:00-17:00 UTC + EMA50 | 2-of-3 Squeeze, Session 07-17, TP=2.5x | Unambiguous | **`VALIDLY REPRODUCED — REJECTED`** |
| **`H-208A`**| Long-Only Squeeze, Bullish EMA50 slope | Slope horizon unspecified in precommit | **Ambiguous Spec** | **`SPECIFICATION AMBIGUOUS — EXACT REPRODUCTION IMPOSSIBLE`** |
| **`H-208B`**| Short-Only Squeeze, Bearish EMA50 slope | Slope horizon unspecified in precommit | **Ambiguous Spec** | **`SPECIFICATION AMBIGUOUS — EXACT REPRODUCTION IMPOSSIBLE`** |
| **`H-208C`**| Symmetrical entries, Asymmetric TP | Entry filter unspecified in precommit | **Ambiguous Spec** | **`SPECIFICATION AMBIGUOUS — EXACT REPRODUCTION IMPOSSIBLE`** |
