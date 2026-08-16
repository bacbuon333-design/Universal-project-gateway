# V3.7.1.1 EXECUTION HANDOFF

Branch: `research/quant-v3.7.1.1-utc-boundary-reproduction`

Execution only. No strategy research.

## Required order

1. Verify branch and initial HEAD.
2. Read `V3_7_1_1_UTC_BOUNDARY_REPRODUCTION_PRECOMMIT.md`.
3. Compile:
   - `export_v3_7_1_1_mt5_canonical_gold_m30_v2.py`
   - `test_v3_7_1_1_utc_boundary_reproduction.py`
   - `generate_v3_7_1_1_reproduction_report.py`
4. Run all V3.7.1.1 tests.
5. Verify exact broker Gold symbol remains `GOLD` on the same intended broker/server lineage.
6. Run the V2 reproduction exactly once.
7. Validate V2 CSV, sidecar, manifest, structural audit, decision.
8. Commit raw V2 artifacts separately.
9. Run report generator only after raw commit.
10. Commit final report separately.
11. STOP.

## Frozen reproduction command

`python AlphaLab_Antigravity/src/export_v3_7_1_1_mt5_canonical_gold_m30_v2.py --symbol GOLD`

Use `--terminal-path` only if technically required to connect the same intended terminal.

## Required checks

- request boundary representation = `UNIX_EPOCH_SECONDS_UTC`;
- no `replace(tzinfo=None)` in V2 acquisition path;
- timestamp semantic = `BAR_OPEN_TIME`;
- timezone = `EXPLICIT_UTC / UTC`;
- lineage = `VERIFIED`;
- structural validation = `PASS`;
- coverage = `PASS`;
- sidecar SHA = actual V2 CSV SHA;
- no sensitive account fields committed;
- terminal maxbars explicitly recorded;
- byte concordance against V3.7.1 reported exactly as generated.

## Forbidden

- overwrite V3.7.1 canonical files;
- edit generated sidecar manually to pass;
- change requested start;
- change timeframe;
- change symbol;
- alter OHLC;
- fill gaps;
- change coverage rule;
- strategy backtest;
- H-221;
- LMDC rerun;
- V3.8.

## Raw outputs

- `AlphaLab_Antigravity/data/canonical/GOLD_M30_CANONICAL_V2.csv`
- `AlphaLab_Antigravity/data/provenance/GOLD_M30_CANONICAL_V2.source.json`
- `AlphaLab_Antigravity/data/provenance/GOLD_M30_CANONICAL_V2.manifest.json`
- `AlphaLab_Antigravity/reports/v3_7_1_1/GOLD_M30_CANONICAL_V2.structural_audit.json`
- `AlphaLab_Antigravity/reports/v3_7_1_1/V3_7_1_1_REPRODUCTION_DECISION.json`

Suggested raw commit:

`feat(v3.7.1.1): execute UTC-boundary canonical V2 reproduction`

Then generate and commit:

`V3_7_1_1_UTC_BOUNDARY_REPRODUCTION_REPORT.md`

Suggested report commit:

`docs(v3.7.1.1): publish UTC-boundary canonical reproduction conclusion`

## Final status

Exactly one of:

`CANONICAL_V2_REPRODUCTION_ELIGIBLE`

or

`CANONICAL_V2_REPRODUCTION_BLOCKED`

Return evidence to the independent designer and STOP.
