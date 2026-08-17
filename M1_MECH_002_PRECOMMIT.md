# ALAB-M1-MECH-002 — PRECOMMIT

## Research purpose
Discover whether Failed Auction events express stable, observable M1 price-state transitions that depend on separate ENERGY, LOCATION, and REJECTION dimensions.

This is mechanism research, not strategy research.

## Immutable development dataset
- Symbol: GOLD
- Timeframe: M1
- Development window: 2018-01-01 <= datetime < 2026-01-01 UTC
- Canonical SHA256: `10d6df33c749315824bb9552b139439e6bbfcbac1bed54f272a62696c2f4965e`
- 2015-2017: **SEALED FINAL HOLDOUT — DO NOT ACCESS**
- 2026+: **DISCOVERY/POST-DEVELOPMENT — DO NOT ACCESS**

## Reused causal trigger
Failed Auction remains exactly the 001R trigger:
- SHORT: event high breaches prior 20-bar high and event close returns below it.
- LONG: event low breaches prior 20-bar low and event close returns above it.
- Prior extreme excludes the event bar.

No trading rule is created.

## Factor decomposition

### ENERGY
Keep components separate:
- continuous Path Efficiency
- continuous Robust Stretch Z / absolute stretch
- ATR percentile
- old threshold matches retained only as descriptive flags
- energy_count = number of the three old threshold matches, descriptive only

### LOCATION
Recompute rather than trust the additive score:
- previous observed trading-day H/L
- completed Asia/London/New-York session H/L with 24 **clock-hour** retention
- confirmed M15 swing zone with flank=2 and preserved width = 0.10 * confirmed M15 ATR14
- location_count is descriptive only

### REJECTION
At event close:
- sweep_depth_atr
- reclaim_depth_atr
- event_range_atr
- signed body in snapback direction / ATR
- close location within event candle normalized toward snapback side

## Primary state definition
Primary transitions are based on **close only** relative to the original failed-auction prior extreme:
- `SNAPBACK_SIDE`: signed close distance > 0
- `BREAKOUT_SIDE`: signed close distance < 0
- `AT_LEVEL`: signed close distance == 0
- `GAP_CONTAMINATED`: the exact requested clock-minute bar is absent

No economic label such as "liquidity refill", "institutional flow", or "informed trading" is authorized from M1 OHLC.

## Gap policy
For +h minute outcomes, the exact timestamp `event_time + h minutes` must exist.
No later bar substitutes for a missing clock minute.
MFE/MAE are valid only when every M1 bar in the requested horizon is contiguous.

## Intrabar policy
OHLC cannot establish event ordering inside one bar.
Primary state transitions therefore do not use High/Low to claim which threshold occurred first.
High/Low are secondary excursion statistics only.

## Descriptive analysis
Development-only empirical quartiles may be used to visualize continuous factors.
Their edges must be written to the manifest.
They are not strategy thresholds.

Required summaries:
- factor-by-factor tail distributions
- LOCATION x ENERGY matrix
- close-state transitions at 1/3/5/10/15/30 exact minutes
- quantiles P1/P5/P10/P25/P50/P75/P90/P95/P99
- skew
- adverse/favorable 5% expected shortfall
- gap-aware MFE/MAE
- LONG vs SHORT descriptions

## Prohibited
- strategy backtest
- PF/PnL optimization
- SL/TP search
- indicator search
- grid search
- paper/live trading
- broker execution
- opening 2015-2017 holdout
- post-hoc "best subgroup" authorization

## Interpretation target
The result may support only an observable price-state map, for example:
ENERGY + LOCATION + REJECTION -> distribution of SNAPBACK_SIDE / BREAKOUT_SIDE states and tails.

Any microstructure causal interpretation requires later tick/order-book validation.
