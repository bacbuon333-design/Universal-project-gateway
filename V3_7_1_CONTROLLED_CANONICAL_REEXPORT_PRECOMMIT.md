# V3.7.1 CONTROLLED CANONICAL RE-EXPORT PRECOMMIT

## PURPOSE

V3.7 established that the legacy `AlphaLab_Antigravity/data/GOLD_M30.csv` is structurally clean but scientifically BLOCKED because exact source lineage, timezone and bar timestamp semantics are unresolved.

V3.7.1 does NOT attempt to repair or relabel that legacy file.

V3.7.1 creates a NEW lineage by controlled re-export from an explicitly identified MetaTrader 5 terminal/broker feed and writes provenance at the same time as the dataset.

## SCIENTIFIC PARENT

- Parent V3.7 final: `80d09a09b5403f9379fe79bcb7522457282b8fcc`
- Branch: `research/quant-v3.7.1-controlled-canonical-reexport`

## ABSOLUTE NO-RESEARCH RULE

This phase contains no strategy research, no signals, no H-221, no backtests, no parameter tuning and no performance evaluation.

## SOURCE CONTRACT

The controlled exporter uses the official `MetaTrader5` Python integration API.

Frozen source method:

- API: `MetaTrader5.copy_rates_range`
- Timeframe: `TIMEFRAME_M30`
- Bar semantic: `BAR_OPEN_TIME`
- Timezone: `UTC`

The bar semantic and timezone are not inferred from observed cadence. They are declared from the exact extraction API contract and recorded in the generated provenance sidecar.

Official MetaQuotes documentation establishes that `copy_rates_range` selects bars by bar open time and that MetaTrader 5 stores/returns bar open times in UTC.

## SYMBOL CONTRACT

The exporter requires an explicit `--symbol` argument identifying the exact broker symbol used for Gold (for example `GOLD` or `XAUUSD`).

The exporter MUST NOT silently fall back between symbols.

The exact selected symbol is recorded with broker/server metadata in provenance.

Choosing the correct broker symbol is an acquisition identity decision, not a historical-performance decision.

## COVERAGE CONTRACT

Requested start:

`2018-01-01T00:00:00Z`

Requested end:

The open timestamp of the most recent fully completed M30 bar at execution time.

The exporter MUST exclude the currently forming M30 bar.

For compatibility with the historical research program, coverage eligibility additionally requires:

- first returned bar open <= `2018-04-01T00:00:00Z`;
- last returned bar no more than 5 calendar days behind the requested last-completed-bar open time.

A provenance-valid but short-history dataset may be CANONICAL but remains RESEARCH_COVERAGE_BLOCKED.

## OUTPUT LINEAGE

The exporter MUST NOT overwrite the legacy file.

New outputs:

- `AlphaLab_Antigravity/data/canonical/GOLD_M30_CANONICAL.csv`
- `AlphaLab_Antigravity/data/provenance/GOLD_M30_CANONICAL.source.json`
- `AlphaLab_Antigravity/data/provenance/GOLD_M30_CANONICAL.manifest.json`
- `AlphaLab_Antigravity/reports/v3_7_1/GOLD_M30_CANONICAL.structural_audit.json`
- `AlphaLab_Antigravity/reports/v3_7_1/V3_7_1_REEXPORT_DECISION.json`

## CSV CONTRACT

Required columns in deterministic order:

1. `time`
2. `timestamp_utc`
3. `open`
4. `high`
5. `low`
6. `close`
7. `tick_volume`
8. `spread`
9. `real_volume`

`time` is the raw Unix epoch seconds returned by MT5.

`timestamp_utc` is deterministically derived from `time`, serialized as an explicit UTC ISO-8601 timestamp.

Rows are sorted strictly ascending by `time` and exact duplicate `time` values are forbidden.

## STRUCTURAL VALIDATION

Required PASS conditions:

- non-empty output;
- required columns present;
- `time` strictly increasing;
- zero duplicate timestamps;
- OHLC finite;
- high >= low;
- high >= max(open, close);
- low <= min(open, close);
- median cadence = 30 minutes;
- no bar timestamp later than requested final completed bar open.

Gaps caused by market closure are allowed and must not be filled synthetically.

## PROVENANCE SIDECAR

The sidecar is generated automatically AFTER the canonical CSV is written and hashed.

Required provenance includes:

- exact dataset SHA-256;
- dataset byte size and row count;
- source type;
- broker/company;
- broker server;
- exact broker symbol;
- extraction method;
- exporter repository path;
- exporter Git SHA;
- MetaTrader5 Python package version;
- terminal build/version metadata when available;
- extraction generated-at UTC;
- requested start/end UTC;
- returned first/last bar UTC;
- `BAR_OPEN_TIME` semantic;
- `EXPLICIT_UTC` timezone contract;
- deterministic transform chain;
- official documentation references.

Sensitive account identifiers such as account login/name MUST NOT be written to repository artifacts.

## TRANSFORM CHAIN

Frozen deterministic transforms:

1. initialize explicitly identified MetaTrader 5 terminal connection;
2. request broker symbol M30 rates via `copy_rates_range` using UTC-aware start/end datetimes;
3. preserve raw MT5 `time,open,high,low,close,tick_volume,spread,real_volume` fields;
4. sort ascending by raw epoch `time`;
5. reject duplicate epoch timestamps;
6. derive `timestamp_utc` directly from epoch seconds with UTC timezone;
7. serialize deterministic CSV with fixed column order;
8. calculate SHA-256 on exact serialized bytes;
9. create hash-bound provenance and manifest JSON.

No interpolation, resampling, timezone shift, OHLC modification, gap filling or price normalization is allowed.

## OFFICIAL TIME SEMANTIC CONTRACT

The new dataset can use `BAR_OPEN_TIME` and `EXPLICIT_UTC` because this semantic is tied directly to the frozen source API, not inferred from the legacy file.

If execution uses any source other than the frozen MetaTrader5 Python rates API, this precommit does NOT authorize that export.

## SOURCE IDENTITY REQUIREMENTS

The exporter must capture non-sensitive terminal/account source identity.

At minimum:

- broker/company must be non-empty;
- server must be non-empty;
- selected symbol must exist and be queryable;
- rates request must return data.

If broker/server identity cannot be obtained, final lineage is BLOCKED rather than guessed.

## CANONICAL ELIGIBILITY

`CANONICAL_LINEAGE_VERIFIED = True` requires:

- exact CSV hash bound to sidecar;
- source identity complete;
- exporter identity complete;
- explicit BAR_OPEN_TIME;
- explicit UTC;
- non-empty deterministic transform chain;
- structural validation PASS.

`RESEARCH_ELIGIBILITY = ELIGIBLE` additionally requires coverage PASS.

Otherwise fail closed.

## REPRODUCIBILITY

Every execution records environment metadata, but environmental metadata must not be allowed to change semantic decisions.

The same raw MT5 response serialized under this frozen transform must produce deterministic CSV bytes and SHA-256.

## GIT GOVERNANCE

Required order:

A. This precommit exists before exporter execution.

B. Exporter/tests are committed before execution.

C. Execution writes data/provenance/audit artifacts and commits them separately.

D. Final report is generated/committed separately.

No performance research follows automatically.

## STOP RULE

After controlled export and canonical validation:

- if ELIGIBLE: stop and return evidence for independent audit;
- if BLOCKED: stop and return exact blockers;
- do not start strategy research in V3.7.1.
