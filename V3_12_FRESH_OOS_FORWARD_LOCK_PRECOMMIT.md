# V3.12 FRESH-OOS FORWARD LOCK — PRECOMMIT

## Purpose
V3.11 closes all same-sample H226 research on the historical 2018Q2–2026Q2 evaluation sample. V3.12 does not design a strategy. It establishes a fail-closed forward-OOS acquisition and maturity contract before new observations exist.

## Scientific parent
`b821248667badea5e763173101c52ef95dbcf5d4`

## Frozen canonical authority
- Dataset: `GOLD_M30_CANONICAL_V2`
- SHA-256: `c48ca44dcecae9eb1c2590c586e27c4bc5f246215c549d0d0bc1201d95d5ea1d`
- Last canonical bar open UTC: `2026-08-14T23:30:00+00:00`
- Source lineage: XM Global Limited / XMGlobal-MT5 9 / GOLD / M30 / BAR_OPEN_TIME / UTC / Unix epoch request boundaries.

## Temporal partition
- Historical development/evaluation chapter remains closed through `2026Q2`.
- Bars already present after 2026Q2 but on or before the canonical freeze cutoff are **BRIDGE_QUARANTINED**. They can be used only for continuity checks/warm-up, never as fresh-OOS decision evidence.
- Canonical freeze cutoff: `2026-08-14T23:30:00+00:00` inclusive.
- True fresh OOS bars must have bar-open timestamps strictly greater than that cutoff.
- The first complete calendar quarter eligible for fresh-OOS decision evidence is `2026Q4`.

## No backfill rule
No historical bar with timestamp <= the canonical freeze cutoff may ever be relabeled or copied into the fresh-OOS decision sample.

## Frozen future file identities
- Data: `AlphaLab_Antigravity/data/oos/GOLD_M30_FRESH_OOS.csv`
- Provenance: `AlphaLab_Antigravity/data/oos/GOLD_M30_FRESH_OOS.source.json`
- Readiness artifacts: `AlphaLab_Antigravity/reports/v3_12/`

The OOS dataset must be a separately identified lineage artifact. It must never overwrite canonical V2.

## Accrual-only phase
Until maturity, V3.12 may inspect only:
- timestamps;
- structural validity;
- provenance/hash;
- first-bar information required to count frozen H226-C1/C4 eligibility events.

It must NOT compute:
- 8h signed returns;
- MFE/MAE;
- gap-closure outcomes;
- cost-adjusted excess returns;
- PF/expectancy;
- strategy fills.

## Frozen event-count semantics
For readiness counts only, reproduce the already-frozen H226 signal-close eligibility condition using information available by close of the first UTC-day M30 bar:
- C1: `gap_z >= 0.05`, residual >= `0.25`;
- C4: `gap_z >= 0.10`, residual >= `0.50`;
- exclude first bars that already cross through prior close;
- ATR14 uses data available at the prior bar only.

These counts authorize maturity assessment only. They are not trades.

## Fresh-OOS maturity gate
A final fresh-OOS mechanism decision is forbidden until ALL are true:
1. At least 8 complete decision quarters are present, beginning no earlier than `2026Q4`.
2. Total C1 eligible events >= 160.
3. Total C4 eligible events >= 100.
4. Every complete decision quarter has >= 10 C1 eligible events.
5. Every complete decision quarter has >= 5 C4 eligible events.
6. Provenance, exact hash, BAR_OPEN_TIME and UTC remain verified.

Before all conditions pass, status must be one of:
- `WAITING_FOR_FIRST_FRESH_OOS_BAR`
- `FRESH_OOS_ACCRUING_NOT_MATURE`

Only after all conditions pass may a later, separately precommitted evaluator compute outcome statistics.

## No interim peeking
No return/economic-effect report may be generated before maturity. A readiness report must never contain forward return metrics.

## H226 closure remains binding
All historical H226 strategies remain REJECTED. Same-sample H226 research remains CLOSED. V3.12 does not create H227 and does not authorize a DOWN-gap or recent-regime strategy.

## Strategy authorization
`strategy_design_authorized = false` throughout V3.12.

## Single-agent rule
One agent only. No `/goal`, subagents, teams, delegation, parallel model instances, or duplicate repository contexts.
