# V3.3 BATCH-1 PRECOMMITMENT PROTOCOL: HYPOTHESES H-209 TO H-214
## IMMUTABLE PRE-EXECUTION SPECIFICATION MATRIX

* **Precommitment Timestamp**: `2026-08-16T00:46:50+07:00`
* **Parent Git Commit SHA**: `1ba010d2d706b5985da844f0323441ffd7807a4d`
* **Target Instrument & Timeframe**: `GOLD_M30.csv` (2018Q2 to 2026Q2, 33 complete quarters)
* **Execution Parameters**: Fixed Lot = 0.10, Spread = 25.0 pips, Commission = $7.0/lot

---

## 1. HYPOTHESIS SPECIFICATIONS & ECONOMIC MECHANISMS

### Family 1: `H-209` — Multi-Horizon Trend Persistence (MHTP)
- **Economic Mechanism**: Intraday trend continuation. Fast EMA(20) pullback into medium-term trend EMA(50) > EMA(100) followed by immediate resumption.
- **Entry Rules**:
  - *Long*: `EMA(50) > EMA(100)`, prior bar `Low < EMA(20)`, current bar `Close > EMA(20)`.
  - *Short*: `EMA(50) < EMA(100)`, prior bar `High > EMA(20)`, current bar `Close < EMA(20)`.
- **Configurations**:
  - `H-209-C1`: `SL = 1.5 * ATR(14)`, `TP = 3.0 * ATR(14)` (2.0x SL)
  - `H-209-C2`: `SL = 1.5 * ATR(14)`, `TP = 3.75 * ATR(14)` (2.5x SL)
  - `H-209-C3`: `SL = 2.0 * ATR(14)`, `TP = 4.0 * ATR(14)` (2.0x SL)
  - `H-209-C4`: `SL = 2.0 * ATR(14)`, `TP = 5.0 * ATR(14)` (2.5x SL)

---

### Family 2: `H-210` — Extreme Displacement Mean Reversion (EDMR)
- **Economic Mechanism**: Overextended price mean-reverts back to rolling EMA(50) equilibrium after moving $> K \times \text{ATR}(14)$ away from baseline.
- **Entry Rules**:
  - *Long*: `Close < EMA(50) - K * ATR(14)`.
  - *Short*: `Close > EMA(50) + K * ATR(14)`.
- **Configurations**:
  - `H-210-C1`: `K = 2.5`, `SL = 1.5 * ATR(14)`, `TP = 2.25 * ATR(14)` (1.5x SL)
  - `H-210-C2`: `K = 2.5`, `SL = 1.5 * ATR(14)`, `TP = 3.0 * ATR(14)` (2.0x SL)
  - `H-210-C3`: `K = 3.0`, `SL = 1.5 * ATR(14)`, `TP = 2.25 * ATR(14)` (1.5x SL)
  - `H-210-C4`: `K = 3.0`, `SL = 1.5 * ATR(14)`, `TP = 3.0 * ATR(14)` (2.0x SL)

---

### Family 3: `H-211` — Failed Breakout Reversal / Liquidity Trap (FBRLT)
- **Economic Mechanism**: False breakout / stop hunt. Price exceeds rolling $N$-bar High/Low during the bar but fails to sustain momentum and closes back strictly inside the range.
- **Entry Rules**:
  - *Short (Failed High Breakout)*: `High > Donchian_High(N)[shift 1]` AND `Close < Donchian_High(N)[shift 1]`.
  - *Long (Failed Low Breakout)*: `Low < Donchian_Low(N)[shift 1]` AND `Close > Donchian_Low(N)[shift 1]`.
- **Configurations**:
  - `H-211-C1`: `N = 20`, `SL = 1.5 * ATR(14)`, `TP = 3.0 * ATR(14)` (2.0x SL)
  - `H-211-C2`: `N = 20`, `SL = 1.5 * ATR(14)`, `TP = 3.75 * ATR(14)` (2.5x SL)
  - `H-211-C3`: `N = 40`, `SL = 1.5 * ATR(14)`, `TP = 3.0 * ATR(14)` (2.0x SL)
  - `H-211-C4`: `N = 40`, `SL = 1.5 * ATR(14)`, `TP = 3.75 * ATR(14)` (2.5x SL)

---

### Family 4: `H-212` — Session Opening Range Expansion (SORE)
- **Economic Mechanism**: London/NY institutional liquidity driving expansion beyond the Asian consolidation session (00:00–07:00 UTC).
- **Entry Rules**:
  - Reference window: Asian Session High $H_{\text{asia}}$ and Low $L_{\text{asia}}$ computed daily from 00:00 to 07:00 UTC.
  - Active trade window: 08:00 to 16:00 UTC.
  - *Long*: `Hour in [8, 16]`, `Close > H_asia`, `Close > EMA(50)`.
  - *Short*: `Hour in [8, 16]`, `Close < L_asia`, `Close < EMA(50)`.
- **Configurations**:
  - `H-212-C1`: `EMA = 50`, `SL = 1.5 * ATR(14)`, `TP = 3.0 * ATR(14)` (2.0x SL)
  - `H-212-C2`: `EMA = 50`, `SL = 1.5 * ATR(14)`, `TP = 3.75 * ATR(14)` (2.5x SL)
  - `H-212-C3`: `EMA = 100`, `SL = 1.5 * ATR(14)`, `TP = 3.0 * ATR(14)` (2.0x SL)
  - `H-212-C4`: `EMA = 100`, `SL = 1.5 * ATR(14)`, `TP = 3.75 * ATR(14)` (2.5x SL)

---

### Family 5: `H-213` — Medium-Range Location + Momentum (MRLM)
- **Economic Mechanism**: Normalized range position $\text{Loc} = (C - L_N) / (H_N - L_N)$ combined with directional Rate of Change `ROC(10)`.
- **Entry Rules**:
  - *Long*: $\text{Loc} > \text{Threshold}_{\text{upper}}$ AND `ROC(10) > 0`.
  - *Short*: $\text{Loc} < \text{Threshold}_{\text{lower}}$ AND `ROC(10) < 0`.
- **Configurations**:
  - `H-213-C1`: `N = 50`, `Th_upper = 0.75, Th_lower = 0.25`, `SL = 1.5 * ATR(14)`, `TP = 3.0 * ATR(14)` (2.0x SL)
  - `H-213-C2`: `N = 50`, `Th_upper = 0.75, Th_lower = 0.25`, `SL = 1.5 * ATR(14)`, `TP = 3.75 * ATR(14)` (2.5x SL)
  - `H-213-C3`: `N = 100`, `Th_upper = 0.80, Th_lower = 0.20`, `SL = 1.5 * ATR(14)`, `TP = 3.0 * ATR(14)` (2.0x SL)
  - `H-213-C4`: `N = 100`, `Th_upper = 0.80, Th_lower = 0.20`, `SL = 1.5 * ATR(14)`, `TP = 3.75 * ATR(14)` (2.5x SL)

---

### Family 6: `H-214` — Volatility Regime Acceleration (VRA - Non-Squeeze)
- **Economic Mechanism**: Sudden expansion in fast volatility relative to baseline ($\text{ATR}(7) / \text{ATR}(28) > \text{Ratio}_{\text{th}}$) driving multi-bar trend momentum.
- **Entry Rules**:
  - *Long*: `ATR(7) / ATR(28) > Ratio_th`, `Close > 3-bar High[shift 1]`, `Close > EMA(50)`.
  - *Short*: `ATR(7) / ATR(28) > Ratio_th`, `Close < 3-bar Low[shift 1]`, `Close < EMA(50)`.
- **Configurations**:
  - `H-214-C1`: `Ratio_th = 1.20`, `SL = 1.5 * ATR(14)`, `TP = 3.0 * ATR(14)` (2.0x SL)
  - `H-214-C2`: `Ratio_th = 1.20`, `SL = 1.5 * ATR(14)`, `TP = 3.75 * ATR(14)` (2.5x SL)
  - `H-214-C3`: `Ratio_th = 1.30`, `SL = 1.5 * ATR(14)`, `TP = 3.0 * ATR(14)` (2.0x SL)
  - `H-214-C4`: `Ratio_th = 1.30`, `SL = 1.5 * ATR(14)`, `TP = 3.75 * ATR(14)` (2.5x SL)

---

## 2. PRECOMMITTED FIRST-PASS EXPERIMENT MATRIX (24 CONFIGURATIONS)

| Config ID | Family | Economic Concept | Key Parameters | SL / TP |
| :--- | :--- | :--- | :--- | :--- |
| `H-209-C1` | MHTP | Multi-Horizon Trend Persistence | EMA(50/100) trend + EMA(20) pullback trigger | 1.5 ATR / 3.0 ATR (2.0x) |
| `H-209-C2` | MHTP | Multi-Horizon Trend Persistence | EMA(50/100) trend + EMA(20) pullback trigger | 1.5 ATR / 3.75 ATR (2.5x) |
| `H-209-C3` | MHTP | Multi-Horizon Trend Persistence | EMA(50/100) trend + EMA(20) pullback trigger | 2.0 ATR / 4.0 ATR (2.0x) |
| `H-209-C4` | MHTP | Multi-Horizon Trend Persistence | EMA(50/100) trend + EMA(20) pullback trigger | 2.0 ATR / 5.0 ATR (2.5x) |
| `H-210-C1` | EDMR | Extreme Displacement Mean Reversion | Distance from EMA(50) > 2.5 ATR | 1.5 ATR / 2.25 ATR (1.5x) |
| `H-210-C2` | EDMR | Extreme Displacement Mean Reversion | Distance from EMA(50) > 2.5 ATR | 1.5 ATR / 3.0 ATR (2.0x) |
| `H-210-C3` | EDMR | Extreme Displacement Mean Reversion | Distance from EMA(50) > 3.0 ATR | 1.5 ATR / 2.25 ATR (1.5x) |
| `H-210-C4` | EDMR | Extreme Displacement Mean Reversion | Distance from EMA(50) > 3.0 ATR | 1.5 ATR / 3.0 ATR (2.0x) |
| `H-211-C1` | FBRLT| Failed Breakout Reversal / Trap | Donchian(20) false breakout rejection | 1.5 ATR / 3.0 ATR (2.0x) |
| `H-211-C2` | FBRLT| Failed Breakout Reversal / Trap | Donchian(20) false breakout rejection | 1.5 ATR / 3.75 ATR (2.5x) |
| `H-211-C3` | FBRLT| Failed Breakout Reversal / Trap | Donchian(40) false breakout rejection | 1.5 ATR / 3.0 ATR (2.0x) |
| `H-211-C4` | FBRLT| Failed Breakout Reversal / Trap | Donchian(40) false breakout rejection | 1.5 ATR / 3.75 ATR (2.5x) |
| `H-212-C1` | SORE | Session Opening Range Expansion | Asian 00-07 ref, London 08-16 breakout + EMA50 | 1.5 ATR / 3.0 ATR (2.0x) |
| `H-212-C2` | SORE | Session Opening Range Expansion | Asian 00-07 ref, London 08-16 breakout + EMA50 | 1.5 ATR / 3.75 ATR (2.5x) |
| `H-212-C3` | SORE | Session Opening Range Expansion | Asian 00-07 ref, London 08-16 breakout + EMA100 | 1.5 ATR / 3.0 ATR (2.0x) |
| `H-212-C4` | SORE | Session Opening Range Expansion | Asian 00-07 ref, London 08-16 breakout + EMA100 | 1.5 ATR / 3.75 ATR (2.5x) |
| `H-213-C1` | MRLM | Medium-Range Location + Momentum | 50-bar Channel Loc (0.75/0.25) + ROC(10) | 1.5 ATR / 3.0 ATR (2.0x) |
| `H-213-C2` | MRLM | Medium-Range Location + Momentum | 50-bar Channel Loc (0.75/0.25) + ROC(10) | 1.5 ATR / 3.75 ATR (2.5x) |
| `H-213-C3` | MRLM | Medium-Range Location + Momentum | 100-bar Channel Loc (0.80/0.20) + ROC(10) | 1.5 ATR / 3.0 ATR (2.0x) |
| `H-213-C4` | MRLM | Medium-Range Location + Momentum | 100-bar Channel Loc (0.80/0.20) + ROC(10) | 1.5 ATR / 3.75 ATR (2.5x) |
| `H-214-C1` | VRA  | Volatility Regime Acceleration | ATR(7)/ATR(28) > 1.20 + 3b Breakout + EMA50 | 1.5 ATR / 3.0 ATR (2.0x) |
| `H-214-C2` | VRA  | Volatility Regime Acceleration | ATR(7)/ATR(28) > 1.20 + 3b Breakout + EMA50 | 1.5 ATR / 3.75 ATR (2.5x) |
| `H-214-C3` | VRA  | Volatility Regime Acceleration | ATR(7)/ATR(28) > 1.30 + 3b Breakout + EMA50 | 1.5 ATR / 3.0 ATR (2.0x) |
| `H-214-C4` | VRA  | Volatility Regime Acceleration | ATR(7)/ATR(28) > 1.30 + 3b Breakout + EMA50 | 1.5 ATR / 3.75 ATR (2.5x) |
