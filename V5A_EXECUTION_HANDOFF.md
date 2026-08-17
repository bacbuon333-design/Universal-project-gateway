# V5-A Independent Alpha RR1 Discovery — Execution Handoff

## Role separation

The Independent Research Designer has frozen the V5-A design. The executor acts only as sequential executor, recorder, and auditor.

ONE AGENT ONLY. No `/goal`, subagents, teams, delegation, parallel instances, or hypothesis redesign.

The exact branch HEAD containing this handoff is the Initial Frozen HEAD. The executor receives that SHA out-of-band and must verify exact equality before any compile, test, or experiment command.

## Required frozen files

- `V5A_INDEPENDENT_ALPHA_RR1_PRECOMMIT.md`
- `V5A_EXECUTION_HANDOFF.md`
- `AlphaLab_Antigravity/src/run_v5a_independent_alpha_rr1.py`
- `AlphaLab_Antigravity/src/test_v5a_independent_alpha_rr1.py`
- `AlphaLab_Antigravity/src/generate_v5a_independent_alpha_rr1_report.py`

Read the precommit completely before execution.

## Step 1 — Git governance

Verify:
- repository: `bacbuon333-design/Universal-project-gateway`;
- branch: `research/quant-v5a-independent-alpha-rr1`;
- exact Initial Frozen HEAD supplied by designer;
- clean working tree.

If branch, HEAD, or cleanliness differs: STOP BLOCKED. Do not repair, reset, cherry-pick, merge, or improvise.

## Step 2 — Static compile

Compile exactly:

```bash
python -m py_compile AlphaLab_Antigravity/src/run_v5a_independent_alpha_rr1.py
python -m py_compile AlphaLab_Antigravity/src/test_v5a_independent_alpha_rr1.py
python -m py_compile AlphaLab_Antigravity/src/generate_v5a_independent_alpha_rr1_report.py
```

Record Python version and OS.

If compile fails: STOP. Do not patch and continue this experiment run.

## Step 3 — Frozen tests

Run exactly:

```bash
python AlphaLab_Antigravity/src/test_v5a_independent_alpha_rr1.py
```

Expected frozen suite: exactly 19 tests, all PASS.

The suite freezes:
- 4 families / 4 configs only;
- scientific parent and canonical authority;
- common RR1 risk/cost contract;
- exact 14-gate evaluator and 2018Q2-2026Q2 sample;
- canonical next-bar / pessimistic execution contract;
- no fresh-OOS or H226 reuse;
- no H301-H304 implementation reuse;
- no dynamic grid / Batch 2;
- causal H401 prior extrema;
- H402 inside-bar mother-range semantics;
- H403 body-engulf semantics;
- H404 two-right-bar pivot confirmation;
- raw-result overwrite refusal;
- fail-closed governance flags.

If any test fails: STOP. Do not run the experiment and do not patch in the same run.

## Step 4 — Technical-repair policy

This handoff is stricter than V4.

If a syntax/import/path/serialization/test-runner/API-compatibility defect is found, terminate the current execution run and return the defect to the designer. Any repair must be committed in a separate repair/freeze cycle, producing a new clean Frozen HEAD before another executor run.

Any change touching hypothesis definition, configuration, signal timing, ATR/risk, cost, execution semantics, evaluation sample/window, 14-gate thresholds, multiple-testing budget, or closed-research exclusions is a scientific change and requires a new precommit chapter/revision.

## Step 5 — Run frozen V5-A exactly once

Only after Step 1-3 are clean and PASS:

```bash
python AlphaLab_Antigravity/src/run_v5a_independent_alpha_rr1.py
```

Do not rerun because outcomes are surprising or inconvenient. The runner refuses raw-result overwrite by design.

Expected raw artifact:

`AlphaLab_Antigravity/reports/v5a/V5A_INDEPENDENT_ALPHA_RR1_RESULTS.json`

No human-readable V5-A result report may be generated before the raw artifact is audited and committed.

## Step 6 — Raw result audit and raw-evidence commit FIRST

Verify raw JSON contains:
- chapter `V5A_INDEPENDENT_ALPHA_RR1_DISCOVERY`;
- scientific parent commit `5a1a2f8c28f857789943295f6a59df2f1037e72b`;
- canonical SHA `c48ca44dcecae9eb1c2590c586e27c4bc5f246215c549d0d0bc1201d95d5ea1d`;
- execution contract `CANONICAL_V2_GAP_SAFE_V3_7_3`;
- evaluator contract `V3_8_WRAPPER_OVER_V3_5_FULL_14_GATES`;
- exactly 4 configs and exactly 4 families;
- IDs in exact order: `H401-C1`, `H402-C1`, `H403-C1`, `H404-C1`;
- common `SL=1.5 ATR`, `TP=1.5 ATR`, `risk_reward=1:1`;
- frozen cost contract;
- exact evaluation window counts: 33 quarters, 7 full years, 30 rolling-4, 26 rolling-8;
- all 14 gate booleans per config;
- `all_gates_pass` is exactly the 14-gate conjunction;
- fresh-OOS/H226/V4-reuse/governance authorization flags remain false.

Commit RAW EVIDENCE ONLY. Suggested message:

`feat(v5a): record frozen RR1 independent alpha results`

Record raw-result commit SHA.

The raw-evidence commit must not modify any `.py`, precommit, handoff, evaluator, engine, canonical dataset, or prior research artifact.

## Step 7 — Generate report and commit SECOND

Only after raw-evidence commit:

```bash
python AlphaLab_Antigravity/src/generate_v5a_independent_alpha_rr1_report.py
```

Expected report:

`V5A_INDEPENDENT_ALPHA_RR1_REPORT.md`

Commit report separately. Suggested message:

`docs(v5a): publish RR1 independent alpha conclusion`

The report commit must contain the report only and no scientific code edits.

## Step 8 — Verify commit topology

Verify the final branch lineage is exactly:

`Initial Frozen HEAD -> raw-evidence commit -> final-report commit`

No repair/source/config commit may occur between these three states.

## Classification

A configuration passes only if all 14 frozen gates pass.

Any gate failure => `REJECTED`.

All 14 gates pass => `HISTORICAL_CANDIDATE_ONLY`.

If zero survivors, exact conclusion:

`NO V5-A CONFIGURATION PASSED ALL FROZEN DISTRIBUTED-EDGE GATES`

If one or more survivors, exact conclusion:

`V5-A HISTORICAL CANDIDATE(S) IDENTIFIED — INDEPENDENT VALIDATION REQUIRED`

No survivor is validated alpha. No survivor authorizes tuning, fresh-OOS peeking, paper trading, deployment, or live trading.

## Final executor response

Return:
- repository;
- branch;
- Initial Frozen HEAD;
- Python version and OS;
- compile result;
- frozen tests result, expected `19/19`;
- canonical SHA and execution contract;
- scientific parent commit;
- raw-result commit SHA;
- final report commit SHA;
- verified three-node topology;
- 4 families / 4 configs;
- common risk contract and costs;
- for each config: ID, family, params, total trades, PF, expectancy USD, net PnL USD, min trades/quarter, max-quarter share, max/median quarterly count, quarterly Gini, top-3 and top-5 positive-quarter PnL shares, rolling-4 positive %, rolling-4 PF>=1.20 %, rolling-8 positive %, rolling-8 PF>=1.20 %, min full-year trades, profitable-year %, gates passed/14, primary failure, final status;
- survivor IDs;
- exact batch conclusion;
- `FRESH OOS ACCESSED: false`;
- `H226 REUSED: false`;
- `V4 H301-H304 REUSED: false`;
- `CLOSED RESEARCH MODIFIED: false`;
- `CLOSED RESEARCH DESCENDANT CREATED: false`;
- `STRATEGY DESIGN AUTHORIZED FOR DEPLOYMENT: false`;
- `PAPER TRADING AUTHORIZED: false`;
- `LIVE TRADING AUTHORIZED: false`.

Then STOP. Do not create V5-B, Batch 2, tune a failure, alter RR/cost/gates, access fresh OOS, or move toward paper/live execution.
