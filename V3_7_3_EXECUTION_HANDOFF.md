# V3.7.3 EXECUTION HANDOFF

## ROLE

Executor + evidence recorder only. One agent. No `/goal`, subagents, teams, delegation or parallel model instances.

## BRANCH

`research/quant-v3.7.3-execution-contract-hardening`

## PURPOSE

Verify the frozen hardened execution contract using synthetic fixtures and static evidence. Do not run a real market strategy.

## ORDER

1. Verify branch/HEAD and clean working tree.
2. Read `V3_7_3_EXECUTION_CONTRACT_HARDENING_PRECOMMIT.md`.
3. Compile:
   - `canonical_v2_execution_engine.py`
   - `test_v3_7_3_execution_contract.py`
   - `audit_v3_7_3_execution_contract.py`
   - `generate_v3_7_3_execution_contract_report.py`
4. Run `test_v3_7_3_execution_contract.py`.
5. Only syntax/import/path/test-runner repairs are allowed. Semantic repairs require STOP.
6. Run `audit_v3_7_3_execution_contract.py` exactly once.
7. Inspect `V3_7_3_EXECUTION_CONTRACT_DECISION.json`.
8. Commit raw decision separately.
9. Run report generator.
10. Commit final report separately.
11. STOP.

## PROHIBITED

- no H-221;
- no LMDC;
- no real canonical backtest;
- no parameter optimization;
- no change to legacy `deep_quant_engine.py`;
- no change to canonical V2 dataset;
- no silent change to spread, commission, slippage or fill rules.

## EXPECTED FINAL STATUS

`CANONICAL_EXECUTION_CONTRACT_PASS`

or

`CANONICAL_EXECUTION_CONTRACT_BLOCKED`

Return all test results, raw audit SHA, report SHA and exact failed checks if blocked.
