# V5-A RR 1:1 Independent Alpha Discovery — Execution Handoff

## Role separation

The Independent Research Designer has frozen V5-A. The Executor acts only as sequential executor, recorder, and auditor.

ONE AGENT ONLY. No `/goal`, subagents, teams, delegation, parallel instances, or hypothesis redesign.

The exact branch HEAD containing this handoff is the Initial Frozen HEAD. The executor must be given that SHA out-of-band and verify exact equality before any compile, test, or scientific experiment command.

## Required frozen files

- `V5A_RR1_INDEPENDENT_ALPHA_DISCOVERY_PRECOMMIT.md`
- `V5A_EXECUTION_HANDOFF.md`
- `AlphaLab_Antigravity/src/run_v5a_rr1_independent_alpha_discovery.py`
- `AlphaLab_Antigravity/src/test_v5a_rr1_independent_alpha_discovery.py`
- `AlphaLab_Antigravity/src/generate_v5a_rr1_independent_alpha_report.py`

Read the precommit completely before execution.

## Step 1 — Git and provenance governance

Verify:
- repository `bacbuon333-design/Universal-project-gateway`;
- branch `research/quant-v5a-rr1-independent-alpha-discovery`;
- exact Initial Frozen HEAD supplied by designer;
- scientific parent is exactly `5a1a2f8c28f857789943295f6a59df2f1037e72b`;
- working tree is clean;
- parent-to-Frozen-HEAD diff contains only V5-A design/source/test/report-generator/handoff files and does not modify V4, H226, canonical data, engines, evaluator thresholds, or fresh-OOS artifacts.

If branch, HEAD, parent, cleanliness, or diff scope differs: STOP BLOCKED.

## Step 2 — Independence audit before any experiment

Audit the V5-A runner against V4 and closed H226 lineage.

Confirm V5-A does not reuse the semantic entry logic of:
- H301 prior-channel compression breakout;
- H302 fixed UTC session-range breakout;
- H303 EMA24/EMA96 pullback recapture;
- H304 rolling z-score exhaustion re-entry;
- H226 daily-gap / delayed-reversion lineage.

The only permitted reuse is infrastructure: canonical execution engine, canonical data authority, ATR utility semantics, evaluation preparation, and frozen 14-gate evaluator.

Confirm exactly four new families and one fixed configuration per family:
- H401-C1 / H401_IBC;
- H402-C1 / H402_WFR;
- H403-C1 / H403_TBAR;
- H404-C1 / H404_OBCC.

Confirm there is no parameter grid, alternative threshold set, automatic Batch 2, or post-hoc rescue path.

If semantic reuse or testing-budget drift is found: STOP BLOCKED.

## Step 3 — Static compile

Compile exactly:

```bash
python -m py_compile AlphaLab_Antigravity/src/run_v5a_rr1_independent_alpha_discovery.py
python -m py_compile AlphaLab_Antigravity/src/test_v5a_rr1_independent_alpha_discovery.py
python -m py_compile AlphaLab_Antigravity/src/generate_v5a_rr1_independent_alpha_report.py
```

Record Python version and OS.

## Step 4 — Frozen tests

Run exactly:

```bash
python AlphaLab_Antigravity/src/test_v5a_rr1_independent_alpha_discovery.py
```

Expected frozen suite: 23 tests, all PASS.

The tests must verify, among other invariants:
- exact scientific parent and canonical SHA;
- canonical next-bar/gap-safe execution contract;
- exact 33-quarter / 7-year / rolling-4 / rolling-8 evaluation structure;
- exact 14 gate names and thresholds;
- exact four-family/four-config testing budget;
- exactly SL 1.50 ATR and TP 1.50 ATR, R:R 1:1;
- frozen cost convention;
- no V4 H301-H304 entry-function reuse;
- no H226 delayed-gap semantics;
- no fresh-OOS path;
- overwrite guard;
- deterministic signal fixtures for H401-H404.

If any test fails: DO NOT run the experiment.

## Step 5 — Technical repair policy: mandatory run boundary

Allowed technical repair scope before scientific execution only:
- syntax;
- import;
- path;
- serialization;
- test-runner plumbing;
- API compatibility that provably leaves all scientific semantics unchanged.

If any technical repair is needed:
1. STOP before scientific execution.
2. Make only the permitted technical repair.
3. Commit that repair separately.
4. Return the new clean HEAD and a precise diff summary.
5. END THE CURRENT EXECUTOR RUN.

Do not continue into acquisition/backtest/scientific execution in the same run, even if compile/tests pass after the repair.

A NEW executor run must start from the repaired HEAD, treating that exact SHA as the new Frozen HEAD and repeating provenance, compile, and all 23 tests.

Any proposed change touching hypothesis definition, threshold, signal timing, ATR/risk, RR, cost, execution semantics, evaluation sample/window, any 14-gate threshold, multiple-testing budget, or fresh-OOS boundary is scientific: STOP BLOCKED and return to designer. Do not repair it yourself.

## Step 6 — Run the frozen scientific batch exactly once

Only if Steps 1-5 pass with zero repair in the current run:

```bash
python AlphaLab_Antigravity/src/run_v5a_rr1_independent_alpha_discovery.py
```

Do not rerun because results are surprising. The runner refuses raw-result overwrite by design.

Expected raw artifact:

`AlphaLab_Antigravity/reports/v5a/V5A_RR1_INDEPENDENT_ALPHA_DISCOVERY_RESULTS.json`

No human-readable report may be generated yet.

After this command begins, no source/test/precommit/handoff/evaluator/engine edits are permitted in the chapter.

## Step 7 — Raw result audit and commit FIRST

Verify raw JSON contains:
- exact scientific parent;
- exact canonical SHA;
- `CANONICAL_V2_GAP_SAFE_V3_7_3` execution contract;
- `V3_8_WRAPPER_OVER_V3_5_FULL_14_GATES` evaluator contract;
- exactly 4 configs / 4 families / 1 config per family;
- common fixed `SL=1.5 ATR`, `TP=1.5 ATR`, `RR=1:1` contract;
- spread argument 25.0 GOLD engine pip-units with `pip_size=0.01`, spread-price 0.25 USD/oz;
- all 14 gate booleans for every config;
- `all_gates_pass` equal to the conjunction of all 14 gates;
- governance flags false;
- no fresh-OOS outcome or path.

Commit RAW EVIDENCE ONLY. Suggested message:

`feat(v5a): record frozen RR1 independent alpha results`

Record raw-result commit SHA.

No source, test, handoff, precommit, evaluator, engine, or report file may be changed in the raw-result commit.

## Step 8 — Generate and commit report SECOND

Only after the raw-result commit:

```bash
python AlphaLab_Antigravity/src/generate_v5a_rr1_independent_alpha_report.py
```

Expected report:

`V5A_RR1_INDEPENDENT_ALPHA_DISCOVERY_REPORT.md`

Commit REPORT ONLY in a separate commit. Suggested message:

`docs(v5a): publish RR1 independent alpha discovery conclusion`

No scientific/source code edit is allowed after results.

## Classification

A configuration passes only if ALL 14 frozen gates pass.

Any gate failure => `REJECTED`.

All 14 gates pass => `HISTORICAL_CANDIDATE_ONLY`.

If zero survivors, exact conclusion:

`NO V5-A CONFIGURATION PASSED ALL FROZEN DISTRIBUTED-EDGE GATES`

If one or more survivors, exact conclusion:

`V5-A HISTORICAL CANDIDATE(S) IDENTIFIED — INDEPENDENT VALIDATION REQUIRED`

No survivor is validated alpha or authorized for parameter refinement, fresh-OOS peeking, paper trading, deployment, or live trading.

## Final executor response

Return:
- repository;
- branch;
- Initial Frozen HEAD;
- scientific parent;
- parent-to-Frozen-HEAD diff audit;
- technical repair SHA if any; if a repair occurred, confirm the run STOPPED before scientific execution;
- raw-result commit SHA, if scientific execution occurred;
- final report commit SHA, if report generation occurred;
- Python version and OS;
- canonical SHA and execution contract;
- compile result;
- frozen tests result (expected 23/23);
- independence audit result for H301-H304 and H226;
- fixed RR1 risk/cost contract;
- 4 families / 4 configs;
- for every config: ID, family, trade count, PF, expectancy USD, net PnL USD, minimum trades/quarter, minimum trades/complete-year, rolling-4 positive %, rolling-4 PF>=1.20 %, rolling-8 positive %, rolling-8 PF>=1.20 %, profitable-year %, concentration metrics/gates, gates passed /14, final status;
- survivor IDs;
- exact batch conclusion;
- `FRESH OOS ACCESSED: false`;
- `CLOSED RESEARCH MODIFIED: false`;
- `CLOSED RESEARCH DESCENDANT CREATED: false`;
- `V4 FAILED ENTRY SEMANTICS REUSED: false`;
- `H226 LINEAGE REUSED: false`;
- `STRATEGY DESIGN AUTHORIZED FOR DEPLOYMENT: false`;
- `LIVE TRADING AUTHORIZED: false`.

Then STOP.

Do not create V5-A.1, Batch 2, tune failures, alter thresholds/RR/costs, access fresh OOS, modify closed research, switch asset/timeframe, paper trade, or live trade.
