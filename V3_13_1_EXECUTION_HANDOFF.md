# V3.13.1 EXECUTION HANDOFF — CHECKPOINT HASH CANONICALIZATION REPAIR

Execution role only. One agent. No subagents, no `/goal`, no parallel model instances.

## Branch

`research/quant-v3.13.1-checkpoint-hash-canonicalization`

## Purpose

Audit and close the V3.13 newline/hash portability defect before checkpoint #2 is ever created.

## Required sequence

1. Verify exact branch and frozen initial HEAD supplied by the Independent Research Designer.
2. Read `V3_13_1_CHECKPOINT_HASH_CANONICALIZATION_PRECOMMIT.md`.
3. Compile:
   - `AlphaLab_Antigravity/src/create_v3_13_blind_oos_checkpoint.py`
   - `AlphaLab_Antigravity/src/audit_v3_13_1_checkpoint_hash_repair.py`
   - `AlphaLab_Antigravity/src/test_v3_13_1_checkpoint_hash_repair.py`
   - `AlphaLab_Antigravity/src/generate_v3_13_1_hash_repair_report.py`
4. Run exactly:
   - `python AlphaLab_Antigravity/src/test_v3_13_1_checkpoint_hash_repair.py`
5. Expected: **14/14 tests PASS**.
6. Do NOT run the V3.12 exporter.
7. Do NOT run `create_v3_13_blind_oos_checkpoint.py`; checkpoint #2 is forbidden in this repair chapter.
8. Run exactly once:
   - `python AlphaLab_Antigravity/src/audit_v3_13_1_checkpoint_hash_repair.py`
9. Validate machine decision artifact:
   - `AlphaLab_Antigravity/reports/v3_13_1/V3_13_1_CHECKPOINT_HASH_REPAIR_DECISION.json`
10. Commit the machine artifact separately.
11. Only after the raw commit exists, run:
   - `python AlphaLab_Antigravity/src/generate_v3_13_1_hash_repair_report.py`
12. Commit `V3_13_1_CHECKPOINT_HASH_CANONICALIZATION_REPORT.md` separately.
13. STOP.

## Frozen defect facts

Historical V3.13 report-published local-worktree SHA:

`f8f97c2a7aa47e79784f37dc83072896971d52a34fef8ba28248351447ac000b`

Authoritative SHA of committed GitHub/LF checkpoint content:

`b45ac406bfa7da1436f23f0add600a6354485b5a4d5d25c064b3470e23300876`

Hash scheme after repair:

`SHA256_UTF8_LF_NORMALIZED_V1`

The old `f8f97...` value must be marked superseded for chain authority, not deleted from audit history.

## Absolute immutability

Do NOT edit, delete, rename, regenerate, or recommit:

`AlphaLab_Antigravity/reports/v3_13/checkpoints/000001_20260816T111146Z.json`

Do NOT rewrite:

`V3_13_BLIND_OOS_CHECKPOINT_REPORT_000001.md`

The repair must work around those immutable historical artifacts.

## Technical repair policy

Only syntax/import/path/test-runner/serialization plumbing may be repaired.

Do NOT change:

- canonical cutoff;
- bridge quarter;
- first OOS decision quarter;
- maturity gates;
- C1/C4 definitions;
- H226 status;
- no-peeking rules;
- scientific conclusions.

If any of those appear necessary, STOP.

## Required machine checks

All must be true:

- exactly one checkpoint exists;
- no checkpoint #2 was created;
- genesis filename exact;
- canonical hash scheme exact;
- canonical genesis SHA = `b45ac406...`;
- historical local SHA = `f8f97...` and explicitly superseded;
- chain latest SHA = canonical genesis SHA;
- writer uses deterministic binary LF serialization;
- writer hashes checkpoints using canonical LF hash function;
- future payloads record `checkpoint_hash_scheme`;
- `.gitattributes` forces LF for checkpoint JSON and reports;
- precommit exists;
- no exporter/outcome/engine/strategy execution.

## Allowed final status

Exactly one:

`V3_13_1_CHECKPOINT_HASH_CANONICALIZATION_PASS`

or

`V3_13_1_CHECKPOINT_HASH_CANONICALIZATION_BLOCKED`

Do not manually override machine decision.

## Raw commit

Suggested:

`fix(v3.13.1): audit checkpoint hash canonicalization repair`

Record actual SHA.

## Report commit

Suggested:

`docs(v3.13.1): publish checkpoint hash canonicalization conclusion`

Record actual SHA.

## Final response

Return:

- Repository
- Branch
- Initial frozen HEAD
- Technical Repair SHA, if any
- Raw Audit SHA
- Final Report SHA
- Python / OS
- Tests result
- Genesis filename
- Historical local-worktree SHA
- Its status (`SUPERSEDED_FOR_LEDGER_CHAIN_AUTHORITY`)
- Raw worktree SHA observed during audit
- Hash scheme
- Canonical genesis chain SHA
- Whether genesis payload was rewritten
- Whether historical report was rewritten
- Whether checkpoint #2 was created
- All machine checks PASS/FAIL
- Final status

Then state exactly:

`OOS EXPORTER CALLED: false`

`OUTCOME METRICS COMPUTED: false`

`TRADING ENGINE CALLED: false`

`STRATEGY EXECUTED: false`

`FUTURE OOS OUTCOME EVALUATOR AUTHORIZED: false`

`ALL HISTORICAL H226 STRATEGIES: REJECTED`

`SAME-SAMPLE H226 RESEARCH CLOSED: true`

`STRATEGY DESIGN AUTHORIZED: false`

## Stop

STOP after report commit. Do not run accrual or create checkpoint #2 until independent review accepts V3.13.1.