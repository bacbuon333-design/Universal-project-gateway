# V3.6 MECHANISM CONCLUSION
## LONDON MORNING DIRECTIONAL CARRY (LMDC) VERDICT

## 1. FALSIFICATION RULE EVALUATION

| Rule # | Falsification Criterion | Empirical Finding | Status |
|---|---|---|:---:|
| **Rule 1** | Aggregate effect disappears when 2025–2026 are excluded | Pre-2025 1h effect remains +0.035 ATR; however recent 2025-2026 1h/2h effect turns negative (-0.026 to -0.039 ATR) | ⚠️ PARTIAL FAIL |
| **Rule 2** | Fewer than 4 of 7 full years (2019–2025) show same directional sign | 6 of 7 full years show positive 4h mean return (2022 is negative) | ✅ PASS |
| **Rule 3** | Quarter-level effect is dominated by a few quarters | Moderate concentration across the 33 quarters | ⚠️ WARNING |
| **Rule 4** | Quarter-block bootstrap CI strongly overlaps zero at key horizons | 1h, 2h, 4h 95% CI all cross zero (1h: `[-0.010, +0.058]`, 4h: `[-0.129, +0.161]`) | ❌ FAIL |
| **Rule 5** | Effect magnitude is trivial relative to transaction-cost scale | 1h effect (+0.024 ATR) and 4h effect (+0.031 ATR) are below the roundtrip cost benchmark (0.0798 ATR) | ❌ FAIL |
| **Rule 6** | Positive effect exists only in one hand-picked bucket | Effect is present across multiple tiers, though non-monotonic at 4h | ✅ PASS |
| **Rule 7** | Long/Short effects cancel unstably | Long mornings show stronger positive continuation than Short mornings | ⚠️ WARNING |

---

## 2. OFFICIAL FINAL CLASSIFICATION

> ### **LMDC MECHANISM WEAK / REGIME-DEPENDENT**

### Scientific Synthesis:
1. **Market Microstructure Reality**: There is a real, observable physical tendency for Gold prices to drift in the direction of the London morning move in the first 30–60 minutes after 12:00 UTC. However, the raw magnitude of this effect ($+0.024\text{ ATR}$ to $+0.050\text{ ATR}$) is smaller than the baseline friction of bid-ask spread and commission ($\approx 0.080\text{ ATR}$).
2. **Adverse Pullback Dynamics**: Between 2 hours and 4 hours after 12:00 UTC, the market frequently undergoes an adverse pullback (median return turns negative), causing standalone continuous carry strategies to suffer high drawdowns and low win rates ($< 50\%$).
3. **Statistical Uncertainty**: Under cluster-correlated Quarter-Block Bootstrap resampling, the 95% confidence intervals cross zero across all intraday horizons $\le 4\text{h}$, indicating that the edge cannot be reliably asserted as statistically independent alpha.
4. **Status**: The LMDC mechanism is classified as **WEAK / REGIME-DEPENDENT**. It does NOT constitute a tradeable standalone edge in its naive symmetrical form.

---
## 3. STRICT STOP MANDATE
In accordance with Section 39 of the Research Protocol, all research activities are officially stopped for independent audit review. No new strategies, grid expansions, or parameter optimizations may be executed.