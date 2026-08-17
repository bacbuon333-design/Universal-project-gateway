# V4 Independent Alpha Discovery — Frozen Precommit

## Status

This chapter is a historical discovery batch only. It is not fresh-OOS evaluation, paper-trading authorization, deployment authorization, or live-trading authorization.

Scientific parent: `1971fc24a7649d6a788d0b5c0d66528a9a8baf2e`.

Canonical authority: `GOLD_M30_CANONICAL_V2`, SHA-256 `c48ca44dcecae9eb1c2590c586e27c4bc5f246215c549d0d0bc1201d95d5ea1d`, `BAR_OPEN_TIME`, UTC.

Execution authority: `CanonicalV2ExecutionEngine`, contract `CANONICAL_V2_GAP_SAFE_V3_7_3`:
- signal at close bar i;
- entry at open bar i+1;
- entry bar is managed;
- same-bar SL+TP is SL-first;
- adverse gap-through-stop fills at opening price pessimistically;
- favorable TP gap gets no favorable price improvement;
- frozen spread/slippage/commission semantics are preserved.

Evaluator authority: `distributed_edge_v38.py`, which fail-closes around the audited V3.5 14-gate evaluator without changing thresholds.

## Independence / prohibited reuse

V4 must not read or use the fresh-OOS accrual dataset or sidecar under `AlphaLab_Antigravity/data/oos/`.

V4 must not use the closed daily-gap delayed-reversion research lineage: no gap-z eligibility, residual-gap eligibility, C1/C4 rules, delayed 8-hour outcome, down-gap selection, recent-regime selection, or derivatives of those rules. Historical closed-strategy status remains rejected and unchanged.

V4 must not modify any legacy engine, canonical dataset, V3.12/V3.13 accrual artifact, or closed research result.

## Multiple-testing budget

Exactly four mechanism families, exactly three frozen configurations per family, exactly 12 configurations total. No dynamic parameter grid. No automatic Batch 2. No rescue search around a near miss. A rejected configuration may not be tuned in this chapter.

### H301 — Volatility Compression -> Breakout Continuation

Frozen configurations: channel lookback `L` in `{24, 48, 96}` M30 bars.

At signal bar i:
1. prior channel high/low use bars `i-L ... i-1` only;
2. prior channel width is normalized by ATR14 at `i-1`;
3. compression threshold is the 20th percentile of the preceding 240 valid prior-channel-width observations and is shifted so the current width does not calibrate its own threshold;
4. long signal iff prior width is compressed and `close[i] > prior_high[i]`; short is mirrored.

No current/future bar enters the prior channel or compression calibration.

### H302 — Fixed UTC Session Range Breakout

Frozen anchor: `00:00` through `07:30` UTC inclusive, exactly 16 M30 bars required.

Frozen decision window: `08:00` through `15:30` UTC inclusive.

Frozen ATR breakout buffers: `{0.00, 0.10, 0.20}`.

For each UTC date/config, the first qualifying decision-bar close outside anchor high/low plus/minus the frozen buffer generates at most one signal. Incomplete anchor days produce no signal.

### H303 — Trend Pullback / EMA Recapture

EMA fast = 24; EMA slow = 96; pandas EWM span semantics with `adjust=False` and minimum periods equal to the span.

Frozen minimum absolute EMA separation / ATR14 thresholds: `{0.25, 0.50, 0.75}`.

Long: fast > slow, separation threshold met, previous close <= previous fast EMA, and current close > current fast EMA. Short is mirrored.

### H304 — Exhaustion Mean Reversion

Rolling close z-score window = 48 bars, rolling population standard deviation (`ddof=0`).

Frozen thresholds: `{1.50, 2.00, 2.50}`.

Long only on re-entry from `z[i-1] <= -threshold` to `z[i] > -threshold`; short only on mirrored positive-threshold re-entry.

## Common risk contract

All 12 configurations share exactly:
- ATR14 Wilder-style EWM (`alpha=1/14`, `adjust=False`, `min_periods=14`);
- SL distance = `1.50 * ATR14[i]` at signal close;
- TP distance = `3.00 * ATR14[i]` at signal close;
- spread = 25.0 pips;
- slippage = 0.0 pips;
- commission = 7.0 USD/lot;
- fixed lot = 0.10;
- maximum holding = 120 bars.

No per-family risk tuning, trailing stop, break-even, dynamic RR, or position-management search.

## Frozen evaluation window and 14 gates

Historical evaluation window remains `2018Q2` through `2026Q2`, 33 complete evaluation quarters. Complete calendar years are 2019 through 2025. Rolling-4 has 30 windows; rolling-8 has 26 windows.

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
- E1: overall PF >= 1.25.
- E2: overall expectancy > 0 USD/trade.

`all_gates_pass` is the conjunction of all 14 gates; no discretionary override.

## Classification

Failing any gate => `REJECTED`.

Passing every gate => `HISTORICAL_CANDIDATE_ONLY`.

A survivor is not validated alpha and does not authorize fresh-OOS peeking, paper trading, deployment, or live trading. A separate independently precommitted validation chapter would be required later.

If zero configurations survive, the exact batch conclusion is:

`NO V4 CONFIGURATION PASSED ALL FROZEN DISTRIBUTED-EDGE GATES`

If one or more survive, the exact conclusion is:

`V4 HISTORICAL CANDIDATE(S) IDENTIFIED — INDEPENDENT VALIDATION REQUIRED`

## Execution governance

One agent, sequential only. Compile and frozen tests before experiment. Technical-only repairs (syntax/import/path/serialization/test-runner/API compatibility with no semantic change) require a separate commit before execution. Any proposed change to hypothesis, parameter, timing, risk, cost, execution, evaluator threshold, sample, or testing budget blocks execution and requires designer review.

The frozen batch is run once. Raw machine-readable result must be committed before human-readable report generation. No scientific code edits after results. Stop after report commit.