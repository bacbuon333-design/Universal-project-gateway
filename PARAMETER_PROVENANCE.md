# PARAMETER PROVENANCE & CALIBRATION AUDIT

This document records the exact provenance, calibration history, data exposure, and contamination risk for every frozen parameter of **CAND-001 (ALAB_SQUEEZE_REGIME_V1)**.

---

## 1. PARAMETER INVENTORY & PROVENANCE REGISTRY

| Parameter | Final Value | First Known Appearance | Experiment / Source | Data Available When Chosen | Theoretical / Empirical Justification | Contamination Risk Level |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `bb_period` | `20` | Day 2 Discovery | John Bollinger (1983) standard | Historical OHLC | Classical 20-bar baseline for rolling mean and standard deviation. | **LOW (Standard Benchmark)** |
| `bb_mult` | `2.0` | Day 2 Discovery | John Bollinger standard | Historical OHLC | Standard 2.0 standard deviation volatility band. | **LOW (Standard Benchmark)** |
| `kelt_mult` | `1.2` | `experiment_h040_volatility_squeeze.py` | John Carter Volatility Squeeze | 2001–2026 Gold H1 | Classical Keltner channel bandwidth multiplier ($1.2 \times \text{ATR}_{20}$). | **MEDIUM (Observed in H-040)** |
| `macro_ema_len` | `200` | `experiment_h030_mtf_trend.py` | Classical macro trend literature | 2001–2026 Gold H1 | Standard institutional regime separator (200-period EMA slope). | **LOW (Standard Benchmark)** |
| `min_er` | `0.20` | `experiment_h070_multiscale_squeeze.py` | Midpoint interpolation from H-060 | 2001–2026 Gold H1, M30, M15 | Interpolated between grid points $0.15$ and $0.25$ to balance noise reduction with trade frequency. | **HIGH (Development Data Selected)** |
| `sl_atr_mult` | `2.0` | `experiment_h060_adaptive_squeeze.py` | H-060 Parameter Sweep | 2001–2026 Gold H1 | $2.0 \times \text{ATR}_{14}$ stop buffer provides sufficient room to avoid noise stop-outs. | **MEDIUM (Selected in Grid)** |
| `tp_rr` | `3.0` | `experiment_h060_adaptive_squeeze.py` | H-060 Parameter Sweep | 2001–2026 Gold H1 | $3.0 \times \text{Risk}$ ($6.0 \times \text{ATR}_{14}$) creates an asymmetric payoff ratio $> 3.0$. | **MEDIUM (Selected in Grid)** |
| `spread_pips` | `25.0` | Day 1 Engine Build | Institutional ECN standard | Fixed execution cost | Realistic baseline spread for XAUUSD ($0.25/oz). | **NONE (Cost Stress Parameter)** |
| `commission_per_lot` | `7.0` | Day 1 Engine Build | Institutional ECN standard | Fixed execution cost | $7.00 per 1.0 standard lot round-turn ($0.70 per 0.10 lot). | **NONE (Cost Stress Parameter)** |

---

## 2. DETAILED TRACE FOR `min_er = 0.20`

1. **Origin in H-060 Sweep**:
   - In [`experiment_h060_adaptive_squeeze.py`](file:///C:/Users/gugul/AppData/Roaming/MetaQuotes/Terminal/BB16F565FAAA6B23A20C26C49416FF05/AlphaLab_Antigravity/src/experiment_h060_adaptive_squeeze.py), the discrete grid tested `er_thresholds = [0.15, 0.25, 0.35]`.
   - The result showed that `0.15` produced higher trade frequency but slightly higher whipsaw, while `0.25` produced high Profit Factor (2.31) but fewer trades (~3.5 trades/year).
2. **Interpolation in H-070**:
   - In [`experiment_h070_multiscale_squeeze.py`](file:///C:/Users/gugul/AppData/Roaming/MetaQuotes/Terminal/BB16F565FAAA6B23A20C26C49416FF05/AlphaLab_Antigravity/src/experiment_h070_multiscale_squeeze.py), the researcher selected `min_er = 0.20` as the balanced midpoint to evaluate multi-timeframe behavior (H1, M30, M15).
3. **Audit Assessment**:
   - Because `0.20` was determined based on inspecting historical metrics across the 2001–2026 dataset, this parameter must be classified as **Development / In-Sample Selected**.
   - It cannot be claimed as an a priori theoretical constant.

---

## 3. FREEZE CONSTRAINTS

Under the strict audit rules:
- **No parameter may be retuned or modified.**
- All evaluations must run on the exact frozen parameters above.
