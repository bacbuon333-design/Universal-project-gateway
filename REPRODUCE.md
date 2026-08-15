# INDEPENDENT AUDIT REPRODUCTION GUIDE

This guide provides exact, step-by-step instructions for an independent reviewer to reproduce and audit the quantitative results reported in this repository.

---

## 1. ENVIRONMENT SETUP

Ensure you have Python 3.10 or higher installed.

```bash
# Optional: Create a clean virtual environment
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate

# Install exact dependencies
pip install -r requirements.txt
```

---

## 2. DATASET VERIFICATION

Verify the integrity and SHA256 checksums of the datasets in `AlphaLab_Antigravity/data/`:

```bash
python AlphaLab_Antigravity/src/audit_data_integrity.py
```

*Expected Result*:
- `GOLD_H1_2001_2026.csv`: 81,463 rows, date range `2001-06-04` to `2026-07-24`, 0 NaN values, 0 invalid OHLC records.
- Compare hashes with [`DATA_MANIFEST.md`](file:///C:/Users/gugul/AppData/Roaming/MetaQuotes/Terminal/BB16F565FAAA6B23A20C26C49416FF05/DATA_MANIFEST.md).

---

## 3. ENGINE CAUSALITY & PESSIMISTIC EXECUTION AUDIT

Run the automated test suite to confirm that:
1. Decision time $T$ never sees data at $T+1$ (No lookahead leakage).
2. If both SL and TP are touched inside a single bar, Stop Loss is always triggered first (Pessimistic fill).
3. Spread, commission ($7/lot), and slippage are correctly deducted.

```bash
python AlphaLab_Antigravity/src/test_engine_causality_and_integrity.py
```

*Expected Result*: All assertions pass (`Test 1 PASSED`, `Test 2 PASSED`).

---

## 4. REPRODUCE DISCOVERY & BASELINE PARAMETER SWEEP

Run the systematic evaluation of Candidate `CAND-001` across 25 years of Gold data:

```bash
python AlphaLab_Antigravity/src/experiment_h060_adaptive_squeeze.py
```

*Expected Result*:
- Confirms that all 27 parameter variations generated positive net PnL across 2001–2026.
- Top configuration achieves Overall $PF = 2.078$, OOS $PF = 1.639$, and Expectancy $+0.351\text{ R}$ / trade.

---

## 5. REPRODUCE DAY 3 FREEZE, RANDOM OOS & WALK-FORWARD

Run the frozen candidate validation with pre-committed random quarters (Seed 42) and chronological walk-forward slicing:

```bash
python AlphaLab_Antigravity/src/day3_freeze_and_oos_validation.py
```

*Expected Result*:
- Verifies SHA256 hash matches `addf9673bb779c865e4425e7c397cd8af11aa9152ca045cd5955bfd4641104f5`.
- Random 15-Quarter OOS PnL: `+$181.14 USD` ($PF = 1.331$).
- Walk-Forward Annual Consistency: 9 of 16 active historical years profitable (56.2%).

---

## 6. REPRODUCE DAY 4 ADVERSARIAL STRESS & ABLATION

Stress-test the candidate against severe friction and inspect the architectural components:

```bash
python AlphaLab_Antigravity/src/day4_adversarial_falsification.py
```

*Expected Result*:
- Spread stress: Survives up to 100 pips spread ($PF = 1.950$, Net PnL `+$7,470.01 USD`).
- Slippage stress: Survives up to 15 pips slippage ($PF = 1.826$, Net PnL `+$6,457.76 USD`).
- Directional ablation: Symmetrical short leg made `+$713.84 USD` in the 2013–2015 Gold crash.
- Component ablation: Removing Squeeze or Macro EMA collapses trade generation to 0.

---

## 7. REPRODUCE DAY 5 FINAL BLIND HOLDOUT & MONTE CARLO

Evaluate the reserved final blind period (2025 Q3 – 2026 Q2) and run 10,000 Monte Carlo bootstrap resamples:

```bash
python AlphaLab_Antigravity/src/day5_final_blind_evaluation.py
```

*Expected Result*:
- Final Blind Holdout (4 quarters): 14 trades, Win Rate 57.14%, Profit Factor 5.006, Net PnL `+$6,518.99 USD`.
- 10,000 Monte Carlo Bootstrap: 99.65% probability of positive expectancy; 95% Confidence Interval of Profit Factor: `[1.239, 3.311]`.

---

## 8. INDEPENDENT AUDIT PRINCIPLE
Do not rely on narrative claims or equity curves. Independently audit the source code in [`AlphaLab_Antigravity/src/deep_quant_engine.py`](file:///C:/Users/gugul/AppData/Roaming/MetaQuotes/Terminal/BB16F565FAAA6B23A20C26C49416FF05/AlphaLab_Antigravity/src/deep_quant_engine.py) and [`AlphaLab_Antigravity/src/experiment_h060_adaptive_squeeze.py`](file:///C:/Users/gugul/AppData/Roaming/MetaQuotes/Terminal/BB16F565FAAA6B23A20C26C49416FF05/AlphaLab_Antigravity/src/experiment_h060_adaptive_squeeze.py).
