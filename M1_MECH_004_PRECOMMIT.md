# ALAB-M1-MECH-004 — PRECOMMIT
## Reversion Timing / Compensation Study

## Research question
After a prior-20-bar extreme breach, is short-horizon reversion better described as a continuous timing process in which more snapback movement realized inside the breach candle leaves less additional snapback movement after that candle closes?

This is a development-set observational dynamics study. It is **not** a trading strategy, not randomized causal identification, and not a claim of physical conservation.

## Immutable data boundary
- GOLD M1 canonical SHA256: `10d6df33c749315824bb9552b139439e6bbfcbac1bed54f272a62696c2f4965e`
- Development: `2018-01-01 <= datetime < 2026-01-01 UTC`
- 2015–2017: **SEALED FINAL HOLDOUT — DO NOT ACCESS**
- 2026+: **QUARANTINED — DO NOT ACCESS**
- Breach definition remains the MECH-003 prior-20-closed-M1-bar breach universe.
- Both FAILED_AUCTION and ACCEPTED_BREAKOUT are included as descriptive event classes; event class is not a strategy direction.

## Signed geometry
Use snapback sign:
- lower breach / LONG convention: `s = +1`
- upper breach / SHORT convention: `s = -1`

All ATR normalization uses causal ATR14 available on event bar `t`.

For event extreme `X_t`, prior extreme `L_t`, event close `C_t`, and exact-clock future close `C_{t+h}`:

### Breach excursion
`EXC = s * (L_t - X_t) / ATR_t`

This is positive for a valid single-sided breach.

### In-candle reversion
`R_in = s * (C_t - X_t) / ATR_t`

This measures snapback movement from the event extreme to the event close. It is non-negative for a valid OHLC candle.

### Event-close signed level distance
`D_t = s * (C_t - L_t) / ATR_t`

Identity:
`R_in = EXC + D_t`.

`D_t > 0` means the event close is on SNAPBACK_SIDE.
`D_t < 0` means the event close remains on BREAKOUT_SIDE.

### Post-close reversion
`R_post(h) = s * (C_{t+h} - C_t) / ATR_t`

Equivalently:
`R_post(h) = D_{t+h} - D_t`.

Positive means additional post-close snapback-direction movement.

### Total reversion from event extreme
`R_total(h) = R_in + R_post(h)`.

This is a descriptive path quantity, **not** assumed to be conserved or capped.

### In-candle consumption ratio
`Consumption(h) = R_in / R_total(h)` only when:
- exact-clock endpoint exists; and
- `R_total(h) > 0`.

Otherwise it is `NaN`.

Consumption is secondary/descriptive only because it may exceed 1 when price gives back part of the in-candle reversion after close.

## Exact-clock / gap policy
Horizons are frozen:
`+1,+3,+5,+10,+15,+30 minutes`.

No later bar substitutes for a missing exact-clock timestamp.
Primary regression uses exact-clock endpoints. MFE/MAE are not required for MECH-004.

## Fixed descriptive bins
In-candle reversion ATR bins are frozen before outcomes:
- R0: `[0, 0.25)`
- R1: `[0.25, 0.50)`
- R2: `[0.50, 1.00)`
- R3: `[1.00, 2.00)`
- R4: `[2.00, +inf)`

No empirical quantile binning and no post-result threshold selection.

## Primary compensation model
For each horizon, estimate OLS:

`R_post(h) = beta * R_in + controls + error`

Primary coefficient:
`beta_5m` on `R_in`.

Controls are frozen:
- breach excursion / ATR
- ATR percentile / 100
- path efficiency
- absolute robust stretch
- structural location count
- breach side indicator
- UTC hour cyclical terms: `sin(2πhour/24)`, `cos(2πhour/24)`
- calendar-year fixed effects, baseline 2018

Do **not** include:
- event class (FA/AB), because it is itself determined by the continuous close position this study is decomposing;
- future state;
- future return;
- future timestamp availability;
- MFE/MAE;
- any optimized threshold.

The coefficient is an observational conditional association, not a causal structural parameter.

## Dependence-aware uncertainty
Primary uncertainty:
- fixed-residual Frisch–Waugh–Lovell day-block bootstrap;
- residualize `R_in` and `R_post(5m)` once on the frozen controls using the full valid development sample;
- aggregate residual cross-products by UTC event date;
- resample whole UTC dates with replacement;
- B = 2000;
- seed = 20260817;
- bootstrap beta = `sum(rx*ry) / sum(rx^2)` over sampled day blocks.

This keeps nuisance residualization fixed inside bootstrap and must be reported exactly as such.

## Temporal stability
Estimate the same +5m compensation coefficient separately for each calendar year 2018–2025 using the same control specification except year fixed effects are omitted inside a single-year fit.

## Secondary descriptive analyses
Report, without promotion/tuning:
- mean/median `R_in`, `R_post(h)`, `R_total(h)`;
- fixed R0–R4 bin summaries;
- FAILED_AUCTION vs ACCEPTED_BREAKOUT summaries;
- ENERGY (`energy_count` 0–3) × LOCATION (`location_count` 0–3) total-reversion distributions at +5m;
- consumption ratio distribution when defined;
- yearly coefficients.

No claim of a fixed “reversion budget cap” is permitted from this phase.

## Frozen gates
`REVERSION_COMPENSATION_SUPPORTED_IN_DEVELOPMENT` requires ALL:

- G0: canonical SHA matches; 2015–2017 and 2026+ untouched; all 8 development years represented.
- G1: geometry identity `R_in = EXC + D_t` max absolute numerical error <= `1e-10`, and exact +5m endpoint coverage >= 98%.
- G2: primary `beta_5m < 0`.
- G3: fixed-residual UTC day-block bootstrap 95% CI **upper bound < 0**.
- G4: both `beta_3m < 0` and `beta_10m < 0`.
- G5: at least 6 of 8 yearly +5m coefficients are negative.

Otherwise:
`REVERSION_COMPENSATION_NOT_CONFIRMED`.

Even a PASS is development evidence only. It does not authorize opening the sealed holdout.

## Absolute prohibitions
- No strategy creation.
- No BUY/SELL rule.
- No SL/TP/holding-period optimization.
- No PnL backtest.
- No parameter grid.
- No paper/live trading.
- No broker execution.
- No 2015–2017 access.
- No 2026 access.
- No “conservation law”, liquidity-provider, institutional-flow, or order-book causal claim.
- No rerun because results are unfavorable.

## Required artifacts after the one allowed development run
- `M1_MECH_004_GEOMETRY_AUDIT.json`
- `M1_MECH_004_HORIZON_SUMMARY.csv`
- `M1_MECH_004_FIXED_RECLAIM_BINS.csv`
- `M1_MECH_004_EVENT_CLASS_SUMMARY.csv`
- `M1_MECH_004_ENERGY_LOCATION_BUDGET.csv`
- `M1_MECH_004_REGRESSION.csv`
- `M1_MECH_004_YEARLY_5M.csv`
- `M1_MECH_004_BLOCK_BOOTSTRAP.json`
- `M1_MECH_004_GATES.json`
- `M1_MECH_004_MANIFEST.json`
- `M1_MECH_004_REPORT.md`
- full event table local-only if large, with SHA256 in manifest.

## Run governance
1. Commit/push PRECOMMIT + source + tests.
2. Record remote PRECOMMIT SHA.
3. Run tests.
4. Execute development dataset exactly once.
5. Commit negative or positive results exactly as produced.
6. Do not modify scientific code after outcomes are observed.
