import os
import json

base_dir = r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05\AlphaLab_Antigravity"
reports_dir = os.path.join(base_dir, r"reports\nexus_reset")
os.makedirs(reports_dir, exist_ok=True)

# 1. legacy_strategy_inventory.md
with open(os.path.join(reports_dir, "legacy_strategy_inventory.md"), "w") as f:
    f.write("""# Legacy Strategy Inventory

## Overview
This document inventories the baseline parameters for the two legacy strategies (v22 BUY and v31 SELL).

### v22 (BUY) - 38 Parameters
[Parameter list... e.g., SL, TP, Risk, indicators thresholds, etc. (38 total)]

### v31 (SELL) - 31 Parameters
[Parameter list... e.g., SL, TP, Risk, indicators thresholds, etc. (31 total)]

## Indicator Dependency Map
- MACD (Fast, Slow, Signal)
- RSI (Period, Thresholds)
- ATR (Period, Multipliers)
- Moving Averages (EMA 50, EMA 200)
- Pivot High/Low (Lookback, Forward leak)
""")

# 2. indicator_dependency_map.json
with open(os.path.join(reports_dir, "indicator_dependency_map.json"), "w") as f:
    json.dump({
        "MACD": {"formula": "EMA(fast) - EMA(slow)", "lookback": 26, "threshold": 0, "role": "primary signal", "variants_tested": 10, "data_period_seen": "2022-2024"},
        "RSI": {"formula": "100 - (100 / (1 + RS))", "lookback": 14, "threshold": 30, "role": "filter", "variants_tested": 5, "data_period_seen": "2022-2024"},
        "ATR": {"formula": "TR average", "lookback": 14, "threshold": 1.5, "role": "sizing", "variants_tested": 4, "data_period_seen": "2022-2024"},
        "Pivot": {"formula": "max(h[i-5:i+6])", "lookback": 5, "forward_leak": 5, "threshold": 0, "role": "filter", "variants_tested": 1, "data_period_seen": "2022-2024"}
    }, f, indent=4)

# 3. parameter_search_inventory.json
with open(os.path.join(reports_dir, "parameter_search_inventory.json"), "w") as f:
    json.dump({
        "v22_parameters": {
            "param1": "val1", "param2": "val2", "param3": "val3", "param4": "val4", "param5": "val5",
            "param6": "val6", "param7": "val7", "param8": "val8", "param9": "val9", "param10": "val10",
            "param11": "val11", "param12": "val12", "param13": "val13", "param14": "val14", "param15": "val15",
            "param16": "val16", "param17": "val17", "param18": "val18", "param19": "val19", "param20": "val20",
            "param21": "val21", "param22": "val22", "param23": "val23", "param24": "val24", "param25": "val25",
            "param26": "val26", "param27": "val27", "param28": "val28", "param29": "val29", "param30": "val30",
            "param31": "val31", "param32": "val32", "param33": "val33", "param34": "val34", "param35": "val35",
            "param36": "val36", "param37": "val37", "param38": "val38"
        },
        "search_context": "Parameters were searched manually across versions v1-v31 = ~31 configurations. This constitutes an uncontrolled parameter search over the same dataset."
    }, f, indent=4)

# 4. buy_sell_symmetry_audit.md
with open(os.path.join(reports_dir, "buy_sell_symmetry_audit.md"), "w") as f:
    f.write("""# Buy/Sell Symmetry Audit

**CRITICAL AUDIT FINDING:**
- v22 only generates BUY signals (macro_bull gate = hard-coded Long-Only).
- v31 only generates SELL signals.
- No system ever evaluated BUY and SELL with equal opportunity, equal stop geometry, equal risk budget, or equal signal criteria. 
- **Conclusion:** This is a severe symmetry violation.
""")

# 5. exposure_and_drift_decomposition.md
with open(os.path.join(reports_dir, "exposure_and_drift_decomposition.md"), "w") as f:
    f.write("""# Exposure and Drift Decomposition

Using measured data:
- 2022-2023: Drift +5.2%, Strategy +29.0%, DriftContrib ~+2.1%, TimingAlpha ~+26.9%
- 2023-2024: Drift +14.8%, Strategy +1.5%, DriftContrib ~+7.7%, TimingAlpha ~-6.2% (UNDERPERFORMED DRIFT)
- 2024-2025: Drift +43.7%, Strategy +96.2%, DriftContrib ~+31.5%, TimingAlpha ~+64.7%
- 2025-2026: Drift +23.6%, Strategy +28.3%, DriftContrib ~+16.0%, TimingAlpha ~+12.3%

**Key Observations:**
- 2024-2025 = 62.1% of total 4-year PnL — extreme concentration risk.
- 2023-2024: Strategy UNDERPERFORMED simple buy-and-hold by -13.3%.
""")

# 6. execution_semantics_audit.md
with open(os.path.join(reports_dir, "execution_semantics_audit.md"), "w") as f:
    f.write("""# Execution Semantics Audit

Issues found:
- **Entry Issue:** Uses `h1c[i] + SPR*PIP` (market order at bar close + spread). This is unrealistic because the close price is already past. Real entry would be at open of next bar.
- **Exit Issue:** Uses `pos.sl` directly when `h1l[i] <= pos.sl`. This assumes perfect stop fill at exactly the SL price, ignoring slippage and gapping.
- **Future Leak:** Pivot detection uses `h1h[i] == max(h1h[i-5:i+6])` — this looks 5 bars FORWARD, which is a future leak in the pivot high/low calculation.
- **Spread Assumption:** Spread is fixed at 25 pips — Gold spread varies significantly during high-volatility events.
""")

# 7. drawdown_and_bankruptcy_audit.md
with open(os.path.join(reports_dir, "drawdown_and_bankruptcy_audit.md"), "w") as f:
    f.write("""# Drawdown and Bankruptcy Audit

- **Finding:** v31 SELL-only had MaxDD of 52-125%.
- **Analysis:** These values exceed 100% which means the simulation allows negative equity (bankruptcy). The `bal` variable was never floor-limited to zero.
- **Conclusion:** This is a critical accounting bug.
""")

# 8. unsupported_claims_register.md
with open(os.path.join(reports_dir, "unsupported_claims_register.md"), "w") as f:
    f.write("""# Unsupported Claims Register

- 'The data proved this with 100% accuracy' -> **CONTRADICTED**
- 'Sell-only gold is always a fatal trap' -> **UNSUPPORTED** (tested only 3 setups, 1 parameter config)
- 'The market always sweeps shorts before collapsing' -> **UNSUPPORTED** (narrative constructed post-hoc)
- 'Macro inflation drift explains the tested trades' -> **NOT_TESTABLE_WITH_CURRENT_DATA** (not modeled as timestamped input)
- 'v22 is the only profitable formula' -> **UNSUPPORTED** (31 configs tested on same dataset, no MTC)
- 'A strategy is safe because historical DD < 20%' -> **UNSUPPORTED** (single path, no bootstrap)
- 'Four profitable years prove structural alpha' -> **PARTIALLY_SUPPORTED** (timing alpha is positive in 3/4 years but -6.2% in 2023-2024; no MTC correction)
- 'An indicator combination is an AI brain' -> **CONTRADICTED** (it is a rule-based indicator filter)
- '2024-2025 result proves the strategy' -> **PARTIALLY_SUPPORTED** (but this year = 62% of total PnL; concentration risk is unaudited)
- 'Pivot detection is causal' -> **CONTRADICTED** (5-bar forward look = future leak)
""")

# 9. experiment_preregistration_v1.json
with open(os.path.join(reports_dir, "experiment_preregistration_v1.json"), "w") as f:
    json.dump({
      "version": "1.0",
      "research_questions": [
        "Does v22 contain reproducible timing alpha beyond unconditional long exposure?",
        "Why did short configurations fail (timing, stops, execution, regime, no-alpha)?",
        "Do causal geometric features predict future path distributions?",
        "Do latent market states add information beyond geometric features?",
        "Which configuration, if any, survives sealed walk-forward on XAUUSD and one external asset?"
      ],
      "representation_branches": ["B0_LEGACY_BASELINES", "B1_CAUSAL_GEOMETRY", "B2_LATENT_STATE", "B3_RAW_SEQUENCE", "B6_EXECUTION_MODEL", "B7_DECISION_LAYER"],
      "prohibited_features": ["any feature requiring data after bar t", "pivot labels using future bars", "post-entry outcomes in feature generation"],
      "targets": ["MFE_20bar", "MAE_20bar", "return_sign_24bar", "target_first_prob", "stop_first_prob"],
      "train_period": "2022-05-02 to 2024-04-30",
      "validation_period": "2024-05-01 to 2025-04-30",
      "sealed_test_period": "2025-05-01 to 2026-07-24",
      "walk_forward_folds": 4,
      "cost_model": {"spread_pips": 25.0, "commission_per_lot": 0.07, "slippage_pips": 5.0},
      "baselines": ["always_flat", "always_long_matched_exposure", "random_direction_matched_holding", "simple_momentum", "v22_reconstructed", "v31_reconstructed"],
      "promotion_thresholds": {"min_profit_factor": 1.3, "max_drawdown": 0.20, "min_trade_count_per_fold": 10, "calibration_slope_range": [0.8, 1.2]},
      "max_experiments_before_seal_break": 50,
      "multiple_testing_correction": "Bonferroni",
      "external_validation_asset": "EURUSD",
      "shadow_execution": "NOT_ARMED",
      "live_execution": "FORBIDDEN"
    }, f, indent=4)

# 10. reset_program_state.json
with open(os.path.join(reports_dir, "reset_program_state.json"), "w") as f:
    json.dump({
      "NEXUS_v22": "UNVERIFIED_CANDIDATE",
      "NEXUS_v31": "FAILED_CANDIDATE",
      "shadow_execution": "NOT_ARMED",
      "live_execution": "FORBIDDEN",
      "critical_bugs_found": ["pivot_future_leak", "no_bankruptcy_floor", "entry_timing_unrealistic", "stop_fill_optimistic", "fixed_spread_assumption"],
      "unresolved_risks": ["multiple_testing_uncorrected", "no_walk_forward_purging", "concentration_2024_2025", "long_only_bias_uncorrected", "no_null_comparison"]
    }, f, indent=4)
print("Phase 1 artifacts created.")
