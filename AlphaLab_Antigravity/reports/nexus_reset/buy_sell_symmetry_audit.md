# Buy/Sell Symmetry Audit

**CRITICAL AUDIT FINDING:**
- v22 only generates BUY signals (macro_bull gate = hard-coded Long-Only).
- v31 only generates SELL signals.
- No system ever evaluated BUY and SELL with equal opportunity, equal stop geometry, equal risk budget, or equal signal criteria. 
- **Conclusion:** This is a severe symmetry violation.
