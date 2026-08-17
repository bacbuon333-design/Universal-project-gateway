# ALAB-M1-FUSION-001R-RUN1 — Frozen Out-of-Sample Replication Precommit

## 1. Governance and Experiment Identity

- **Experiment ID**: `ALAB-M1-FUSION-001R-RUN1`
- **Experiment Type**: `FROZEN_OUT_OF_SAMPLE_REPLICATION_EXECUTION`
- **Base Commit**: `88c9b3b36394592283f601e27b299632d3f98b2e`
- **Branch**: `research/quant-m1-fusion-001r-run1`
- **Symbol**: `GOLD` / `XAUUSD`
- **Timeframe**: `M1`
- **Output Location**: `AlphaLab_Antigravity/reports/m1_fusion_001r_run1/`

### Absolute Safety Assertions
```text
strategy_validation = NOT_AUTHORIZED
paper_trading = NO
live_trading = NO
broker_execution = NO
research_only = YES
```

---

## 2. Bound Canonical Dataset Specification

- **Dataset Path**: `AlphaLab_Antigravity/data/canonical/GOLD_M1_PRE2026.csv`
- **Expected SHA-256**: `10d6df33c749315824bb9552b139439e6bbfcbac1bed54f272a62696c2f4965e`
- **Row Count**: `2,827,419` M1 bars
- **Date Range**: `2018-01-02 09:05:00+00:00` to `2025-12-31 19:59:00+00:00`
- **Calendar Years**: `[2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025]` (8 full calendar years)
- **Unique Trading Days**: `2,065` days
- **Discovery 2026 Overlap**: Exactly `0` rows (`max(datetime) < 2026-01-01T00:00:00Z`).
- **Data Hard Fail Conditions**:
  - Missing file $\rightarrow$ `STOP_BLOCKED_DATASET_MISSING`
  - SHA-256 mismatch $\rightarrow$ `STOP_BLOCKED_DATASET_HASH_MISMATCH`
  - Any timestamp $\ge 2026-01-01\text{ UTC}$ $\rightarrow$ `STOP_BLOCKED_DISCOVERY_LEAKAGE`
  - Rows $< 1,000,000$ $\rightarrow$ `STOP_BLOCKED_INSUFFICIENT_HISTORY`
  - Years $< 3$ $\rightarrow$ `STOP_BLOCKED_INSUFFICIENT_TEMPORAL_COVERAGE`

---

## 3. Frozen Scientific Protocol (Strictly Unchanged)

- **Prior Extreme Lookback**: `20` M1 bars (causally excluding current bar).
- **Path Efficiency**: `PATH_WINDOW = 10`, `EFFICIENCY_THRESHOLD = 0.65`.
- **Robust Stretch**: `ROBUST_WINDOW = 60`, `ROBUST_Z_THRESHOLD = 2.0` (Short $Z \ge +2.0$, Long $Z \le -2.0$).
- **Volatility Percentile**: `ATR_PERIOD = 14`, `ATR_PERCENTILE_WINDOW = 500`, `ATR_PERCENTILE_THRESHOLD = 80.0%`.
- **Reaction Zones**:
  - PDH / PDL: Completed day $D-1$, tolerance $\le 0.15 \times \text{ATR14}$ (`+2 points`).
  - Session Extremes: Completed Asia, London, NY sessions, tolerance $\le 0.15 \times \text{ATR14}$ (`+1 point`).
  - Confirmed M15 Swings: Pivot Flank = 2, confirmed at close of $j+2$, width $= 0.10 \times \text{M15\_ATR14}$ (`+1 point`).
- **Reaction Score**: Range $[3, 10]$ with mandatory Failed Auction (`+3 points`).
- **Score Bins**: `3-4`, `5-6`, `7-8`, `9-10`.
- **Diagnostic Strategy**: Score $\ge 7$, next open entry, SL $= 1.00 \times \text{ATR14}$, TP = NONE, holding = 5 bars.
- **Statistical Bootstrap**: UTC Day-Level Block Bootstrap ($B = 2,000$ simulations, fixed seed `20260817`).
- **Temporal Stability**: Minimum valid calendar years $\ge 3$, minimum events/year $\ge 200$, positive valid years ratio $\ge 70\%$.

---

## 4. Primary Replication Gates

- **Gate 0 (Data)**: Rows $\ge 1,000,000$, Valid Years $\ge 3$, Discovery Overlap $= 0$.
- **Gate 1 (Sample)**: Total events $\ge 500$, Long $\ge 150$, Short $\ge 150$.
- **Gate 2 (Primary Mean)**: 5m mean signed return $> 0$.
- **Gate 3 (Day-Block Bootstrap)**: 5m Day-Block bootstrap 95% CI lower bound $> 0$.
- **Gate 4 (Adjacent Horizon)**: 3m or 10m mean signed return $> 0$.
- **Gate 5 (Temporal Stability)**: $\ge 3$ valid years with $\ge 200$ events, $\ge 70\%$ positive.

### Final Verdict Rule
- `REPLICATION_CONFIRMED` if and only if Gates 0–5 all PASS.
- `REPLICATION_NOT_CONFIRMED` if any Gate 0–5 FAILS.
- `STOP_BLOCKED` if technical/data failure occurs.
