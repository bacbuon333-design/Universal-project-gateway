# ALAB-M1-MECH-004 — PRECOMMIT
## Reversion Timing / Compensation Study — PRE-RUN SCIENTIFIC REPAIR

## Governance note
An earlier pre-run draft proposed regressing `R_post(h)` directly on `R_in`. Before any development outcome was executed, this was rejected because the variables are algebraically coupled through the event close:

`R_post(h) = D_{t+h} - D_t`

and

`R_in = EXC + D_t`.

Controlling `EXC` would mechanically load `-D_t` into the outcome and `+D_t` into the predictor, creating an artificial negative slope. No real dataset outcome was observed under that specification.

The final frozen primary test therefore uses **total reversion at the future endpoint**, not post-close reversion, as the regression outcome.

## Research question
After a prior-20-bar extreme breach, does more snapback movement realized inside the breach candle persist one-for-one into the future total reversion state, or is part of that movement systematically attenuated/compensated over the next minutes?

This is a development-set observational dynamics study. It is **not** a trading strategy, not randomized causal identification, and not a claim of physical conservation.

## Immutable data boundary
- GOLD M1 canonical SHA256: `10d6df33c749315824bb9552b139439e6bbfcbac1bed54f272a62696c2f4965e`
- Development: `2018-01-01 <= datetime < 2026-01-01 UTC`
- 2015–2017: **SEALED FINAL HOLDOUT — DO NOT ACCESS**
- 2026+: **QUARANTINED — DO NOT ACCESS**
- Breach definition remains the MECH-003 prior-20-closed-M1-bar breach universe.
- FAILED_AUCTION and ACCEPTED_BREAKOUT remain descriptive event classes only.

## Signed geometry
Use snapback sign:
- lower breach / LONG convention: `s = +1`
- upper breach / SHORT convention: `s = -1`

All ATR normalization uses causal ATR14 available on event bar `t`.

For event extreme `X_t`, prior extreme `L_t`, event close `C_t`, and exact-clock future close `C_{t+h}`:

### Breach excursion
`EXC = s * (L_t - X_t) / ATR_t`

### In-candle reversion
`R_in = s * (C_t - X_t) / ATR_t`

### Event-close signed level distance
`D_t = s * (C_t - L_t) / ATR_t`

Identity:
`R_in = EXC + D_t`.

### Post-close reversion — descriptive only
`R_post(h) = s * (C_{t+h} - C_t) / ATR_t = D_{t+h} - D_t`.

Because this variable contains `-D_t`, it is **not permitted as the primary regression outcome against R_in**.

### Total reversion from event extreme — primary future state
`R_total(h) = s * (C_{t+h} - X_t) / ATR_t`

Identity:
`R_total(h) = R_in + R_post(h) = EXC + D_{t+h}`.

This future-state quantity does not algebraically contain the event close once `X_t`, `C_{t+h}`, and ATR are fixed.

### In-candle consumption ratio
`Consumption(h) = R_in / R_total(h)` only when exact-clock endpoint exists and `R_total(h) > 0`; otherwise `NaN`.

Consumption is secondary/descriptive only.

## Exact-clock / gap policy
Frozen horizons:
`+1,+3,+5,+10,+15,+30 minutes`.

No later bar substitutes for a missing exact-clock endpoint.

## Fixed descriptive bins
In-candle reversion ATR bins are frozen:
- R0: `[0, 0.25)`
- R1: `[0.25, 0.50)`
- R2: `[0.50, 1.00)`
- R3: `[1.00, 2.00)`
- R4: `[2.00, +inf)`

No empirical quantile binning and no post-result threshold selection.

## Primary persistence/compensation model
For each horizon estimate:

`R_total(h) = rho_h * R_in + controls + error`

Primary coefficient: `rho_5m`.

Interpretation relative to the precommitted null value `1.0`:
- `rho = 1`: in-candle reversion persists one-for-one into the future total-reversion state; no compensation evidence.
- `rho < 1`: partial attenuation/compensation; one additional ATR of in-candle reversion maps to less than one additional ATR of total reversion at the future endpoint.
- `rho > 1`: reinforcement/amplification.

Define descriptive `compensation_fraction = 1 - rho`.

Controls are frozen:
- breach excursion / ATR
- ATR percentile / 100
- path efficiency
- absolute robust stretch
- structural location count
- breach side indicator
- UTC hour cyclical terms: `sin(2πhour/24)`, `cos(2πhour/24)`
- calendar-year fixed effects, baseline 2018

Do **not** include event class, future state, post-close return, future timestamp availability, MFE/MAE, or optimized thresholds as controls.

## Dependence-aware uncertainty
Primary uncertainty:
- Frisch–Waugh–Lovell residualization of `R_in` and `R_total(5m)` on frozen controls;
- nuisance residualization fitted once on the full valid development sample;
- aggregate residual cross-products by UTC event date;
- resample whole UTC dates with replacement;
- B = 2000;
- seed = 20260817;
- bootstrap `rho = sum(rx*ry)/sum(rx^2)`.

This is reported exactly as a **fixed-residual FWL UTC day-block bootstrap**.

## Temporal stability
Estimate `rho_5m` separately for each calendar year 2018–2025, omitting year fixed effects inside each single-year fit.

## Secondary descriptive analyses
Report:
- `R_in`, `R_post(h)`, `R_total(h)` distributions;
- fixed R0–R4 summaries;
- FA vs Accepted Breakout summaries;
- ENERGY × LOCATION total-reversion distributions at +5m;
- consumption ratio when defined;
- yearly `rho_5m`.

Post-close reversion may be shown descriptively, but no inferential claim may be based on a regression of `R_post` on `R_in`.
No claim of a fixed reversion-budget cap is permitted.

## Frozen gates
`REVERSION_COMPENSATION_SUPPORTED_IN_DEVELOPMENT` requires ALL:

- G0: canonical SHA matches; sealed/quarantine boundaries hold; all 8 development years represented.
- G1: geometry identity `R_in = EXC + D_t` max abs error <= `1e-10`; no materially negative excursion/in-candle reversion; exact +5m endpoint coverage >=98%.
- G2: primary `rho_5m < 1.0`.
- G3: fixed-residual UTC day-block bootstrap 95% CI **upper bound for rho_5m < 1.0**.
- G4: both `rho_3m < 1.0` and `rho_10m < 1.0`.
- G5: all 8 years valid and at least 6/8 yearly `rho_5m < 1.0`.

Otherwise:
`REVERSION_COMPENSATION_NOT_CONFIRMED`.

A PASS means only that attenuation relative to one-for-one persistence is supported in the 2018–2025 development set. It does not prove a conservation law, fixed budget, or economic microstructure cause.

## Absolute prohibitions
- No strategy creation.
- No BUY/SELL rule.
- No SL/TP/holding optimization.
- No PnL backtest.
- No parameter grid.
- No paper/live trading.
- No broker execution.
- No 2015–2017 access.
- No 2026 access.
- No post-result specification repair.
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
- full event table local-only if large, SHA256 in manifest.

## Run governance
1. Commit/push this final repaired PRECOMMIT + source/tests.
2. Record the final PRECOMMIT SHA remotely.
3. Run tests.
4. Execute development dataset exactly once.
5. Commit results exactly as produced.
6. Do not modify scientific source after outcomes are observed.
