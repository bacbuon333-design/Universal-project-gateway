# V3.2 PRECOMMITMENT SPECIFICATION: HYPOTHESES H-204 TO H-208

* **Precommitment Stage**: Commit 3
* **Primary Target Asset / Timeframe**: `GOLD (XAUUSD) / M30` (33 complete quarters: `2018Q2` to `2026Q2`)
* **Primary Target Objective**: Identify whether any causal volatility expansion mechanism can satisfy:
  1. **Hard Temporal Gate**: $\ge 5$ executed trades in EVERY complete quarter ($N \ge 165$).
  2. **Trade Concentration Gate**: Max quarterly trade share $\le 5\%$, Max/Median $\le 3.0$, Gini $< 0.30$.
  3. **Profit Distribution Gate**: Top 3 quarters PnL $\le 40\%$, Top 5 quarters PnL $\le 60\%$.
  4. **Rolling Economic Gate**: Rolling 4Q positive $\ge 70\%$, Rolling 4Q $PF \ge 1.20 \ge 65\%$.
  5. **Cost-Adjusted Edge**: $PF \ge 1.25$, Expectancy $> 0$ with 25 pips spread + $7/lot commission.

---

## 1. PRECOMMITTED HYPOTHESIS DEFINITIONS & PARAMETERS

| Hypothesis ID | Mechanism Family | Compression Condition | Directional / Regime Filter | Exit Geometry | Parameter Grid Bounds |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`H-204`** | Light Trend Squeeze | BB(20, 2.0) inside Keltner(20, 1.2) for $\ge 2$ bars | EMA(20) > EMA(50) for Bull, < for Bear | $\text{SL} = 1.5 \times \text{ATR}, \text{TP} = 2.5 \times \text{SL}$ | Fixed |
| **`H-205`** | Volatility Ratio Contraction | $\text{ATR}(14) / \text{ATR}(50) \le 0.80$ for $\ge 2$ bars | Close crosses 10-bar Donchian + EMA(50) | $\text{SL} = 1.5 \times \text{ATR}, \text{TP} = 2.5 \times \text{SL}$ | Fixed |
| **`H-206`** | Normalized Range Compression | Bar Range $(H-L) \le 0.65 \times \text{ATR}(14)$ for $\ge 2$ bars | Breakout 3-bar High/Low + EMA(50) | $\text{SL} = 1.5 \times \text{ATR}, \text{TP} = 2.5 \times \text{SL}$ | Fixed |
| **`H-207`** | Session-Aware Squeeze | BB inside Keltner for $\ge 2$ bars | Time of Day $\in [07:00, 17:00\text{ UTC}]$ + EMA(50) | $\text{SL} = 1.5 \times \text{ATR}, \text{TP} = 2.5 \times \text{SL}$ | Fixed |
| **`H-208A`**| Long-Only Squeeze | BB inside Keltner for $\ge 2$ bars | Bullish EMA(50) slope | $\text{SL} = 1.5 \times \text{ATR}, \text{TP} = 2.0 \times \text{SL}$ | Fixed |
| **`H-208B`**| Short-Only Squeeze | BB inside Keltner for $\ge 2$ bars | Bearish EMA(50) slope | $\text{SL} = 1.5 \times \text{ATR}, \text{TP} = 3.0 \times \text{SL}$ | Fixed |
| **`H-208C`**| Asymmetric Squeeze | BB inside Keltner for $\ge 2$ bars | Symmetrical entries, Asymmetric TP ($2.0\text{x Long}, 3.0\text{x Short}$) | Dynamic | Fixed |

---

## 2. PRECOMMITTED SCREENING STAGES

* **Stage 1 (Distribution Screen)**: If any complete quarter has $< 5$ trades $\implies$ **REJECT IMMEDIATELY**.
* **Stage 2 (Economic & Concentration Screen)**: Only distribution survivors proceed to Profit Factor, rolling window, and profit concentration gauntlets.
