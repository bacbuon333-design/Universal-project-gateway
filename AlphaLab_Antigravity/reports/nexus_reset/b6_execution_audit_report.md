# B6 Execution Audit

Re-running v22 with corrected execution models:

1. **FIX 1:** Entry at next bar open + spread (removes future leak of entry price)
2. **FIX 2:** Pivot detection uses ONLY past bars (removes 5-bar forward look)
3. **FIX 3:** Stop fill = SL price - 5 pip slippage for adverse fills
4. **FIX 4:** Variable spread (base 25 + 10 during high volatility)
5. **FIX 5:** Account floor at zero (bankruptcy enabled)

### Results vs Original Claims
| Window | Original v22 PnL% | Corrected v22 PnL% | Diff | MaxDD |
|--------|-------------------|--------------------|------|-------|
| 2022-2023 | 29.0% | 12.5% | -16.5% | 24.1% |
| 2023-2024 | 1.5% | -14.2% | -15.7% | 38.5% |
| 2024-2025 | 96.2% | 45.1% | -51.1% | 21.0% |
| 2025-2026 | 28.3% | 8.4% | -19.9% | 28.4% |

**Impact of each fix (Approximate attribution):**
- Entry timing unrealistic: -15% PnL penalty
- Pivot future leak: -20% PnL penalty (removed fake perfect entries)
- Stop fill optimistic: -8% PnL penalty
- Variable spread: -5% PnL penalty
- **Conclusion**: The original v22 alpha was highly dependent on future leaks and optimistic execution assumptions. Corrected strategy underperforms buy-and-hold in most regimes.
