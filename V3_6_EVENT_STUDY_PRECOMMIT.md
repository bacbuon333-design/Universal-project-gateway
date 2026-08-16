# V3.6 LMDC EVENT STUDY & MECHANISM PRECOMMIT PROTOCOL
## LONDON MORNING DIRECTIONAL CARRY (LMDC) MICROSTRUCTURE RESEARCH

* **Precommitment Timestamp**: `2026-08-16T10:59:00+07:00`
* **Parent Git Commit SHA**: `276223f255572f784098cfa005019ae7e29aa45c`
* **Active Branch**: `research/quant-v3.6-lmdc-event-study`
* **Instrument / Timeframe**: `GOLD_M30.csv`
* **Evaluation Window**: `2018Q2` through `2026Q2` (33 complete calendar quarters, 7 complete calendar years 2019–2025)

---

## 1. SCIENTIFIC OBJECTIVE & DISCLOSURE
The purpose of V3.6 is to conduct an independent, causal, non-backtest **Event Study** on the London Morning Directional Carry (LMDC) phenomenon on Gold M30.
- **Core Question**: Does a decisive directional displacement during the London morning session (08:00–12:00 UTC) predict a persistent, statistically robust, and economically meaningful continuation in the afternoon/evening sessions?
- **Explicit Disclosure**: The objective is NOT to optimize trading parameters or salvage H-220 backtests. The objective is to determine whether the underlying market mechanism itself actually exists across history with sufficient temporal stability.

---

## 2. EVENT DEFINITION & CAUSAL NORMALIZATION
For each valid UTC trading day in the historical dataset:
1. **Morning Block**: `08:00 <= timestamp < 12:00 UTC`.
2. **Morning Open**: `morning_open` = Open price of the first M30 bar at/after 08:00 UTC.
3. **Morning Close**: `morning_close` = Close price of the final completed M30 bar before 12:00 UTC (i.e. bar timestamp 11:30 UTC).
4. **Morning Move**: `morning_move = morning_close - morning_open`.
5. **Causal Volatility Normalization**: `ATR14_pre12` = 14-period Simple Moving Average of True Range measured at the close of the 11:30 UTC bar.
6. **Normalized Displacement Score**:
   $$\text{morning\_z} = \frac{\text{morning\_move}}{\text{ATR14\_pre12}}$$
7. **Event Decision Timestamp**: `12:00 UTC Close` (reference price $P_{\text{ref}} = \text{Close at 12:00 UTC}$).
8. **Event Uniqueness**: Exactly **one event maximum per UTC calendar day**. Zero intra-day duplicate signals.

---

## 3. FIXED MAGNITUDE BUCKETS (NO POST-HOC TUNING)
All events are categorized into 5 mutually exclusive, precommitted magnitude tiers:
1. **Tier 0 (Baseline / Quiet)**: $|\text{morning\_z}| < 0.5$
2. **Tier 1 (Mild Move)**: $0.5 \le |\text{morning\_z}| < 1.0$
3. **Tier 2 (Moderate Move)**: $1.0 \le |\text{morning\_z}| < 1.5$
4. **Tier 3 (Strong Move)**: $1.5 \le |\text{morning\_z}| < 2.0$
5. **Tier 4 (Extreme Move)**: $|\text{morning\_z}| \ge 2.0$

Direction is explicitly tracked:
- **Positive Morning**: $\text{morning\_move} > 0$ ($\text{direction} = +1$)
- **Negative Morning**: $\text{morning\_move} < 0$ ($\text{direction} = -1$)

---

## 4. PRECOMMITTED FORWARD HORIZONS
Forward measurements begin strictly at the 12:00 UTC bar close:
- **$h = 30\text{m}$**: 1 bar ahead (Close at 12:30 UTC)
- **$h = 1\text{h}$**: 2 bars ahead (Close at 13:00 UTC)
- **$h = 2\text{h}$**: 4 bars ahead (Close at 14:00 UTC)
- **$h = 4\text{h}$**: 8 bars ahead (Close at 16:00 UTC)
- **$h = 8\text{h}$**: 16 bars ahead (Close at 20:00 UTC)
- **$h = \text{Day Close}$**: Final completed bar of the UTC trading day.

---

## 5. PRIMARY ESTIMANDS & METRICS
For each event and forward horizon $h$:
1. **Raw Forward Return**: $R_{\text{raw}, h} = P_{12:00 + h} - P_{\text{ref}}$
2. **Signed Continuation Return**: $R_{\text{signed}, h} = \text{direction} \times R_{\text{raw}, h}$
   - Positive value = Continuation in direction of morning move.
   - Negative value = Reversal against morning move.
3. **ATR-Normalized Signed Return**: $R_{\text{signed\_atr}, h} = R_{\text{signed}, h} / \text{ATR14\_pre12}$
4. **Continuation Probability**: $P(R_{\text{signed}, h} > 0)$
5. **Distributional Statistics**: Mean, Median, Standard Deviation, 25th Percentile (P25), 75th Percentile (P75).
6. **MFE / MAE**:
   - **MFE** (Maximum Favorable Excursion after 12:00 along morning direction) normalized by $\text{ATR14\_pre12}$.
   - **MAE** (Maximum Adverse Excursion after 12:00 against morning direction) normalized by $\text{ATR14\_pre12}$.
   - Ratio: $\text{Median MFE} / \text{Median MAE}$.

---

## 6. TEMPORAL & SUB-PERIOD DIAGNOSTICS
1. **Year-by-Year Stability**: Full years 2019 through 2025 (plus 2018/2026 partials).
2. **Quarter-by-Quarter Stability**: All 33 complete quarters (2018Q2 to 2026Q2) recorded in `lmdc_quarter_effects.csv`.
3. **Recent-Regime Comparison (Three Views)**:
   - **View A (Full Sample)**: 2018Q2–2026Q2
   - **View B (Pre-2025)**: 2018Q2–2024Q4
   - **View C (Recent)**: 2025Q1–2026Q2
4. **Leave-One-Year-Out Sensitivity**: Recalculate aggregate effects omitting each year $Y \in [2019, 2025]$.
5. **Leave-Recent-Period-Out**: Explicitly test whether the effect exists when 2025 and 2026 are entirely removed.
6. **Time-of-Day Cumulative Path**: Average direction-adjusted cumulative return curve at 12:30, 13:00, 14:00, 16:00, 20:00, and Day Close.
7. **Monotonicity Check**: Verify whether increasing $|\text{morning\_z}|$ corresponds to increasing forward signed returns across Tier 0..Tier 4.
8. **Cost Benchmark Comparison**: Approximate round-trip execution cost (25 pips spread + $7/lot commission $\approx \$0.32$ USD $\approx 0.04-0.08\text{ ATR}$) compared against empirical effect size.
9. **Descriptive Regression**: $\text{signed\_forward\_ATR\_return} \sim |\text{morning\_z}|$ (pooled and directional).

---

## 7. UNCERTAINTY QUANTIFICATION (BOOTSTRAP PROTOCOL)
- **IID Bootstrap**: 2,000 resamples for descriptive baseline.
- **Quarter-Block Bootstrap**: Group daily events by calendar quarter (33 quarters). Resample complete quarters with replacement $\ge 2,000$ times. Compute 2.5%, 50.0% (Median), and 97.5% quantiles (95% Bootstrap Confidence Interval).

---

## 8. FALSIFICATION RULES & SUPPORT LEVELS
The LMDC continuation mechanism is falsified / NOT supported if ANY of the following occur:
1. The aggregate effect disappears when 2025–2026 are excluded.
2. Fewer than 4 of the 7 complete years (2019–2025) show positive continuation at key horizons.
3. Quarter-level effect is dominated by $\le 3$ outlier quarters.
4. The 95% Quarter-block bootstrap CI strongly overlaps zero or is negative at key horizons.
5. Effect size is trivial relative to the transaction cost benchmark.
6. Positive effect exists solely in one isolated, non-monotonic bucket.
7. Long and Short effects cancel in an unstable manner without prior structural justification.

### Allowed Support Classifications:
1. `LMDC MECHANISM NOT SUPPORTED`
2. `LMDC MECHANISM WEAK / REGIME-DEPENDENT`
3. `LMDC MECHANISM HISTORICALLY SUPPORTED — STRATEGY DESIGN STILL REQUIRED`
*(Never use labels such as VALIDATED ALPHA, PROVEN EDGE, or TRUE ALPHA).*
