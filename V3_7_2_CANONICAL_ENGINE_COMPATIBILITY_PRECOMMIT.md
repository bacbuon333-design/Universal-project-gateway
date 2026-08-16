# V3.7.2 CANONICAL ENGINE COMPATIBILITY PRECOMMIT

## PURPOSE

V3.7.2 is a DATA/ENGINE INTERFACE AUDIT ONLY.

It does not create H-221, a strategy, an event study, a backtest candidate, or a parameter search.

The canonical dataset produced by V3.7.1 is authorized at the data-provenance layer, but it must also be proven safe at the research-engine interface before any new strategy chapter is allowed.

Scientific parent:

`468599dd44f75453aaf98143d234409599c23091`

Target branch:

`research/quant-v3.7.2-canonical-engine-compatibility`

Canonical dataset contract:

- file: `AlphaLab_Antigravity/data/canonical/GOLD_M30_CANONICAL.csv`
- frozen SHA-256 from V3.7.1: `c48ca44dcecae9eb1c2590c586e27c4bc5f246215c549d0d0bc1201d95d5ea1d`
- timestamp semantic: `BAR_OPEN_TIME`
- timezone: `UTC`
- lineage: `VERIFIED`
- V3.7.1 research eligibility: `ELIGIBLE`

## DISCOVERED INTERFACE DEFECT

The current `DeepQuantEngine._prepare_dataframe()` searches timestamp columns in this order:

`datetime_str`, `dt`, `time`, `timestamp`, `date`, `datetime`.

The canonical dataset contains both:

- `time`: Unix epoch seconds;
- `timestamp_utc`: explicit ISO-8601 UTC bar-open timestamps.

Therefore the old engine can select numeric `time` and pass it to `pd.to_datetime()` without `unit="s"`, which can interpret seconds as nanoseconds and corrupt the calendar timeline.

This defect is discovered BEFORE any canonical strategy research.

## FROZEN REPAIR

The repair is interface-only:

1. `timestamp_utc` must have first priority when present.
2. `timestamp_utc` must be parsed with `utc=True`.
3. If no explicit textual timestamp exists and numeric `time` is used, it must be parsed as Unix seconds with `unit="s", utc=True`.
4. Existing legacy files with `datetime_str` retain their existing behavior.
5. No execution, spread, PnL, SL/TP, signal, or strategy semantics may change.

## CANONICAL AUTHORIZATION LOADER

New research must not instantiate the canonical CSV merely because the file exists.

A dedicated loader must fail closed unless all of the following agree:

- actual CSV SHA-256;
- canonical manifest SHA;
- source sidecar SHA;
- V3.7.1 decision SHA;
- `research_eligibility == ELIGIBLE`;
- `lineage_status == VERIFIED`;
- `timestamp_semantic == BAR_OPEN_TIME`;
- `timestamp_timezone_status == EXPLICIT_UTC`;
- timezone == UTC;
- structural validation == PASS;
- coverage == PASS.

The loader may return a DataFrame only after this verification.

## LEGACY/CANONICAL CONCORDANCE AUDIT

A diagnostic comparison is allowed between the legacy and canonical Gold M30 files.

This comparison is NOT allowed to retroactively canonize the legacy file.

Precommitted diagnostics:

- exact overlapping timestamp count;
- same-label OHLC exact-match rate;
- same-label OHLC max absolute difference;
- canonical timestamp shifted +30m vs legacy match rate;
- canonical timestamp shifted -30m vs legacy match rate;
- date-range overlap;
- missing-bar asymmetry;
- spread/tick-volume comparison only as diagnostic if columns exist.

Interpretation rule:

- concordance may show empirical similarity;
- it cannot prove original legacy source lineage;
- it cannot overwrite the V3.7 legacy status `BLOCKED`.

## ENGINE COMPATIBILITY PASS CONDITIONS

All must pass:

1. canonical authorization loader validates the exact frozen dataset;
2. DeepQuantEngine parses canonical first/last timestamps exactly as expected UTC bar-open times;
3. engine calendar includes 2018Q2 through 2026Q2 correctly;
4. no canonical timestamp is parsed into a 1970/nanosecond artifact;
5. legacy `datetime_str` behavior remains unchanged;
6. instrument spec resolves to `GOLD` commodity economics;
7. no strategy is executed during V3.7.2.

Allowed final statuses:

`CANONICAL_ENGINE_COMPATIBILITY_PASS`

or

`CANONICAL_ENGINE_COMPATIBILITY_BLOCKED`

## STOP RULE

Even if PASS:

- do not create H-221;
- do not rerun LMDC;
- do not run a strategy;
- do not tune parameters;
- do not start a new mechanism chapter automatically.

Return the compatibility evidence for independent audit first.
