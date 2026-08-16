# V3.7 CANONICAL DATA AUDIT REPORT

- Dataset: `GOLD_M30`
- SHA-256: `979d7e410efbdc17e37ecae7f6a37ed30ba1844097bd012f2b90dd6d0be4f5f0`
- Rows: `99999`
- Structural validation: `PASS`
- Lineage: `UNRESOLVED`
- Timestamp semantic: `UNRESOLVED`
- Timezone status: `NAIVE_UNRESOLVED`
- Research eligibility: **`BLOCKED`**

## Blocking reasons

- `TIMESTAMP_SEMANTIC_UNRESOLVED`
- `TIMESTAMP_TIMEZONE_UNRESOLVED`
- `LINEAGE_NOT_VERIFIED`
- `SOURCE_TYPE_UNRESOLVED`
- `SOURCE_IDENTIFIER_UNRESOLVED`
- `EXTRACTION_METHOD_UNRESOLVED`
- `TRANSFORM_CHAIN_UNRESOLVED`
- `PROVENANCE:PROVENANCE_SIDECAR_NOT_FOUND`

## Governance interpretation

Structural integrity is not provenance. M30 cadence does not prove bar-open/bar-close semantics, and naive timestamps are not promoted to UTC without exact-hash source evidence.
