# ALAB-M1-MECH-005 — PRECOMMIT
## Compensation Invariance & Falsification Audit

## Research question
Does the MECH-004 attenuation relationship survive changes of coordinate/normalization and disappear when the event-specific future increment linkage is deliberately destroyed?

This is an adversarial development-set falsification study. The objective is to kill the surviving MECH-004 phenomenon if it is a scaling, anchoring, or temporal-linkage artifact.

It is not a strategy study, not randomized causal identification, and not a claim of a market law.

## Immutable data boundary
- GOLD M1 canonical SHA256: `10d6df33c749315824bb9552b139439e6bbfcbac1bed54f272a62696c2f4965e`
- Development: `2018-01-01 <= datetime < 2026-01-01 UTC`
- 2015–2017: **SEALED FINAL HOLDOUT — DO NOT ACCESS**
- 2026+: **QUARANTINED — DO NOT ACCESS**
- Breach universe remains the MECH-003/004 prior-20-closed-M1-bar breach universe.
- Exact-clock horizons remain `+1,+3,+5,+10,+15,+30 minutes`.
- Primary horizon remains `+5m`.

## Known reference used only for implementation reproducibility
MECH-004 published:
`rho_5m(ATR_t) = 0.94191764717577`.

MECH-005 Model A must reproduce this value within absolute error `<=1e-10` before any new falsification claim is allowed.
This is a checksum against implementation drift, not a newly selected target.

## Common geometry
Let `s=+1` for lower breach / LONG measurement convention and `s=-1` for upper breach / SHORT convention.

Raw price displacements:
- `raw_in = s*(C_t - X_t)`
- `raw_total(h) = s*(C_{t+h} - X_t)`
- `raw_post(h) = raw_total(h) - raw_in`
- `raw_exc = s*(L_t - X_t) > 0`

The test always estimates a one-for-one persistence slope:
`Y_total(h) = rho_h * X_in + frozen controls + error`.

Null benchmark remains `rho=1`.

## Invariance battery — frozen before MECH-005 outcomes

### A. ATR_T — reproduction/base coordinate
- `X = raw_in / ATR_t`
- `Y = raw_total / ATR_t`
- excursion control = `raw_exc / ATR_t`

### B. ATR_PRE — causal pre-event scale
- `ATR_pre = ATR14 shifted by one M1 bar`
- `X = raw_in / ATR_pre`
- `Y = raw_total / ATR_pre`
- excursion control = `raw_exc / ATR_pre`

Purpose: remove the breach candle's own contribution from the normalization scale.

### C. PRICE_BPS — no ATR denominator
- `X = raw_in / prior_extreme * 10000`
- `Y = raw_total / prior_extreme * 10000`
- excursion control = `raw_exc / prior_extreme * 10000`

Purpose: remove ATR normalization completely while retaining a dimensionless price-relative coordinate.

### D. EXCURSION_RATIO — no ATR denominator in X/Y
- include only events with `breach_excursion_atr >= 0.10`
- `X = raw_in / raw_exc`
- `Y = raw_total / raw_exc`
- nuisance excursion control remains the original causal `breach_excursion_atr`

The `0.10 ATR` floor is frozen before outcome and exists only to prevent near-zero ratio explosion. D must retain at least 50% of exact-5m events or G0 fails.

## Frozen nuisance controls
For every coordinate:
- representation-specific excursion control above;
- ATR percentile / 100;
- path efficiency;
- absolute robust stretch;
- structural location count;
- breach side indicator;
- UTC hour sine/cosine;
- calendar-year fixed effects, baseline 2018.

Do not include event class, future state, future return, MFE/MAE, outcome-derived thresholds, or post-result selected variables.

## Inference
For each representation and horizon use FWL residualization.
At +5m, uncertainty uses fixed-residual UTC day-block bootstrap:
- B = 2000;
- seed = 20260817;
- resample whole UTC event dates;
- report 95% empirical CI for rho.

## Gradient invariance
For each representation at +5m:
- create exactly five equal-count bins `G1..G5` from `X_in` only using `qcut`;
- no outcome is used to determine cutpoints;
- report mean and median `post = Y-X` per bin;
- the frozen directional criterion is that mean post must be monotonically non-increasing from G1 to G5.

This is deliberately strict. Any representation that loses the inverse gradient fails G3.

## Placebo falsification battery
The original phrase “orthogonal horizon” is rejected before outcome because scalar M1 price has no well-defined orthogonal spatial direction. It is replaced by a second negative-control transform that preserves local magnitude information while destroying directional linkage.

Both placebos operate on the ATR_T +5m coordinate and preserve each event's `R_in`. They alter only the event-specific `R_post`, then reconstruct:
`Y_placebo = R_in + placebo(R_post)`.

Therefore the pre-registered placebo null is `rho=1`, not `rho=0`.

### P1. WITHIN_DAY_SIDE_CYCLIC_POST_SHUFFLE
Within each `UTC date × breach side` group:
- cyclically reassign `R_post` by a deterministic seeded non-zero offset;
- groups with fewer than 2 events are omitted;
- seed = 20260818.

This preserves each local group's exact R_post multiset but destroys the event→future-increment pairing.

### P2. WITHIN_DAY_SIDE_BALANCED_POST_SIGN
Within each `UTC date × breach side` group:
- multiply each event's own R_post by approximately balanced random `+1/-1` signs;
- groups with fewer than 2 events are omitted;
- seed = 20260819.

This preserves local post-movement magnitudes but destroys directional information.

Each placebo is fitted with the same frozen controls and its own fixed-residual UTC day-block bootstrap, B=2000.

## Yearly descriptive robustness
For A/B/C/D, estimate +5m rho separately for each year 2018–2025 without year fixed effects.
This table is descriptive in MECH-005 and is not an additional gate, because temporal stability was already an inferential gate in MECH-004.

## Frozen gates
`COMPENSATION_INVARIANCE_SURVIVES_FALSIFICATION` requires ALL:

- G0: dataset/holdout/quarantine boundaries hold; all 8 years represented; exact +5m coverage >=98%; D coverage >=50% of exact +5m; Model A reproduces MECH-004 rho within `1e-10`.
- G1: all four +5m coordinate slopes are `<1.0`.
- G2: all four +5m UTC-day bootstrap 95% CI upper bounds are `<1.0`.
- G3: all four five-bin mean-post gradients are monotonically non-increasing from low to high in-candle realization.
- G4: P1 placebo 95% CI contains `1.0`.
- G5: P2 placebo 95% CI contains `1.0`.

Otherwise:
`COMPENSATION_FALSIFIED_OR_NOT_INVARIANT`.

A PASS means only that the MECH-004 development-set attenuation is robust to these four frozen coordinate systems and collapses under the two frozen negative controls. It still does not prove a physical conservation law, fixed reversion budget, market-maker behavior, liquidity-provider behavior, institutional flow, or a tradable edge.

## Absolute prohibitions
- No strategy creation.
- No BUY/SELL entry rule.
- No SL/TP/holding optimization.
- No PnL backtest.
- No parameter grid.
- No paper/live trading.
- No broker execution.
- No 2015–2017 access.
- No 2026 access.
- No post-result representation repair.
- No relaxing the D excursion floor, gradient gate, or placebo definitions after outcome.
- No rerun because the result is unfavorable.

## Required artifacts after the one allowed development run
- `M1_MECH_005_COORDINATE_AUDIT.json`
- `M1_MECH_005_INVARIANCE_REGRESSION.csv`
- `M1_MECH_005_COORDINATE_BOOTSTRAP.json`
- `M1_MECH_005_GRADIENT.csv`
- `M1_MECH_005_GRADIENT_AUDIT.json`
- `M1_MECH_005_PLACEBO.csv`
- `M1_MECH_005_YEARLY_INVARIANCE.csv`
- `M1_MECH_005_GATES.json`
- `M1_MECH_005_MANIFEST.json`
- `M1_MECH_005_REPORT.md`
- local full event table if large, with SHA256 in manifest.

## Run governance
1. Commit/push this PRECOMMIT + source/tests.
2. Record PRECOMMIT SHA remotely.
3. Run tests first.
4. Execute the 2018–2025 development dataset exactly once.
5. Commit negative results exactly as produced.
6. Do not alter scientific source after outcomes are observed.
