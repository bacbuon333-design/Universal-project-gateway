# ALAB-M1-MECH-004 — Reversion Timing / Compensation Study

## Scope
Development-only continuous reversion timing study on frozen GOLD M1 2018–2025.
No strategy, PnL backtest, paper/live trading, broker execution, 2015–2017 holdout access, or 2026 access.

## Dataset
- SHA256: `10d6df33c749315824bb9552b139439e6bbfcbac1bed54f272a62696c2f4965e`
- Rows: `2,827,419`
- Range: `2018-01-02 09:05:00+00:00` to `2025-12-31 19:59:00+00:00`
- Breach events: `615,058`
- Sealed holdout: `2015–2017 NOT ACCESSED`

## Mechanics
- `R_in`: snapback-direction movement from event extreme to event close, normalized by event ATR14.
- `R_post(h)`: additional exact-clock snapback-direction movement after event close; descriptive only.
- `R_total(h)`: snapback-direction displacement from event extreme to exact-clock future close.
- Consumption ratio is descriptive only and defined only when `R_total(h) > 0`.

## Pre-run scientific repair
A draft regression of `R_post` on `R_in` was rejected before any real outcome was run because those variables are algebraically coupled through event close. The frozen primary model instead uses future `R_total`.

## Primary model
`R_total(h) = rho_h * R_in + frozen controls + error`.

Null reference: `rho=1` (one-for-one persistence). Evidence for attenuation/compensation requires `rho<1`, with the +5m UTC day-block bootstrap upper 95% bound also below 1.

## Interpretation boundary
A rho below 1 is development-set attenuation relative to one-for-one persistence. It is not a physical conservation law, a fixed budget, or randomized causal identification.
No liquidity-provider, institutional-flow, or order-book causality is claimed.

## Verdict
`REVERSION_COMPENSATION_SUPPORTED_IN_DEVELOPMENT`

See regression, yearly, bootstrap, fixed-bin, energy/location, and geometry artifacts for details.
