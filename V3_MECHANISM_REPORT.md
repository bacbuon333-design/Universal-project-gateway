# V3 MECHANISM REPORT: ECONOMETRIC EVENT STUDY OF VOLATILITY COMPRESSION

This report documents the fundamental econometric investigation into whether **Volatility Compression** provides standalone predictive power for future price dynamics.

---

## 1. RESEARCH QUESTIONS & EMPIRICAL FINDINGS

### Question A: Does Compression Predict Future Volatility Expansion?
* **Finding**: **PARTIALLY CONFIRMED (TRIGGER DEPENDENT)**.
  - While inside the compression episode itself (Definition A: Bollinger inside Keltner for $\ge 4$ bars), forward 12-hour maximum range is $1.136\%$ vs $1.200\%$ baseline.
  - Volatility expansion does NOT occur until the **transition / release bar (price crossing outside Bollinger Bands)** occurs.
  - Once the breakout occurs, forward 24-hour range expands to $1.725\%$ and 48-hour range expands to $2.398\%$.

### Question B: Does Compression Predict Direction or Only Magnitude?
* **Finding**: **DIRECTION IS PREDICTABLE ONLY WHEN ALIGNED WITH MACRO TREND**.
  - **Pure Breakouts (No Squeeze)**: Downward breaks have negative return ($-0.187\%$ at 48h) and MFE/MAE ratio $< 1.0$ ($0.916$), proving pure breakouts suffer severe mean-reverting chop.
  - **Squeeze + Upper Breakout (Long)**: MFE/MAE ratio jumps to $1.330$ (vs $1.078$ baseline). When aligned with Macro Bullish trend (200 EMA slope), MFE/MAE reaches **$1.474$**.
  - **Squeeze + Lower Breakout (Short)**: When aligned with Macro Bearish trend (200 EMA slope), forward 48h return reaches **$+0.402\%$** (Win Rate $55.0\%$, MFE/MAE ratio **$1.402$**).
  - Adding Kaufman Efficiency Ratio ($ER \ge 0.20$) further improves short return to **$+0.432\%$** with MFE/MAE **$1.423$**.

---

## 2. CROSS-TIMEFRAME PERSISTENCE (H-102)

| Timeframe | History Span | Total Bars | Trades | Net PnL (USD) | Profit Factor | Win Rate | Expectancy | Scale Invariance Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`GOLD H4`** | 26 years | 23,493 | 33 | **+$3,625.89** | **2.150** | 36.4% | **+0.455 R** | **CONFIRMED (Strongest edge)** |
| **`GOLD H1`** | 26 years | 81,463 | 136 | **+$6,451.00** | **1.837** | 32.4% | **+0.273 R** | **CONFIRMED (Primary Benchmark)** |
| **`GOLD M30`**| 9 years | 99,999 | 151 | **+$3,160.46** | **1.316** | 31.8% | **+0.239 R** | **CONFIRMED (Materially profitable)** |
| **`GOLD M15`**| 5 years | 99,999 | 151 | **+$68.21** | **1.008** | 28.5% | **+0.127 R** | **BORDERLINE (Friction bound)** |

* **Insight**: The compression-expansion mechanism is qualitatively scale-invariant across H4, H1, and M30. The edge degrades on M15 due to fixed 25-pip spread eating a larger percentage of smaller ATR.

---

## 3. CROSS-ASSET ZERO-TUNING TRANSFER (H-103)

| Asset | Timeframe | History Span | Trades | Net PnL (USD) | Profit Factor | Win Rate | Expectancy | Transfer Verdict |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`GOLD`** | H1 | 26 years | 136 | **+$6,451.00** | **1.837** | 32.4% | **+0.273 R** | **SURVIVES** |
| **`EURUSD`** | H1 | 13 years | 94 | -$68.11 | 0.000 | 0.0% | -0.012 R | **FAILS TRANSFER** |
| **`GBPUSD`** | H1 | 13 years | 105 | -$75.15 | 0.000 | 0.0% | -0.008 R | **FAILS TRANSFER** |
| **`USDJPY`** | H1 | 13 years | 135 | -$240.74 | 0.369 | 12.6% | -0.501 R | **FAILS TRANSFER** |
| **`BTCUSD`** | H1 | 14 years | 159 | -$126,635.06 | 0.742 | 28.3% | +0.132 R | **FAILS TRANSFER** |

* **Insight**: The mechanism is **strictly instrument-specific to Gold**. FX pairs exhibit strong mean-reversion at session boundaries and fail normalized transfer.

---

## 4. MODEL COMPLEXITY PENALTY & MINIMALIST HYPOTHESIS (H-105)

| Architecture | Components | Trades | Net PnL (USD) | Profit Factor | Expectancy | Complexity Justification |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **H-104B (Pure Squeeze)** | 1 (Squeeze only) | 239 | +$8,633.10 | 1.598 | +0.164 R | Raw standalone alpha |
| **H-105 (Minimalist)** | 2 (Squeeze + Macro EMA) | 144 | +$6,169.71 | **1.752** | **+0.233 R** | **High efficiency plateau** |
| **CAND-001 (Flagship)** | 4 (Squeeze + Macro + ER + MACD) | 136 | +$6,451.00 | **1.837** | **+0.273 R** | Baseline Benchmark (+0.085 PF) |

* **Plateau Stability**: The $4 \times 4$ parameter grid for H-105 (Macro EMA $100–250$, RR $2.0–3.5$) shows **zero cliffs**, with all 16 configurations achieving $PF > 1.26$ and $PF > 1.56$ for $RR \ge 2.5$.
