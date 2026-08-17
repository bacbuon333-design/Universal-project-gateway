# ALAB-M1-MECH-003 — PRECOMMIT

## Research question
Does a Failed Auction contain forward information beyond the mechanical fact that its trigger candle already closed back inside the breached prior 20-bar extreme?

This is a matched observational control study. It is **not** a strategy study and does not claim randomized causal identification.

## Immutable dataset boundary
- GOLD M1 canonical dataset SHA256: `10d6df33c749315824bb9552b139439e6bbfcbac1bed54f272a62696c2f4965e`
- Development window: `2018-01-01 <= datetime < 2026-01-01 UTC`
- 2015-2017: **SEALED FINAL HOLDOUT — DO NOT ACCESS**
- 2026+: **DO NOT ACCESS**

## Event universe
Prior-extreme lookback remains 20 closed M1 bars excluding event bar `t`.

Upper-extreme breach:
- breach if `high[t] > prior_high[t]`
- FAILED_AUCTION if `close[t] < prior_high[t]`
- ACCEPTED_BREAKOUT if `close[t] > prior_high[t]`

Lower-extreme breach:
- breach if `low[t] < prior_low[t]`
- FAILED_AUCTION if `close[t] > prior_low[t]`
- ACCEPTED_BREAKOUT if `close[t] < prior_low[t]`

Exclude:
- close exactly at the prior extreme;
- a bar that breaches both upper and lower prior extremes.

For signed outcomes, upper breaches use SHORT/snapback sign and lower breaches use LONG/snapback sign. This is a measurement convention, not a trade direction.

## Matching design — frozen before outcomes
Use deterministic Coarsened Exact Matching (CEM). No propensity model, no ML, no nearest-neighbour parameter tuning.

Exact/coarsened key:
- side: exact
- calendar year: exact
- UTC hour: exact
- structural location count: exact
- ATR percentile: `[-inf,50) [50,80) [80,95) [95,inf)`
- path efficiency: `[-inf,.25) [.25,.50) [.50,.65) [.65,.80) [.80,inf)`
- absolute robust stretch: `[-inf,1) [1,2) [2,3) [3,inf)`
- sweep depth / ATR: `[-inf,.10) [.10,.25) [.25,.50) [.50,1) [1,inf)`

No forward outcome, close-state, MFE, MAE, future return, or future timestamp availability is permitted in the match key.

Common-support strata must contain at least one FAILED_AUCTION and one ACCEPTED_BREAKOUT.
ATT-style weighting:
- treatment weight = 1;
- control weight in stratum = `N_treatment / N_control`.

## Covariate balance
Report standardized mean difference before and after matching for:
- ATR percentile
- path efficiency
- absolute stretch
- sweep depth / ATR

Frozen balance requirement: max absolute post-match SMD <= 0.10.

## Outcomes
Exact-clock, gap-aware horizons remain:
`+1,+3,+5,+10,+15,+30 minutes`.

Primary endpoint:
- matched FAILED_AUCTION minus ACCEPTED_BREAKOUT mean signed forward return at +5 exact clock minutes.

Secondary endpoints:
- signed forward return differences at all horizons;
- difference in probability of closing on SNAPBACK_SIDE at each horizon;
- yearly +5m matched effect.

No later bar substitutes for a missing exact-clock endpoint.

## Dependence-aware inference
Primary uncertainty estimator:
- UTC day-level block bootstrap;
- resample whole UTC event dates with replacement;
- B = 2000;
- seed = 20260817;
- matching strata and CEM weights are frozen before bootstrap.

## Frozen mechanism gates
`MECHANISM_SUPPORTED` requires ALL:

- G0: >=70% of FAILED_AUCTION events remain in common support.
- G1: max absolute matched continuous-covariate SMD <=0.10.
- G2: primary +5m matched ATT >0 bps.
- G3: UTC day-block bootstrap 95% CI lower bound for +5m ATT >0.
- G4: +3m or +10m matched ATT >0.
- G5: all 8 development years are represented and at least 6/8 yearly +5m matched effects are positive.

Otherwise: `MECHANISM_NOT_CONFIRMED`.

These gates validate a conditional observational association only. They do not prove liquidity refill, institutional flow, market-maker behavior, or order-book causality.

## Absolute prohibitions
- No strategy creation.
- No SL/TP/holding optimization.
- No PnL backtest.
- No paper/live trading.
- No broker execution.
- No 2015-2017 access.
- No 2026 access.
- No selection of a favorable subgroup after outcomes.
- No change to matching bins/gates after the run.

## Required artifacts after the one allowed development run
- `M1_MECH_003_MATCHING_AUDIT.json`
- `M1_MECH_003_BALANCE.csv`
- `M1_MECH_003_MATCHED_EFFECTS.csv`
- `M1_MECH_003_YEARLY_5M.csv`
- `M1_MECH_003_BLOCK_BOOTSTRAP.json`
- `M1_MECH_003_GATES.json`
- `M1_MECH_003_MANIFEST.json`
- `M1_MECH_003_REPORT.md`
- full matched event table local-only if large, with SHA256 in manifest.

## Run governance
1. Commit and push this PRECOMMIT plus source/tests.
2. Record PRECOMMIT SHA remotely.
3. Only then execute the development dataset once.
4. Do not rerun because the result is unfavorable.
5. Commit negative results exactly as produced.
