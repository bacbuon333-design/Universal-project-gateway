# V3.11 H226 ECONOMIC-MATERIALITY & ASYMMETRY CLOSURE

## Purpose

V3.11 is a read-only scientific closure chapter for the already-rejected H226 family.
It does **not** design or execute a trading strategy.

Scientific parent:
`b387e25bdf6fd814c3034f3688af50e976f5cc59`

Frozen V3.9 event source:
`AlphaLab_Antigravity/reports/v3_9/v3_9_h226_events.csv`

Frozen source SHA-256:
`aecdb78d22598a962c29adbd7448755eaf31399d351d5efcbeeddc0c823d920f`

Canonical market-data authority remains:
`GOLD_M30_CANONICAL_V2`
SHA-256:
`c48ca44dcecae9eb1c2590c586e27c4bc5f246215c549d0d0bc1201d95d5ea1d`

## Immutable prior conclusions

1. Every H226 trading configuration remains `REJECTED`.
2. V3.9 mechanism label was weak / tail-unstable.
3. V3.10 found positive pooled 8h delayed reversion but C4 failed the frozen quarter-block robustness conjunction.
4. V3.10 did **not** authorize strategy design.
5. V3.11 cannot upgrade any H226 strategy.

## Scientific question

Is the frozen 8h delayed-reversion effect economically material broadly enough to survive a round-trip cost hurdle across time and gap direction, or is the apparent effect concentrated in favorable volatility/regime/direction slices?

This is the final same-sample H226 diagnostic. After V3.11, the H226 chapter closes regardless of the label.

## Frozen scope

- Horizon: `8h` only.
- Cohorts described: H226-C1, C2, C3, C4.
- Decision cohorts: H226-C1 and H226-C4 only.
- No new threshold, horizon, direction filter, SL, TP, RR, asset, timeframe, or strategy.
- No `run_strategy()`.
- No trading-engine call.
- No raw market-data reconstruction.
- No event reconstruction.

## Cost-hurdle diagnostic

Frozen round-trip price-equivalent baseline:

- spread: `0.25 USD/oz`
- commission: `0.07 USD/oz`
- slippage: `0`
- total: `0.32 USD/oz`

For each frozen event:

`cost_hurdle_atr = 0.32 / atr_prev`

`excess_reversion_atr = signed_reversion_return_atr - cost_hurdle_atr`

This is an economic-scale diagnostic, **not simulated strategy PnL**.

## Frozen views

For C1-C4:

- FULL: 2018Q2–2026Q2
- PRE_2025: through 2024Q4
- RECENT: 2025Q1–2026Q2
- UP_GAP
- DOWN_GAP

For C1-C4 also report each complete year 2019–2025 and each complete quarter 2018Q2–2026Q2 using mean excess-reversion ATR.

## Frozen bootstrap

For each C1-C4 cohort:

Quarter-block bootstrap:
- reps: `5000`
- seed: `311226`
- units: all 33 evaluation quarters
- statistic: pooled mean excess-reversion ATR

Complete-year block bootstrap:
- reps: `5000`
- seed: `311227`
- units: years 2019–2025
- statistic: pooled mean excess-reversion ATR

## Frozen broad-economic-materiality rule

Decision cohorts are C1 and C4 only.

`BROADLY ECONOMICALLY MATERIAL` requires BOTH C1 and C4 to satisfy ALL:

1. FULL mean excess > 0
2. FULL median excess > 0
3. quarter-block CI lower > 0
4. year-block CI lower > 0
5. PRE_2025 mean excess > 0
6. RECENT mean excess > 0
7. UP_GAP mean excess > 0
8. DOWN_GAP mean excess > 0
9. at least 5 of 7 complete years have positive mean excess
10. every leave-one-year-out mean excess > 0

Exact label:

`H226 DELAYED 8H REVERSION BROADLY ECONOMICALLY MATERIAL — H226 STRATEGY CHAPTER CLOSED; FRESH OOS REQUIRED`

## Frozen asymmetric/regime-concentrated rule

If broad materiality fails, but BOTH C1 and C4 have FULL mean excess > 0:

`H226 DELAYED 8H REVERSION ECONOMICALLY ASYMMETRIC / REGIME-CONCENTRATED — H226 STRATEGY CHAPTER CLOSED; FRESH OOS REQUIRED`

## Frozen economically-immaterial rule

If either C1 or C4 has FULL mean excess <= 0:

`H226 DELAYED 8H REVERSION ECONOMICALLY IMMATERIAL — H226 CHAPTER CLOSED`

## Interpretation boundary

The asymmetric/regime-concentrated label does not prove that a one-direction filter is tradable. It means only that broad economic materiality failed while pooled excess remained positive.

No result in V3.11 authorizes a strategy on the already-mined 2018Q2–2026Q2 sample.
Any future H226-inspired strategy requires fresh out-of-sample data collected after the frozen canonical endpoint or a separately justified independent dataset.

## Stop rule

After V3.11 report:

- close H226 same-sample research;
- do not create an H226 descendant on this historical sample;
- do not convert UP/DOWN or PRE/RECENT differences into a filter;
- do not tune thresholds;
- do not add horizons;
- do not backtest a new H226 strategy.
