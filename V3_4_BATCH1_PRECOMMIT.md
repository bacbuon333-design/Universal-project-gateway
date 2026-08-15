# V3.4 BATCH-1 PRECOMMIT — H-215 TO H-217 DIRECTIONAL FOLLOW-UP

## Status

This document is the immutable pre-execution specification for V3.4 Batch 1.

- Repository: `bacbuon333-design/Universal-project-gateway`
- Branch: `research/quant-v3.4-h215-directional-followup`
- Artifact generation parent SHA: `f5b9748995666fe9174d82084239d13e9b316b41`
- Parent research state: V3.3.1 repaired Batch-1 audit is closed; no H-209→H-214 configuration passed the Distributed Edge Standard.
- Instrument / timeframe: `GOLD_M30.csv`
- Authoritative evaluation window: entry quarter `2018Q2` through `2026Q2`, inclusive; 33 complete quarters.
- Baseline execution: fixed lot `0.10`, spread `25.0` pips, commission `$7.00/lot`, slippage `0.0` pips, pessimistic ambiguous-bar handling, one active position at a time, signal at bar i close and execution at bar i+1 open.

The actual Git SHA of this precommit must be read from Git after commit. Do not type or predict it inside this artifact.

---

## 1. SCIENTIFIC MOTIVATION AND CONTAMINATION DISCLOSURE

V3.3/V3.3.1 observed that some momentum-like families, especially H-213 and portions of H-214, had stronger historical Long diagnostics than Short diagnostics. H-209 also showed a weaker Long-over-Short tendency in several configurations.

This observation was made **after looking at historical results**. Therefore it is contaminated research knowledge and is **not validation evidence**.

V3.4 asks a new, explicitly post-hoc exploratory question:

> If the already-frozen causal signal mechanisms are converted into Long-only systems, while every numerical signal/exit parameter remains unchanged, do they naturally retain sufficient opportunity density and produce distributed historical economics under the same hard gates?

A V3.4 survivor may only be called a **HISTORICAL DIRECTIONAL SURVIVOR — REQUIRES STABILITY BATCH**. It is not validated alpha and is not true OOS evidence.

---

## 2. ABSOLUTE NO-RESCUE RULE

V3.4 Batch 1 is NOT permission to repair V3.3 losers.

Forbidden after this precommit:

- changing channel length;
- changing EMA length;
- changing ATR lookbacks;
- changing thresholds;
- changing SL or TP;
- adding/removing regime filters;
- changing session rules;
- changing timeframe;
- adding a trailing stop;
- changing position concurrency;
- lowering any hard gate;
- tuning a failed quarter;
- adding configurations after results are observed;
- testing Short-only variants in this same batch;
- selecting only the best configuration after seeing Batch-1 results and calling it validated.

The ONLY structural change versus the corresponding V3.3 family is:

`all Short signals are deterministically masked to zero before execution.`

The underlying Long signal, SL distance, and TP distance remain exactly those of the frozen V3.3.1 functions.

---

## 3. H-215 — LONG-ONLY MEDIUM-RANGE LOCATION + MOMENTUM (MRLM-L)

Source mechanism: frozen H-213 `make_h213_signals`.

Economic question:

> Does positive momentum near the upper region of a medium-term price range create a sufficiently persistent Long-side historical effect when Short trades are removed as a newly precommitted directional hypothesis?

Exact rule:

1. Generate the original H-213 signals exactly.
2. Preserve every `+1` Long signal with its original SL/TP distances.
3. Convert every `-1` Short signal to `0` and zero its SL/TP output.
4. No other change.

Configurations:

| ID | Frozen source parameters | Direction |
|---|---|---|
| `H-215-C1` | H-213-C1: Channel 50, upper/lower 0.75/0.25, SL 1.5 ATR, TP 3.0 ATR | Long-only |
| `H-215-C2` | H-213-C2: Channel 50, upper/lower 0.75/0.25, SL 1.5 ATR, TP 3.75 ATR | Long-only |
| `H-215-C3` | H-213-C3: Channel 100, upper/lower 0.80/0.20, SL 1.5 ATR, TP 3.0 ATR | Long-only |
| `H-215-C4` | H-213-C4: Channel 100, upper/lower 0.80/0.20, SL 1.5 ATR, TP 3.75 ATR | Long-only |

---

## 4. H-216 — LONG-ONLY VOLATILITY REGIME ACCELERATION (VRA-L)

Source mechanism: frozen H-214 `make_h214_signals`.

Economic question:

> During causal volatility acceleration plus breakout conditions, does the Long continuation leg exhibit a distributed historical edge when evaluated as its own newly frozen system?

Exact rule:

1. Generate the original H-214 signals exactly.
2. Preserve every `+1` Long signal and original SL/TP distances.
3. Convert every `-1` Short signal to `0` and zero its SL/TP output.
4. No other change.

Configurations:

| ID | Frozen source parameters | Direction |
|---|---|---|
| `H-216-C1` | H-214-C1: ATR7/ATR28 > 1.20, 3-bar breakout, EMA50, SL 1.5 ATR, TP 3.0 ATR | Long-only |
| `H-216-C2` | H-214-C2: ATR7/ATR28 > 1.20, 3-bar breakout, EMA50, SL 1.5 ATR, TP 3.75 ATR | Long-only |
| `H-216-C3` | H-214-C3: ATR7/ATR28 > 1.30, 3-bar breakout, EMA50, SL 1.5 ATR, TP 3.0 ATR | Long-only |
| `H-216-C4` | H-214-C4: ATR7/ATR28 > 1.30, 3-bar breakout, EMA50, SL 1.5 ATR, TP 3.75 ATR | Long-only |

---

## 5. H-217 — LONG-ONLY MULTI-HORIZON TREND PERSISTENCE CONTROL (MHTP-L)

Source mechanism: frozen H-209 `make_h209_signals`.

Purpose:

H-217 is deliberately included as a weaker directional-control family so the batch does not only cherry-pick H-213/H-214. It asks whether any Long-side improvement is broadly present in another trend/momentum family rather than uniquely appearing in the two strongest post-hoc diagnostics.

Exact rule:

1. Generate original H-209 signals exactly.
2. Preserve every `+1` Long signal and original SL/TP distances.
3. Convert every `-1` Short signal to `0` and zero its SL/TP output.
4. No other change.

Configurations:

| ID | Frozen source parameters | Direction |
|---|---|---|
| `H-217-C1` | H-209-C1: EMA50/100 + EMA20 pullback, SL 1.5 ATR, TP 3.0 ATR | Long-only |
| `H-217-C2` | H-209-C2: EMA50/100 + EMA20 pullback, SL 1.5 ATR, TP 3.75 ATR | Long-only |
| `H-217-C3` | H-209-C3: EMA50/100 + EMA20 pullback, SL 2.0 ATR, TP 4.0 ATR | Long-only |
| `H-217-C4` | H-209-C4: EMA50/100 + EMA20 pullback, SL 2.0 ATR, TP 5.0 ATR | Long-only |

Total Batch-1 research budget: **12 configurations. No dynamic expansion.**

---

## 6. AUTHORITATIVE EVALUATION POPULATION

A realized trade belongs to the quarter of its **entry time**.

Include only trades with:

`2018Q2 <= entry_quarter <= 2026Q2`

Exclude 2018Q1 and 2026Q3.

A trade entering in 2026Q2 and exiting in 2026Q3 remains a 2026Q2 evaluation trade.

Every candidate metric must be rebuilt from this same evaluation population. Never use a full-engine summary that contains trades outside the window.

---

## 7. FROZEN HARD DISTRIBUTED-EDGE GATES

All gates must pass simultaneously.

### A — Opportunity / trade distribution

- `A1`: minimum trades in every complete quarter >= 5.
- `A2`: maximum single-quarter trade share <= 5.0%.
- `A3`: max quarterly trade count / median quarterly trade count <= 3.0.
- `A4`: quarterly trade-count Gini < 0.30.

### B — Profit distribution

Define `positive_quarter_pnl = max(quarter_net_pnl, 0)`.

Denominator = sum of positive-quarter PnL only.

- `B1`: Top-3 positive-quarter PnL share <= 40.0%.
- `B2`: Top-5 positive-quarter PnL share <= 60.0%.

If there is no positive-quarter profit pool, B1 and B2 fail.

### D — Rolling robustness

Across exactly 30 overlapping 4-quarter windows:

- `D1`: >= 70.0% of rolling-4Q windows have positive net PnL.
- `D2`: >= 65.0% of rolling-4Q windows have PF >= 1.20.

These are stability diagnostics/gates, not independent statistical tests.

### E — Economics

From evaluation trades only:

- `E1`: PF >= 1.25.
- `E2`: mean net expectancy > $0.

Baseline costs remain exactly spread 25.0 pips, commission $7.00/lot, slippage 0.0 pips.

---

## 8. ADDITIONAL REQUIRED DIAGNOSTICS — NOT NEW HARD GATES

For every configuration report:

- total trades;
- min / P10 / P25 / median / mean / P75 / P90 / max quarterly trades;
- CV and Gini;
- top1 / top3 / top5 / top10 positive-quarter PnL shares;
- net PnL / PF / expectancy / win rate;
- rolling-4Q individual windows;
- profitable calendar-year count;
- best-quarter and best-year contribution;
- best-trade / top3 / top5 trade contribution relative to total positive trade PnL;
- comparison against the corresponding frozen symmetric V3.3.1 configuration as **diagnostic context only**.

Do not use non-precommitted diagnostics to override a failed hard gate.

---

## 9. INTERPRETATION RULES

Because Long-only direction was motivated by already-observed historical asymmetry:

- a pass is exploratory historical evidence, not validation;
- no p-value or probability-of-alpha claim is allowed;
- do not say Gold has a universal Long bias;
- do not say Short removal proves a causal mechanism;
- do not call a survivor true/proven/validated alpha.

Allowed final statuses:

- `REJECTED`
- `HISTORICAL DIRECTIONAL SURVIVOR — REQUIRES STABILITY BATCH`
- `INVALID — EXECUTION OR SPECIFICATION FAILURE`

---

## 10. RESULT GOVERNANCE

The implementation must be committed separately after this precommit.

After implementation is frozen:

1. run tests;
2. run exactly 12 configurations;
3. save raw trade / quarter / rolling files;
4. save one authoritative machine-readable summary;
5. commit raw results separately;
6. generate report from the authoritative summary;
7. commit report separately;
8. STOP.

If a code defect is discovered before/during execution, do not silently edit and continue. Document it and stop for audit unless the repair is purely implementation-level and can be committed before any valid result is interpreted.

---

## 11. STOP RULE

After Batch 1, do not automatically:

- create H-218+;
- optimize the strongest H-215/H-216/H-217 configuration;
- run another timeframe;
- run another asset;
- add slippage stress;
- change RR;
- run a stability grid.

Return the evidence for independent audit first.
