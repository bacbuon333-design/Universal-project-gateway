# AUDIT V2 FINDINGS & INDEPENDENT REPRODUCTION REPORT

This document records the formal verification status and code evidence for each finding identified by the independent auditor.

---

## 1. SUMMARY OF AUDIT FINDINGS VERIFICATION

| Finding | Topic | Verification Status | Exact Code Evidence | Corrective Action Implemented |
| :--- | :--- | :--- | :--- | :--- |
| **Finding A** | SELL Spread Accounting | **CONFIRMED** | `deep_quant_engine.py` (lines 172–187 & 237–242): Short positions did not add spread price on exit or entry, paying $0$ spread round-trip while Long paid 25 pips. | Symmetrical Ask-based buying back added to short exits. Both directions now pay exactly 1 round-trip spread. |
| **Finding B** | One-Sided Unit Test | **CONFIRMED** | `test_engine_causality_and_integrity.py` (lines 45 & 89): Unit tests only tested `sig[0] = 1` (BUY). Zero tests existed for SELL. | Added 10 comprehensive unit tests covering BUY/SELL TP, SL, ambiguous fills, and cost symmetry. |
| **Finding C** | Invalid Macro EMA Ablation | **CONFIRMED** | `day4_adversarial_falsification.py` (line 140): Used `macro_ema_len = 1`, making `c[i] > macro_ema[i]` evaluate to `c[i] > c[i]` (False), artificially forcing 0 trades. | Refactored `experiment_h060_adaptive_squeeze.py` with explicit boolean flag `use_macro=False` (unconditional macro). |
| **Finding D** | Invalid Squeeze Ablation | **CONFIRMED** | `day4_adversarial_falsification.py` (line 144): Used `kelt_mult = 0.0`, requiring `bb_upper < kelt_mid` and `bb_lower > kelt_mid` (mathematically impossible), artificially forcing 0 trades. | Refactored with explicit boolean flag `use_squeeze=False` (unconditional compression). |
| **Finding 5** | Hardcoded Machine Path | **CONFIRMED** | `deep_quant_engine.py` (line 22): Hardcoded `C:\Users\gugul\AppData\...` broke cross-platform execution on Linux/macOS/clean clones. | Implemented dynamic `resolve_data_path()` supporting environment variables and relative path discovery. |
| **Finding 7** | OOS Contamination (2001–2021) | **CONFIRMED** | `experiment_h060_adaptive_squeeze.py` (lines 144–145): Grid sweep sorted by `oos_pf` on `year < 2022`, proving 2001–2021 was used for model selection. | Reclassified 2001–2021 as **Development / Model-Selection Data**, permanently removing the label "pristine OOS". |
| **Finding 8** | Pseudo-Random OOS Reclassification | **CONFIRMED** | Seed 42 quarters sampled from 2001–2021 after seeing 2001–2021 in H-060. | Reclassified as **Resampled Development Robustness Test**, not clean OOS. |
| **Finding 9** | Walk-Forward Terminology | **CONFIRMED** | Day 3 merely evaluated fixed model across annual slices without re-training windows. | Renamed to **Year-by-Year Temporal Robustness Analysis**. |
| **Finding 10** | Provenance of `min_er = 0.20` | **CONFIRMED** | `min_er = 0.20` was an interpolated midpoint between grid points $0.15$ and $0.25$ in H-070 after inspecting historical performance. | Documented in [`PARAMETER_PROVENANCE.md`](file:///C:/Users/gugul/AppData/Roaming/MetaQuotes/Terminal/BB16F565FAAA6B23A20C26C49416FF05/PARAMETER_PROVENANCE.md) as development-selected. |

---

## 2. CODE EVIDENCE SUMMARY

All 9 audit findings were **CONFIRMED** by direct inspection of the frozen code commit (`31affc2b4e8053da74fe8b7363a5c67f8aa17f9e`). All engine flaws, path dependencies, ablation logic, and testing gaps have been corrected.
