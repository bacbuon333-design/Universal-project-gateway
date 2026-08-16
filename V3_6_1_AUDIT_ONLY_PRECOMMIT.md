# QUANT RESEARCH V3.6.1 — LMDC SEMANTIC CLOSURE AUDIT

## Scope
Audit-only closure of V3.6 LMDC event study. No new strategy, no H-221, no parameter tuning, no threshold search, no direction filtering, no new asset/timeframe.

## Parent
- Repository: `bacbuon333-design/Universal-project-gateway`
- Parent V3.6 final commit: `2e7c1b43138ca5e455847b0c87b58ed73dc99918`
- V3.6 frozen precommit: `a573368acfb3dd57396b9a141a5d32c1b46bff06`
- V3.6 implementation: `4ef4a52c1f4b45dbc164f86d4f8f0400261fc47f`
- V3.6 raw results: `abbb8c03ddedd032a2561ccd2202916a3ea31f7c`

## Independent audit findings to resolve

### A. Frozen falsification semantics
The V3.6 precommit states that LMDC is `falsified / NOT supported if ANY` frozen falsification criterion occurs.

V3.6 raw evidence already shows:
- Rule 4 triggered at key horizons: 1h, 2h and 4h quarter-block bootstrap 95% confidence intervals cross zero.
- Rule 5 triggered at key intraday horizons: estimated 1h/2h/4h effects are below the frozen transaction-cost benchmark.

Therefore, absent invalidation of the underlying measurements by a timestamp-semantics defect, the frozen classification must be:

`LMDC MECHANISM NOT SUPPORTED`

The softer label `LMDC MECHANISM WEAK / REGIME-DEPENDENT` is not permitted when an ANY-rule falsification condition is true.

### B. M30 timestamp semantics
V3.6 code selects the row timestamped `12:00` and uses that row's `close` as `p_ref`, while documentation calls this value `12:00 UTC close`.

V3.6.1 must determine, using evidence available in the repository/data format rather than performance outcomes, whether `GOLD_M30.csv` timestamps represent:

1. BAR_OPEN_TIME — a row stamped 12:00 covers approximately 12:00–12:30 and its close is known near 12:30; or
2. BAR_CLOSE_TIME — a row stamped 12:00 closes at 12:00.

No convention may be chosen because it gives better results.

## Timestamp decision hierarchy
Use this evidence order:

1. Explicit immutable dataset/source documentation.
2. Loader/export code that created `GOLD_M30.csv`.
3. Deterministic adjacency checks against known M30 conventions and neighboring timestamps.
4. If still unprovable: return `TIMESTAMP_SEMANTICS_AMBIGUOUS` and do not claim exact V3.6 horizon semantics.

## Required outcomes

### Outcome 1 — BAR_CLOSE_TIME proven
Do not rerun the event study merely to change numbers.
- Preserve V3.6 raw results.
- Correct the mechanism classification to `LMDC MECHANISM NOT SUPPORTED`.
- Explain which frozen falsification rules triggered.

### Outcome 2 — BAR_OPEN_TIME proven
The existing V3.6 horizon labels/reference semantics are invalid relative to the frozen language.
- Reproduce the SAME frozen event study with only timestamp alignment repaired.
- Keep event window, magnitude buckets, ATR definition, horizons, sample range, bootstrap protocol and falsification rules unchanged.
- No new threshold/filter/strategy.
- Recompute all machine outputs and apply the original ANY-rule falsification logic exactly.

### Outcome 3 — semantics cannot be proven
Do not silently pick a convention.
- Final status: `V3.6 EXACT HORIZON INTERPRETATION AMBIGUOUS — TIMESTAMP SEMANTICS UNRESOLVED`.
- The original `WEAK / REGIME-DEPENDENT` classification is withdrawn.
- No H-221 may be created.

## Additional locked interpretation rules
- A positive 8h pooled effect alone cannot rescue LMDC if frozen Rule 4 or Rule 5 already triggers at key horizons.
- Magnitude non-monotonicity must be reported descriptively; no post-hoc bucket selection.
- Recent-period behavior must not be used to invent a new regime filter.
- Long/short asymmetry is diagnostic only.

## Required files
- `V3_6_1_AUDIT_ONLY_PRECOMMIT.md`
- `AlphaLab_Antigravity/src/audit_v3_6_1_timestamp_semantics.py`
- `AlphaLab_Antigravity/src/evaluate_v3_6_1_frozen_verdict.py`
- `AlphaLab_Antigravity/src/test_v3_6_1_semantic_closure.py`
- generated evidence under `AlphaLab_Antigravity/reports/v3_6_1/`
- `V3_6_1_FINAL_AUDIT_CONCLUSION.md`

## Git protocol
- Commit A: this audit precommit only.
- Commit B: timestamp-audit/verdict code + tests only.
- Commit C: raw audit evidence and, only if required by proven BAR_OPEN_TIME semantics, exact repaired reproduction outputs.
- Commit D: machine-generated/final audit conclusion.

No results may be used to modify Commit A or to change the frozen decision rules.
