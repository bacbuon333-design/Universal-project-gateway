# V3.10 EXECUTION HANDOFF

Executor role only. Single agent. No redesign.

## Frozen branch

`research/quant-v3.10-h226-delayed-reversion-stability`

## Required order

1. Verify branch / clean working tree / initial HEAD.
2. Read `V3_10_H226_DELAYED_REVERSION_STABILITY_PRECOMMIT.md`.
3. Compile:
   - `AlphaLab_Antigravity/src/audit_v3_10_h226_delayed_reversion.py`
   - `AlphaLab_Antigravity/src/test_v3_10_h226_delayed_reversion.py`
   - `AlphaLab_Antigravity/src/generate_v3_10_report.py`
4. Run the frozen test file. Expected: **14 tests**.
5. Technical repairs are allowed only for syntax/import/path/serialization/test-runner defects. No scientific-semantic repair is authorized.
6. Run the V3.10 audit exactly once.
7. Validate machine artifacts before committing.
8. Commit machine artifacts first.
9. Generate the human report only after the raw commit exists.
10. Commit the report separately.
11. STOP.

## Frozen source expectation

The audit reads only the V3.9 event artifact and filters H226 cohort rows at horizon `8h`.

Expected frozen 8h cohort counts from V3.9:

- H226-C1: 913
- H226-C2: 696
- H226-C3: 851
- H226-C4: 639
- total H226 8h rows: 3,099

If those counts do not match, STOP and report source drift. Do not reconstruct events.

## Required output dimensions

- `v3_10_8h_view_summary.csv`: 24 rows
- `v3_10_8h_year_stability.csv`: 28 rows
- `v3_10_8h_quarter_stability.csv`: 132 rows
- `v3_10_8h_leave_one_year_out.csv`: 28 rows
- `v3_10_8h_cluster_bootstrap.csv`: 8 rows
- `v3_10_8h_decision.json`: one JSON object
- `v3_10_metadata.json`: one JSON object

## Metadata checks

Must state:

- canonical dataset `GOLD_M30_CANONICAL_V2`
- canonical SHA `c48ca44dcecae9eb1c2590c586e27c4bc5f246215c549d0d0bc1201d95d5ea1d`
- horizon `8h`
- raw_market_data_read = false
- events_reconstructed = false
- trading_engine_called = false
- strategy_executed = false
- H226 strategy status remains REJECTED
- strategy_design_authorized = false
- 5000 quarter-block bootstrap reps, seed 310226
- 5000 complete-year-block bootstrap reps, seed 310227

## Final status

Return exactly one machine-derived label:

- `H226 DELAYED 8H REVERSION ROBUSTLY SUPPORTED — STRATEGY DESIGN NOT AUTHORIZED`
- `H226 DELAYED 8H REVERSION REGIME / DIRECTION DEPENDENT — STRATEGY DESIGN NOT AUTHORIZED`
- `H226 DELAYED 8H REVERSION NOT SUPPORTED — H226 CHAPTER CLOSED`

Regardless of label, all H226 strategies remain REJECTED.

No H227, strategy design, direction filter, threshold tuning, SL/TP/RR change, new horizon, new timeframe or new asset is authorized.
