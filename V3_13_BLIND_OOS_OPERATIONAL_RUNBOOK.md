# V3.13 BLIND OOS OPERATIONAL RUNBOOK

Operational continuation after accepted V3.13.1.1 provenance closure.

Scientific closure parent: `1971fc24a7649d6a788d0b5c0d66528a9a8baf2e`

This is **not** a new research chapter. It is the recurring operating procedure for fresh-OOS accrual and blind readiness checkpoints.

## 1. Frozen scientific state

- Historical H226 strategies remain `REJECTED`.
- Same-sample H226 research remains `CLOSED`.
- Strategy design remains `NOT AUTHORIZED`.
- Future OOS outcome evaluator remains `NOT AUTHORIZED` until a separate precommitted evaluation chapter is created after maturity.
- No H227 or H226 descendant may be created under this runbook.

## 2. Frozen temporal authority

- Canonical historical dataset: `GOLD_M30_CANONICAL_V2`
- Canonical SHA-256: `c48ca44dcecae9eb1c2590c586e27c4bc5f246215c549d0d0bc1201d95d5ea1d`
- Canonical cutoff inclusive: `2026-08-14T23:30:00Z`
- `2026Q3` is permanently `BRIDGE_QUARANTINED`.
- First complete OOS decision quarter: `2026Q4`.
- Any bar at or before the canonical cutoff is forbidden from fresh-OOS storage.

## 3. Frozen checkpoint authority

- Hash scheme: `SHA256_UTF8_LF_NORMALIZED_V1`.
- Genesis checkpoint: `000001_20260816T111146Z.json`.
- Authoritative genesis chain SHA: `b45ac406bfa7da1436f23f0add600a6354485b5a4d5d25c064b3470e23300876`.
- Historical local-worktree SHA `f8f97c2a7aa47e79784f37dc83072896971d52a34fef8ba28248351447ac000b` is `SUPERSEDED_FOR_LEDGER_CHAIN_AUTHORITY`.
- Checkpoint #2 and later must point to the canonical hash of the immediately prior checkpoint.
- Existing checkpoint files and reports are immutable.

## 4. Frozen maturity contract

A future OOS evaluation chapter may be proposed only after all readiness conditions pass:

1. at least 8 complete decision quarters, beginning no earlier than `2026Q4`;
2. C1 total >= 160;
3. C4 total >= 100;
4. every complete decision quarter has C1 >= 10;
5. every complete decision quarter has C4 >= 5;
6. OOS provenance and ledger chain remain valid.

Maturity does **not** itself authorize outcome evaluation. It only permits the independent research designer to freeze a separate evaluator before any OOS outcomes are opened.

## 5. Before every recurring run

1. Checkout `ops/quant-v3.13-blind-oos-accrual`.
2. Record `PRE_RUN_HEAD = git rev-parse HEAD`.
3. Require a clean working tree before execution.
4. Compile the frozen exporter, checkpoint writer, and tests.
5. Run the V3.13.1 hash-repair tests and relevant V3.13 ledger tests before mutation.
6. If any code repair is required, **STOP**. Commit the technical repair separately, obtain a new clean HEAD, rerun tests, then restart the operational run. Never combine a source repair with raw accrual/checkpoint evidence.

## 6. Recurring acquisition sequence

Run exactly once:

`python AlphaLab_Antigravity/src/export_v3_12_fresh_oos_mt5.py --symbol GOLD`

Exact source contract remains:

- Broker company: `XM Global Limited`
- Broker server: `XMGlobal-MT5 9`
- Symbol: `GOLD`
- Timeframe: `M30`
- Timestamp semantic: `BAR_OPEN_TIME`
- Timezone: `UTC`
- Request boundary: `UNIX_EPOCH_SECONDS_UTC`

Allowed exporter results:

- `NO_FRESH_BARS_AVAILABLE`
- `FRESH_OOS_ACCRUAL_WRITTEN`

### If `NO_FRESH_BARS_AVAILABLE`

Do not lower the cutoff. Do not synthesize data. Do not create a redundant checkpoint. Stop the operational run with no repository mutation.

### If `FRESH_OOS_ACCRUAL_WRITTEN`

Verify the OOS CSV/source pair, SHA/provenance, exact broker identity, strict timestamp partition, append-only history, and absence of conflicting duplicate timestamps. Then continue to checkpoint creation.

## 7. Create exactly one blind checkpoint after new data

Run exactly once:

`python AlphaLab_Antigravity/src/create_v3_13_blind_oos_checkpoint.py`

The new checkpoint must:

- use the next contiguous sequence;
- use `SHA256_UTF8_LF_NORMALIZED_V1`;
- point to the canonical hash of the immediately prior checkpoint;
- preserve strictly increasing checkpoint time;
- include only provenance, storage state, C1/C4 eligibility counts, maturity checks, and readiness status;
- contain no post-signal outcome information.

Revalidate the full ledger chain after checkpoint creation.

## 8. Absolute no-peeking boundary

Before a separately precommitted OOS evaluator exists, do **not** compute or expose:

- signed 8h return;
- any forward return;
- economic excess;
- MFE or MAE;
- gap-closure outcome;
- PF;
- expectancy;
- win rate;
- strategy PnL;
- simulated fills.

Do not call `run_strategy` or `CanonicalV2ExecutionEngine`.

## 9. Commit discipline

After a successful new-data accrual and checkpoint:

1. Commit OOS CSV/source changes and the new checkpoint as **raw evidence**.
2. Record the raw commit SHA.
3. Only after the raw commit exists, generate the immutable checkpoint report with `generate_v3_13_checkpoint_report.py`.
4. Commit the report separately.
5. Stop.

No research interpretation, parameter change, new strategy, or additional acquisition run is allowed in the same cycle.

## 10. When maturity eventually passes

If readiness status becomes `FRESH_OOS_MATURE_FOR_SEPARATELY_PRECOMMITTED_EVALUATION`:

- do **not** evaluate outcomes;
- do **not** inspect 8h returns;
- do **not** create a strategy;
- stop after committing the blind checkpoint/report;
- return evidence to the independent research designer.

Only then may a new, separately frozen OOS evaluation chapter be designed.

## 11. Current intended next action

Wait for genuinely new Gold M30 bars after the frozen cutoff. The next meaningful mutation is the first successful fresh-OOS append followed by checkpoint `000002` under this repaired protocol.
