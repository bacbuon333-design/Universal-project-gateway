# V3.6.1 EXECUTION HANDOFF — E.7

## Role
Executor and evidence recorder only. Do not redesign LMDC and do not create a new strategy.

## Expected initial branch
`research/quant-v3.6.1-lmdc-semantic-closure`

Expected initial HEAD:
`1762ec68e50e21ae7c157d6018ad9ac8e32bc72a`

Parent V3.6 final:
`2e7c1b43138ca5e455847b0c87b58ed73dc99918`

## Existing V3.6.1 files
- `V3_6_1_AUDIT_ONLY_PRECOMMIT.md`
- `AlphaLab_Antigravity/src/audit_v3_6_1_timestamp_semantics.py`
- `AlphaLab_Antigravity/src/evaluate_v3_6_1_frozen_verdict.py`
- `AlphaLab_Antigravity/src/test_v3_6_1_semantic_closure.py`

## Execute in this order
1. Verify exact Git branch/HEAD and clean working tree.
2. Compile the three V3.6.1 Python files.
3. Run `test_v3_6_1_semantic_closure.py`.
4. Run `audit_v3_6_1_timestamp_semantics.py`.
5. Inspect `timestamp_semantics_audit.json` and independently inspect every evidence hit used by the classifier.
6. Run `evaluate_v3_6_1_frozen_verdict.py`.
7. Save raw stdout/test logs/evidence under `AlphaLab_Antigravity/reports/v3_6_1/` and commit them separately.

## Critical human/evidence check
Do not accept a classifier result merely because a regex matched text.

For any `BAR_OPEN_TIME_PROVEN` or `BAR_CLOSE_TIME_PROVEN` result, verify the cited source file actually proves the timestamp meaning of `GOLD_M30.csv` or its exporter.

M30 spacing by itself is NOT proof.

A generic mention of CopyRates/copy_rates by itself is NOT enough unless the exporter/data lineage connection to `GOLD_M30.csv` is proven.

If the source chain cannot be proven, override final semantic status to:

`TIMESTAMP_SEMANTICS_AMBIGUOUS`

and record exactly why.

## Conditional stop rules

### If BAR_CLOSE_TIME is proven
- Existing V3.6 numerical outputs remain the authoritative measurements.
- Frozen rules 4 and 5 are already triggered by committed raw evidence.
- Final scientific classification must be:

`LMDC MECHANISM NOT SUPPORTED`

- Generate `V3_6_1_FINAL_AUDIT_CONCLUSION.md`, commit it, then STOP.

### If timestamp semantics remain unresolved
- Do not choose a convention.
- Final status must state:

`V3.6 EXACT HORIZON INTERPRETATION AMBIGUOUS — TIMESTAMP SEMANTICS UNRESOLVED`

- Withdraw the prior `WEAK / REGIME-DEPENDENT` label.
- Generate `V3_6_1_FINAL_AUDIT_CONCLUSION.md`, commit it, then STOP.

### If BAR_OPEN_TIME is proven
- Existing V3.6 horizon alignment is not semantically exact.
- DO NOT modify `lmdc_event_study_engine.py`.
- DO NOT create a corrected event engine.
- DO NOT rerun with a self-authored repair.
- Save the proof, commit the audit evidence, and STOP with:

`ALIGNMENT_REPRODUCTION_REQUIRED — RETURN TO INDEPENDENT DESIGNER`

The independent designer will write the exact-alignment rerun code in a subsequent commit.

## Prohibited
- H-221 or any new H-ID
- new threshold or bucket
- long-only/short-only variants
- new regime filter
- new session definition
- asset/timeframe change
- strategy backtest
- optimization
- selecting the 8h effect as a rescue argument

## Required final response
Report actual:
- branch
- initial HEAD
- test results
- timestamp semantic status
- source files/lines supporting that status
- Rule 4 evidence
- Rule 5 evidence
- raw-evidence commit SHA
- final-report commit SHA if a final report is allowed by the conditional stop rule
- exact final status

Then STOP.
