# V3.3.1 CAUSALITY AUDIT REPORT
## VERIFICATION OF TEMPORAL INTEGRITY & SESSION BOUNDARIES

---

## 1. SIGNAL AND EXECUTION TIMING
- **Signal Formation**: Computed strictly on the close of bar $i$.
- **Execution**: Triggered strictly on the open of bar $i+1$.
- **Rolling Levels**: All historical channel extremes and breakout references use `shift(1)` (e.g. `pd.Series(High).rolling(N).max().shift(1)`).
- **Concurrency**: At most 1 position active at any time.

---

## 2. H-212 SESSION RANGE CAUSALITY
- **Asian Session Definition**: 00:00 UTC to 07:59 UTC (`0 <= hour < 8`).
- **Trade Expansion Window**: 08:00 UTC to 16:59 UTC (`8 <= hour <= 16`).
- **Causality Verification**: Because the active trade window begins at 08:00 UTC, the entire Asian session (00:00–07:59 UTC) has already completed in real time. When evaluating signals at bar $i \ge 08:00\text{ UTC}$, `asia_h` and `asia_l` are strictly based on past bars from the current day's Asian session. No future data from the current day is referenced.
