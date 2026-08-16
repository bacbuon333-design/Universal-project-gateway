# V3.7 EXECUTION HANDOFF — CANONICAL DATA LINEAGE AUDIT

This handoff was generated after the V3.7 design/code commits.

`artifact_generation_parent_sha = 931ab047e2f62fc0414e281cd74c0d31722b973c`

The executor is NOT authorized to create strategies or to manufacture provenance.

## ROLE

You are an executor, evidence collector, and recorder.

You are not a strategy designer and not a provenance author unless you possess direct deterministic source evidence.

## FIRST ACTIONS

1. Verify repository and branch.
2. Read `V3_7_CANONICAL_DATA_LINEAGE_PRECOMMIT.md`.
3. Inspect:
   - `AlphaLab_Antigravity/src/canonical_data_contract.py`
   - `AlphaLab_Antigravity/src/audit_v3_7_canonical_data.py`
   - `AlphaLab_Antigravity/src/test_v3_7_canonical_data.py`
   - `AlphaLab_Antigravity/data/provenance/GOLD_M30.source.template.json`
4. Compile the three Python files.
5. Run the V3.7 unit tests.
6. Run the canonical data auditor exactly once under the frozen contract.

## PROVENANCE RULE

Do not create `GOLD_M30.source.json` just to make the gate pass.

You may create it ONLY if repository evidence or an externally supplied immutable source record proves all required fields AND binds them to the exact current dataset SHA-256.

Generic `CopyRates`, `copy_rates_*`, symbol similarity, cadence, or prior comments are insufficient.

## EXPECTED MACHINE OUTPUTS

`AlphaLab_Antigravity/reports/v3_7/GOLD_M30.canonical_manifest.json`

`AlphaLab_Antigravity/reports/v3_7/GOLD_M30.structural_audit.json`

`AlphaLab_Antigravity/reports/v3_7/V3_7_DATA_ELIGIBILITY_DECISION.json`

Human report:

`V3_7_CANONICAL_DATA_AUDIT_REPORT.md`

## OUTCOME A — ELIGIBLE

Only if all frozen requirements are objectively satisfied:

`RESEARCH_ELIGIBILITY = ELIGIBLE`

Then report exact evidence establishing:

- exact source identity;
- exact extraction method;
- exact transform chain;
- exact timezone;
- BAR_OPEN_TIME or BAR_CLOSE_TIME;
- dataset hash binding.

Do not start strategy research.

## OUTCOME B — BLOCKED

If any required field remains unresolved:

`RESEARCH_ELIGIBILITY = BLOCKED`

Report every blocking reason exactly from the machine artifact.

Do not override it.

The scientific next step is provenance acquisition or controlled re-export, not a strategy experiment.

## TECHNICAL REPAIRS

You may fix only demonstrable syntax, import, path, serialization, or test-runner defects that do not change:

- evidence hierarchy;
- required manifest fields;
- eligibility criteria;
- fail-closed logic;
- timestamp semantic enum;
- timezone policy;
- lineage rules.

Any technical repair must be committed before valid audit execution.

## COMMIT ORDER AFTER EXECUTION

Raw machine outputs first:

`feat(v3.7): execute canonical GOLD M30 data audit`

Then human report if generated/updated separately:

`docs(v3.7): publish canonical data eligibility conclusion`

Record actual SHAs from Git. Do not guess them.

## STOP

After V3.7 report, stop.

Do not create H-221 or any new hypothesis.

Do not rerun LMDC.

Do not modify GOLD_M30.csv.

Do not infer missing metadata from performance or common platform conventions.
