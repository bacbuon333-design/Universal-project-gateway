# V3.2.3 SPECIFICATION RESOLUTION AUDIT REPORT
## RIGOROUS PRECOMMIT AMBIGUITY DECOMPOSITION & HISTORICAL EVIDENCE AUDIT

This document establishes the authoritative resolution of the three remaining specification ambiguities for hypotheses H-204 through H-208 based strictly on historical artifacts predating the original precommit commit (`f5be62deba702fd737149c64b5faca3599f0daca`).

---

## 1. ISSUE #1: SEMANTICS OF ">= 2 BARS" COMPRESSION / SQUEEZE

### A. Historical Evidence Audit
1. **Pre-Precommit Codebase Search**:
   - In V3 (`AlphaLab_Antigravity/src/experiment_h101_directionality_and_trigger_study.py` at `b983d57`):
     ```python
     is_sqz = (bb_u < kelt_u) & (bb_l > kelt_l)
     sqz_cnt = pd.Series(is_sqz.astype(int)).rolling(5).sum().values
     was_sqz = (pd.Series(sqz_cnt).shift(1).values >= 4)
     ```
     *Observation*: "Squeeze $\ge 4$ bars" was implemented as $\ge 4$ of previous 5 bars.
   - In V3.1 (`AlphaLab_Antigravity/src/experiment_h200_to_h203_high_frequency.py` at `ee40ec8`):
     ```python
     is_sqz = (bb_u < kelt_u) & (bb_l > kelt_l)
     sqz_cnt = pd.Series(is_sqz.astype(int)).rolling(3).sum().values
     was_sqz = (pd.Series(sqz_cnt).shift(1).values >= 2)
     ```
     *Observation*: "Squeeze $\ge 2$ bars" was operationally implemented as $\ge 2$ of previous 3 bars.
   - In V3.1 H-206 (`make_h206_signals`):
     ```python
     is_comp = ((h - l) <= 0.65 * atr14)
     was_comp = (pd.Series(is_comp.astype(int)).rolling(2).sum().shift(1).values >= 2)
     ```
     *Observation*: Range compression was implemented as 2 consecutive bars.

### B. Resolution & Classification
- **Historical Convention Status**: **HISTORICAL CODE CONVENTION PROVEN (`2-of-3 bars` for Squeeze, `2 consecutive bars` for Range Compression)**.
- **Decision**: The existing implementation faithfully reflects the operational coding convention established in V3/V3.1 prior to the H-204 precommit.
- **Affected Hypotheses**: H-204, H-205, H-206, H-207.

---

## 2. ISSUE #2: EMA50 SLOPE HORIZON FOR H-208A & H-208B

### A. Historical Evidence Audit
1. **Precommit Text**:
   - `H-208A`: "Bullish EMA(50) slope"
   - `H-208B`: "Bearish EMA(50) slope"
2. **Codebase Pre-Precommit Search**:
   - In H-200 (`experiment_h200_to_h203_high_frequency.py`), trend alignment was written as:
     `bull = (c > ema50) & (ema50 > pd.Series(ema50).shift(3).values)`
   - In V3.2.2, H-208A/B used:
     `bull_slope = (ema50 > pd.Series(ema50).shift(1).values)`
3. **Audit Finding**:
   - The precommit text `V3_2_PRECOMMIT_H204_PLUS.md` never specified whether "slope" meant 1-bar, 3-bar, 5-bar, or percentage slope.
   - While 1-bar difference is the standard discrete derivative ($\Delta \text{EMA} = \text{EMA}[i] - \text{EMA}[i-1]$), the lack of explicit horizon $k$ in the precommit leaves the exact parameterization underspecified.

### B. Resolution & Classification
- **Status**: **SPECIFICATION AMBIGUOUS — EXACT REPRODUCTION IMPOSSIBLE WITHOUT POST-HOC ASSUMPTION**.
- **Decision**: For scientific integrity, H-208A and H-208B are formally classified as **`SPECIFICATION AMBIGUOUS — EXACT REPRODUCTION IMPOSSIBLE`** because their slope horizon was never precommitted. (Their 1-bar baseline results are preserved and reported as non-binding audit references only).

---

## 3. ISSUE #3: H-208C DIRECTIONAL / REGIME FILTER

### A. Historical Evidence Audit
1. **Precommit Text (`V3_2_PRECOMMIT_H204_PLUS.md`)**:
   - `H-208C`: `BB inside Keltner for >= 2 bars | Symmetrical entries, Asymmetric TP (2.0x Long, 3.0x Short) | Dynamic | Fixed`
   - Unlike H-204/205/206/207/208A/208B, `H-208C` **omitted any reference to `EMA(50)`** in its precommitment specification.
2. **Pre-Precommit Design Intent**:
   - The V3.2 prompt requested: "LONG only (H-208A), SHORT only (H-208B), symmetric Long+Short (H-208C)".
   - However, whether "symmetrical entries" meant pure squeeze breakout (`c > bb_u` / `c < bb_l` without any filter) or breakout with a symmetrical regime filter (`c > ema50` / `c < ema50`) was never explicitly written down.

### B. Resolution & Classification
- **Status**: **SPECIFICATION AMBIGUOUS — EXACT REPRODUCTION IMPOSSIBLE**.
- **Decision**: We do NOT invent a rule post-hoc. H-208C is formally classified as **`SPECIFICATION AMBIGUOUS — EXACT REPRODUCTION IMPOSSIBLE`**.

---

## 4. FINAL RECONCILIATION SUMMARY TABLE

| Hypothesis | Precommit Description | Operational Semantics Used | Ambiguity Status | Final V3.2.3 Status |
| :--- | :--- | :--- | :--- | :--- |
| **`H-204`** | Squeeze $\ge 2$b, `EMA20 > EMA50`, TP=2.5x | 2-of-3 Squeeze, pure EMA20/50, TP=2.5x | Unambiguous | **`VALIDLY REPRODUCED — REJECTED`** |
| **`H-205`** | Vol Ratio $\le 0.80$, Donchian 10, TP=2.5x | 2-of-3 Ratio, Donchian 10, TP=2.5x | Unambiguous | **`VALIDLY REPRODUCED — REJECTED`** |
| **`H-206`** | Range $\le 0.65$ ATR, 3b Breakout + EMA50 | 2 cons. Range, 3b Breakout + EMA50, TP=2.5x | Unambiguous | **`VALIDLY REPRODUCED — REJECTED`** |
| **`H-207`** | Squeeze $\ge 2$b, 07:00-17:00 UTC + EMA50 | 2-of-3 Squeeze, Session 07-17, TP=2.5x | Unambiguous | **`VALIDLY REPRODUCED — REJECTED`** |
| **`H-208A`**| Long-Only Squeeze, Bullish EMA50 slope | Slope horizon unspecified in precommit | **Ambiguous Spec** | **`SPECIFICATION AMBIGUOUS — EXACT REPRODUCTION IMPOSSIBLE`** |
| **`H-208B`**| Short-Only Squeeze, Bearish EMA50 slope | Slope horizon unspecified in precommit | **Ambiguous Spec** | **`SPECIFICATION AMBIGUOUS — EXACT REPRODUCTION IMPOSSIBLE`** |
| **`H-208C`**| Symmetrical entries, Asymmetric TP | Entry filter unspecified in precommit | **Ambiguous Spec** | **`SPECIFICATION AMBIGUOUS — EXACT REPRODUCTION IMPOSSIBLE`** |
