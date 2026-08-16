# V3.13 EXECUTION HANDOFF — BLIND OOS ACCRUAL LEDGER

The independent designer supplies the exact frozen branch HEAD in the execution prompt. Verify it before doing anything.

## Role

Executor + provenance/checkpoint recorder only. One agent. No strategy research.

## Frozen order

1. Verify branch and clean working tree.
2. Read `V3_13_BLIND_OOS_ACCRUAL_LEDGER_PRECOMMIT.md`.
3. Compile:
   - `fresh_oos_v312_contract.py`
   - `export_v3_12_fresh_oos_mt5.py`
   - `create_v3_13_blind_oos_checkpoint.py`
   - `test_v3_13_blind_oos_ledger.py`
   - `generate_v3_13_checkpoint_report.py`
4. Run `python AlphaLab_Antigravity/src/test_v3_13_blind_oos_ledger.py`; exactly 15 tests must pass.
5. Run the frozen V3.12 exporter exactly once with exact symbol `GOLD`.
6. Accept either `NO_FRESH_BARS_AVAILABLE` or `FRESH_OOS_ACCRUAL_WRITTEN`.
7. Run `python AlphaLab_Antigravity/src/create_v3_13_blind_oos_checkpoint.py` exactly once.
8. Verify the full checkpoint chain and new checkpoint SHA.
9. Commit raw evidence first. If the exporter wrote/updated fresh-OOS CSV and source sidecar, include them in the same raw evidence commit with the new checkpoint.
10. Only after raw evidence commit, run `python AlphaLab_Antigravity/src/generate_v3_13_checkpoint_report.py`.
11. Commit the immutable checkpoint report separately.
12. Stop.

## Technical repair policy

Only syntax/import/path/serialization/test-runner plumbing repairs are allowed before a valid run. No change to cutoff, bridge quarter, maturity thresholds, C1/C4 eligibility definitions, hash-chain rules, no-peeking rules, source identity, or outcome prohibition.

## Absolute prohibitions

Do not calculate post-signal returns, excess reversion, MFE, MAE, gap closure, PF, expectancy, strategy PnL, or fills. Do not call a trading engine. Do not create H227 or any H226 descendant. Do not convert DOWN-gap or RECENT into a filter.

## Raw evidence requirements

The new checkpoint must contain:

- contiguous sequence;
- exact previous checkpoint filename/SHA, or null/null for genesis;
- exact canonical V2 authority and cutoff;
- exact current fresh-OOS dataset/provenance SHA if present;
- V3.12 readiness counts and maturity checks only;
- all no-peeking governance booleans false/closed as frozen.

Broken chain, source/provenance mismatch, temporal overlap/backfill, future checkpoint timestamp, or non-monotonic checkpoint time are strict blockers.

## Commit messages

Raw evidence suggested:

`feat(v3.13): record blind OOS accrual checkpoint`

Report suggested:

`docs(v3.13): publish blind OOS checkpoint report`

## Stop boundary

Even if the checkpoint readiness status becomes `FRESH_OOS_MATURE_FOR_SEPARATELY_PRECOMMITTED_EVALUATION`, do not create or run the evaluator in V3.13. Return evidence to the independent designer for a new precommit decision.
