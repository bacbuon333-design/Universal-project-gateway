# V3.13.1.1 EXECUTION HANDOFF

Execution-only provenance closure. No scientific redesign.

## Frozen workflow

1. Verify branch and expected frozen HEAD supplied by Independent Research Designer.
2. Verify clean working tree.
3. Compile audit, tests, report generator.
4. Run the 12 frozen tests.
5. If any technical repair is required, STOP the audit workflow, make a separate technical-repair commit, return the new clean HEAD, and only then resume. Never combine a code repair with raw audit evidence.
6. Run exactly once: `python AlphaLab_Antigravity/src/audit_v3_13_1_1_repair_provenance.py`.
7. Verify the machine artifact records the exact clean execution HEAD used before artifact write.
8. Commit raw artifact separately.
9. Generate the human report from the committed machine artifact.
10. Commit report separately and STOP.

## Absolute prohibitions

Do not run the OOS exporter. Do not create checkpoint #2. Do not calculate OOS outcomes. Do not call any trading engine. Do not create H227 or alter H226. Do not alter V3.13.1 hash semantics.