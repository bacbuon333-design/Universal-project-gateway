# V3.7.3 CANONICAL EXECUTION CONTRACT REPORT

- Artifact-generation parent SHA: `385cd739cb6c02325e81f2a2551281f0a0fb02ff`
- Canonical dataset: `GOLD_M30_CANONICAL_V2`
- SHA-256: `c48ca44dcecae9eb1c2590c586e27c4bc5f246215c549d0d0bc1201d95d5ea1d`
- Legacy gap-stop defect confirmed: `True`
- Legacy engine modified: `False`
- Real-market strategy executed: `False`
- Synthetic unit execution only: `True`
- Final status: **`CANONICAL_EXECUTION_CONTRACT_PASS`**

## Confirmed legacy defect

- legacy_buy_stop_uses_low_touch: `PASS`
- legacy_buy_stop_fills_at_old_stop: `PASS`
- legacy_sell_stop_uses_ask_high_touch: `PASS`
- legacy_sell_stop_fills_at_old_stop: `PASS`
- legacy_has_no_explicit_gap_stop_branch: `PASS`

## Hardened contract checks

- separate_adapter_not_legacy_mutation: `PASS`
- buy_gap_stop_branch_present: `PASS`
- buy_gap_exit_at_open_present: `PASS`
- sell_ask_open_defined: `PASS`
- sell_gap_stop_branch_present: `PASS`
- sell_gap_exit_at_ask_open_present: `PASS`
- gap_exit_reason_present: `PASS`
- next_open_entry_present: `PASS`
- pessimistic_ambiguous_present: `PASS`
- favorable_tp_capped: `PASS`
- canonical_v2_authorized: `PASS`
- post_eval_buffer_pass: `PASS`

## Post-evaluation buffer

- Evaluation end: `2026-06-30T23:30:00+00:00`
- Dataset last datetime: `2026-08-14T23:30:00+00:00`
- Required buffer minutes: `3600`
- Available buffer minutes: `64800.0`
- Buffer check: `PASS`

## Scientific conclusion

> **CANONICAL_EXECUTION_CONTRACT_PASS**

A PASS authorizes the hardened canonical execution adapter for a future independently precommitted research chapter. It does not validate any legacy backtest and does not start a strategy.

## Stop rule

No H-221, LMDC rerun, parameter tuning, or new mechanism batch is executed by V3.7.3.
