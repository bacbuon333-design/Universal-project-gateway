# V3.8 CANONICAL V2 NEW-MECHANISM DISCOVERY — PRECOMMIT

## 1. PURPOSE

V3.8 is the first new strategy-research chapter authorized after the V3.7 data/provenance/engine/execution hardening sequence.

Scientific parent: `c4b5bf68c4beb5c6490eacb73f31c16160424ab4`.

Required data authority:

- `GOLD_M30_CANONICAL_V2`
- frozen SHA-256 `c48ca44dcecae9eb1c2590c586e27c4bc5f246215c549d0d0bc1201d95d5ea1d`
- `BAR_OPEN_TIME`
- `EXPLICIT_UTC / UTC`
- `UNIX_EPOCH_SECONDS_UTC`
- lineage `VERIFIED`
- V2 reproduction `ELIGIBLE`

Required execution authority:

- `CanonicalV2ExecutionEngine`
- gap-safe adverse stop handling
- signal at bar-close i, entry at bar-open i+1
- entry-bar SL/TP management
- pessimistic SL-first ambiguous bars
- no favorable TP gap improvement
- one open position maximum

Legacy `GOLD_M30.csv` and legacy `DeepQuantEngine` are not authorized for V3.8 execution.

## 2. SCIENTIFIC POSITION

No earlier strategy is promoted into V3.8.

H-204 through H-220 remain closed/rejected/ambiguous according to their accepted chapter conclusions.

V3.8 MUST NOT:

- repair or retune H-204→H-220;
- create an H-220 descendant;
- create LMDC Long-only/Short-only variants;
- select thresholds from prior near-misses;
- change gates after observing results;
- launch a second batch automatically.

A V3.8 pass is historical evidence only:

`HISTORICAL DISTRIBUTED SURVIVOR — REQUIRES PRECOMMITTED STABILITY BATCH`

It is not validated alpha and not true OOS.

## 3. DATA/EVALUATION WINDOW

Instrument: broker symbol `GOLD`.

Timeframe: M30.

Evaluation window by ENTRY quarter:

`2018Q2` through `2026Q2`, inclusive.

Exactly 33 complete quarters.

Complete calendar years for yearly gates:

2019 through 2025 inclusive (7 years).

Bars after 2026Q2 may be used only to finish positions whose entries fall inside the frozen evaluation window. They are not evaluation entries.

## 4. EXECUTION/COST CONTRACT

- fixed lot: `0.10`
- spread: `25.0` Gold pips
- commission: `$7.00 / lot round-trip`
- slippage baseline: `0.0 pips`
- pessimistic ambiguous bars: `True`
- max holding: `120 M30 bars`
- adverse stop gap: fill at worse executable open-side price
- favorable target gap: no price improvement beyond TP

No cost sensitivity batch in V3.8.

## 5. FULL 14 HARD GATES

All gates are simultaneous and frozen.

### Trade distribution

A1. minimum trades in every complete evaluation quarter >= 5

A2. maximum single-quarter trade share <= 5%

A3. maximum quarterly trade count / median quarterly count <= 3

A4. quarterly trade-count Gini < 0.30

### Profit concentration

B1. Top-3 positive-quarter PnL share <= 40%

B2. Top-5 positive-quarter PnL share <= 60%

If there is no valid positive-quarter pool, B gates fail.

### Rolling 4-quarter robustness

D4_1. >= 70% of 30 rolling-4Q windows have positive net PnL

D4_2. >= 65% of rolling-4Q windows have PF >= 1.20

### Rolling 8-quarter robustness

D8_1. >= 75% of 26 rolling-8Q windows have positive net PnL

D8_2. >= 70% of rolling-8Q windows have PF >= 1.20

### Complete-year robustness

Y1. every complete year 2019–2025 has >= 20 trades

Y2. >= 70% of complete years are profitable

### Economics

E1. aggregate PF >= 1.25

E2. aggregate expectancy > $0 after frozen costs

No config passes unless ALL 14 gates pass.

## 6. INDICATOR DEFINITIONS

ATR14 is causal Wilder-style-equivalent EWM true range using only bars through signal bar i.

`TR_i = max(high_i-low_i, abs(high_i-close_{i-1}), abs(low_i-close_{i-1}))`.

EMA values at bar i use closes through i only.

Signals are produced after bar i is complete and enter only at i+1 open.

For each signal, SL/TP arrays contain DISTANCES, never absolute prices.

## 7. H-221 — WICK REJECTION REVERSAL (WRR)

Hypothesis: a large rejection wick that closes back toward the opposite side of the same bar reflects failed intrabar auction pressure and predicts short-horizon reversal/continuation in the close direction.

For bar i:

- `range = high-low`
- `upper_wick = high-max(open,close)`
- `lower_wick = min(open,close)-low`
- `close_location = (close-low)/range`

Minimum bar range is expressed in ATR14.

LONG when:

- lower_wick/range >= W
- close_location >= 0.70
- range/ATR14 >= RMIN

SHORT symmetric:

- upper_wick/range >= W
- close_location <= 0.30
- range/ATR14 >= RMIN

Stops/targets:

- SL = 1.25 ATR
- RR = 2.0

Frozen configs:

- C1 W=0.45, RMIN=0.50
- C2 W=0.55, RMIN=0.50
- C3 W=0.45, RMIN=0.80
- C4 W=0.55, RMIN=0.80

## 8. H-222 — CONSECUTIVE RUN EXHAUSTION (CRE)

Hypothesis: sufficiently long same-direction close-to-close runs become locally exhausted.

For K most recent close-to-close changes ending at i:

- all K changes must have identical sign;
- cumulative move magnitude = `abs(close_i-close_{i-K}) / ATR14_i`.

After K positive changes and magnitude >= Z: SHORT.

After K negative changes and magnitude >= Z: LONG.

- SL = 1.50 ATR
- RR = 2.0

Frozen configs:

- C1 K=3, Z=1.50
- C2 K=3, Z=2.00
- C3 K=4, Z=1.50
- C4 K=4, Z=2.00

## 9. H-223 — INSIDE-BAR BREAKOUT CONTINUATION (IBC)

Hypothesis: compression inside a prior mother bar followed by a confirmed close beyond the mother range predicts continuation.

For `inside_count = N`:

- the N bars immediately before signal bar i must each lie inside the same mother-bar high/low;
- mother bar is i-N-1;
- signal bar i closes above mother high + BUFFER*ATR14_i => LONG;
- signal bar i closes below mother low - BUFFER*ATR14_i => SHORT.

All range references are historical/current-close known at signal time.

- SL = 1.25 ATR
- RR = 2.0

Frozen configs:

- C1 N=1, BUFFER=0.00
- C2 N=1, BUFFER=0.10
- C3 N=2, BUFFER=0.00
- C4 N=2, BUFFER=0.10

## 10. H-224 — OUTSIDE-BAR SWEEP REVERSAL (OSR)

Hypothesis: an outside bar that sweeps both sides of the previous bar but closes near one extreme reflects a completed liquidity sweep and predicts movement in the close direction.

At i:

- high_i > high_{i-1}
- low_i < low_{i-1}
- range_i / ATR14_i >= RMIN

LONG if close_location >= CL.

SHORT if close_location <= 1-CL.

- SL = 1.50 ATR
- RR = 2.0

Frozen configs:

- C1 CL=0.70, RMIN=1.00
- C2 CL=0.80, RMIN=1.00
- C3 CL=0.70, RMIN=1.50
- C4 CL=0.80, RMIN=1.50

## 11. H-225 — EMA DEVIATION REVERSION (EDR)

Hypothesis: large persistent displacement from a causal medium-horizon centerline, followed by a one-bar turn back toward the center, predicts mean reversion.

At i:

`z = (close_i - EMA_L_i) / ATR14_i`.

LONG when:

- z <= -K
- close_i > close_{i-1}

SHORT when:

- z >= +K
- close_i < close_{i-1}

- SL = 1.50 ATR
- RR = 2.0

Frozen configs:

- C1 L=48, K=1.50
- C2 L=48, K=2.00
- C3 L=96, K=1.50
- C4 L=96, K=2.00

## 12. H-226 — DAILY REOPEN GAP REVERSION (DRGR)

Hypothesis: a UTC-day reopen gap from the immediately previous M30 close that remains materially unfilled after the first bar tends to mean-revert.

Only the first observed M30 bar of each UTC calendar day is eligible to generate a signal.

At first bar i of a new UTC date:

- previous close = close_{i-1}
- gap = open_i - close_{i-1}
- normalized gap = abs(gap)/ATR14_{i-1}
- residual after first bar = abs(close_i-close_{i-1}) / max(abs(gap), epsilon)

If normalized gap >= G and residual >= RESID:

- positive gap with close_i still above previous close => SHORT
- negative gap with close_i still below previous close => LONG

No signal if the first bar already crosses through the previous close.

- SL = 1.25 ATR14_i
- RR = 2.0

Frozen configs:

- C1 G=0.05, RESID=0.25
- C2 G=0.10, RESID=0.25
- C3 G=0.05, RESID=0.50
- C4 G=0.10, RESID=0.50

## 13. MULTIPLE-TESTING BUDGET

Exactly 6 mechanism families.

Exactly 4 configs per family.

Exactly 24 configurations total.

No config may be added after any V3.8 result is observed.

No random search, grid expansion, Bayesian search, genetic search, local tuning or direction removal.

## 14. REQUIRED MACHINE OUTPUTS

Directory:

`AlphaLab_Antigravity/reports/v3_8/`

Required aggregate files:

- `v3_8_all_configs.csv`
- `v3_8_gate_matrix.csv`
- `v3_8_metadata.json`

For every config, persist:

- evaluation trades
- quarter table
- rolling-4 table
- rolling-8 table
- year table

Reports must be generated from authoritative machine outputs.

## 15. DECISION RULE

Allowed config statuses only:

- `HISTORICAL DISTRIBUTED SURVIVOR — REQUIRES PRECOMMITTED STABILITY BATCH`
- `REJECTED`

Allowed batch conclusions only:

- `NO V3.8 CONFIGURATION PASSED ALL FROZEN DISTRIBUTED-EDGE GATES`
- `ONE OR MORE V3.8 HISTORICAL DISTRIBUTED SURVIVORS REQUIRE A SEPARATE PRECOMMITTED STABILITY BATCH`

A survivor MUST NOT be tuned inside V3.8.

## 16. STOP RULE

After the 24 frozen configs are run, saved and reported:

STOP.

Do not:

- create H-227;
- alter a failed threshold;
- remove one direction;
- change RR;
- add a filter;
- run another asset/timeframe;
- automatically create a stability batch.

Return all evidence for independent audit.