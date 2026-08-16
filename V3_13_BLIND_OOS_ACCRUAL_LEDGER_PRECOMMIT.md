# V3.13 — BLIND OOS ACCRUAL LEDGER PRECOMMIT

Scientific parent: V3.12 final `c1d7ba04aeb3b5bbc275a1a223c9d2bb5624a315`.

## Purpose

Operational governance only. V3.13 creates immutable, hash-chained checkpoints for future fresh-OOS accrual and readiness state. It does not evaluate H226 outcomes, does not run a strategy, and does not authorize strategy design.

## Frozen scientific state

- Historical H226 strategies: REJECTED.
- Same-sample H226 research: CLOSED.
- Canonical authority: `GOLD_M30_CANONICAL_V2`, SHA-256 `c48ca44dcecae9eb1c2590c586e27c4bc5f246215c549d0d0bc1201d95d5ea1d`.
- Canonical freeze cutoff: `2026-08-14T23:30:00Z` inclusive.
- Bridge quarter: `2026Q3`, permanently quarantined.
- First complete decision quarter: `2026Q4`.
- OOS maturity contract remains V3.12: >=8 complete quarters, C1>=160 total, C4>=100 total, every complete quarter C1>=10 and C4>=5.

## Ledger contract

Each checkpoint is a new immutable JSON file under:

`AlphaLab_Antigravity/reports/v3_13/checkpoints/`

Checkpoint fields include:

- monotonically increasing `sequence`;
- `created_at_utc`;
- `scientific_parent_v312_final`;
- canonical dataset ID/hash/cutoff;
- previous checkpoint filename and exact SHA-256, or null for genesis;
- fresh-OOS file presence;
- fresh-OOS dataset SHA-256 if present;
- fresh-OOS provenance SHA-256 if present;
- OOS row count / first timestamp / last timestamp if present;
- previous OOS dataset SHA-256 recorded by the current source sidecar;
- complete decision-quarter list;
- C1/C4 readiness counts only;
- readiness status and maturity checks;
- hardcoded `outcome_metrics_computed=false`, `trading_engine_called=false`, `strategy_executed=false`, `strategy_design_authorized=false`, `same_sample_h226_research_closed=true`.

The checkpoint filename is deterministic from sequence and UTC creation time. Existing checkpoint files may never be overwritten.

## Chain validation

Before writing a new checkpoint, the writer must:

1. discover existing checkpoint JSON files;
2. validate sequences are contiguous from 1..N;
3. recompute every checkpoint file SHA-256;
4. verify each checkpoint N references the exact filename and SHA-256 of checkpoint N-1;
5. fail closed on duplicate sequence, missing sequence, broken parent pointer, malformed JSON, or future/non-monotonic checkpoint timestamps.

## No-peeking rule

The ledger and its tests/auditor may not calculate or serialize:

- signed 8h returns;
- excess reversion;
- MFE/MAE;
- gap-closure outcome;
- PF;
- expectancy;
- strategy fills or PnL.

Eligibility counts are permitted because they use only information available at the frozen signal-close time.

## OOS immutability rule

If a fresh-OOS file exists, the ledger must verify V3.12 provenance and temporal partition before checkpointing. A previously checkpointed dataset SHA may differ from the current dataset SHA only because new rows were appended under the V3.12 exporter. The ledger does not revise or relabel prior acquired bars.

## Execution order

A future executor may:

1. run frozen V3.13 tests;
2. run the frozen V3.12 exporter exactly once;
3. create one V3.13 blind checkpoint;
4. commit raw checkpoint evidence;
5. generate a human checkpoint report from the new checkpoint;
6. commit report;
7. stop.

No outcome evaluator is authorized even if maturity is reached; maturity only permits a separately precommitted future evaluator chapter.
