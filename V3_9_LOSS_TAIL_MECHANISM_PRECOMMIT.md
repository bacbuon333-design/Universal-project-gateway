# V3.9 LOSS-CONCENTRATION & H226 TAIL-MECHANISM AUDIT

## PURPOSE

V3.9 is a DIAGNOSTIC / EVENT-STUDY chapter only.

It does NOT create H227, redesign H226, change any V3.8 strategy, optimize parameters, alter costs, or execute a historical trading strategy.

Scientific parent:

`635258edb87da39cb3bd1a599bec2f6c94a0b477`

Target branch:

`research/quant-v3.9-loss-tail-mechanism-audit`

V3.8 accepted conclusion remains frozen:

`NO V3.8 CONFIGURATION PASSED ALL FROZEN DISTRIBUTED-EDGE GATES`

## SCIENTIFIC QUESTIONS

Q1. For the rejected V3.8 strategies, are losses broadly distributed or concentrated in a small number of quarters / trades?

Q2. H226 displayed unusually strong temporal positivity despite PF < 1. Is that pattern consistent with a genuine daily-gap reversion tendency overwhelmed by adverse continuation tails, or is the underlying reversion mechanism itself weak?

These are explanatory questions only. No V3.8 verdict can be upgraded by V3.9.

## AUTHORITATIVE INPUTS

Read-only inputs:

- `AlphaLab_Antigravity/reports/v3_8/v3_8_all_configs.csv`
- all 24 frozen V3.8 `*_trades.csv`, `*_quarters.csv`, `*_years.csv`
- `AlphaLab_Antigravity/data/canonical/GOLD_M30_CANONICAL_V2.csv`
- V3.7.1.1/V3.7.2 canonical provenance artifacts

Canonical SHA-256:

`c48ca44dcecae9eb1c2590c586e27c4bc5f246215c549d0d0bc1201d95d5ea1d`

No legacy CSV may be used for event measurements.

## PART A — LOSS-CONCENTRATION DIAGNOSTICS FOR ALL 24 CONFIGS

For every V3.8 configuration, compute from the already-frozen evaluation trades / quarter tables only:

### Negative-quarter concentration

For quarters with net PnL < 0:

- worst-1 negative-quarter loss share;
- worst-3 negative-quarter loss share;
- worst-5 negative-quarter loss share;
- number of negative quarters;
- total absolute negative-quarter PnL.

Denominator is the SUM OF ABSOLUTE LOSSES from negative quarters only.

Do not divide by net PnL.

### Negative-year concentration

For complete calendar years 2019-2025 with net PnL < 0:

- worst-1 negative-year loss share;
- worst-3 negative-year loss share;
- number of negative complete years;
- total absolute negative-year PnL.

### Trade-level loss tail

Among losing evaluation trades only:

- losing trade count;
- median absolute losing-trade loss;
- mean absolute losing-trade loss;
- 95th percentile absolute loss;
- 99th percentile absolute loss;
- mean of worst 5% absolute losing-trade losses (`loss_cvar95_abs_usd`);
- worst 1% losing-trade share of total losing-trade loss pool;
- worst 5% losing-trade share of total losing-trade loss pool;
- largest single-trade absolute loss;
- largest-loss / median-loss ratio when denominator > 0.

These are DIAGNOSTICS, not new hard gates.

## PART B — H226 DAILY REOPEN GAP EVENT STUDY

No trading engine is called.

### Base event

A candidate daily-gap event occurs on bar `i` when canonical UTC date differs from bar `i-1`.

Definitions:

- `prev_close = close[i-1]`
- `gap = open[i] - prev_close`
- `gap_direction = sign(gap)`
- `ATR_prev = ATR14 available at i-1`
- `gap_z = abs(gap) / ATR_prev`

Require finite positive ATR and nonzero gap.

### Exact H226 signal-close semantics

H226 strategy signal was evaluated at CLOSE of the first UTC-day bar `i`.

The event is in a frozen H226 trigger cohort only if:

1. gap threshold passes;
2. first bar did NOT already close through / beyond prior close;
3. `residual = abs(close[i] - prev_close) / abs(gap)` passes the cohort threshold.

Frozen cohorts reproduce the exact V3.8 H226 configurations:

- `H226-C1`: gap_z >= 0.05 and residual >= 0.25
- `H226-C2`: gap_z >= 0.10 and residual >= 0.25
- `H226-C3`: gap_z >= 0.05 and residual >= 0.50
- `H226-C4`: gap_z >= 0.10 and residual >= 0.50

These cohorts are diagnostic reproductions of frozen definitions. They are NOT parameter searches.

Also retain an `ALL_DAILY_GAPS` descriptive cohort with no H226 threshold, but do not use it to rescue H226.

### Reference and forward horizons

Reference information time is first-day-bar close `close[i]`.

Entry-proxy price for path measurement is next bar open `open[i+1]`, matching the earliest price available after the signal close under the frozen next-open convention.

Forward horizons from the entry-proxy bar:

- +30m = 1 bar
- +1h = 2 bars
- +2h = 4 bars
- +4h = 8 bars
- +8h = 16 bars

Require sufficient future bars for each horizon independently.

### Signed reversion return

`reversion_sign = -sign(gap)`

For horizon H:

`signed_reversion_return_atr = reversion_sign * (close[end_H] - entry_proxy) / ATR_prev`

Positive values mean movement in the gap-reversion direction.

### Gap closure

A gap is considered closed by a horizon if the observed high/low path from bars `i+1 ... end_H` touches or crosses `prev_close`.

### Horizon-specific MFE / MAE

Compute separately for every horizon from the entry-proxy price using actual high/low path:

- MFE_ATR in reversion direction;
- MAE_ATR against reversion direction.

No stop, target, or fill rule is applied.

### Tail diagnostics per cohort/horizon

Compute:

- event count;
- mean signed reversion return;
- median signed reversion return;
- probability signed return > 0;
- 10th / 25th / 75th / 90th percentiles;
- mean MFE_ATR;
- mean MAE_ATR;
- median MFE_ATR;
- median MAE_ATR;
- gap-closure probability;
- worst 5% mean signed return (left-tail CVaR-like diagnostic).

## TEMPORAL STABILITY

For H226-C1 through C4 at +2h and +4h, report:

- annual event count and mean signed return for complete years 2019-2025;
- quarterly event count and mean signed return for 2018Q2-2026Q2;
- percent complete years with positive mean;
- worst year;
- best year.

No quiet year/quarter may be excluded.

## QUARTER-BLOCK BOOTSTRAP

For H226-C1 through C4 and horizons +1h, +2h, +4h, +8h:

- 2000 bootstrap replications;
- fixed seed `390226`;
- resampling unit = calendar quarter;
- sample quarters with replacement;
- preserve all events inside each selected quarter;
- statistic = mean signed reversion return ATR;
- report 2.5% / 97.5% percentile CI and P(mean > 0).

Do not use IID bootstrap as the primary inference.

## LOSS-TAIL EXPLANATION CHECK

For each H226 cohort, mechanically report these descriptive booleans at +4h:

- `mean_reversion_positive`
- `median_reversion_positive`
- `block_ci_excludes_zero_positive`
- `positive_years_at_least_4_of_7`
- `gap_closure_probability_gt_50pct`
- `left_tail_abs_exceeds_mean_magnitude`

The last condition is true when absolute value of worst-5%-mean signed return exceeds absolute mean signed return.

These are diagnostics, not strategy gates.

## FROZEN MECHANISM LABEL

The H226 mechanism label is determined using H226-C1 and H226-C4 only, because these were the two V3.8 configs with the largest gate pass count (10/14) BEFORE this audit.

No post-result cohort may replace them.

At the +2h and +4h horizons:

### `H226 GAP-REVERSION MECHANISM DESCRIPTIVELY SUPPORTED — STRATEGY STILL REJECTED`

Only if BOTH C1 and C4 satisfy ALL:

- mean signed reversion > 0 at +2h and +4h;
- median signed reversion > 0 at +2h and +4h;
- quarter-block 95% CI lower bound > 0 at +2h and +4h;
- at least 4 of 7 complete years have positive +4h mean.

### `H226 GAP-REVERSION MECHANISM WEAK / TAIL-UNSTABLE — STRATEGY STILL REJECTED`

If descriptive means are positive at either +2h or +4h for BOTH C1 and C4, but the full support rule above is not satisfied.

### `H226 GAP-REVERSION MECHANISM NOT SUPPORTED — STRATEGY REJECTED`

Otherwise.

No label authorizes strategy redesign.

## REQUIRED MACHINE OUTPUTS

`AlphaLab_Antigravity/reports/v3_9/`

- `v3_9_loss_concentration_all_configs.csv`
- `v3_9_h226_event_summary.csv`
- `v3_9_h226_events.csv`
- `v3_9_h226_year_stability.csv`
- `v3_9_h226_quarter_stability.csv`
- `v3_9_h226_block_bootstrap.csv`
- `v3_9_h226_mechanism_decision.json`
- `v3_9_metadata.json`

Human report is generated only after raw artifacts are committed:

`V3_9_LOSS_TAIL_MECHANISM_REPORT.md`

## STOP RULE

After V3.9:

- do not create H227;
- do not tune H226;
- do not add a gap-size filter;
- do not change residual thresholds;
- do not change SL/TP/RR;
- do not remove a direction;
- do not run another asset/timeframe;
- do not start a new strategy batch automatically.

Return evidence for independent audit.
