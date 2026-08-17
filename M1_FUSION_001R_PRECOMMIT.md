# ALAB-M1-FUSION-001R — Replication & Research Infrastructure Repair Precommit

## 1. Governance and Provenance

- **Experiment ID**: `ALAB-M1-FUSION-001R`
- **Experiment Version**: `v1.1-replication`
- **Research Type**: `REPLICATION_EVENT_STUDY_PLUS_DUAL_DIAGNOSTIC_BACKTEST`
- **Timeframe**: `M1`
- **Symbol**: `GOLD` / `XAUUSD`
- **Repository**: `bacbuon333-design/Universal-project-gateway`
- **Branch**: `research/quant-m1-fusion-001r-replication`
- **Base SHA (V1 Result SHA)**: `6c257c313a83e2dec5813fc36be921912209bc68`

### Absolute Safety Assertions
```text
strategy_validation = NOT_AUTHORIZED
paper_trading = NO
live_trading = NO
broker_execution = NO
research_only = YES
```

---

## 2. Discovery Sample Quarantine Contract

- **Quarantined Discovery Sample**: 2026-04-15 01:12:00 UTC to 2026-07-24 23:57:00 UTC (99,999 bars, SHA256: `b980ac086f5de4ab60621d0ddcb3bac59d37ebd0bec236d24971f81918b1f3ec`).
- **Status**: `DISCOVERY_SAMPLE_SEEN`.
- **Primary Replication Cutoff**: `datetime < 2026-01-01T00:00:00Z`.
- **Inference Overlap**: Exactly `0` rows from the discovery sample are permitted in the primary replication inference.

---

## 3. Hard Data Gate Fail-Closed Requirements

- `MIN_REPLICATION_ROWS = 1,000,000` pre-2026 M1 bars.
- `MIN_VALID_CALENDAR_YEARS = 3` distinct calendar years.
- **Fail-Closed Rule**: If $N_{\text{replication}} < 1,000,000$ rows, runner must immediately raise `STOP_BLOCKED_INSUFFICIENT_HISTORY`. If calendar years $< 3$, runner must raise `STOP_BLOCKED_INSUFFICIENT_TEMPORAL_COVERAGE`. Zero scientific inference may proceed without satisfying these data thresholds.

---

## 4. Frozen Core Mechanism & Parameters (Strictly Unchanged from V1)

- **Prior Extreme Lookback**: `PRIOR_EXTREME_LOOKBACK = 20` M1 bars (excludes current bar).
- **Path Efficiency**: `PATH_WINDOW = 10`, `EFFICIENCY_THRESHOLD = 0.65`.
- **Robust Stretch**: `ROBUST_WINDOW = 60`, `ROBUST_Z_THRESHOLD = 2.0` (Short $Z \ge +2.0$, Long $Z \le -2.0$).
- **Volatility Percentile**: `ATR_PERIOD = 14`, `ATR_PERCENTILE_WINDOW = 500`, `ATR_PERCENTILE_THRESHOLD = 80.0%`.
- **Reaction Zones**:
  - PDH / PDL: Completed day $D-1$, tolerance $\le 0.15 \times \text{ATR14}$ (`+2 points`).
  - Session Extremes: Asia (00:00-07:59), London (08:00-12:59), NY (13:00-17:59) UTC completed sessions only, tolerance $\le 0.15 \times \text{ATR14}$ (`+1 point`).
  - Confirmed M15 Swings: Pivot Flank = 2, confirmation at close of $j+2$, width $= 0.10 \times \text{M15\_ATR14}$ (`+1 point`).
- **Reaction Score**: Range $[3, 10]$ with mandatory Failed Auction (`+3 points`).
- **Score Bins**: `3-4`, `5-6`, `7-8`, `9-10`.

---

## 5. Statistical Methodology & Bootstrap Repair

- **Primary Horizon**: 5 minutes ($h = 5$).
- **Serial Correlation Protection**: UTC Day-Level Block Bootstrap ($B = 2,000$ simulations, fixed seed `20260817`).
- **Overlap Audit**: Mandatory quantification of event gaps and forward return window overlap percentages at 5m, 10m, and 30m.

---

## 6. Replication Discovery Gate Battery

1. **Gate 0 (Data)**: Rows $\ge 1,000,000$ and Valid Calendar Years $\ge 3$.
2. **Gate 1 (Event Sample)**: Total events $\ge 500$, Long $\ge 150$, Short $\ge 150$.
3. **Gate 2 (Primary Mean)**: 5m mean signed return $> 0$.
4. **Gate 3 (Day-Block Bootstrap)**: 5m Day-Block bootstrap 95% CI lower bound $> 0$.
5. **Gate 4 (Adjacent Horizon)**: At least one adjacent horizon (3m or 10m) mean signed return $> 0$.
6. **Gate 5 (Temporal Stability Repair)**:
   - Valid year defined as $\ge 200$ Failed Auction events (`MIN_VALID_YEAR_EVENTS = 200`).
   - Valid calendar years $\ge 3$.
   - Positive valid calendar years ratio $\ge 70\%$ ($\ge 0.70$).
   - Single year or two years strictly FAILS.
7. **Gate 6 (Score Behavior Description)**: Honest descriptive reporting (`MONOTONIC`, `PARTIAL`, `INVERTED`, or `INSUFFICIENT_HIGH_SCORE_SAMPLE`).

---

## 7. Dual Gross / Net Diagnostic Strategy

- **Signal**: Failed Auction with Reaction Score $\ge 7$.
- **Entry**: Open of bar $t+1$.
- **Stop Loss**: $1.00 \times \text{ATR14}[t]$ from entry open.
- **Take Profit**: NONE.
- **Holding Period**: 5 M1 bars.
- **Execution Model**: `M1_OHLC_CONSERVATIVE_STOP`.
- **Cost Model**: Verified dynamic broker point conversion (`spread_points * symbol_point`), 100 oz contract size, documented commission ($7.0/lot).
- **Reporting**: Both GROSS and NET metrics mandatory.
