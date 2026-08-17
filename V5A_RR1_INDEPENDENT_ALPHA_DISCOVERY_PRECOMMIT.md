# V5-A RR 1:1 Independent Alpha Discovery — Frozen Precommit

## Status and scientific parent

V5-A is a new historical discovery chapter only. It is not a rescue of V4, not a descendant of H226, not fresh-OOS evaluation, not paper-trading authorization, and not deployment/live-trading authorization.

Scientific parent commit: `5a1a2f8c28f857789943295f6a59df2f1037e72b` (final V4 conclusion).

V4 remains closed with zero 14-gate survivors. H301-H304 remain rejected and may not be tuned, reparameterized, or semantically reused here.

Canonical authority: `GOLD_M30_CANONICAL_V2`, SHA-256 `c48ca44dcecae9eb1c2590c586e27c4bc5f246215c549d0d0bc1201d95d5ea1d`, `BAR_OPEN_TIME`, explicit UTC.

Execution authority: `CanonicalV2ExecutionEngine`, contract `CANONICAL_V2_GAP_SAFE_V3_7_3`:
- signal at close bar i;
- entry at open bar i+1;
- entry bar is managed;
- same-bar SL+TP is SL-first;
- adverse gap-through-stop fills at opening price pessimistically;
- favorable TP gap receives no favorable price improvement;
- frozen spread/slippage/commission semantics are preserved.

Evaluator authority: `distributed_edge_v38.py`, fail-closed around the audited V3.5 full 14-gate evaluator without threshold changes.

## Independence / prohibited reuse

V5-A must not read or use the fresh-OOS accrual dataset or sidecar under `AlphaLab_Antigravity/data/oos/`.

V5-A must not use the closed H226 daily-gap delayed-reversion lineage: no gap-z eligibility, residual-gap eligibility, C1/C4 rule, delayed 8-hour outcome, down-gap selection, recent-regime selection, or derivatives of those rules.

V5-A must not reuse the semantic entry mechanisms of V4:
- H301: prior-channel compression followed by channel breakout;
- H302: fixed UTC session-range breakout;
- H303: EMA24/EMA96 separation with pullback recapture;
- H304: rolling close z-score exhaustion re-entry.

Utility/evaluation infrastructure may be reused. Entry semantics may not.

V5-A must not modify any legacy engine, canonical dataset, V3.12/V3.13 prospective OOS artifact, H226 research artifact, V4 code/result/report, or any other closed research result.

## Multiple-testing budget

Exactly four new mechanism families, exactly one frozen configuration per family, exactly four configurations total.

No parameter grid, no alternatives inside a family, no automatic Batch 2, no post-result threshold adjustment, and no rescue search around a near miss.

### H401 — Impulse Body Continuation (IBC)

One fixed configuration only.

At signal close i, using current completed bar and ATR14 known at that close:
- `body = abs(close-open)`;
- `range = high-low`;
- `close_location = (close-low)/range`.

Long iff:
- close > open;
- body / ATR14 >= 0.80;
- close_location >= 0.80.

Short is mirrored:
- close < open;
- body / ATR14 >= 0.80;
- close_location <= 0.20.

This is a single completed-bar impulse/closing-control continuation mechanism. It has no prior-channel breakout, session anchor, EMA recapture, z-score, or gap rule.

### H402 — Wick Failure Reversal (WFR)

One fixed configuration only.

At signal close i:
- `lower_wick = min(open, close) - low`;
- `upper_wick = high - max(open, close)`;
- `body = abs(close-open)`;
- `close_location = (close-low)/(high-low)`.

Long iff:
- lower_wick >= 1.50 * body;
- lower_wick >= 0.50 * ATR14;
- close_location >= 0.70.

Short iff:
- upper_wick >= 1.50 * body;
- upper_wick >= 0.50 * ATR14;
- close_location <= 0.30.

This is completed-bar auction-failure/rejection, not rolling statistical mean reversion.

### H403 — Three-Bar Absorption Reversal (TBAR)

One fixed configuration only.

Long at signal close i iff:
- bars i-2 and i-1 are both bearish (`close < open`);
- bar i is bullish (`close > open`);
- current body >= 0.60 * ATR14[i];
- current open < previous close;
- current close > previous open.

Short is the exact mirror: two prior bullish bars, current bearish bar, current body threshold met, current open > previous close, current close < previous open.

This is a fixed three-bar directional absorption/body-engulf mechanism. No trend average, channel, z-score, session, or gap calibration is used.

### H404 — Outside-Bar Closing Control (OBCC)

One fixed configuration only.

At signal close i, bar i must strictly engulf the immediately prior full range:
- `high[i] > high[i-1]`;
- `low[i] < low[i-1]`;
- current range >= 1.25 * ATR14[i].

Long iff the outside bar is bullish and closes in the top 25% of its own range (`close_location >= 0.75`).

Short iff the outside bar is bearish and closes in the bottom 25% (`close_location <= 0.25`).

This is a two-bar range-expansion/closing-control mechanism. It does not break a rolling channel or fixed session range and does not use EMA/z-score/gap rules.

## Common risk and cost contract — V5-A RR 1:1

All four configurations share exactly:
- ATR14 Wilder-style EWM (`alpha=1/14`, `adjust=False`, `min_periods=14`);
- SL distance = `1.50 * ATR14[i]` at signal close;
- TP distance = `1.50 * ATR14[i]` at signal close;
- fixed R:R = 1:1;
- engine spread argument = 25.0 GOLD pip-units, where frozen GOLD `pip_size=0.01`, preserving the canonical V4 spread-price of 0.25 USD/oz;
- slippage = 0.0 pip-units;
- commission = 7.0 USD/lot;
- fixed lot = 0.10;
- maximum holding = 120 bars.

No per-family risk tuning, trailing stop, break-even, dynamic RR, position-management search, or alternative TP/SL ratio is authorized.

## Frozen evaluation window and 14 gates

Historical evaluation window remains `2018Q2` through `2026Q2`, exactly 33 complete quarters. Complete calendar years are 2019 through 2025. Rolling-4 has 30 windows; rolling-8 has 26 windows.

All 14 gates must pass simultaneously:
- A1: minimum trades per complete quarter >= 5.
- A2: maximum single-quarter trade-count share <= 5%.
- A3: maximum quarter trade count / median quarter trade count <= 3.0.
- A4: quarterly trade-count Gini < 0.30.
- B1: top 3 positive quarters contribute <= 40% of positive-quarter PnL pool.
- B2: top 5 positive quarters contribute <= 60% of positive-quarter PnL pool.
- D4_1: >= 70% rolling-4-quarter windows have positive net PnL.
- D4_2: >= 65% rolling-4-quarter windows have PF >= 1.20.
- D8_1: >= 75% rolling-8-quarter windows have positive net PnL.
- D8_2: >= 70% rolling-8-quarter windows have PF >= 1.20.
- Y1: minimum trades in each complete calendar year >= 20.
- Y2: >= 70% complete calendar years have positive net PnL.
- E1: overall PF >= 1.25.
- E2: overall expectancy > 0 USD/trade.

`all_gates_pass` is the conjunction of all 14 booleans with no discretionary override.

## Classification

Failing any gate => `REJECTED`.

Passing all 14 => `HISTORICAL_CANDIDATE_ONLY`.

A survivor is not validated alpha and does not authorize fresh-OOS peeking, paper trading, deployment, or live trading. A separate independently precommitted validation chapter would be required.

If zero configurations survive, exact conclusion:

`NO V5-A CONFIGURATION PASSED ALL FROZEN DISTRIBUTED-EDGE GATES`

If one or more survive, exact conclusion:

`V5-A HISTORICAL CANDIDATE(S) IDENTIFIED — INDEPENDENT VALIDATION REQUIRED`

## Execution governance

ONE AGENT, SEQUENTIAL ONLY. Compile and frozen tests before experiment.

A technical-only repair may address syntax/import/path/serialization/test-runner/API compatibility only, with zero scientific semantic change. If any technical repair is needed, the executor must STOP BEFORE SCIENTIFIC EXECUTION, commit the repair separately, return the new clean HEAD, and end that run. A new executor run must start from that repaired Frozen HEAD. The repair run may not continue into the experiment.

Any proposed change to hypothesis, threshold, timing, risk, cost, execution, evaluator gate, sample, or multiple-testing budget is a scientific change and blocks execution pending designer review.

The frozen batch is run exactly once. Raw machine-readable result must be committed alone before human-readable report generation. No scientific/source code edits are permitted after results. Stop after the separate report commit.