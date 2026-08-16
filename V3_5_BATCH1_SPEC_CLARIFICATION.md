# V3.5 BATCH-1 PRE-IMPLEMENTATION SPEC CLARIFICATION

Status: committed BEFORE implementation and BEFORE any H-218/H-219/H-220 execution result exists.

## H-218 crossing-level indexing
The H-218 precommit describes the first close through the completed previous UTC day's range. To implement that economic definition consistently across a day boundary, both sides of the crossing test must reference the SAME previous-day level assigned to the current day D.

Authoritative H-218 trigger:

Long at bar i close:
- `close[i] > prev_day_high_for_current_day[i]`
- `close[i-1] <= prev_day_high_for_current_day[i]`

Short:
- `close[i] < prev_day_low_for_current_day[i]`
- `close[i-1] >= prev_day_low_for_current_day[i]`

Do NOT use `prev_day_high[i-1]` / `prev_day_low[i-1]` for the second comparison because at the first bar of a new UTC day those arrays refer to D-2 rather than the intended completed D-1 boundary.

This is a pre-result semantic clarification, not a performance-driven change. All other H-218/H-219/H-220 specifications remain frozen exactly as committed.
