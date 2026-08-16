# V3.7.2 V2 CANONICAL ENGINE COMPATIBILITY — EXECUTION HANDOFF

## ROLE

Single executor/auditor only. No strategy research.

## REPOSITORY

`bacbuon333-design/Universal-project-gateway`

Branch:

`research/quant-v3.7.2-v2-canonical-engine-compatibility`

This branch is based on V3.7.1.1 final report commit:

`4062f755b50af5369c81912f15c62990d36b4eb9`

## READ FIRST

- `V3_7_2_V2_CANONICAL_ENGINE_COMPATIBILITY_PRECOMMIT.md`
- `AlphaLab_Antigravity/src/canonical_v2_research_engine.py`
- `AlphaLab_Antigravity/src/test_v3_7_2_v2_canonical_engine_compatibility.py`
- `AlphaLab_Antigravity/src/audit_v3_7_2_v2_engine_and_concordance.py`
- `AlphaLab_Antigravity/src/generate_v3_7_2_v2_engine_compatibility_report.py`

## EXECUTION ORDER

1. Verify branch/HEAD and clean worktree.
2. Compile the four V3.7.2 Python files.
3. Run the V3.7.2-V2 unit tests.
4. Run `audit_v3_7_2_v2_engine_and_concordance.py` exactly once under frozen semantics.
5. Validate machine outputs.
6. Commit raw machine outputs separately.
7. Run report generator only after raw commit exists.
8. Commit report separately.
9. STOP.

## REQUIRED MACHINE OUTPUTS

`AlphaLab_Antigravity/reports/v3_7_2_v2/canonical_v2_engine_snapshot.json`

`AlphaLab_Antigravity/reports/v3_7_2_v2/legacy_canonical_v2_concordance.json`

`AlphaLab_Antigravity/reports/v3_7_2_v2/V3_7_2_V2_ENGINE_COMPATIBILITY_DECISION.json`

## REQUIRED REPORT

`V3_7_2_V2_CANONICAL_ENGINE_COMPATIBILITY_REPORT.md`

## TECHNICAL REPAIR POLICY

Only syntax/import/path/test-runner/serialization repairs are allowed.

Do not modify:

- canonical V2 SHA;
- timestamp semantic;
- UTC parsing;
- Unix-epoch request-boundary contract;
- authorization gates;
- DeepQuantEngine execution behavior;
- legacy status;
- concordance shifts;
- compatibility pass conditions.

Any semantic repair requires STOP and return to independent designer.

## STOP RULE

Even if compatibility passes:

- no H-221;
- no LMDC;
- no strategy execution;
- no backtest;
- no parameter tuning;
- no V3.8.

Return evidence for independent audit.
