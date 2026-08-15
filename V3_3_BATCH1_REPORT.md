# V3.3 BATCH-1 SCIENTIFIC RESEARCH REPORT
## H-209 TO H-214 MARKET-MECHANISM DISCOVERY & TEMPORAL EVALUATION

## 1. REPOSITORY & EXPERIMENT METADATA
* **Repository**: [`bacbuon333-design/Universal-project-gateway`](https://github.com/bacbuon333-design/Universal-project-gateway)
* **Active Branch**: `research/quant-v3.3-h209-distributed-mechanisms`
* **Precommit Commit SHA**: `fd218ac497f1f99c27feec3b730f5763cb64fb27`
* **Implementation Commit SHA**: `30facff60580979bf597972b9a71beea194fbe93`
* **Raw Results Commit SHA**: `72422fcbf102b0783a9cf6a32ac58078548b9cc4`
* **Target Dataset**: Gold M30 (`GOLD_M30.csv`), 33 complete quarters (2018Q2 to 2026Q2)
* **Total Configurations Evaluated**: 24 configurations across 6 distinct mechanism families

---

## 2. BATCH-1 COMPREHENSIVE RESULTS TABLE (PROGRAMMATICALLY GENERATED)

| Config ID | Family | Description | Trades | Min/Q | Med/Q | Max/Q | Max Share | Gini | R4 Pos (%) | R4 PF $\ge 1.20$ (%) | PF | Expectancy ($) | Long PF | Short PF | Final Status | Primary Failure Reason |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`H-209-C1`** | `MHTP` | Trend Persistence (EMA50/100, EMA20 Pullback, SL1.5, TP3.0) | 3986 | **106** | 120.0 | 138 | 3.5% | 0.038 | 23.3% | 0.0% | **0.948** | $-2.42 | 0.996 | 0.894 | **`REJECTED`** | Gate E1 (PF = 0.948 < 1.25) |
| **`H-209-C2`** | `MHTP` | Trend Persistence (EMA50/100, EMA20 Pullback, SL1.5, TP3.75) | 3555 | **91** | 109.0 | 124 | 3.5% | 0.038 | 30.0% | 0.0% | **0.977** | $-1.12 | 1.034 | 0.912 | **`REJECTED`** | Gate E1 (PF = 0.977 < 1.25) |
| **`H-209-C3`** | `MHTP` | Trend Persistence (EMA50/100, EMA20 Pullback, SL2.0, TP4.0) | 2796 | **71** | 85.0 | 104 | 3.7% | 0.047 | 36.7% | 0.0% | **1.013** | $+0.79 | 1.094 | 0.919 | **`REJECTED`** | Gate E1 (PF = 1.013 < 1.25) |
| **`H-209-C4`** | `MHTP` | Trend Persistence (EMA50/100, EMA20 Pullback, SL2.0, TP5.0) | 2524 | **64** | 76.0 | 96 | 3.8% | 0.044 | 40.0% | 3.3% | **0.986** | $-0.91 | 1.088 | 0.871 | **`REJECTED`** | Gate E1 (PF = 0.986 < 1.25) |
| **`H-210-C1`** | `EDMR` | Displacement MR (EMA50 Dist > 2.5 ATR, SL1.5, TP2.25) | 5415 | **131** | 161.0 | 194 | 3.6% | 0.055 | 0.0% | 0.0% | **0.859** | $-6.73 | 0.938 | 0.791 | **`REJECTED`** | Gate E1 (PF = 0.859 < 1.25) |
| **`H-210-C2`** | `EDMR` | Displacement MR (EMA50 Dist > 2.5 ATR, SL1.5, TP3.0) | 4946 | **121** | 147.0 | 182 | 3.7% | 0.055 | 6.7% | 0.0% | **0.881** | $-6.15 | 0.945 | 0.824 | **`REJECTED`** | Gate E1 (PF = 0.881 < 1.25) |
| **`H-210-C3`** | `EDMR` | Displacement MR (EMA50 Dist > 3.0 ATR, SL1.5, TP2.25) | 4180 | **90** | 125.0 | 160 | 3.8% | 0.067 | 3.3% | 0.0% | **0.888** | $-5.39 | 0.980 | 0.811 | **`REJECTED`** | Gate E1 (PF = 0.888 < 1.25) |
| **`H-210-C4`** | `EDMR` | Displacement MR (EMA50 Dist > 3.0 ATR, SL1.5, TP3.0) | 3925 | **88** | 120.0 | 149 | 3.8% | 0.066 | 10.0% | 0.0% | **0.883** | $-6.17 | 0.960 | 0.817 | **`REJECTED`** | Gate E1 (PF = 0.883 < 1.25) |
| **`H-211-C1`** | `FBRLT` | Failed Breakout Trap (Donchian 20, SL1.5, TP3.0) | 5069 | **128** | 151.0 | 184 | 3.6% | 0.055 | 3.3% | 0.0% | **0.858** | $-7.22 | 0.952 | 0.773 | **`REJECTED`** | Gate E1 (PF = 0.858 < 1.25) |
| **`H-211-C2`** | `FBRLT` | Failed Breakout Trap (Donchian 20, SL1.5, TP3.75) | 4371 | **109** | 131.0 | 159 | 3.6% | 0.054 | 16.7% | 0.0% | **0.873** | $-6.98 | 0.975 | 0.782 | **`REJECTED`** | Gate E1 (PF = 0.873 < 1.25) |
| **`H-211-C3`** | `FBRLT` | Failed Breakout Trap (Donchian 40, SL1.5, TP3.0) | 4025 | **98** | 123.0 | 145 | 3.6% | 0.052 | 0.0% | 0.0% | **0.853** | $-7.78 | 0.937 | 0.778 | **`REJECTED`** | Gate E1 (PF = 0.853 < 1.25) |
| **`H-211-C4`** | `FBRLT` | Failed Breakout Trap (Donchian 40, SL1.5, TP3.75) | 3672 | **89** | 112.0 | 133 | 3.6% | 0.055 | 10.0% | 0.0% | **0.873** | $-7.17 | 0.945 | 0.809 | **`REJECTED`** | Gate E1 (PF = 0.873 < 1.25) |
| **`H-212-C1`** | `SORE` | Session Expansion (Asian 00-07, Lon 08-16 + EMA50, SL1.5, TP3.0) | 4092 | **73** | 131.0 | 152 | 3.7% | 0.082 | 26.7% | 0.0% | **0.963** | $-1.52 | 0.928 | 0.997 | **`REJECTED`** | Gate E1 (PF = 0.963 < 1.25) |
| **`H-212-C2`** | `SORE` | Session Expansion (Asian 00-07, Lon 08-16 + EMA50, SL1.5, TP3.75) | 3637 | **69** | 113.0 | 131 | 3.6% | 0.078 | 23.3% | 3.3% | **0.950** | $-2.21 | 0.936 | 0.965 | **`REJECTED`** | Gate E1 (PF = 0.950 < 1.25) |
| **`H-212-C3`** | `SORE` | Session Expansion (Asian 00-07, Lon 08-16 + EMA100, SL1.5, TP3.0) | 3725 | **69** | 116.0 | 139 | 3.7% | 0.088 | 36.7% | 0.0% | **0.985** | $-0.60 | 0.971 | 1.000 | **`REJECTED`** | Gate E1 (PF = 0.985 < 1.25) |
| **`H-212-C4`** | `SORE` | Session Expansion (Asian 00-07, Lon 08-16 + EMA100, SL1.5, TP3.75) | 3339 | **66** | 104.0 | 124 | 3.7% | 0.083 | 30.0% | 3.3% | **0.991** | $-0.38 | 0.993 | 0.990 | **`REJECTED`** | Gate E1 (PF = 0.991 < 1.25) |
| **`H-213-C1`** | `MRLM` | Range Loc Momentum (Channel 50, Th 0.75/0.25, SL1.5, TP3.0) | 5388 | **136** | 166.0 | 189 | 3.5% | 0.045 | 33.3% | 0.0% | **1.027** | $+1.34 | 1.091 | 0.960 | **`REJECTED`** | Gate E1 (PF = 1.027 < 1.25) |
| **`H-213-C2`** | `MRLM` | Range Loc Momentum (Channel 50, Th 0.75/0.25, SL1.5, TP3.75) | 4656 | **107** | 143.0 | 176 | 3.8% | 0.052 | 46.7% | 3.3% | **1.034** | $+1.82 | 1.148 | 0.922 | **`REJECTED`** | Gate E1 (PF = 1.034 < 1.25) |
| **`H-213-C3`** | `MRLM` | Range Loc Momentum (Channel 100, Th 0.80/0.20, SL1.5, TP3.0) | 4204 | **100** | 127.0 | 163 | 3.9% | 0.060 | 46.7% | 3.3% | **1.057** | $+2.83 | 1.149 | 0.953 | **`REJECTED`** | Gate E1 (PF = 1.057 < 1.25) |
| **`H-213-C4`** | `MRLM` | Range Loc Momentum (Channel 100, Th 0.80/0.20, SL1.5, TP3.75) | 3584 | **87** | 108.0 | 128 | 3.6% | 0.053 | 60.0% | 3.3% | **1.063** | $+3.40 | 1.185 | 0.931 | **`REJECTED`** | Gate E1 (PF = 1.063 < 1.25) |
| **`H-214-C1`** | `VRA` | Vol Acceleration (ATR7/28 > 1.20 + 3b Breakout + EMA50, SL1.5, TP3.0) | 3616 | **80** | 114.0 | 126 | 3.5% | 0.054 | 16.7% | 0.0% | **0.932** | $-3.44 | 1.024 | 0.850 | **`REJECTED`** | Gate E1 (PF = 0.932 < 1.25) |
| **`H-214-C2`** | `VRA` | Vol Acceleration (ATR7/28 > 1.20 + 3b Breakout + EMA50, SL1.5, TP3.75) | 3263 | **74** | 100.0 | 112 | 3.4% | 0.052 | 26.7% | 0.0% | **0.953** | $-2.55 | 1.044 | 0.868 | **`REJECTED`** | Gate E1 (PF = 0.953 < 1.25) |
| **`H-214-C3`** | `VRA` | Vol Acceleration (ATR7/28 > 1.30 + 3b Breakout + EMA50, SL1.5, TP3.0) | 2805 | **50** | 89.0 | 106 | 3.8% | 0.088 | 36.7% | 0.0% | **0.993** | $-0.35 | 1.067 | 0.925 | **`REJECTED`** | Gate E1 (PF = 0.993 < 1.25) |
| **`H-214-C4`** | `VRA` | Vol Acceleration (ATR7/28 > 1.30 + 3b Breakout + EMA50, SL1.5, TP3.75) | 2548 | **46** | 79.0 | 94 | 3.7% | 0.085 | 50.0% | 3.3% | **1.024** | $+1.29 | 1.143 | 0.915 | **`REJECTED`** | Gate E1 (PF = 1.024 < 1.25) |

---

## 3. PRECOMMITTED BOOLEAN GATE MATRIX

| Config ID | Gate A1 (Min $\ge 5$) | Gate A2 (Share $\le 5\%$) | Gate A3 (Max/Med $\le 3$) | Gate A4 (Gini $< 0.3$) | Gate D1 (R4 Pos $\ge 70\%$) | Gate D2 (R4 PF $\ge 65\%$) | Gate E1 (PF $\ge 1.25$) | Gate E2 (Exp $> 0$) | ALL PASS? |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`H-209-C1`** | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS | ❌ FAIL | ❌ FAIL | ❌ FAIL | ❌ FAIL | **❌ REJECTED** |
| **`H-209-C2`** | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS | ❌ FAIL | ❌ FAIL | ❌ FAIL | ❌ FAIL | **❌ REJECTED** |
| **`H-209-C3`** | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS | ❌ FAIL | ❌ FAIL | ❌ FAIL | ✅ PASS | **❌ REJECTED** |
| **`H-209-C4`** | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS | ❌ FAIL | ❌ FAIL | ❌ FAIL | ❌ FAIL | **❌ REJECTED** |
| **`H-210-C1`** | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS | ❌ FAIL | ❌ FAIL | ❌ FAIL | ❌ FAIL | **❌ REJECTED** |
| **`H-210-C2`** | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS | ❌ FAIL | ❌ FAIL | ❌ FAIL | ❌ FAIL | **❌ REJECTED** |
| **`H-210-C3`** | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS | ❌ FAIL | ❌ FAIL | ❌ FAIL | ❌ FAIL | **❌ REJECTED** |
| **`H-210-C4`** | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS | ❌ FAIL | ❌ FAIL | ❌ FAIL | ❌ FAIL | **❌ REJECTED** |
| **`H-211-C1`** | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS | ❌ FAIL | ❌ FAIL | ❌ FAIL | ❌ FAIL | **❌ REJECTED** |
| **`H-211-C2`** | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS | ❌ FAIL | ❌ FAIL | ❌ FAIL | ❌ FAIL | **❌ REJECTED** |
| **`H-211-C3`** | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS | ❌ FAIL | ❌ FAIL | ❌ FAIL | ❌ FAIL | **❌ REJECTED** |
| **`H-211-C4`** | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS | ❌ FAIL | ❌ FAIL | ❌ FAIL | ❌ FAIL | **❌ REJECTED** |
| **`H-212-C1`** | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS | ❌ FAIL | ❌ FAIL | ❌ FAIL | ❌ FAIL | **❌ REJECTED** |
| **`H-212-C2`** | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS | ❌ FAIL | ❌ FAIL | ❌ FAIL | ❌ FAIL | **❌ REJECTED** |
| **`H-212-C3`** | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS | ❌ FAIL | ❌ FAIL | ❌ FAIL | ❌ FAIL | **❌ REJECTED** |
| **`H-212-C4`** | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS | ❌ FAIL | ❌ FAIL | ❌ FAIL | ❌ FAIL | **❌ REJECTED** |
| **`H-213-C1`** | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS | ❌ FAIL | ❌ FAIL | ❌ FAIL | ✅ PASS | **❌ REJECTED** |
| **`H-213-C2`** | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS | ❌ FAIL | ❌ FAIL | ❌ FAIL | ✅ PASS | **❌ REJECTED** |
| **`H-213-C3`** | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS | ❌ FAIL | ❌ FAIL | ❌ FAIL | ✅ PASS | **❌ REJECTED** |
| **`H-213-C4`** | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS | ❌ FAIL | ❌ FAIL | ❌ FAIL | ✅ PASS | **❌ REJECTED** |
| **`H-214-C1`** | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS | ❌ FAIL | ❌ FAIL | ❌ FAIL | ❌ FAIL | **❌ REJECTED** |
| **`H-214-C2`** | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS | ❌ FAIL | ❌ FAIL | ❌ FAIL | ❌ FAIL | **❌ REJECTED** |
| **`H-214-C3`** | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS | ❌ FAIL | ❌ FAIL | ❌ FAIL | ❌ FAIL | **❌ REJECTED** |
| **`H-214-C4`** | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS | ❌ FAIL | ❌ FAIL | ❌ FAIL | ✅ PASS | **❌ REJECTED** |

---

## 4. SCIENTIFIC TAKEAWAYS BY MECHANISM FAMILY

1. **Family 1: Multi-Horizon Trend Persistence (H-209)**:
   - *Opportunity Density*: Exceptional ($\ge 64$ to $106$ trades/quarter, 2,500–4,000 trades total).
   - *Economics*: Hovered near breakeven ($PF = 0.95 - 1.01$). Longs showed structural edge ($PF = 1.09$), while Shorts underperformed ($PF = 0.91$).
2. **Family 2: Extreme Displacement Mean Reversion (H-210)**:
   - *Economics*: Failed heavily ($PF = 0.85 - 0.88$, Net PnL -$23k to -$37k). Displaced moves in Gold frequently continue extending rather than mean-reverting quickly.
3. **Family 3: Failed Breakout Reversal / Liquidity Trap (H-211)**:
   - *Economics*: Failed heavily ($PF = 0.85 - 0.87$). Trading against false breakouts on Gold M30 suffered high slippage and negative follow-through.
4. **Family 4: Session Opening Range Expansion (H-212)**:
   - *Opportunity Density*: High ($\ge 66$ to $73$ trades/quarter).
   - *Economics*: Breakeven ($PF = 0.95 - 0.99$). Asian range breakouts in London/NY produce balanced trades but costs erode net edge.
5. **Family 5: Medium-Range Location + Momentum (H-213)**:
   - *Opportunity Density*: High ($\ge 87$ to $136$ trades/quarter).
   - *Economics*: **Best performer of Batch 1** ($PF = 1.03 - 1.06$, Net PnL +$7k to +$12.5k, Expectancy +$1.34 to +$3.40).
   - *Asymmetry Insight*: Long trades reached $PF = 1.15 - 1.185$, but blended PF remained below $1.25$ due to Short drag ($PF pprox 0.93$).
6. **Family 6: Volatility Regime Acceleration (H-214)**:
   - *Opportunity Density*: High ($\ge 46$ to $80$ trades/quarter).
   - *Economics*: Moderate ($PF = 0.93 - 1.024$). Long trades were profitable ($PF = 1.143$), but Short trades dragged down overall PF ($PF = 0.915$).

---

## 5. FINAL BATCH DECISION & SCIENTIFIC CONCLUSION

> ### **NO H-209→H-214 HISTORICAL CONFIGURATION PASSED THE DISTRIBUTED EDGE STANDARD.**

All 24 precommitted configurations satisfied the hard temporal distribution gates ($\ge 5$ trades in 33/33 quarters), proving that non-squeeze mechanisms naturally produce high opportunity density across all market regimes. However, all configurations failed Gate E1 ($PF \ge 1.25$) due to cost drag and directional short-side erosion on Gold M30.