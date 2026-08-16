# V3.7.2 V2 CANONICAL ENGINE COMPATIBILITY REPORT

- Artifact-generation parent SHA: `0ec52afc9d16e64df53782a2d4228f9a2629d074`
- Canonical dataset: `GOLD_M30_CANONICAL_V2`
- SHA-256: `c48ca44dcecae9eb1c2590c586e27c4bc5f246215c549d0d0bc1201d95d5ea1d`
- Rows: `100000`
- First parsed datetime: `2018-02-22T18:30:00+00:00`
- Last parsed datetime: `2026-08-14T23:30:00+00:00`
- Parsed timezone: `UTC`
- Timestamp semantic: `BAR_OPEN_TIME`
- Request boundary: `UNIX_EPOCH_SECONDS_UTC`
- Instrument: `GOLD / COMMODITY`
- Strategy executed: `False`
- Final status: **`CANONICAL_V2_ENGINE_COMPATIBILITY_PASS`**

## Compatibility checks

- frozen_sha_match: `PASS`
- dataset_id_v2: `PASS`
- calendar_not_1970: `PASS`
- first_timestamp_correct: `PASS`
- last_timestamp_correct: `PASS`
- timezone_utc: `PASS`
- has_2018Q2: `PASS`
- has_2026Q2: `PASS`
- gold_spec: `PASS`
- row_count_100000: `PASS`
- request_boundary_epoch_utc: `PASS`
- data_authorized: `PASS`

## Legacy/canonical empirical concordance

Legacy research eligibility remains: **`BLOCKED`**.

- Canonical labels missing in legacy inside common range: `0`
- Legacy labels missing in canonical inside common range: `0`

### Same label

- Shift minutes: `0`
- Overlap rows: `99310`
- All-OHLC exact-match rate: `100.000000%`

### Canonical +30m to legacy

- Shift minutes: `30`
- Overlap rows: `97137`
- All-OHLC exact-match rate: `0.000000%`

### Canonical -30m to legacy

- Shift minutes: `-30`
- Overlap rows: `97138`
- All-OHLC exact-match rate: `0.000000%`


## Interpretation boundary

Concordance is descriptive only. It does not retroactively prove the legacy file's source, timezone, or bar-label semantics, and does not change legacy status `BLOCKED`.

## Scientific conclusion

> **CANONICAL_V2_ENGINE_COMPATIBILITY_PASS**

A PASS authorizes the V2 canonical dataset/engine interface for a future independently precommitted research chapter. It does not validate prior strategies or authorize strategy execution inside V3.7.2.

## Stop rule

No strategy, H-221, LMDC rerun, parameter tuning, or new mechanism batch is executed by this report.
