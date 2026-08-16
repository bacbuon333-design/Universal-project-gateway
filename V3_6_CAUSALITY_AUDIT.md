# V3.6 CAUSALITY AUDIT REPORT
## TEMPORAL INTEGRITY & NO-LOOKAHEAD VERIFICATION

---

## 1. TEMPORAL BOUNDARY VERIFICATION
- **Morning Event Window**: 08:00 UTC to 11:59 UTC (`8 <= hour < 12`).
- **Morning Open**: Price at the start of the 08:00 UTC bar.
- **Morning Close**: Price at the end of the 11:30 UTC bar (final completed M30 bar before 12:00).
- **Volatility Estimator**: `ATR14_pre12` is evaluated at the close of the 11:30 UTC bar. No bars at or after 12:00 UTC enter the ATR calculation.
- **Decision Timestamp**: 12:00 UTC bar close.

---

## 2. FORWARD EVALUATION ISOLATION
- **Forward Measurement Start**: Strictly at the 12:00 UTC bar close ($P_{\text{ref}} = \text{Close at 12:00 UTC}$).
- **Forward Horizons**:
  - $h = 30\text{m}$: Bar 12:00 UTC $\to$ Bar 12:30 UTC close.
  - $h = 1\text{h}$: Bar 13:00 UTC close.
  - $h = 2\text{h}$: Bar 14:00 UTC close.
  - $h = 4\text{h}$: Bar 16:00 UTC close.
  - $h = 8\text{h}$: Bar 20:00 UTC close.
  - $h = \text{Day Close}$: Final bar of current UTC date.
- **Zero Information Bleed**: No forward bar prices or returns are used in classifying event direction or magnitude tiers.
- **Single Daily Event**: Exactly 1 event per day. No overlapping intraday event sampling.
