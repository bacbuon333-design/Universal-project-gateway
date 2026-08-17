# V4 Independent Alpha Discovery — Execution Handoff

## Role separation

Independent Research Designer has frozen the design. Executor acts only as sequential executor, recorder, and auditor.

ONE AGENT ONLY. No `/goal`, subagents, teams, delegation, parallel instances, or hypothesis redesign.

The exact branch HEAD containing this handoff is the Initial Frozen HEAD. The executor must be given that SHA out-of-band and verify exact equality before any compile/test/experiment command.

## Required frozen files

- `V4_INDEPENDENT_ALPHA_DISCOVERY_PRECOMMIT.md`
- `V4_EXECUTION_HANDOFF.md`
- `AlphaLab_Antigravity/src/run_v4_independent_alpha_discovery.py`
- `AlphaLab_Antigravity/src/test_v4_independent_alpha_discovery.py`
- `AlphaLab_Antigravity/src/generate_v4_independent_alpha_report.py`

Read the precommit completely before execution.

## Step 1 — Git governance

Verify:
- repository `bacbuon333-design/Universal-project-gateway`;
- branch `research/quant-v4-independent-alpha-discovery`;
- exact Initial Frozen HEAD supplied by designer;
- clean working tree.

If branch or HEAD differs, STOP BLOCKED.

## Step 2 — Static compile

Compile exactly:

```bash
python -m py_compile AlphaLab_Antigravity/src/run_v4_independent_alpha_discovery.py
python -m py_compile AlphaLab_Antigravity/src/test_v4_independent_alpha_discovery.py
python -m py_compile AlphaLab_Antigravity/src/generate_v4_independent_alpha_report.py
```

Record Python version and OS.

## Step 3 — Frozen tests

Run:

```bash
python AlphaLab_Antigravity/src/test_v4_independent_alpha_discovery.py
```

Expected frozen suite: 17 tests, all PASS.

If any test fails, do not run the experiment.

## Step 4 — Repair policy

Allowed before experiment only: syntax, import, path, serialization, test-runner plumbing, or API compatibility repair that provably does not alter scientific semantics.

A permitted technical repair must be committed separately, then clean tree + compile + all 17 tests must pass from the new HEAD. Record that repair SHA.

Any repair touching hypothesis definition, configuration value, signal timing, ATR/risk, cost, execution semantics, evaluation sample/window, any of the 14 gate thresholds, multiple-testing budget, or fresh-OOS boundary is a scientific change: STOP BLOCKED and return to designer.

## Step 5 — Run the frozen batch exactly once

Only after clean compile/tests:

```bash
python AlphaLab_Antigravity/src/run_v4_independent_alpha_discovery.py
```

Do not rerun because results are surprising. The runner refuses raw-result overwrite by design.

Expected raw artifact:

`AlphaLab_Antigravity/reports/v4/V4_INDEPENDENT_ALPHA_DISCOVERY_RESULTS.json`

No human-readable report may be generated yet.

## Step 6 — Raw result audit and commit FIRST

Verify raw JSON contains:
- exact canonical SHA;
- `CANONICAL_V2_GAP_SAFE_V3_7_3` execution contract;
- audited 14-gate evaluator contract;
- exactly 12 configs / 4 families;
- common fixed risk contract;
- all 14 gate booleans per config;
- all-gates conjunction classification;
- governance flags false;
- no fresh-OOS outcome or path.

Commit raw evidence only. Suggested message:

`feat(v4): record frozen independent alpha discovery results`

Record raw-result commit SHA. No scientific code edit is allowed in this commit.

## Step 7 — Generate and commit report SECOND

Only after the raw result commit:

```bash
python AlphaLab_Antigravity/src/generate_v4_independent_alpha_report.py
```

Expected report:

`V4_INDEPENDENT_ALPHA_DISCOVERY_REPORT.md`

Commit report separately. Suggested message:

`docs(v4): publish independent alpha discovery conclusion`

No scientific code edit is allowed after results.

## Classification

A configuration passes only if all frozen 14 gates pass.

Any gate failure => `REJECTED`.

All gates pass => `HISTORICAL_CANDIDATE_ONLY`.

If zero survivors, exact conclusion:

`NO V4 CONFIGURATION PASSED ALL FROZEN DISTRIBUTED-EDGE GATES`

If one or more survivors, exact conclusion:

`V4 HISTORICAL CANDIDATE(S) IDENTIFIED — INDEPENDENT VALIDATION REQUIRED`

No survivor is authorized for deployment, paper trading, live trading, or immediate parameter refinement.

## Final executor response

Return:
- repository;
- branch;
- Initial Frozen HEAD;
- technical repair SHA if any;
- raw-result commit SHA;
- final report commit SHA;
- Python version and OS;
- canonical SHA and execution contract;
- compile result;
- frozen tests result (expected 17/17);
- 4 families / 12 configs;
- for every config: ID, family, trade count, PF, expectancy USD, net PnL USD, minimum trades/quarter, minimum trades/complete-year, rolling-4 positive %, rolling-4 PF>=1.20 %, rolling-8 positive %, rolling-8 PF>=1.20 %, profitable-year %, concentration metrics/gates, gates passed /14, final status;
- survivor IDs;
- exact batch conclusion;
- `FRESH OOS ACCESSED: false`;
- `CLOSED RESEARCH MODIFIED: false`;
- `CLOSED RESEARCH DESCENDANT CREATED: false`;
- `STRATEGY DESIGN AUTHORIZED FOR DEPLOYMENT: false`;
- `LIVE TRADING AUTHORIZED: false`.

Then STOP.

Do not create V4.1, Batch 2, tune failures, alter thresholds/risk/costs, access fresh OOS, modify closed strategy research, switch asset/timeframe, paper trade, or live trade.