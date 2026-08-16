# V3.7.1.1 UTC-BOUNDARY CANONICAL REPRODUCTION PRECOMMIT

## STATUS OF V3.7.1

V3.7.1 produced a structurally clean, hash-bound Gold M30 dataset, but an independent audit found a semantic acquisition defect in technical-repair commit `94bc77443ef623d45d7ce2003330f03212668ae8`.

That repair converted timezone-aware UTC request boundaries to timezone-naive Python `datetime` objects before calling `MetaTrader5.copy_rates_range`.

Official MetaQuotes documentation states that Python datetime uses the local timezone while MT5 bar open times are UTC, and therefore time-based request datetimes should be created in UTC.

The V3.7.1 sidecar simultaneously described the extraction as using UTC-aware start/end boundaries. Therefore the acquisition implementation and recorded provenance contract are not exactly aligned.

V3.7.1 `ELIGIBLE` is suspended pending exact reproduction.

## PURPOSE

Reproduce the controlled Gold M30 export with one and only one semantic change:

- request boundaries are passed to `MetaTrader5.copy_rates_range` as Unix epoch seconds derived from timezone-aware UTC datetimes.

This removes local-time interpretation completely.

## IMMUTABILITY

Do not overwrite V3.7.1 artifacts.

New outputs:

- `AlphaLab_Antigravity/data/canonical/GOLD_M30_CANONICAL_V2.csv`
- `AlphaLab_Antigravity/data/provenance/GOLD_M30_CANONICAL_V2.source.json`
- `AlphaLab_Antigravity/data/provenance/GOLD_M30_CANONICAL_V2.manifest.json`
- `AlphaLab_Antigravity/reports/v3_7_1_1/GOLD_M30_CANONICAL_V2.structural_audit.json`
- `AlphaLab_Antigravity/reports/v3_7_1_1/V3_7_1_1_REPRODUCTION_DECISION.json`

## FROZEN SOURCE CONTRACT

Keep unchanged:

- broker company/server discovered from connected MT5 terminal;
- exact explicit Gold symbol supplied by operator;
- `MetaTrader5.copy_rates_range`;
- `TIMEFRAME_M30`;
- `BAR_OPEN_TIME`;
- UTC bar epoch semantics;
- request start 2018-01-01T00:00:00Z;
- end at latest fully completed M30 bar;
- no current forming candle;
- no resampling;
- no interpolation;
- no gap fill;
- no OHLC modification;
- deterministic CSV serialization;
- exact SHA-256 sidecar binding;
- no account login/name/password committed.

## FROZEN REQUEST-BOUNDARY REPRESENTATION

For every chunk:

`date_from = int(aware_utc_start.timestamp())`

`date_to = int(aware_utc_end.timestamp())`

The MT5 API explicitly allows seconds elapsed since Unix epoch for these parameters.

No `.replace(tzinfo=None)` is allowed anywhere in the acquisition path.

## CHUNKING

Two-year chunks are allowed only as transport plumbing.

Adjacent chunk boundaries may overlap because `copy_rates_range` is inclusive. Deduplicate only by raw MT5 epoch `time`.

Do not alter any OHLC or volume field during deduplication.

## TERMINAL MAX-BARS LIMIT

V3.7.1 recorded terminal `maxbars = 100000` and returned exactly 100,000 bars.

V3.7.1.1 must explicitly report:

- requested start;
- returned first bar;
- terminal maxbars;
- whether the returned dataset is capped by available terminal history.

Coverage remains sufficient for the research program only if first returned bar is no later than 2018-04-01T00:00:00Z and recency passes the frozen rule.

Do not claim the dataset contains every requested bar back to 2018-01-01 if it does not.

## BYTE-CONCORDANCE DIAGNOSTIC

After V2 is generated, compare its CSV SHA-256 with V3.7.1 V1 SHA:

`c48ca44dcecae9eb1c2590c586e27c4bc5f246215c549d0d0bc1201d95d5ea1d`

Allowed observations:

- `BYTE_IDENTICAL_TO_V3_7_1`
- `BYTE_DIFFERENT_FROM_V3_7_1`

Byte identity does not erase the V3.7.1 provenance defect; it only shows whether the defect changed returned dataset bytes under this terminal state.

## FINAL STATUS

Allowed:

`CANONICAL_V2_REPRODUCTION_ELIGIBLE`

or

`CANONICAL_V2_REPRODUCTION_BLOCKED`

No strategy research is allowed in this phase.
