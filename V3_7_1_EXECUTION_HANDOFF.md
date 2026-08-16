# V3.7.1 EXECUTION HANDOFF

## ROLE

Executor + provenance recorder only. No strategy research.

## BRANCH

`research/quant-v3.7.1-controlled-canonical-reexport`

## DESIGN ARTIFACT GENERATION PARENT

`1828928ccc5d889888445b6b92912bd0f1a729eb`

Do not treat this as the final branch SHA. Read actual Git HEAD before execution.

## REQUIRED ORDER

1. Verify Git branch and clean worktree.
2. Read `V3_7_1_CONTROLLED_CANONICAL_REEXPORT_PRECOMMIT.md`.
3. Compile exporter/tests/report generator.
4. Run `test_v3_7_1_controlled_reexport.py`.
5. Verify MetaTrader5 package/terminal connectivity.
6. Determine the exact broker Gold symbol without performance inspection.
7. Run the frozen exporter exactly once with explicit `--symbol`.
8. Inspect machine artifacts and verify no sensitive account login/name was serialized.
9. Commit canonical CSV + provenance + machine audit as one raw-export commit.
10. Run machine report generator only after raw-export commit exists.
11. Commit final report separately.
12. STOP.

## EXACT EXECUTION

Exporter:

`python AlphaLab_Antigravity/src/export_v3_7_1_mt5_canonical_gold_m30.py --symbol <EXACT_BROKER_GOLD_SYMBOL>`

Tests:

`python AlphaLab_Antigravity/src/test_v3_7_1_controlled_reexport.py`

Report:

`python AlphaLab_Antigravity/src/generate_v3_7_1_reexport_report.py`

## SYMBOL RULE

Do not silently substitute symbols.

If the exact intended Gold symbol is not objectively identifiable from the connected broker terminal, STOP and report available Gold/XAU candidates. Do not export an arbitrary one.

## EXPECTED DATA CONTRACT

- source API: MetaTrader5 Python `copy_rates_range`;
- timeframe: M30;
- timestamp semantic: BAR_OPEN_TIME;
- timezone: UTC;
- requested history start: 2018-01-01 UTC;
- latest included bar: latest fully completed M30 bar only;
- no current forming bar;
- no interpolation/resampling/gap filling;
- legacy `GOLD_M30.csv` untouched.

## EXPECTED OUTPUTS

- `AlphaLab_Antigravity/data/canonical/GOLD_M30_CANONICAL.csv`
- `AlphaLab_Antigravity/data/provenance/GOLD_M30_CANONICAL.source.json`
- `AlphaLab_Antigravity/data/provenance/GOLD_M30_CANONICAL.manifest.json`
- `AlphaLab_Antigravity/reports/v3_7_1/GOLD_M30_CANONICAL.structural_audit.json`
- `AlphaLab_Antigravity/reports/v3_7_1/V3_7_1_REEXPORT_DECISION.json`
- `V3_7_1_CANONICAL_REEXPORT_REPORT.md` after raw commit.

## PRIVACY

Do not commit account login, account holder name, credentials, terminal executable path or other unnecessary local secrets.

Broker company, server and exact market symbol are provenance and are expected to be committed.

## FINAL DECISION

Allowed data statuses:

- `ELIGIBLE`
- `BLOCKED`

No `MOSTLY_ELIGIBLE`, `LIKELY_CANONICAL`, or discretionary override.

Even if ELIGIBLE, do not start H-221 or any strategy research in V3.7.1.
