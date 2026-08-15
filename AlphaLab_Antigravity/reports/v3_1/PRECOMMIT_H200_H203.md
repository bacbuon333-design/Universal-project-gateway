# PRECOMMITMENT PROTOCOL: HYPOTHESES H-200 TO H-203 (HIGH-FREQUENCY TEMPORAL DISTRIBUTION)

* **Precommitment Timestamp**: `2026-08-15T23:45:00+07:00`
* **Target Objective**: Identify whether any causal volatility-expansion mechanism can generate $\ge 5$ trades in EVERY complete quarter ($N \ge 500$ trades over 100 quarters) while maintaining cost-adjusted profitability ($PF \ge 1.25$, positive expectancy).

---

## 1. PRECOMMITTED HYPOTHESIS SPECIFICATIONS

### Hypothesis H-200: M30 Intraday Squeeze Expansion
* **Concept**: M30 Volatility Squeeze (BB 20/2.0 inside Keltner 20/1.2 for $\ge 2$ bars) with Intraday Trend (EMA 50) alignment.
* **Parameters**: `bb_period=20, bb_mult=2.0, kelt_mult=1.2, macro_ema=50, sl_atr=1.5, tp_rr=2.5`.
* **Data**: `GOLD_M30.csv` (2018–2026, 33 complete quarters).

### Hypothesis H-201: H1 Short-Cycle Range Compression Breakout
* **Concept**: Range Compression where Bar Range $(H-L) \le 0.70 \times \text{ATR}(14)$ for $\ge 2$ bars, followed by breakout of 3-bar High/Low aligned with EMA 100.
* **Parameters**: `atr_comp_mult=0.70, lookback=3, trend_ema=100, sl_atr=1.5, tp_rr=2.5`.
* **Data**: `GOLD_H1_2001_2026.csv` (2001–2026, 100 complete quarters).

### Hypothesis H-202: H1 Adaptive Donchian Volatility Compression (ATR Ratio Contraction)
* **Concept**: 20-bar Donchian Channel breakout filtered by ATR contraction ratio ($\text{ATR}(14) / \text{ATR}(50) \le 0.85$).
* **Parameters**: `donchian_len=20, atr_fast=14, atr_slow=50, atr_ratio_max=0.85, sl_atr=1.5, tp_rr=2.5`.
* **Data**: `GOLD_H1_2001_2026.csv` (2001–2026, 100 complete quarters).

### Hypothesis H-203: H1 London Session Opening Range Breakout (ORB)
* **Concept**: Breakout of Asian consolidation range (00:00–07:00 UTC) during London/NY expansion (08:00–14:00 UTC) with ATR filter.
* **Parameters**: `asian_start=0, asian_end=7, orb_end=14, sl_atr=1.5, tp_rr=2.0`.
* **Data**: `GOLD_H1_2001_2026.csv` (2001–2026, 100 complete quarters).

---

## 2. PRECOMMITTED ACCEPTANCE & REJECTION GATES

1. **Gate 1 (Hard Temporal Frequency)**: Must achieve $\ge 5$ trades in 100% of complete quarters evaluated.
2. **Gate 2 (Sample Size)**: Total historical trades $\ge 500$ (or $\ge 150$ on M30).
3. **Gate 3 (Economic Quality)**: Net PnL $> 0$, $PF \ge 1.25$ with 25 pips spread + \$7/lot commission.
4. **Rejection Rule**: If ANY complete quarter has $< 5$ trades $\implies$ **REJECTED**.
