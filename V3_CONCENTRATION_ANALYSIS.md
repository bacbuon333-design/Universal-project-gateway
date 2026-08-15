# V3 PROFIT & EVENT CONCENTRATION ANALYSIS

This report documents the outlier dependency, tail trade concentration, and macro regime clustering of **CAND-001** and **H-105**.

---

## 1. PROFIT CONCENTRATION PROFILE

| Outlier Slice | CAND-001 Benchmark | H-105 Minimalist | Interpretation |
| :--- | :--- | :--- | :--- |
| **Total Net Profit** | **+$6,451.00 USD** | **+$6,169.71 USD** | Full 25-year sample |
| **Top 1 Best Trade** | +$1,226.80 (**19.0%**) | +$1,226.80 (**19.9%**) | Single largest winner |
| **Top 3 Best Trades** | +$3,440.43 (**53.3%**) | +$3,440.43 (**55.8%**) | Top 3 winners generate $> 50\%$ PnL |
| **Top 5 Best Trades** | +$5,473.67 (**84.8%**) | +$5,473.67 (**88.7%**) | Top 5 winners generate $> 80\%$ PnL |
| **Top 10% Trades** | +$8,965.43 (**139.0%**) | +$9,257.61 (**150.0%**) | Asymmetric payoff tail |
| **Best Single Quarter (2026 Q2)** | +$2,802.83 (**43.4%**) | +$2,802.83 (**45.4%**) | Concentrated in 2026 expansion |
| **Best Single Year (2026)** | +$4,484.67 (**69.5%**) | +$4,484.67 (**72.7%**) | Concentrated in recent bull run |

---

## 2. OUTLIER REMOVAL STRESS GAUNTLET

| Stress Condition | CAND-001 PF | CAND-001 PnL | H-105 PF | H-105 PnL | Scientific Verdict |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Full Uncut History** | **1.837** | +$6,451.00 | **1.752** | +$6,169.71 | **Baseline** |
| **Remove Top 1 Trade** | **1.678** | +$5,224.20 | **1.602** | +$4,942.91 | **SURVIVES** |
| **Remove Top 3 Trades** | **1.391** | +$3,010.57 | **1.333** | +$2,729.29 | **SURVIVES** |
| **Remove Top 5 Trades** | **1.127** | +$977.33 | **1.085** | +$696.04 | **DEGRADES (Breakeven)** |
| **Remove Best Quarter (2026 Q2)** | **1.516** | +$3,648.17 | **1.445** | +$3,366.89 | **SURVIVES** |

* **Scientific Conclusion on Outliers**:
  - The strategy is an **asymmetric positive-skew system** ($3.0 \times \text{RR}$, $6.0 \times \text{ATR}$ targets).
  - Removing up to 3 extreme winners leaves a healthy Profit Factor $> 1.33$.
  - Removing the best single quarter leaves $PF = 1.516$, confirming the edge is not a 1-quarter fluke.

---

## 3. MACRO REGIME & CRISIS EPISODE BREAKDOWN

| Historical Regime | Period | CAND-001 Trades | CAND-001 PnL | CAND-001 PF | Economic Context |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Secular Bull Start** | 2001–2007 | 3 | -$338.01 | 0.000 | Low historical volatility / few triggers |
| **Global Financial Crisis** | 2008–2011 | 0 | $0.00 | 0.000 | Extreme gaps / no 4-bar compression |
| **Gold Bear Market / Crash** | 2012–2015 | 42 | **+$136.00** | **1.085** | **Survives bear market via short alpha** |
| **Consolidation / Chop** | 2016–2019 | 27 | -$35.77 | 0.963 | Break-even during tight multi-year range |
| **COVID-19 Shock** | 2020 | 15 | **+$1,011.89** | **2.084** | Strong expansion monetization |
| **Inflationary Regime** | 2021–2023 | 26 | **+$439.00** | **1.323** | Consistent positive performance |
| **Record Bull Run** | 2024–2026 | 23 | **+$5,237.90** | **3.077** | Major expansion monetization |
