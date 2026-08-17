# ALAB-M1 — FINAL HOLDOUT 2015–2017 PRECOMMIT
## One-shot confirmation of the surviving narrow attenuation hypothesis

## Governance transition
The 2018–2025 development laboratory is formally closed for this mechanism family. No further mining, subgroup selection, threshold adjustment, gradient repair, placebo redesign, or specification rescue on 2018–2025 is authorized.

MECH-005 remains officially `COMPENSATION_FALSIFIED_OR_NOT_INVARIANT` because the strict five-bin monotonic-shape gate failed. The final holdout does **not** relabel MECH-005 as PASS. Instead, it tests one narrower next-generation hypothesis formed from the development evidence that survived adversarial testing.

2015–2017 has not been used in V1/001R/MECH-002/003/004/005 and remains sealed until this PRECOMMIT plus source/tests is committed and pushed.

### Pre-open implementation audit
Before any 2015–2017 rates were requested, the implementation underwent a final fail-closed audit. Two governance repairs were made while the holdout was still sealed:
1. the extractor now refuses to seal a canonical file that fails timestamp/OHLC/row-sufficiency quality checks;
2. the confirmation runner now blocks all scientific regressions/bootstrap if breach-count, exact-clock, or EXCURSION_RATIO coverage is insufficient.

No holdout data or outcome was accessed during these repairs. The Git branch head containing this document and those repaired sources is the **authoritative PRECOMMIT**; all earlier pre-open branch states are superseded.

## Single final hypothesis
After a breach of the prior 20 closed M1 bars' extreme, greater snapback realization inside the breach candle is associated with **sub-one-for-one persistence** in total snapback displacement at exactly +5 clock minutes.

The hypothesis is operationalized as:

`rho_5m < 1.0`

under **all four frozen coordinate representations**:
1. `ATR_T`
2. `ATR_PRE`
3. `PRICE_BPS`
4. `EXCURSION_RATIO`

This final hypothesis contains NO claim of strict monotonic five-bin shape, fixed 100% reversion budget, physical conservation law, liquidity-provider/institutional-flow cause, randomized causal identification, or tradable edge/entry signal.

## Holdout data boundary — immutable
Target: `GOLD`, `M1`.

Permitted timestamps:
`2015-01-01 00:00:00 UTC <= datetime < 2018-01-01 00:00:00 UTC`.

Forbidden to this final runner:
- any 2018–2025 development file;
- any 2026+ discovery data;
- any merged development+holdout dataset.

Canonical holdout path after one-time opening:
`AlphaLab_Antigravity/data/canonical/GOLD_M1_FINAL_HOLDOUT_2015_2017.csv`

The holdout SHA256 is necessarily unknown before opening. The one-time extractor must calculate it immediately after canonicalization and write it into:
`AlphaLab_Antigravity/reports/m1_final_holdout/M1_FINAL_HOLDOUT_EXTRACTION_SEAL.json`.
The confirmation runner must refuse if the on-disk SHA differs from the sealed SHA.

## One-time unsealing / extraction protocol
Extraction is read-only through `MetaTrader5.copy_rates_range(symbol='GOLD', timeframe=M1)`.

Frozen procedure:
1. Preflight only: initialize MT5, read terminal_info, require `maxbars >= 1,000,000`, select GOLD.
2. Only after preflight succeeds, request exactly three annual chunks: 2015, 2016, 2017.
3. Each annual chunk must contain at least `250,000` M1 rows.
4. Concatenate in time order; no interpolation and no deduplication repair.
5. Duplicate timestamps, boundary violations, missing years, invalid schema, or insufficient annual rows are extraction failures.
6. Write canonical CSV and SHA seal atomically only after all three chunks and canonical quality checks pass.
7. Canonical CSV is local/gitignored; seal/audit artifacts are committed with the final result.

### Irreversibility rule
Before any **non-empty** 2015–2017 rates array is returned, an infrastructure-only failure may be repaired and retried because no holdout observations have been exposed.

Once any **non-empty** 2015–2017 rates array has been returned, the holdout is considered OPENED. If extraction then fails, the extractor must create `M1_FINAL_HOLDOUT_OPENED_FAILURE.json` with `rerun_authorized=false`; the program must not rerun extraction or the scientific test.

If a successful extraction seal or opened-failure marker already exists, the extractor must refuse overwrite/re-extraction.

## Data quality gates before scientific inference
The canonical holdout must satisfy all:
- all three years 2015, 2016, 2017 represented;
- total rows >= `750,000`;
- each year rows >= `250,000`;
- monotonically increasing unique timestamps;
- whole-minute timestamps;
- no non-finite or invalid OHLC;
- no pre-2015 and no 2018+ data;
- no interpolation;
- breach universe >= `100,000` events;
- exact +5m endpoint coverage >= `98%`;
- EXCURSION_RATIO retains >= `50%` of exact +5m events.

Market-closure gaps are audited but are neither repaired nor themselves a failure.

If the row/schema/timestamp/OHLC checks fail during extraction after a non-empty holdout response has been exposed, extraction ends with the irreversible opened-failure marker. If event/endpoint/representation coverage fails after a valid canonical seal, the runner must write a DATA_BLOCKED final verdict **without running rho regressions or bootstrap**.

## Frozen breach universe and causal features
Use the MECH-003/004/005 mechanics:
- prior-extreme lookback = 20 closed M1 bars excluding event bar;
- upper breach `high[t] > prior_high[t]`;
- lower breach `low[t] < prior_low[t]`;
- dual-side breach bars excluded;
- exact close at prior extreme excluded;
- both FAILED_AUCTION and ACCEPTED_BREAKOUT included; event class is descriptive only and not a control.

Frozen controls:
- representation-specific excursion;
- ATR percentile / 100;
- path efficiency;
- absolute robust stretch;
- structural location count using repaired MECH-002 location implementation;
- breach side indicator;
- UTC hour sine/cosine;
- holdout year fixed effects, 2015 baseline, dummies 2016/2017.

No outcome-derived variable, event class, future state, MFE/MAE, optimized threshold, or development coefficient is permitted as a control.

## Frozen coordinates
For snapback sign `s=+1` lower breach/LONG and `s=-1` upper breach/SHORT:

`raw_in = s*(C_t-X_t)`

`raw_total_5m = s*(C_{t+5m}-X_t)`

`raw_exc = s*(L_t-X_t)`

### A. ATR_T
`X = raw_in / ATR_t`; `Y = raw_total_5m / ATR_t`; excursion control `raw_exc / ATR_t`.

### B. ATR_PRE
`ATR_pre = ATR14 shifted one M1 bar`; `X = raw_in / ATR_pre`; `Y = raw_total_5m / ATR_pre`; excursion control `raw_exc / ATR_pre`.

### C. PRICE_BPS
`X = raw_in / prior_extreme * 10000`; `Y = raw_total_5m / prior_extreme * 10000`; excursion control `raw_exc / prior_extreme * 10000`.

### D. EXCURSION_RATIO
Include only `breach_excursion_atr >= 0.10`.
`X = raw_in/raw_exc`; `Y = raw_total_5m/raw_exc`; excursion nuisance control remains `breach_excursion_atr`.

## Primary regression
For each representation:
`Y_5m = rho_5m * X_in + frozen_controls + error`.

Estimate `rho` by Frisch–Waugh–Lovell residualization. Null benchmark: `rho = 1.0`.

The final holdout concerns pooled 2015–2017 confirmation only. Year-specific slopes are descriptive and not gates.

## Dependence-aware inference
For each representation:
- exact +5 clock minutes only;
- fixed-residual UTC-day block bootstrap;
- B = `2000`;
- seed = `20260820`;
- empirical two-sided 95% interval;
- confirmatory requirement uses upper bound `<1.0`.

### Joint four-coordinate robustness gate
Use the same sampled UTC-day indices across A/B/C/D. For each bootstrap iteration compute all four rho values and retain `max_rho = max(rho_A,rho_B,rho_C,rho_D)`.

Frozen joint requirement: 97.5th percentile of bootstrap `max_rho` distribution `<1.0`.
This is a pre-registered simultaneous robustness gate, not a physical-law confidence interval.

## Frozen final gates
### G0 — data integrity / coverage
All data-quality requirements pass; each coordinate bootstrap has 2000 valid iterations; joint bootstrap has 2000 valid iterations.

### G1 — point-direction confirmation
All four pooled +5m coefficients satisfy `rho_5m < 1.0`.

### G2 — individual dependence-aware confirmation
All four individual UTC-day bootstrap 95% CI upper bounds satisfy `upper < 1.0`.

### G3 — joint four-coordinate confirmation
Shared-day bootstrap 97.5th percentile of `max_rho` satisfies `joint_upper_max_rho < 1.0`.

## Final verdicts — exhaustive
If data cannot validly support the test:
`FINAL_HOLDOUT_BLOCKED_DATA_INSUFFICIENT_OR_INVALID`.

If G0 passes and G1–G3 all pass:
`FINAL_HOLDOUT_CONFIRMED`.

If G0 passes but any G1–G3 fails:
`FINAL_HOLDOUT_REJECTED`.

Program closure mapping:
- CONFIRMED -> `CLOSE_CONFIRMED_PHENOMENON`
- REJECTED -> `CLOSE_REJECTED_MECHANISM_FAMILY`
- DATA BLOCKED -> `CLOSED_WITHOUT_SCIENTIFIC_VERDICT_DATA_BLOCKED`

There is no rescue MECH-006/007 on this same mechanism family after a valid holdout rejection.

## Explicitly NOT tested in final holdout
- five-bin monotonic gradient;
- MECH-005 placebo tests;
- trade profitability/costs;
- SL/TP/holding optimization;
- threshold or subgroup/session/side selection;
- other horizons as confirmatory gates.

## Required artifacts after opening and one scientific execution
- `M1_FINAL_HOLDOUT_EXTRACTION_SEAL.json`
- `M1_FINAL_HOLDOUT_DATA_AUDIT.json`
- `M1_FINAL_HOLDOUT_CONFIRMATION.csv`
- `M1_FINAL_HOLDOUT_BOOTSTRAP.json`
- `M1_FINAL_HOLDOUT_JOINT_MAX_RHO.json`
- `M1_FINAL_HOLDOUT_YEARLY_DESCRIPTIVE.csv`
- `M1_FINAL_HOLDOUT_GATES.json`
- `M1_FINAL_HOLDOUT_MANIFEST.json`
- `M1_FINAL_HOLDOUT_REPORT.md`
- local full event table with SHA256 in manifest.

If unsealing fails after a non-empty holdout response, `M1_FINAL_HOLDOUT_OPENED_FAILURE.json` replaces the normal scientific artifact path and permanently records that no valid scientific verdict was obtained.

## Absolute prohibitions after PRECOMMIT
No 2018–2025 mining; no 2026 access; no coordinate/control/horizon/floor/coverage/gate changes; no gradient rescue; no rerun because result is unfavorable; no strategy/PnL/paper/live/broker execution; no source modification after holdout outcomes are observed.

## Execution governance
1. Commit/push PRECOMMIT + extractor + confirmation source + tests.
2. Record authoritative PRECOMMIT SHA remotely.
3. Run unit tests before opening holdout.
4. Run preflight and one-time extraction.
5. Record extraction seal SHA256.
6. Run final scientific confirmation exactly once.
7. Commit result exactly as produced, including a negative result.
8. Close mechanism family according to frozen verdict mapping.
