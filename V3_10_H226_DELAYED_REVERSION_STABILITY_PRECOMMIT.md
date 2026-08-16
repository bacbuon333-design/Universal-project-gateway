# V3.10 — H226 DELAYED 8H REVERSION STABILITY AUDIT

## Purpose

V3.9 closed all H226 trading strategies as REJECTED and classified the underlying gap-reversion mechanism as WEAK / TAIL-UNSTABLE at the frozen +2h/+4h decision horizons. A precommitted +8h diagnostic already existed in V3.9 and showed a later positive mean signal, including positive quarter-block bootstrap lower bounds for C1 and C2, while C4 remained uncertain.

V3.10 asks one narrower question only:

> Is the already-observed +8h delayed reversion tendency temporally and directionally robust, or is it another pooled historical artifact?

This is an event-study stability audit, not strategy research.

## Governance

Scientific parent: `ae3e4a0d0116b07867ead4e09a6466e54faef8d5`

Branch: `research/quant-v3.10-h226-delayed-reversion-stability`

Single agent only. No `/goal`, subagents, teams, delegation, parallel model instances or multi-agent orchestration.

All H226 trading configurations remain REJECTED. V3.10 cannot alter that status.

No H227. No SL/TP/RR. No execution engine. No strategy backtest. No parameter search. No new asset or timeframe.

## Frozen source artifact

V3.10 MUST read the already-generated V3.9 event artifact:

`AlphaLab_Antigravity/reports/v3_9/v3_9_h226_events.csv`

It MUST NOT reconstruct H226 events from raw prices.

Required V3.9 provenance:

- artifact-generation parent SHA: `505e217fba0d27bc250d14890093215c1cea8f69`
- canonical dataset: `GOLD_M30_CANONICAL_V2`
- canonical SHA-256: `c48ca44dcecae9eb1c2590c586e27c4bc5f246215c549d0d0bc1201d95d5ea1d`
- strategy_executed: false
- trading_engine_called: false

## Frozen horizon

Only `8h` is analyzed.

No 30m/1h/2h/4h re-selection and no horizons beyond 8h.

The 8h horizon was already frozen and computed before V3.9 results were known; V3.10 is an independent stability audit of that existing diagnostic.

## Frozen cohorts

Descriptive cohorts:

- H226-C1
- H226-C2
- H226-C3
- H226-C4

Decision cohorts remain the pre-frozen V3.9 pair:

- H226-C1
- H226-C4

No post-result substitution to C2 or C3.

## Required views

For every H226 cohort at 8h compute:

1. FULL: 2018Q2–2026Q2
2. PRE_2025: 2018Q2–2024Q4
3. RECENT: 2025Q1–2026Q2
4. each complete year 2019–2025
5. all 33 evaluation quarters 2018Q2–2026Q2
6. UP-gap events
7. DOWN-gap events
8. leave-one-complete-year-out for each year 2019–2025
9. leave-2025-and-2026-out

For each view report at minimum:

- N
- mean signed reversion ATR
- median signed reversion ATR
- P(return > 0)
- p10 / p90
- worst-5% mean signed return
- gap closure probability

## Bootstrap

Two frozen clustered bootstraps are required for each H226 cohort at 8h.

### Quarter-block bootstrap

- replications: 5000
- seed: 310226
- resampling unit: all 33 evaluation quarters
- preserve all events inside each sampled quarter
- statistic: pooled mean signed reversion ATR

### Complete-year block bootstrap

- replications: 5000
- seed: 310227
- resampling unit: complete calendar years 2019–2025
- preserve all events inside each sampled year
- statistic: pooled mean signed reversion ATR

Report 2.5%, 97.5%, and P(mean > 0).

## Direction robustness

UP-gap and DOWN-gap splits are diagnostic only.

They may falsify pooled robustness but MUST NOT be turned into long-only / short-only / one-direction strategy filters.

## Economic-scale diagnostic

No trading PnL is computed.

For scale only, use the frozen Gold round-trip price-equivalent cost benchmark:

- spread: 25 Gold pips = 0.25 USD/oz
- commission: 7 USD/lot with 100 oz/lot = 0.07 USD/oz
- slippage baseline: 0
- total: 0.32 USD/oz

For each cohort compute event-specific `cost_hurdle_atr = 0.32 / atr_prev`, then report median cost hurdle ATR and `mean_8h_signed_return_atr / median_cost_hurdle_atr`.

This is not a strategy-profitability claim and is not part of the mechanism-support gate.

## Frozen decision rule

Decision cohorts are C1 and C4 only.

`H226 DELAYED 8H REVERSION ROBUSTLY SUPPORTED — STRATEGY DESIGN NOT AUTHORIZED`

requires BOTH C1 and C4 to satisfy ALL of:

1. FULL mean > 0
2. FULL median > 0
3. quarter-block 95% CI lower bound > 0
4. complete-year block 95% CI lower bound > 0
5. PRE_2025 mean > 0
6. RECENT mean > 0
7. UP-gap mean > 0
8. DOWN-gap mean > 0
9. at least 5 of 7 complete years have positive mean
10. every leave-one-complete-year-out mean > 0
11. leave-2025-and-2026-out mean > 0

If robust support fails, but BOTH C1 and C4 FULL means remain > 0:

`H226 DELAYED 8H REVERSION REGIME / DIRECTION DEPENDENT — STRATEGY DESIGN NOT AUTHORIZED`

Otherwise:

`H226 DELAYED 8H REVERSION NOT SUPPORTED — H226 CHAPTER CLOSED`

No manual override.

## Required outputs

Machine artifacts under `AlphaLab_Antigravity/reports/v3_10/`:

- `v3_10_8h_view_summary.csv`
- `v3_10_8h_year_stability.csv`
- `v3_10_8h_quarter_stability.csv`
- `v3_10_8h_leave_one_year_out.csv`
- `v3_10_8h_cluster_bootstrap.csv`
- `v3_10_8h_decision.json`
- `v3_10_metadata.json`

Human report:

- `V3_10_H226_DELAYED_REVERSION_STABILITY_REPORT.md`

## Stop rule

After the report, STOP.

Do not create H227, do not design a delayed-reversion strategy, do not add direction filters, do not change H226 thresholds, and do not extend horizons.
