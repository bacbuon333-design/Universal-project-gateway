# V3.7.2 EXECUTION HANDOFF

Branch: `research/quant-v3.7.2-canonical-engine-compatibility`

This is execution/audit only. No strategy research.

## Required order

1. Verify branch and frozen initial HEAD.
2. Read `V3_7_2_CANONICAL_ENGINE_COMPATIBILITY_PRECOMMIT.md`.
3. Compile:
   - `canonical_research_engine.py`
   - `test_v3_7_2_canonical_engine_compatibility.py`
   - `audit_v3_7_2_engine_and_concordance.py`
   - `generate_v3_7_2_engine_compatibility_report.py`
4. Run all V3.7.2 tests.
5. Run the engine/concordance audit exactly once.
6. Validate the three machine artifacts under `reports/v3_7_2/`.
7. Commit raw machine artifacts separately.
8. Run the report generator only after raw commit exists.
9. Commit the generated report separately.
10. STOP.

## Forbidden

- H-221 or any new hypothesis;
- strategy backtest;
- LMDC rerun;
- parameter tuning;
- changing V3.7.1 canonical CSV;
- changing its provenance sidecar;
- changing the frozen SHA;
- weakening authorization checks;
- changing execution logic in `deep_quant_engine.py`;
- retroactively changing legacy V3.7 `BLOCKED` status.

## Technical repair policy

Only syntax/import/path/serialization/test plumbing defects may be repaired before valid execution.

Any change to timestamp semantics, authorization fields, frozen hash, engine execution model, or concordance interpretation requires STOP and return to the independent designer.

## Concordance interpretation

Compute the frozen same-label, canonical +30m, and canonical -30m views.

Do not choose the highest-match shift as a new legacy semantic contract.

The comparison is empirical similarity only.

## Required raw outputs

- `AlphaLab_Antigravity/reports/v3_7_2/canonical_engine_snapshot.json`
- `AlphaLab_Antigravity/reports/v3_7_2/legacy_canonical_concordance.json`
- `AlphaLab_Antigravity/reports/v3_7_2/V3_7_2_ENGINE_COMPATIBILITY_DECISION.json`

Suggested raw commit:

`feat(v3.7.2): execute canonical engine compatibility audit`

Then generate:

`V3_7_2_CANONICAL_ENGINE_COMPATIBILITY_REPORT.md`

Suggested report commit:

`docs(v3.7.2): publish canonical engine compatibility conclusion`

## Allowed final status

Exactly one of:

`CANONICAL_ENGINE_COMPATIBILITY_PASS`

`CANONICAL_ENGINE_COMPATIBILITY_BLOCKED`

Even on PASS, do not start a strategy chapter.
