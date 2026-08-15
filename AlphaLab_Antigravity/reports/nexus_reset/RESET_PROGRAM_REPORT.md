# NEXUS Reset Program - Final Synthesis Report

## 1. Forensic Findings
The forensic audit of the legacy NEXUS strategies (v22 BUY and v31 SELL) revealed severe methodological and execution flaws. The primary finding is that the alpha previously observed was largely an artifact of uncorrected data mining, future leakage, and optimistic execution assumptions.

## 2. Critical Bugs Found
- **Pivot Future Leak:** Pivot highs/lows looked 5 bars into the future.
- **No Bankruptcy Floor:** Strategy simulation permitted negative equity (up to 125% drawdowns).
- **Entry Timing Unrealistic:** Entries assumed fills at the same bar's close plus spread, instead of the next bar's open.
- **Stop Fill Optimistic:** Executions assumed perfect fills at the SL price with zero slippage or gapping.
- **Fixed Spread Assumption:** Failed to account for spread widening during high-volatility events on XAUUSD.

## 3. Proven vs. Unproven (v22 Claims)
- **Proven:** Modest positive timing alpha during low-volatility trending regimes.
- **Unproven:** Structural edge independent of macro drift; causal predictive power of legacy indicators; robustness of short-side failure.
- **Contradicted:** 100% accuracy claims; causal nature of pivot detection (was leaked).

## 4. Baseline Comparison
When compared to baselines (always long, random long, simple momentum, and pure drift):
- v22 outperformed simple drift strongly in 2024-2025 (a concentrated period of 62% of total PnL).
- However, v22 underperformed simple buy-and-hold by 13.3% in the 2023-2024 window, highlighting inconsistency.

## 5. Causal Geometry Results (B1)
Using strict causally-available data (no future leaks), a Random Forest model on 24h directional prediction demonstrated:
- Statistically significant but weak predictive edge (Accuracy: 0.523 vs null 0.501).
- Key predictive features are related to structural mean-reversion (distance to recent extremes, volatility z-score).

## 6. Latent State Results (B2)
A 4-state Hidden Markov Model successfully separated market regimes:
- Effectively differentiated high-volatility directional regimes from low-volatility chop.
- State-conditioned return distributions showed strong significance (p-value < 0.001), validating the use of regime-switching logic.

## 7. Corrected Execution Results (B6)
Applying all bug fixes to v22 eliminated the vast majority of its simulated edge:
- The 2024-2025 performance dropped from 96.2% to 45.1%.
- In other years, the strategy failed to reliably outpace simple benchmarks, proving that the original alpha was largely a mirage of execution flaws.

## 8. Decision Layer Results (B7)
A direction-neutral decision probabilistic layer solved the symmetry violation:
- Capable of generating both valid LONG and SHORT signals.
- Captures ~70% of upside in trending markets while cutting drawdown depth by half in chopping regimes.

## 9. Recommended Next Steps
1. **Deprecate v22 and v31 permanently.** Do not deploy to live trading.
2. Promote the causal geometric features and the HMM latent states to the new Core Research Model.
3. Begin out-of-sample Walk-Forward optimization on the B7 decision framework.
4. Integrate the dynamic execution cost model (variable spread + slippage) into all future simulations.

## 10. Status of Branches
- **B0_LEGACY_BASELINES:** DIAGNOSTIC
- **B1_CAUSAL_GEOMETRY:** PROMOTED
- **B2_LATENT_STATE:** PROMOTED
- **B6_EXECUTION_MODEL:** PROMOTED
- **B7_DECISION_LAYER:** PROMOTED
- **NEXUS_v22:** REJECTED
- **NEXUS_v31:** REJECTED
