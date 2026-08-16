# REUSABLE PROMPT — V3.13 BLIND OOS CHECKPOINT

Use this prompt for checkpoint #2, #3, and later recurring accrual runs.

Repository:
`bacbuon333-design/Universal-project-gateway`

Branch:
`ops/quant-v3.13-blind-oos-accrual`

Operate as ONE agent only.

NO `/goal`.
NO subagents.
NO teams.
NO delegation.
NO parallel model instances.

Role:
EXECUTOR + OOS PROVENANCE RECORDER + BLIND LEDGER AUDITOR.

You are NOT a strategy researcher.

## 1. Freeze execution state

- Read `V3_13_BLIND_OOS_OPERATIONAL_RUNBOOK.md` completely.
- Record `PRE_RUN_HEAD = git rev-parse HEAD`.
- Require clean working tree.
- Record current checkpoint count and latest checkpoint filename/hash using the canonical ledger hash scheme.
- Verify hash scheme is `SHA256_UTF8_LF_NORMALIZED_V1`.
- Verify genesis authority remains `b45ac406bfa7da1436f23f0add600a6354485b5a4d5d25c064b3470e23300876`.

If working tree is dirty before execution: STOP.

## 2. Frozen scientific state

Historical H226 strategies = `REJECTED`.
Same-sample H226 research = `CLOSED`.
Strategy design authorized = `false`.
Future OOS outcome evaluator authorized = `false`.

Do not modify these states.

## 3. Compile and test before mutation

Compile:

- `AlphaLab_Antigravity/src/export_v3_12_fresh_oos_mt5.py`
- `AlphaLab_Antigravity/src/create_v3_13_blind_oos_checkpoint.py`
- `AlphaLab_Antigravity/src/test_v3_13_blind_oos_ledger.py`
- `AlphaLab_Antigravity/src/test_v3_13_1_checkpoint_hash_repair.py`
- `AlphaLab_Antigravity/src/generate_v3_13_checkpoint_report.py`

Run the frozen ledger/hash tests.

If a technical repair is needed:
STOP before acquisition.
Commit repair separately.
Return the new clean HEAD.
Do not combine code repair with raw checkpoint evidence.

## 4. Run exporter exactly once

Execute:

`python AlphaLab_Antigravity/src/export_v3_12_fresh_oos_mt5.py --symbol GOLD`

Exact source contract:

- XM Global Limited
- XMGlobal-MT5 9
- GOLD
- M30
- BAR_OPEN_TIME
- UTC
- UNIX_EPOCH_SECONDS_UTC

Allowed results only:

`NO_FRESH_BARS_AVAILABLE`

or

`FRESH_OOS_ACCRUAL_WRITTEN`

### If NO_FRESH_BARS_AVAILABLE

- Do not alter cutoff.
- Do not synthesize/backfill data.
- Do not create a redundant checkpoint.
- Do not commit anything.
- Return exporter result and STOP.

### If FRESH_OOS_ACCRUAL_WRITTEN

Verify:

- OOS CSV and source sidecar both exist;
- first OOS timestamp > `2026-08-14T23:30:00Z`;
- dataset SHA matches sidecar;
- canonical parent SHA exact;
- broker/server/symbol/timeframe exact;
- BAR_OPEN_TIME / UTC / UNIX_EPOCH_SECONDS_UTC exact;
- append-only history;
- no conflicting duplicate timestamps;
- no credentials/account-holder data.

Then continue.

## 5. Create exactly one checkpoint

Execute exactly once:

`python AlphaLab_Antigravity/src/create_v3_13_blind_oos_checkpoint.py`

Verify:

- sequence = previous sequence + 1;
- previous checkpoint filename exact;
- previous checkpoint SHA exact under `SHA256_UTF8_LF_NORMALIZED_V1`;
- `checkpoint_hash_scheme = SHA256_UTF8_LF_NORMALIZED_V1` for checkpoint #2+;
- checkpoint timestamp strictly increases;
- full ledger chain validates after write.

For checkpoint #2 specifically, parent must be:

filename:
`000001_20260816T111146Z.json`

canonical parent SHA:
`b45ac406bfa7da1436f23f0add600a6354485b5a4d5d25c064b3470e23300876`

Never use the superseded historical local SHA `f8f97c2a7aa47e79784f37dc83072896971d52a34fef8ba28248351447ac000b` as ledger authority.

## 6. Absolute no-outcome rule

Do NOT calculate or inspect:

- 8h signed return;
- forward returns;
- economic excess;
- MFE/MAE;
- gap closure outcome;
- PF;
- expectancy;
- win rate;
- PnL;
- trading fills.

Do NOT call:

- `run_strategy`
- `CanonicalV2ExecutionEngine`
- any trading engine.

Checkpoint may contain only provenance, storage state, C1/C4 eligibility counts, maturity checks, and readiness state.

## 7. Maturity contract

Readiness evaluation only:

- >=8 complete decision quarters starting no earlier than 2026Q4;
- C1 total >=160;
- C4 total >=100;
- every complete decision quarter C1 >=10;
- every complete decision quarter C4 >=5;
- provenance/ledger valid.

Even if ALL pass:

DO NOT calculate outcomes.
DO NOT create evaluator.
DO NOT create strategy.

Commit blind evidence and STOP for independent designer review.

## 8. Raw evidence commit

After a successful append + checkpoint:

Commit together as raw evidence:

- changed `GOLD_M30_FRESH_OOS.csv`;
- changed `GOLD_M30_FRESH_OOS.source.json`;
- exactly one new checkpoint JSON.

Suggested message:

`feat(v3.13): record next blind OOS accrual checkpoint`

Record actual raw commit SHA.

## 9. Report commit

Only after raw evidence commit:

Run:

`python AlphaLab_Antigravity/src/generate_v3_13_checkpoint_report.py`

Verify report sequence matches the newly created checkpoint and old reports are untouched.

Commit report separately.

Suggested message:

`docs(v3.13): publish next blind OOS checkpoint report`

Record actual report commit SHA.

## 10. Final response

Return:

- repository;
- branch;
- PRE_RUN_HEAD;
- technical repair SHA if any;
- exporter result;
- rows added;
- raw checkpoint commit SHA;
- report commit SHA;
- Python / OS / MT5 version;
- checkpoint sequence and filename;
- checkpoint canonical SHA;
- previous checkpoint filename/SHA;
- OOS dataset SHA;
- OOS row count;
- first/last OOS timestamp;
- bridge-quarantine rows;
- complete decision quarters;
- C1 total / C4 total;
- minimum C1/C4 per complete quarter;
- all maturity checks;
- readiness status.

Then state exactly:

`OUTCOME METRICS COMPUTED: false`

`TRADING ENGINE CALLED: false`

`STRATEGY EXECUTED: false`

`FUTURE OOS OUTCOME EVALUATOR AUTHORIZED: false`

`ALL HISTORICAL H226 STRATEGIES: REJECTED`

`SAME-SAMPLE H226 RESEARCH CLOSED: true`

`STRATEGY DESIGN AUTHORIZED: false`

STOP.
