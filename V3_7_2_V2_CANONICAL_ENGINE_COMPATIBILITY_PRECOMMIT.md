# V3.7.2 V2 CANONICAL ENGINE COMPATIBILITY PRECOMMIT

## PURPOSE

V3.7.2 is a DATA/ENGINE INTERFACE AUDIT ONLY.

It does not create H-221, a strategy, an event study, a backtest candidate, or a parameter search.

Scientific parent:

`4062f755b50af5369c81912f15c62990d36b4eb9`

Target branch:

`research/quant-v3.7.2-v2-canonical-engine-compatibility`

Canonical authority:

- file: `AlphaLab_Antigravity/data/canonical/GOLD_M30_CANONICAL_V2.csv`
- frozen SHA-256: `c48ca44dcecae9eb1c2590c586e27c4bc5f246215c549d0d0bc1201d95d5ea1d`
- timestamp semantic: `BAR_OPEN_TIME`
- timezone: `UTC`
- request-boundary representation: `UNIX_EPOCH_SECONDS_UTC`
- lineage: `VERIFIED`
- V3.7.1.1 status: `CANONICAL_V2_REPRODUCTION_ELIGIBLE`

The earlier V3.7.1 canonical file is byte-identical but is NOT the provenance authority because its technical repair used timezone-naive request boundaries. V2 is the sole canonical authority for this phase.

## DISCOVERED ENGINE INTERFACE DEFECT

The legacy `DeepQuantEngine._prepare_dataframe()` searches timestamp columns in an order that can select numeric `time` before the canonical `timestamp_utc` field. Calling `pd.to_datetime()` on Unix seconds without `unit="s"` can interpret seconds as nanoseconds and corrupt the calendar to 1970-era timestamps.

This defect was discovered before any strategy research on canonical data.

## FROZEN REPAIR DESIGN

Do NOT modify `deep_quant_engine.py`.

Instead create a dedicated `CanonicalV2DeepQuantEngine` adapter that:

1. accepts only the authorized V2 canonical lineage;
2. requires `timestamp_utc` for canonical research;
3. parses `timestamp_utc` with `utc=True`;
4. if numeric `time` is tested as a fallback, parses it with `unit="s", utc=True`;
5. inherits execution logic unchanged from `DeepQuantEngine`;
6. fixes the instrument spec to `STANDARD_SPECS["GOLD"]`;
7. never calls `run_strategy` during V3.7.2.

## FAIL-CLOSED AUTHORIZATION

The adapter must fail closed unless all machine artifacts agree on the exact V2 dataset:

- actual CSV SHA-256;
- V2 source sidecar SHA;
- V2 manifest SHA;
- V2 reproduction decision SHA;
- `research_eligibility == ELIGIBLE`;
- `canonical_v2_status == CANONICAL_V2_REPRODUCTION_ELIGIBLE`;
- `lineage_status == VERIFIED`;
- `timestamp_semantic == BAR_OPEN_TIME`;
- `timestamp_timezone_status == EXPLICIT_UTC`;
- timezone == UTC;
- `request_boundary_representation == UNIX_EPOCH_SECONDS_UTC`;
- structural validation == PASS;
- coverage == PASS;
- no blocking reasons.

## LEGACY/CANONICAL CONCORDANCE

A diagnostic comparison against legacy `GOLD_M30.csv` is allowed only to quantify empirical similarity.

Precommitted views:

- same-label OHLC exact-match rate;
- canonical labels shifted +30 minutes vs legacy;
- canonical labels shifted -30 minutes vs legacy;
- overlap-row counts;
- max and mean OHLC absolute differences;
- tick-volume/spread exact-match rates where available.

This audit MUST NOT change legacy status `BLOCKED` or infer its provenance.

## ENGINE COMPATIBILITY PASS CONDITIONS

All must pass:

1. exact V2 SHA authorization succeeds;
2. V2 decision and sidecar satisfy the frozen canonical contract;
3. adapter first timestamp is `2018-02-22T18:30:00+00:00`;
4. adapter last timestamp is `2026-08-14T23:30:00+00:00`;
5. timezone is UTC;
6. min/max years are 2018/2026, not 1970;
7. 2018Q2 and 2026Q2 are present;
8. instrument spec is GOLD / COMMODITY;
9. row count remains 100000;
10. no strategy is executed.

Allowed final statuses:

`CANONICAL_V2_ENGINE_COMPATIBILITY_PASS`

or

`CANONICAL_V2_ENGINE_COMPATIBILITY_BLOCKED`

## STOP RULE

Even if PASS:

- do not create H-221;
- do not rerun LMDC;
- do not run a strategy;
- do not tune parameters;
- do not start a new mechanism chapter automatically.

Return compatibility evidence for independent audit first.
