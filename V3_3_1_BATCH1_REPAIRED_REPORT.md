# V3.3.1 BATCH-1 REPAIRED SCIENTIFIC AUDIT REPORT
## EVALUATION WINDOW & CONCENTRATION ESTIMATOR AUDIT REPAIR

## 1. REPOSITORY & EXPERIMENT METADATA
* **Repository**: [`bacbuon333-design/Universal-project-gateway`](https://github.com/bacbuon333-design/Universal-project-gateway)
* **Active Branch**: `research/quant-v3.3.1-batch1-audit-repair`
* **Audit Precommit Commit SHA**: `4a26372bf9d750c1f51390494cfcecbfeee77b4c`
* **Estimator Fix Commit SHA**: `e8c99ed8ee1925aafeeeadce30df8ad4e4e9a8f4`
* **Raw Repaired Results Commit SHA**: `68578b7c212ca0ea5082ab1e1710a32dc254367e`
* **Authoritative Evaluation Population**: `evaluation_trades` (Strictly 2018Q2 <= entry_quarter <= 2026Q2, 33 complete quarters)
* **Baseline Cost Model**: Spread = 25.0 pips, Commission = $7.0/lot, Baseline Slippage = 0.0 pips (Zero post-hoc assumptions)

---

## 2. REPAIRED BATCH-1 COMPREHENSIVE RESULTS TABLE (PROGRAMMATICALLY GENERATED)

| Config ID | Family | Description | Trades | Min/Q | Med/Q | Max/Q | Max Share | Gini | Top 3 Positive Q PnL | Top 5 Positive Q PnL | R4 Pos (%) | R4 PF $\ge 1.20$ (%) | PF | Expectancy ($) | Long PF | Short PF | Final Status | Primary Failure Reason |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`H-209-C1`** | `MHTP` | Trend Persistence (EMA50/100, EMA20 Pullback, SL1.5, TP3.0) | 3986 | **106** | 120.0 | 138 | 3.5% | 0.038 | 58.0% | 77.5% | 23.3% | 0.0% | **0.951** | $-2.28 | 0.990 | 0.906 | **`REJECTED`** | Gate E1 (PF = 0.951 < 1.25) |
| **`H-209-C2`** | `MHTP` | Trend Persistence (EMA50/100, EMA20 Pullback, SL1.5, TP3.75) | 3555 | **91** | 109.0 | 124 | 3.5% | 0.038 | 35.9% | 54.1% | 30.0% | 0.0% | **0.984** | $-0.81 | 1.030 | 0.929 | **`REJECTED`** | Gate E1 (PF = 0.984 < 1.25) |
| **`H-209-C3`** | `MHTP` | Trend Persistence (EMA50/100, EMA20 Pullback, SL2.0, TP4.0) | 2796 | **71** | 85.0 | 104 | 3.7% | 0.047 | 47.4% | 62.7% | 36.7% | 0.0% | **1.011** | $+0.67 | 1.086 | 0.924 | **`REJECTED`** | Gate E1 (PF = 1.011 < 1.25) |
| **`H-209-C4`** | `MHTP` | Trend Persistence (EMA50/100, EMA20 Pullback, SL2.0, TP5.0) | 2524 | **64** | 76.0 | 96 | 3.8% | 0.044 | 44.8% | 65.1% | 40.0% | 3.3% | **0.988** | $-0.80 | 1.083 | 0.878 | **`REJECTED`** | Gate E1 (PF = 0.988 < 1.25) |
| **`H-210-C1`** | `EDMR` | Displacement MR (EMA50 Dist > 2.5 ATR, SL1.5, TP2.25) | 5415 | **131** | 161.0 | 194 | 3.6% | 0.055 | 96.9% | 100.0% | 0.0% | 0.0% | **0.862** | $-6.56 | 0.953 | 0.785 | **`REJECTED`** | Gate E1 (PF = 0.862 < 1.25) |
| **`H-210-C2`** | `EDMR` | Displacement MR (EMA50 Dist > 2.5 ATR, SL1.5, TP3.0) | 4946 | **121** | 147.0 | 182 | 3.7% | 0.055 | 62.5% | 85.9% | 6.7% | 0.0% | **0.883** | $-6.05 | 0.956 | 0.819 | **`REJECTED`** | Gate E1 (PF = 0.883 < 1.25) |
| **`H-210-C3`** | `EDMR` | Displacement MR (EMA50 Dist > 3.0 ATR, SL1.5, TP2.25) | 4180 | **90** | 125.0 | 160 | 3.8% | 0.067 | 89.5% | 100.0% | 3.3% | 0.0% | **0.885** | $-5.54 | 0.981 | 0.805 | **`REJECTED`** | Gate E1 (PF = 0.885 < 1.25) |
| **`H-210-C4`** | `EDMR` | Displacement MR (EMA50 Dist > 3.0 ATR, SL1.5, TP3.0) | 3925 | **88** | 120.0 | 149 | 3.8% | 0.066 | 58.1% | 85.0% | 10.0% | 0.0% | **0.885** | $-6.08 | 0.965 | 0.817 | **`REJECTED`** | Gate E1 (PF = 0.885 < 1.25) |
| **`H-211-C1`** | `FBRLT` | Failed Breakout Trap (Donchian 20, SL1.5, TP3.0) | 5069 | **128** | 151.0 | 184 | 3.6% | 0.055 | 75.4% | 98.7% | 3.3% | 0.0% | **0.855** | $-7.40 | 0.955 | 0.765 | **`REJECTED`** | Gate E1 (PF = 0.855 < 1.25) |
| **`H-211-C2`** | `FBRLT` | Failed Breakout Trap (Donchian 20, SL1.5, TP3.75) | 4371 | **109** | 131.0 | 159 | 3.6% | 0.054 | 62.5% | 88.5% | 16.7% | 0.0% | **0.865** | $-7.43 | 0.968 | 0.774 | **`REJECTED`** | Gate E1 (PF = 0.865 < 1.25) |
| **`H-211-C3`** | `FBRLT` | Failed Breakout Trap (Donchian 40, SL1.5, TP3.0) | 4025 | **98** | 123.0 | 145 | 3.6% | 0.052 | 86.3% | 100.0% | 0.0% | 0.0% | **0.849** | $-7.96 | 0.942 | 0.768 | **`REJECTED`** | Gate E1 (PF = 0.849 < 1.25) |
| **`H-211-C4`** | `FBRLT` | Failed Breakout Trap (Donchian 40, SL1.5, TP3.75) | 3672 | **89** | 112.0 | 133 | 3.6% | 0.055 | 78.4% | 93.8% | 10.0% | 0.0% | **0.867** | $-7.49 | 0.942 | 0.801 | **`REJECTED`** | Gate E1 (PF = 0.867 < 1.25) |
| **`H-212-C1`** | `SORE` | Session Expansion (Asian 00-07, Lon 08-16 + EMA50, SL1.5, TP3.0) | 4092 | **73** | 131.0 | 152 | 3.7% | 0.082 | 72.9% | 94.3% | 26.7% | 0.0% | **0.959** | $-1.68 | 0.921 | 0.998 | **`REJECTED`** | Gate E1 (PF = 0.959 < 1.25) |
| **`H-212-C2`** | `SORE` | Session Expansion (Asian 00-07, Lon 08-16 + EMA50, SL1.5, TP3.75) | 3637 | **69** | 113.0 | 131 | 3.6% | 0.078 | 63.8% | 89.1% | 23.3% | 3.3% | **0.941** | $-2.65 | 0.922 | 0.959 | **`REJECTED`** | Gate E1 (PF = 0.941 < 1.25) |
| **`H-212-C3`** | `SORE` | Session Expansion (Asian 00-07, Lon 08-16 + EMA100, SL1.5, TP3.0) | 3725 | **69** | 116.0 | 139 | 3.7% | 0.088 | 69.3% | 86.2% | 36.7% | 0.0% | **0.982** | $-0.76 | 0.964 | 0.999 | **`REJECTED`** | Gate E1 (PF = 0.982 < 1.25) |
| **`H-212-C4`** | `SORE` | Session Expansion (Asian 00-07, Lon 08-16 + EMA100, SL1.5, TP3.75) | 3339 | **66** | 104.0 | 124 | 3.7% | 0.083 | 63.0% | 82.3% | 30.0% | 3.3% | **0.983** | $-0.77 | 0.982 | 0.983 | **`REJECTED`** | Gate E1 (PF = 0.983 < 1.25) |
| **`H-213-C1`** | `MRLM` | Range Loc Momentum (Channel 50, Th 0.75/0.25, SL1.5, TP3.0) | 5388 | **136** | 166.0 | 189 | 3.5% | 0.045 | 64.3% | 77.4% | 33.3% | 0.0% | **1.028** | $+1.41 | 1.098 | 0.957 | **`REJECTED`** | Gate E1 (PF = 1.028 < 1.25) |
| **`H-213-C2`** | `MRLM` | Range Loc Momentum (Channel 50, Th 0.75/0.25, SL1.5, TP3.75) | 4656 | **107** | 143.0 | 176 | 3.8% | 0.052 | 67.5% | 81.1% | 46.7% | 3.3% | **1.037** | $+1.99 | 1.156 | 0.921 | **`REJECTED`** | Gate E1 (PF = 1.037 < 1.25) |
| **`H-213-C3`** | `MRLM` | Range Loc Momentum (Channel 100, Th 0.80/0.20, SL1.5, TP3.0) | 4204 | **100** | 127.0 | 163 | 3.9% | 0.060 | 72.2% | 85.8% | 46.7% | 3.3% | **1.059** | $+2.94 | 1.151 | 0.956 | **`REJECTED`** | Gate E1 (PF = 1.059 < 1.25) |
| **`H-213-C4`** | `MRLM` | Range Loc Momentum (Channel 100, Th 0.80/0.20, SL1.5, TP3.75) | 3584 | **87** | 108.0 | 128 | 3.6% | 0.053 | 54.4% | 68.9% | 60.0% | 3.3% | **1.062** | $+3.36 | 1.180 | 0.935 | **`REJECTED`** | Gate E1 (PF = 1.062 < 1.25) |
| **`H-214-C1`** | `VRA` | Vol Acceleration (ATR7/28 > 1.20 + 3b Breakout + EMA50, SL1.5, TP3.0) | 3616 | **80** | 114.0 | 126 | 3.5% | 0.054 | 69.5% | 89.9% | 16.7% | 0.0% | **0.936** | $-3.23 | 1.022 | 0.859 | **`REJECTED`** | Gate E1 (PF = 0.936 < 1.25) |
| **`H-214-C2`** | `VRA` | Vol Acceleration (ATR7/28 > 1.20 + 3b Breakout + EMA50, SL1.5, TP3.75) | 3263 | **74** | 100.0 | 112 | 3.4% | 0.052 | 55.8% | 76.0% | 26.7% | 0.0% | **0.954** | $-2.53 | 1.037 | 0.876 | **`REJECTED`** | Gate E1 (PF = 0.954 < 1.25) |
| **`H-214-C3`** | `VRA` | Vol Acceleration (ATR7/28 > 1.30 + 3b Breakout + EMA50, SL1.5, TP3.0) | 2805 | **50** | 89.0 | 106 | 3.8% | 0.088 | 43.7% | 65.7% | 36.7% | 0.0% | **0.996** | $-0.20 | 1.066 | 0.932 | **`REJECTED`** | Gate E1 (PF = 0.996 < 1.25) |
| **`H-214-C4`** | `VRA` | Vol Acceleration (ATR7/28 > 1.30 + 3b Breakout + EMA50, SL1.5, TP3.75) | 2548 | **46** | 79.0 | 94 | 3.7% | 0.085 | 44.8% | 62.1% | 50.0% | 3.3% | **1.023** | $+1.20 | 1.135 | 0.920 | **`REJECTED`** | Gate E1 (PF = 1.023 < 1.25) |

---

## 3. PRECOMMITTED BOOLEAN GATE MATRIX

| Config ID | Gate A1 (Min $\ge 5$) | Gate A2 (Share $\le 5\%$) | Gate A3 (Max/Med $\le 3$) | Gate A4 (Gini $< 0.3$) | Gate B1 (Top3 $\le 40\%$) | Gate B2 (Top5 $\le 60\%$) | Gate D1 (R4 Pos $\ge 70\%$) | Gate D2 (R4 PF $\ge 65\%$) | Gate E1 (PF $\ge 1.25$) | Gate E2 (Exp $> 0$) | ALL PASS? |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`H-209-C1`** | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS | ❌ FAIL | ❌ FAIL | ❌ FAIL | ❌ FAIL | ❌ FAIL | ❌ FAIL | **❌ REJECTED** |
| **`H-209-C2`** | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS | ❌ FAIL | ❌ FAIL | ❌ FAIL | ❌ FAIL | **❌ REJECTED** |
| **`H-209-C3`** | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS | ❌ FAIL | ❌ FAIL | ❌ FAIL | ❌ FAIL | ❌ FAIL | ✅ PASS | **❌ REJECTED** |
| **`H-209-C4`** | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS | ❌ FAIL | ❌ FAIL | ❌ FAIL | ❌ FAIL | ❌ FAIL | ❌ FAIL | **❌ REJECTED** |
| **`H-210-C1`** | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS | ❌ FAIL | ❌ FAIL | ❌ FAIL | ❌ FAIL | ❌ FAIL | ❌ FAIL | **❌ REJECTED** |
| **`H-210-C2`** | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS | ❌ FAIL | ❌ FAIL | ❌ FAIL | ❌ FAIL | ❌ FAIL | ❌ FAIL | **❌ REJECTED** |
| **`H-210-C3`** | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS | ❌ FAIL | ❌ FAIL | ❌ FAIL | ❌ FAIL | ❌ FAIL | ❌ FAIL | **❌ REJECTED** |
| **`H-210-C4`** | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS | ❌ FAIL | ❌ FAIL | ❌ FAIL | ❌ FAIL | ❌ FAIL | ❌ FAIL | **❌ REJECTED** |
| **`H-211-C1`** | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS | ❌ FAIL | ❌ FAIL | ❌ FAIL | ❌ FAIL | ❌ FAIL | ❌ FAIL | **❌ REJECTED** |
| **`H-211-C2`** | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS | ❌ FAIL | ❌ FAIL | ❌ FAIL | ❌ FAIL | ❌ FAIL | ❌ FAIL | **❌ REJECTED** |
| **`H-211-C3`** | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS | ❌ FAIL | ❌ FAIL | ❌ FAIL | ❌ FAIL | ❌ FAIL | ❌ FAIL | **❌ REJECTED** |
| **`H-211-C4`** | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS | ❌ FAIL | ❌ FAIL | ❌ FAIL | ❌ FAIL | ❌ FAIL | ❌ FAIL | **❌ REJECTED** |
| **`H-212-C1`** | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS | ❌ FAIL | ❌ FAIL | ❌ FAIL | ❌ FAIL | ❌ FAIL | ❌ FAIL | **❌ REJECTED** |
| **`H-212-C2`** | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS | ❌ FAIL | ❌ FAIL | ❌ FAIL | ❌ FAIL | ❌ FAIL | ❌ FAIL | **❌ REJECTED** |
| **`H-212-C3`** | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS | ❌ FAIL | ❌ FAIL | ❌ FAIL | ❌ FAIL | ❌ FAIL | ❌ FAIL | **❌ REJECTED** |
| **`H-212-C4`** | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS | ❌ FAIL | ❌ FAIL | ❌ FAIL | ❌ FAIL | ❌ FAIL | ❌ FAIL | **❌ REJECTED** |
| **`H-213-C1`** | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS | ❌ FAIL | ❌ FAIL | ❌ FAIL | ❌ FAIL | ❌ FAIL | ✅ PASS | **❌ REJECTED** |
| **`H-213-C2`** | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS | ❌ FAIL | ❌ FAIL | ❌ FAIL | ❌ FAIL | ❌ FAIL | ✅ PASS | **❌ REJECTED** |
| **`H-213-C3`** | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS | ❌ FAIL | ❌ FAIL | ❌ FAIL | ❌ FAIL | ❌ FAIL | ✅ PASS | **❌ REJECTED** |
| **`H-213-C4`** | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS | ❌ FAIL | ❌ FAIL | ❌ FAIL | ❌ FAIL | ❌ FAIL | ✅ PASS | **❌ REJECTED** |
| **`H-214-C1`** | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS | ❌ FAIL | ❌ FAIL | ❌ FAIL | ❌ FAIL | ❌ FAIL | ❌ FAIL | **❌ REJECTED** |
| **`H-214-C2`** | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS | ❌ FAIL | ❌ FAIL | ❌ FAIL | ❌ FAIL | ❌ FAIL | ❌ FAIL | **❌ REJECTED** |
| **`H-214-C3`** | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS | ❌ FAIL | ❌ FAIL | ❌ FAIL | ❌ FAIL | ❌ FAIL | ❌ FAIL | **❌ REJECTED** |
| **`H-214-C4`** | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS | ❌ FAIL | ❌ FAIL | ❌ FAIL | ❌ FAIL | ❌ FAIL | ✅ PASS | **❌ REJECTED** |

---

## 4. EVIDENCE-ACCURATE MECHANISM TAKEAWAYS

1. **Directional Asymmetry is Mechanism-Dependent**: Some momentum families, particularly H-213 (Location Momentum) and H-214 (Volatility Acceleration), showed stronger Long performance than Short performance on Gold M30. However, this pattern was not universal across all 24 configurations (e.g., in H-212 Session Expansion, Short PF was equal to or slightly above Long PF).
2. **Mean-Reversion Failure Specificity**: The specific mean-reversion and false-breakout definitions tested in H-210 and H-211 produced strongly negative historical performance under the frozen execution assumptions. This is evidence against these specific implementations, not against the entire broad theoretical class of mean-reversion mechanisms.
3. **Opportunity Density Invariance**: Rebuilding the 33-quarter tables strictly from the clean evaluation population confirms that all 24 configurations generated high opportunity density ($\ge 46$ to $136$ trades/quarter) across all 33 complete quarters without a single quiet-quarter violation.

---

## 5. FINAL SCIENTIFIC DECISION

> ### **NO H-209→H-214 CONFIGURATION PASSED THE REPAIRED V3.3 DISTRIBUTED EDGE STANDARD.**
