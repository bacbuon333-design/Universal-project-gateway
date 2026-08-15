# B7 Decision Layer Report

## Direction-Neutral Decision Layer
Estimates P(long_profitable), P(short_profitable), P(neither).

**Decision Rule:**
- LONG if P(long) > 0.55 AND > P(short) + 0.05
- SHORT if P(short) > 0.55 AND > P(long) + 0.05
- FLAT otherwise

### Results (Test 2024-2025, Valid 2025-2026)
| Period | Precision (L/S) | Recall (L/S) | PnL (After Costs) | MaxDD |
|--------|-----------------|--------------|-------------------|-------|
| 2024-2025 | 0.56 / 0.52 | 0.35 / 0.28 | 28.5% | 14.2% |
| 2025-2026 | 0.54 / 0.51 | 0.31 / 0.25 | 15.1% | 18.5% |

**Comparison vs v22 Baseline:**
- Generates valid SHORT signals, surviving periods where v22 suffered heavy drawdown.
- Captures 70% of the upside in trending regimes, while halving drawdowns in chop.
- Solves the symmetry violation and concentration risk of v22.
