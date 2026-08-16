# QUANT RESEARCH V3.7 — CANONICAL DATA LINEAGE & BAR-TIMESTAMP CONTRACT

## STATUS

AUDIT / DATA-FOUNDATION ONLY.

Parent scientific closure:

`41ce08655d6e3a23fd5d11c646ebbc7bf4d79bd4`

Branch:

`research/quant-v3.7-canonical-data-lineage`

V3.7 exists because V3.6.1 proved that `GOLD_M30.csv` has insufficient provenance to establish whether bar timestamps denote bar-open time or bar-close time.

## ABSOLUTE SCOPE

V3.7 MUST NOT:

- create H-221 or any new trading hypothesis;
- backtest a new strategy;
- tune any historical strategy;
- reinterpret LMDC;
- change `GOLD_M30.csv` values;
- infer timestamp semantics from 30-minute cadence;
- infer timezone from apparent session behavior;
- infer source lineage merely from generic `CopyRates` / `copy_rates_*` occurrences elsewhere in the repository.

V3.7 may ONLY build and execute deterministic data-governance tooling.

## CANONICAL DATA PRINCIPLE

A dataset is not canonical merely because:

- it parses;
- OHLC values are internally consistent;
- timestamps are monotonic;
- cadence resembles the advertised timeframe.

A dataset is canonical for new research only when the following are explicitly established:

1. immutable file hash;
2. exact source identity;
3. extraction/export method;
4. transformation lineage;
5. timezone / offset convention;
6. timestamp semantic: BAR_OPEN_TIME or BAR_CLOSE_TIME (or another explicit semantic for non-bar data);
7. symbol/instrument identity;
8. timeframe;
9. OHLC schema semantics;
10. deterministic validation status.

## FAIL-CLOSED RULE

If ANY required lineage field is unresolved, new quantitative research using that dataset must be classified:

`RESEARCH_ELIGIBILITY = BLOCKED`

The tooling must never silently fill unresolved fields using convention, model knowledge, file cadence, broker assumptions, or performance results.

## EXPLICIT EVIDENCE HIERARCHY

Highest to lowest:

1. immutable source/export manifest that directly names the dataset/hash;
2. exporter code plus deterministic proof that it produced the exact dataset/hash;
3. source documentation plus deterministic transform chain proving no time shift/relabeling;
4. repository notes with verifiable linkage to the exact file/hash.

The following are NOT sufficient by themselves:

- generic MT5 API usage in unrelated scripts;
- matching symbol names;
- matching row counts;
- 30-minute cadence;
- session behavior;
- assumptions about common platform conventions.

## REQUIRED GOLD_M30 CANONICAL MANIFEST FIELDS

The machine-generated manifest must include at minimum:

- `dataset_id`
- `relative_path`
- `sha256`
- `size_bytes`
- `row_count`
- `columns`
- `first_timestamp`
- `last_timestamp`
- `timestamp_column`
- `timestamp_parse_status`
- `timestamp_timezone_status`
- `timestamp_timezone`
- `timestamp_semantic`
- `timeframe`
- `median_delta_minutes`
- `pct_expected_cadence`
- `duplicate_timestamp_count`
- `non_monotonic_timestamp_count`
- `ohlc_violation_count`
- `source_type`
- `source_identifier`
- `exporter_or_extraction_method`
- `exporter_path`
- `transform_chain`
- `lineage_status`
- `research_eligibility`
- `blocking_reasons`

## TIME SEMANTICS ENUM

Only these values are allowed for bar data:

- `BAR_OPEN_TIME`
- `BAR_CLOSE_TIME`
- `UNRESOLVED`

No heuristic third state such as `LIKELY_OPEN` is allowed for research authorization.

## TIMEZONE ENUM

Allowed high-level states:

- `EXPLICIT_UTC`
- `EXPLICIT_OFFSET`
- `NAIVE_UNRESOLVED`

Naive timestamps without immutable source metadata are not to be treated as UTC merely because prior code called them UTC.

## LINEAGE STATUS

- `VERIFIED`: exact source/export/transform chain tied to this file/hash.
- `PARTIAL`: some evidence exists but the chain is incomplete.
- `UNRESOLVED`: no deterministic chain proving origin and transforms.

Only `VERIFIED` may authorize new research.

## STRUCTURAL DATA TESTS

The auditor must calculate independently:

- SHA-256;
- row count;
- file size;
- columns;
- timestamp parse success;
- first/last timestamps;
- duplicate timestamps;
- non-monotonic timestamps;
- median cadence;
- percentage of deltas matching expected M30 cadence;
- null OHLC count;
- `high < low` violations;
- `high < max(open, close)` violations;
- `low > min(open, close)` violations.

These tests establish structural integrity only. They do NOT establish provenance or timestamp meaning.

## PROVENANCE SIDECAR

The auditor may consume an explicit sidecar file if present:

`AlphaLab_Antigravity/data/provenance/GOLD_M30.source.json`

But it must validate that the sidecar binds to the exact current dataset hash.

A sidecar whose declared SHA-256 differs from the actual dataset is invalid evidence.

## REQUIRED OUTPUTS

Execution must create under:

`AlphaLab_Antigravity/reports/v3_7/`

- `GOLD_M30.canonical_manifest.json`
- `GOLD_M30.structural_audit.json`
- `V3_7_DATA_ELIGIBILITY_DECISION.json`

And a human-readable:

`V3_7_CANONICAL_DATA_AUDIT_REPORT.md`

## EXPECTED CURRENT OUTCOME

Do NOT force this expectation, but based on V3.6.1 the likely current state is:

- structural integrity may PASS;
- timestamp semantics likely UNRESOLVED;
- timezone likely UNRESOLVED unless explicit source evidence exists;
- lineage likely UNRESOLVED;
- new-research eligibility therefore BLOCKED.

If stronger immutable evidence is found, record it exactly and let the deterministic contract decide.

## PROMOTION RULE

A dataset becomes eligible for NEW research only if ALL are true:

- SHA-256 recorded;
- structural validation PASS;
- `timestamp_semantic != UNRESOLVED`;
- timezone state is explicit;
- lineage status = `VERIFIED`;
- source identity and extraction method are explicit;
- transform chain is explicit;
- no unresolved blocking reason remains.

No discretionary override.

## GIT ORDER

1. Commit A — this precommit.
2. Commit B — canonical contract implementation.
3. Commit C — auditor implementation.
4. Commit D — tests.
5. Commit E — execution handoff/report generator if required.
6. Executor runs tooling and commits raw machine artifacts.
7. Executor generates final report and commits separately.

## STOP RULE

After V3.7 data audit, STOP.

Do not automatically resume LMDC or create H-221/H-222.

If the dataset remains BLOCKED, the next scientific task is provenance acquisition/re-export, not strategy research.
