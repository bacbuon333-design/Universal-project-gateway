# V3.9 EXECUTION HANDOFF

## Role

Single executor + evidence recorder only.

No `/goal`, subagents, delegation, teams, or parallel model instances.

## Repository

`bacbuon333-design/Universal-project-gateway`

Branch:

`research/quant-v3.9-loss-tail-mechanism-audit`

Scientific parent:

`635258edb87da39cb3bd1a599bec2f6c94a0b477`

## Read first

- `V3_9_LOSS_TAIL_MECHANISM_PRECOMMIT.md`
- `AlphaLab_Antigravity/src/audit_v3_9_loss_tail_and_h226_event.py`
- `AlphaLab_Antigravity/src/test_v3_9_loss_tail_mechanism.py`
- `AlphaLab_Antigravity/src/generate_v3_9_report.py`

## Execution order

1. verify exact branch / HEAD / clean tree;
2. compile the three V3.9 Python files;
3. run the frozen V3.9 tests;
4. only if all tests pass, run the V3.9 audit exactly once;
5. inspect machine artifacts without editing them;
6. commit raw artifacts;
7. run report generator only after raw commit exists;
8. commit human report separately;
9. STOP.

## Frozen test expectation

Exactly 14 tests.

Technical repairs are limited to syntax/import/path/serialization/test-runner plumbing. Any change to event definitions, H226 cohorts, horizons, bootstrap, loss formulas, mechanism-label rules, canonical authority, or V3.8 inputs requires STOP and return to independent designer.

## Audit command

`python AlphaLab_Antigravity/src/audit_v3_9_loss_tail_and_h226_event.py`

The audit is read-only with respect to strategy research. It must not call a trading engine or `run_strategy`.

## Expected raw artifact dimensions

- `v3_9_loss_concentration_all_configs.csv`: exactly 24 config rows;
- `v3_9_h226_event_summary.csv`: expected 25 rows = 5 cohorts x 5 horizons if every frozen cohort has events;
- `v3_9_h226_year_stability.csv`: exactly 56 rows = 4 H226 cohorts x 2 horizons x 7 years;
- `v3_9_h226_quarter_stability.csv`: exactly 264 rows = 4 x 2 x 33 quarters;
- `v3_9_h226_block_bootstrap.csv`: exactly 16 rows = 4 cohorts x 4 horizons;
- `v3_9_h226_events.csv`: variable row count, must be non-empty;
- `v3_9_h226_mechanism_decision.json`: one machine decision;
- `v3_9_metadata.json`: frozen lineage / governance metadata.

If the event summary has fewer than 25 rows because a frozen cohort genuinely has zero events, do not fabricate data. Report the zero-event condition and STOP before final scientific classification because the precommitted decision would be underidentified.

## Required invariants

- canonical dataset ID = `GOLD_M30_CANONICAL_V2`;
- canonical SHA = `c48ca44dcecae9eb1c2590c586e27c4bc5f246215c549d0d0bc1201d95d5ea1d`;
- V3.8 strategy conclusion remains frozen;
- V3.8 config count audited = 24;
- strategy executed = false;
- trading engine called = false;
- H226 cohorts are exactly C1-C4 frozen V3.8 definitions;
- mechanism decision cohorts are C1 and C4;
- bootstrap reps = 2000;
- bootstrap seed = 390226.

## Allowed mechanism labels

Exactly one:

- `H226 GAP-REVERSION MECHANISM DESCRIPTIVELY SUPPORTED — STRATEGY STILL REJECTED`
- `H226 GAP-REVERSION MECHANISM WEAK / TAIL-UNSTABLE — STRATEGY STILL REJECTED`
- `H226 GAP-REVERSION MECHANISM NOT SUPPORTED — STRATEGY REJECTED`

No manual override.

## Raw commit

Suggested message:

`feat(v3.9): execute loss-tail and H226 event-study audit`

Record actual SHA.

## Human report

Only after raw commit:

`python AlphaLab_Antigravity/src/generate_v3_9_report.py`

Expected:

`V3_9_LOSS_TAIL_MECHANISM_REPORT.md`

Suggested report commit:

`docs(v3.9): publish loss-tail and H226 mechanism conclusion`

## Final response

Return:

- repository / branch;
- initial frozen HEAD;
- technical repair SHA if any;
- raw audit SHA;
- final report SHA;
- Python / OS;
- test result out of 14;
- all artifact row counts;
- canonical ID / SHA;
- strategy executed = false;
- trading engine called = false;
- for H226-C1/C4: V3.8 PF / expectancy / R8-positive / profitable-year %, negative-quarter concentration, worst 1% and 5% losing-trade shares;
- for H226-C1/C4 at +2h/+4h: N, mean, median, positive %, gap closure %, worst-5% mean, block CI, P(mean>0), positive complete years / 7;
- final frozen mechanism label;
- explicit statement that all H226 strategies remain REJECTED.

## Stop

Do not create H227, tune H226, add filters, modify RR/SL/TP, remove a direction, change asset/timeframe, or begin a new strategy chapter.
