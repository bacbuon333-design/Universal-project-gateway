# V3.12 EXECUTION HANDOFF

## Role
EXECUTOR + OOS-PROVENANCE AUDITOR + READINESS RECORDER only.

Single agent. No `/goal`, subagents, teams, delegation, or parallel instances.

## Absolute prohibition
Do not calculate forward H226 returns, 8h effect, economic excess, MFE/MAE, gap closure, PF, expectancy, or strategy fills. Do not create H227. Do not authorize strategy design.

## Required order
1. Verify branch and clean tree.
2. Read `V3_12_FRESH_OOS_FORWARD_LOCK_PRECOMMIT.md`.
3. Compile:
   - `fresh_oos_v312_contract.py`
   - `export_v3_12_fresh_oos_mt5.py`
   - `audit_v3_12_fresh_oos_readiness.py`
   - `test_v3_12_fresh_oos_lock.py`
   - `generate_v3_12_report.py`
4. Run the frozen test suite. Expected: **16 tests**.
5. If and only if all tests pass, execute the controlled accrual exporter once with exact symbol `GOLD`.
6. Accept either `NO_FRESH_BARS_AVAILABLE` or `FRESH_OOS_ACCRUAL_WRITTEN`. No fresh bars is a valid state and must not be bypassed.
7. Run the blind readiness audit exactly once.
8. Validate machine artifacts. No outcome metric may appear.
9. Commit raw OOS/provenance artifacts if created plus readiness artifacts.
10. Only after raw commit, generate the human report and commit it separately.
11. STOP.

## Technical repair policy
Only syntax/import/path/serialization/test-runner plumbing may be repaired. Any change to cutoff, quarter partition, maturity thresholds, event eligibility, source identity, or no-peeking policy requires STOP and independent redesign.

## Current temporal expectation
Canonical cutoff is `2026-08-14T23:30:00+00:00`. `2026Q3` is bridge/quarantine. The first complete decision quarter is `2026Q4`. On a current 2026 execution, maturity is impossible. A machine result claiming 8 complete fresh-OOS quarters in 2026 indicates temporal/data contamination and must be rejected.

## Required machine artifacts
- `AlphaLab_Antigravity/reports/v3_12/V3_12_FRESH_OOS_READINESS.json`
- `AlphaLab_Antigravity/reports/v3_12/v3_12_fresh_oos_event_counts.csv`

Optional, only if actual fresh bars exist:
- `AlphaLab_Antigravity/data/oos/GOLD_M30_FRESH_OOS.csv`
- `AlphaLab_Antigravity/data/oos/GOLD_M30_FRESH_OOS.source.json`

## Raw commit
Suggested message:
`feat(v3.12): execute fresh-OOS accrual readiness lock`

## Report
After raw commit:
`python AlphaLab_Antigravity/src/generate_v3_12_report.py`

Suggested report commit:
`docs(v3.12): publish fresh-OOS forward-lock readiness`

## Final response
Return repository, branch, initial frozen HEAD, technical repair SHA if any, exporter result, raw SHA, report SHA, Python/OS/MT5 package if exporter connected, 16/16 tests, cutoff, OOS first/last timestamp if present, OOS SHA if present, bridge rows, complete decision-quarter count, C1/C4 counts, each maturity check, final readiness status, and explicit confirmations:
- outcome metrics computed: false
- trading engine called: false
- strategy executed: false
- same-sample H226 research closed: true
- strategy design authorized: false

Then STOP.