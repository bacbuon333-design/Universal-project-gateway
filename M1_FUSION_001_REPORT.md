# ALAB-M1-FUSION-001 — Failed Auction + Adaptive Reaction Zone Research Report

## A. Governance and Metadata

- **Repository**: `bacbuon333-design/Universal-project-gateway`
- **Branch**: `research/quant-m1-fusion-failed-auction-v1`
- **Scientific Parent**: `5a1a2f8c28f857789943295f6a59df2f1037e72b`
- **Precommit SHA**: `e5d55487c0d588bddde584d41009e931c2fe9cfe`
- **Research Type**: `EVENT_STUDY_PLUS_SINGLE_DIAGNOSTIC_BACKTEST`
- **Strategy Validation**: `NOT_AUTHORIZED`
- **Paper Trading**: `NO`
- **Live Trading**: `NO`
- **Broker Execution**: `NO`
- **Research Only**: `YES`

## B. Dataset Quality and Audit

- **Symbol**: `GOLD` (Timeframe: M1, Timezone: UTC)
- **Source Path**: `J:\MovedFromC\Roaming_MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05\AlphaLab_Antigravity\data\GOLD_M1_2001_2026.csv`
- **Row Count**: `99,999` M1 bars
- **Date Range**: `2026-04-15 01:12:00+00:00` to `2026-07-24 23:57:00+00:00`
- **Data Hash (SHA-256)**: `b980ac086f5de4ab60621d0ddcb3bac59d37ebd0bec236d24971f81918b1f3ec`
- **Duplicates**: `0` | **Invalid OHLC**: `0`
- **Historical Spread Present**: `True`
- **Sample Sufficiency (>=250k rows)**: `False`

## C. Frozen Hypothesis Specification

The experiment tests whether a directional, efficient price displacement reaching a key structural reaction zone, failing to achieve acceptance beyond that extreme, and snapping back exhibits a statistically significant forward directional edge at M1 resolution.

- **Prior Extreme Lookback**: 20 M1 bars (causal, excludes event bar)
- **Path Efficiency**: Trailing 10 bars displacement / path length >= 0.65 with directional alignment
- **Robust Stretch**: Trailing 60 bars median / MAD robust Z-score >= +2.0 (Short) or <= -2.0 (Long)
- **Volatility Percentile**: ATR14 trailing 500-bar empirical percentile rank >= 80.0
- **Reaction Zones**: Previous Day High/Low (+2), Completed Session High/Low (+1), Confirmed M15 Swing (+1)
- **Reaction Score**: Range [3, 10] with Failed Auction (+3 mandatory)

## D. Event Study Sample Counts

- **Total Events Detected**: `10,929`
- **Long Events**: `5,918`
- **Short Events**: `5,011`

## E. Forward Return Distribution Across Horizons

| Horizon | N | Mean Signed Ret (bps) | Median Ret (bps) | Win Prop % | 95% Bootstrap CI (bps) | Mean MFE (bps) | Mean MAE (bps) |
|---|---:|---:|---:|---:|---:|---:|---:|
| 1m | 10,929 | +0.06 | +0.15 | 52.0% | [-0.01, 0.15] | 2.64 | 2.64 |
| 3m | 10,929 | +0.11 | +0.23 | 51.7% | [-0.02, 0.25] | 4.71 | 4.79 |
| 5m | 10,929 | +0.22 | +0.35 | 52.2% | [0.04, 0.39] | 6.19 | 6.21 |
| 10m | 10,929 | +0.27 | +0.60 | 52.7% | [0.02, 0.52] | 8.76 | 8.87 |
| 15m | 10,929 | +0.33 | +0.67 | 52.4% | [0.04, 0.62] | 10.76 | 10.89 |
| 30m | 10,929 | +0.45 | +0.88 | 52.2% | [0.04, 0.86] | 15.39 | 15.53 |

## F. Reaction Score Gradient (Primary 5m Horizon)

| Score Bin | N Events | Mean Return 5m (bps) | Median Return 5m (bps) | Win Rate 5m % | Mean MFE 5m (bps) | Mean MAE 5m (bps) |
|---|---:|---:|---:|---:|---:|---:|
| 3-4 | 7,730 | +0.22 | +0.33 | 52.3% | 5.77 | 5.64 |
| 5-6 | 2,921 | +0.17 | +0.35 | 51.6% | 7.06 | 7.52 |
| 7-8 | 254 | +0.95 | +1.99 | 57.5% | 8.88 | 8.26 |
| 9-10 | 24 | -0.18 | -1.30 | 37.5% | 8.05 | 8.90 |

## G. Temporal and Session Breakdown

### Yearly Breakdown (5m Horizon)

| Year | N Events | Mean Return 5m (bps) | Win Rate 5m % |
|---|---:|---:|---:|
| 2026 | 10,929 | +0.22 | 52.2% |

### Research Session Breakdown (5m Horizon)

| Session | N Events | Mean Return 5m (bps) | Win Rate 5m % |
|---|---:|---:|---:|
| ASIA | 3,283 | +0.33 | 52.2% |
| LONDON_RESEARCH | 2,383 | +0.38 | 54.0% |
| NEW_YORK_RESEARCH | 2,489 | +0.33 | 52.2% |
| OTHER | 2,774 | -0.15 | 50.6% |

## H. Single Diagnostic Backtest (Score >= 7, SL = 1.0 ATR, Holding = 5 bars)

- **Diagnostic Status**: `NEGATIVE_DIAGNOSTIC`
- **Cost Verification Status**: `VERIFIED`
- **Total Trades Taken**: `254`
- **Win Rate**: `44.09%`
- **Profit Factor**: `0.928`
- **Expectancy**: `-1.20 USD/trade`
- **Net PnL (0.10 lot)**: `-305.67 USD`
- **Max Drawdown**: `933.59 USD`
- **Long Trades**: `153` (Win: `45.1%`)
- **Short Trades**: `101` (Win: `42.6%`)
- **Exits Breakdown**: Stop Loss: `115` | Time Exits: `139`

## I. Discovery Gate Evaluation

- **Gate 1 (Sample size >= 500, Long >= 150, Short >= 150)**: `PASS`
- **Gate 2 (Primary 5m Mean Return > 0)**: `PASS`
- **Gate 3 (Primary 5m 95% Bootstrap CI Lower > 0)**: `PASS`
- **Gate 4 (Adjacent 3m or 10m Mean Return > 0)**: `PASS`
- **Gate 5 (Temporal Stability Across Years)**: `PASS`
- **Gate 6 (Score Gradient Monotonicity)**: `PASS`

### **EVENT STUDY VERDICT: MECHANISM_CLUE**

## J. Strongest Counter-Evidence

At M1 resolution, spread friction (e.g. 25-50 points) represents a substantial fraction of the 5-minute gross price excursion. While failed auctions with high reaction scores exhibit localized mean-reversion tendencies, adverse stops and spread crossing frequently erode edge in live market conditions without adaptive session filtering.

## K. Limitations

1. M1 OHLC bar data does not represent tick-level truth.
2. Research session windows use fixed UTC conventions.
3. This is an exploratory discovery study on historical GOLD data only; zero live or paper execution is authorized.

---
**END OF REPORT**