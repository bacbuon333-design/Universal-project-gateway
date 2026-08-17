# ALAB-M1-FUSION-001 — Failed Auction + Adaptive Reaction Zone Precommit

## 1. Experiment Identity and Governance

- **Experiment ID**: `ALAB-M1-FUSION-001`
- **Experiment Version**: `v1`
- **Research Type**: `EVENT_STUDY_PLUS_SINGLE_DIAGNOSTIC_BACKTEST`
- **Timeframe**: `M1`
- **Primary Symbol**: `GOLD` / `XAUUSD`
- **Repository**: `bacbuon333-design/Universal-project-gateway`
- **Branch**: `research/quant-m1-fusion-failed-auction-v1`
- **Scientific Parent**: `5a1a2f8c28f857789943295f6a59df2f1037e72b`
- **Base HEAD**: `e94f03865114a34657ed744876d052b5859e1153`

### Absolute Safety Assertions
```text
strategy_validation = NOT_AUTHORIZED
paper_trading = NO
live_trading = NO
broker_execution = NO
research_only = YES
```

---

## 2. Scientific Hypotheses

### Hypothesis
A directional, efficient price displacement reaching or breaching a structural reaction zone, failing to achieve acceptance beyond that extreme, and snapping back exhibits a statistically significant forward directional edge at M1 resolution.

### Null Hypothesis ($H_0$)
The forward signed returns following a Failed Auction event at M1 resolution have an expected mean $\le 0$ across forward horizons $[1, 3, 5, 10, 15, 30]$ minutes.

### Alternative Hypothesis ($H_1$)
Failed Auction events occurring in confluence with high path efficiency, robust stretch, elevated volatility, and structural reaction zones exhibit a statistically positive mean signed forward return ($> 0$) at the 5-minute primary horizon with a 95% bootstrap confidence interval lower bound $> 0$.

---

## 3. Frozen Parameters and Mechanism Specification

### A. Core Failed Auction
- `PRIOR_EXTREME_LOOKBACK = 20` M1 bars.
- Short Failed Auction: `high[t] > prior_high[t]` AND `close[t] < prior_high[t]` (Bearish snapback expected).
- Long Failed Auction: `low[t] < prior_low[t]` AND `close[t] > prior_low[t]` (Bullish snapback expected).
- Causal: Prior extreme calculation strictly excludes event bar $t$.

### B. Path Efficiency
- `PATH_WINDOW = 10` bars preceding the event.
- $\text{efficiency\_ratio} = \text{net\_displacement} / \text{path\_length}$.
- Direction agreement required (Upward for Short Failed Auction, Downward for Long Failed Auction).
- `EFFICIENCY_THRESHOLD = 0.65`.

### C. Robust Stretch Z-Score
- `ROBUST_WINDOW = 60` bars trailing $t-1$.
- $\text{center} = \text{median}(\text{close})$.
- $\text{MAD} = \text{median}(|\text{close} - \text{center}|)$.
- $\text{robust\_sigma} = 1.4826 \times \text{MAD}$.
- $\text{stretch\_z} = (\text{close}[t-1] - \text{center}) / \text{robust\_sigma}$.
- `ROBUST_Z_THRESHOLD = 2.0` (Short: $Z \ge +2.0$, Long: $Z \le -2.0$).

### D. Volatility Percentile
- `ATR_PERIOD = 14` (Wilder-style EWM).
- `ATR_PERCENTILE_WINDOW = 500` bars trailing $t-1$.
- `ATR_PERCENTILE_THRESHOLD = 80.0%`.

### E. Reaction Zones
1. **Previous Day High / Low (PDH / PDL)**: Completed UTC calendar day $D-1$. Distance tolerance $\le 0.15 \times \text{ATR14}$. (+2 points)
2. **Completed Session Extremes**: Asia (00:00-07:59), London (08:00-12:59), New York (13:00-17:59) UTC. Extreme available only after session completion. Distance tolerance $\le 0.15 \times \text{ATR14}$. (+1 point)
3. **Confirmed M15 Swings**: M15 resampled, Pivot Flank = 2. Swing at M15 index $j$ confirmed at close of $j+2$. Zone width $= 0.10 \times \text{M15\_ATR14}$. (+1 point)

### F. Frozen Reaction Score
- Failed Auction (mandatory): `+3`
- High Path Efficiency: `+1`
- Extreme Robust Stretch: `+1`
- High Volatility Percentile: `+1`
- PDH / PDL Interaction: `+2`
- Completed Session Extreme: `+1`
- Confirmed M15 Swing: `+1`
- **Total Score**: Range $[3, 10]$. Bins: `3-4`, `5-6`, `7-8`, `9-10`.

---

## 4. Primary Horizon and Discovery Gates

- **Primary Horizon**: 5 minutes ($h = 5$).
- **Secondary Horizons**: 1m, 3m, 10m, 15m, 30m.
- **Bootstrap Parameters**: 2,000 simulations, fixed seed `20260817`, 95% confidence interval.

### Discovery Gate Battery (All 6 Required for `MECHANISM_CLUE`):
1. **Sample Size**: Total events $\ge 500$, Long events $\ge 150$, Short events $\ge 150$.
2. **Primary Mean**: 5m mean signed return $> 0$.
3. **Primary Bootstrap**: 5m 95% bootstrap CI lower bound $> 0$.
4. **Adjacent Consistency**: At least one adjacent horizon (3m or 10m) mean signed return $> 0$.
5. **Temporal Stability**: Effect not produced by a single isolated calendar year.
6. **Score Gradient**: Higher score bins (7-8, 9-10) do not invert and collapse below lower bins.

---

## 5. Single Diagnostic Backtest Specification

- **Qualifying Filter**: Failed Auction event with Reaction Score $\ge 7$.
- **Entry**: Open of bar $t+1$.
- **Stop Loss**: $1.00 \times \text{ATR14}[t]$ from entry open.
- **Take Profit**: NONE.
- **Holding Period**: 5 M1 bars (Exit at Close of $t+5$ or stop hit first).
- **Intrabar Stop**: Conservative fill on OHLC touch.
- **Position Limit**: One active trade at a time per symbol.
- **Cost Policy**: Actual historical spread if present, otherwise labeled `RESEARCH_ONLY_UNVERIFIED_COST`.

---

## 6. Anti-Overfit and Multiple-Testing Rules

- Exactly ONE frozen parameter configuration.
- No parameter grid search, no threshold optimization.
- No dynamic indicators (RSI, MACD, Stochastic, SuperTrend, ML, LLM).
- No post-hoc tuning or subset cherry-picking.
- If gates fail $\rightarrow$ `NO_MECHANISM_EVIDENCE` or `INSUFFICIENT_EVIDENCE`.
