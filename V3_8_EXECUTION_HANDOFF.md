# V3.8 EXECUTION HANDOFF

Executor role only. No redesign, no tuning, no subagents.

## Frozen branch

`research/quant-v3.8-new-mechanisms-canonical-v2`

## Required sequence

1. Verify exact branch/HEAD and clean worktree.
2. Read `V3_8_CANONICAL_NEW_MECHANISM_PRECOMMIT.md`.
3. Compile V3.8 evaluator, experiment, tests and report generator.
4. Run `test_v3_8_new_mechanisms.py`.
5. If all tests pass, execute `experiment_v3_8_h221_to_h226.py` exactly once.
6. Inspect all machine artifacts and confirm exactly 24 config rows, 6 families and 14 frozen gate columns.
7. Commit raw machine artifacts separately.
8. Run `generate_v3_8_report.py` only after the raw commit exists.
9. Commit `V3_8_CANONICAL_NEW_MECHANISM_REPORT.md` separately.
10. Return evidence and STOP.

## Technical repair policy

Allowed only before valid batch execution:

- syntax;
- import;
- path;
- serialization;
- test-runner plumbing.

Do not change:

- any H221-H226 mechanism definition;
- any config parameter;
- family count or config count;
- SL/TP multipliers or RR;
- canonical dataset authority;
- costs;
- execution contract;
- evaluation window;
- any of the 14 hard gates;
- signal direction;
- one-position rule.

If a semantic repair appears necessary, stop and return evidence to the independent designer.

## No extra research

Do not create H227, a second batch, long-only variants, short-only variants, threshold refinements, alternate RR values, alternate cost assumptions, another asset or another timeframe.

A survivor, if any, remains only a historical distributed survivor requiring a separately precommitted stability batch.
