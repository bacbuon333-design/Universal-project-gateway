# V3.11 EXECUTION HANDOFF

## Role

Executor + evidence recorder only. Single agent. No strategy design.

## Read first

- `V3_11_H226_ECONOMIC_MATERIALITY_CLOSURE_PRECOMMIT.md`
- `AlphaLab_Antigravity/src/audit_v3_11_h226_economic_materiality.py`
- `AlphaLab_Antigravity/src/test_v3_11_h226_economic_materiality.py`
- `AlphaLab_Antigravity/src/generate_v3_11_report.py`

Frozen code parent before this handoff document:
`a06fba4e068591362bfa993bf71a26da6790d2bb`

The actual branch HEAD including this handoff document must be recorded before execution and must become the machine artifact-generation parent SHA.

## Sequence

1. Verify branch and clean working tree.
2. Compile all three Python files.
3. Run exactly `AlphaLab_Antigravity/src/test_v3_11_h226_economic_materiality.py`.
4. Expected test count: exactly `14`.
5. If any semantic test fails, STOP. Only syntax/import/path/serialization/test-runner plumbing repairs are permitted before execution.
6. Execute exactly once:
   `python AlphaLab_Antigravity/src/audit_v3_11_h226_economic_materiality.py`
7. Validate machine artifacts and dimensions.
8. Commit raw machine evidence separately.
9. Only after raw commit, run `generate_v3_11_report.py`.
10. Commit `V3_11_H226_ECONOMIC_MATERIALITY_CLOSURE_REPORT.md` separately.
11. STOP.

## Required machine artifacts

Under `AlphaLab_Antigravity/reports/v3_11/`:

- `v3_11_8h_economic_views.csv` — 20 rows
- `v3_11_8h_economic_years.csv` — 28 rows
- `v3_11_8h_economic_quarters.csv` — 132 rows
- `v3_11_8h_economic_leave_one_year_out.csv` — 28 rows
- `v3_11_8h_economic_cluster_bootstrap.csv` — 8 rows
- `v3_11_8h_economic_decision.json`
- `v3_11_metadata.json`

## Frozen invariants

- horizon = 8h only
- C1-C4 source counts = 913 / 696 / 851 / 639
- V3.9 event SHA = `aecdb78d22598a962c29adbd7448755eaf31399d351d5efcbeeddc0c823d920f`
- canonical V2 SHA = `c48ca44dcecae9eb1c2590c586e27c4bc5f246215c549d0d0bc1201d95d5ea1d`
- cost hurdle = 0.32 USD/oz round-trip price equivalent
- quarter bootstrap = 5000, seed 311226
- year bootstrap = 5000, seed 311227
- decision cohorts = C1 and C4 only
- strategy executed = false
- trading engine called = false
- raw market data read = false
- events reconstructed = false
- H226 strategy status remains REJECTED
- same-sample H226 research closes after this chapter
- strategy design authorized = false

## Forbidden

No H227. No H226 descendant. No direction filter. No threshold change. No SL/TP/RR. No new horizon. No new asset/timeframe. No strategy execution.

## Raw commit

Suggested message:
`feat(v3.11): execute H226 economic materiality closure audit`

## Report commit

Suggested message:
`docs(v3.11): publish H226 economic materiality closure`
