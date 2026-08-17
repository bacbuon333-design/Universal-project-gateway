# V5-A Independent Alpha RR1 Discovery — Frozen Precommit

## Status

V5-A is a historical discovery batch only. It is not fresh-OOS evaluation, paper-trading authorization, deployment authorization, or live-trading authorization.

Scientific parent commit: `5a1a2f8c28f857789943295f6a59df2f1037e72b` (final V4 conclusion).

Scientific parent tree: `b740558d0f1b7904bd1d1f22dddb25adc91693b2`.

Canonical authority: `GOLD_M30_CANONICAL_V2`, SHA-256 `c48ca44dcecae9eb1c2590c586e27c4bc5f246215c549d0d0bc1201d95d5ea1d`, `BAR_OPEN_TIME`, UTC.

Execution authority: `CanonicalV2ExecutionEngine`, contract `CANONICAL_V2_GAP_SAFE_V3_7_3`:
- signal at close bar i;
- entry at open bar i+1;
- entry bar is managed;
- same-bar SL+TP is SL-first;
- adverse gap-through-stop fills at opening price pessimistically;
- favorable TP gap gets no favorable price improvement;
- frozen spread/slippage/commission semantics are preserved.

Evaluator authority: `distributed_edge_v38.py`, which fail-closes around the audited V3.5 full 14-gate evaluator without changing thresholds.

## Scientific question

V4 tested four entry mechanisms under a common 1:2 ATR risk contract and found no configuration passing all frozen gates. V5-A asks a separate question:

> Can four independently specified, non-V4 price-action entry mechanisms produce distributed historical edge under a strictly symmetric `SL = 1.5 ATR`, `TP = 1.5 ATR` risk/reward contract?

V5-A is NOT a re-test or rescue of H301-H304. The entry mechanisms are different and the multiple-testing budget is reduced to one frozen configuration per family.

## Independence / prohibited reuse

V5-A must not read or use fresh-OOS accrual data or sidecars under `AlphaLab_Antigravity/data/oos/`.

V5-A must not use or derive from the closed H226 gap-reversion lineage: no `gap_z`, residual-gap eligibility, delayed 8-hour outcome, C1/C4 eligibility, down-gap selection, recent-regime selection, or H226 descendants.

V5-A must not reuse V4 H301-H304 mechanisms:
- no rolling-channel compression percentile calibration or H301 compressed-channel breakout;
- no fixed 00:00-07:30 UTC anchor / 08:00-15:30 decision-window breakout or H302 session-range logic;
- no EMA24/EMA96 separation, pullback, or recapture logic from H303;
- no rolling close z-score exhaustion/re-entry logic from H304.

V5-A also does not revive the closed V3.5 previous-day breakout, normalized impulse continuation, or London-morning directional-carry strategy chapters.

No closed strategy result, canonical data, legacy engine, V3.12/V3.13 accrual artifact, or V4 result may be modified.

## Multiple-testing budget

Exactly four mechanism families, exactly one frozen configuration per family, exactly four configurations total.

No dynamic grid. No threshold search. No automatic Batch 2. No rescue search around a near miss. No post-result parameter tuning in this chapter.

### H401 — Liquidity Sweep Reclaim (LSR)

Fixed lookback = 24 M30 bars.

At signal bar i:
- prior high = maximum high of bars i-24 ... i-1;
- prior low = minimum low of bars i-24 ... i-1;
- LONG iff `low[i] < prior_low[i]` and `close[i] > prior_low[i]`;
- SHORT iff `high[i] > prior_high[i]` and `close[i] < prior_high[i]`.

This is a same-bar failed-auction/sweep-and-reclaim reversal. Prior extrema exclude the signal bar. No z-score, EMA, session anchor, gap rule, or compression calibration is used.

### H402 — Inside-Bar Mother-Range Breakout (IBB)

At signal bar i:
- bar i-1 must be strictly inside mother bar i-2: `high[i-1] < high[i-2]` and `low[i-1] > low[i-2]`;
- LONG iff `close[i] > high[i-2]`;
- SHORT iff `close[i] < low[i-2]`.

No rolling compression percentile, session range, EMA, z-score, or tunable lookback is used.

### H403 — Body Engulf Reversal (BER)

Fixed minimum current body size = `0.50 * ATR14[i]`.

LONG iff:
- bar i-1 is bearish;
- bar i is bullish;
- current real body fully engulfs prior real body (`open[i] <= close[i-1]` and `close[i] >= open[i-1]`);
- `abs(close[i]-open[i]) >= 0.50 * ATR14[i]`.

SHORT is the exact mirror.

No trend filter, EMA, z-score, session rule, or parameter search is used.

### H404 — Confirmed Pivot Breakout (CPB)

Fixed pivot flank = 2 bars.

A pivot high at j is defined by `high[j]` strictly exceeding highs at j-2, j-1, j+1, j+2. A pivot low is mirrored. The pivot becomes usable only at bar j+2, after both right-side bars have closed.

At signal bar i, use only the most recent pivot level confirmed no later than i. LONG iff a confirmed pivot-high level exists, `close[i-1] <= level`, and `close[i] > level`. SHORT is mirrored using the latest confirmed pivot low.

No future information is available at the time a pivot becomes eligible; confirmation delay is part of the frozen mechanism.

## Common risk and cost contract

All four configurations share exactly:
- ATR14 Wilder-style EWM (`alpha=1/14`, `adjust=False`, `min_periods=14`);
- SL distance = `1.50 * ATR14[i]` at signal close;
- TP distance = `1.50 * ATR14[i]` at signal close;
- risk/reward = exactly 1:1 before costs;
- spread = 25.0 pips;
- slippage = 0.0 pips;
- commission = 7.0 USD/lot;
- fixed lot = 0.10;
- maximum holding = 120 bars.

No per-family risk tuning, trailing stop, break-even, dynamic RR, partial exit, or position-management search.

## Frozen evaluation window and 14 gates

Historical evaluation remains `2018Q2` through `2026Q2`, exactly 33 complete evaluation quarters. Complete calendar years are 2019 through 2025. Rolling-4 has 30 windows; rolling-8 has 26 windows.

All 14 gates must pass simultaneously:
- A1: minimum trades per complete quarter >= 5.
- A2: maximum single-quarter trade-count share <= 5% of all evaluation trades.
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
- E1: overall PF >= 1.25 after frozen costs.
- E2: overall expectancy > 0 USD/trade.

`all_gates_pass` is the conjunction of all 14; no discretionary override.

## Classification

Any gate failure => `REJECTED`.

All 14 gates pass => `HISTORICAL_CANDIDATE_ONLY`.

A survivor is not validated alpha and authorizes nothing operational. Independent validation would require a separately precommitted future chapter.

If zero configurations survive, exact conclusion:

`NO V5-A CONFIGURATION PASSED ALL FROZEN DISTRIBUTED-EDGE GATES`

If one or more survive, exact conclusion:

`V5-A HISTORICAL CANDIDATE(S) IDENTIFIED — INDEPENDENT VALIDATION REQUIRED`

## Execution governance

ONE AGENT, sequential only. No `/goal`, subagents, teams, delegation, parallel models, or hypothesis redesign.

The designer must first commit and publish the complete V5-A code/test/report-generator/handoff. Only the resulting real branch HEAD is the Initial Frozen HEAD.

Executor must verify exact branch, exact Frozen HEAD, and clean worktree before compile/test.

Technical failure policy is strict: if compile/tests reveal a technical defect, STOP before experiment. A technical-only repair may be designed and committed in a separate repair cycle; do not patch and continue the experiment in the same execution run. Any semantic change requires a new research design/freeze.

The frozen experiment is run exactly once after compile/tests pass. Raw machine-readable result must be committed first. Human-readable report must be generated from committed raw JSON and committed separately. No scientific source edit after results.
