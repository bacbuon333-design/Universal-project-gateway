# REPRODUCE V2: INDEPENDENT REVALIDATION REPRODUCTION GUIDE

This guide provides exact instructions to replicate the corrected Revalidation V2 findings on the `audit/quant-research-revalidation-v2` branch.

---

## 1. QUICKSTART

```bash
# 1. Checkout revalidation branch
git checkout audit/quant-research-revalidation-v2

# 2. Run Comprehensive Synthetic Execution Unit Tests (All 10 tests must pass)
python AlphaLab_Antigravity/src/test_engine_causality_and_integrity.py

# 3. Run Full Revalidation Suite (Data Partitions, Spread Stress, True Ablations, Bootstraps)
python AlphaLab_Antigravity/src/revalidation_v2_runner.py
```

---

## 2. KEY REVALIDATION ARTIFACTS

1. **[`AUDIT_V2_FINDINGS.md`](file:///C:/Users/gugul/AppData/Roaming/MetaQuotes/Terminal/BB16F565FAAA6B23A20C26C49416FF05/AUDIT_V2_FINDINGS.md)**: Detailed verification of all 9 independent auditor findings.
2. **[`EXECUTION_MODEL.md`](file:///C:/Users/gugul/AppData/Roaming/MetaQuotes/Terminal/BB16F565FAAA6B23A20C26C49416FF05/EXECUTION_MODEL.md)**: Mathematical formulas, Bid/Ask pricing rules, and worked numerical examples.
3. **[`PARAMETER_PROVENANCE.md`](file:///C:/Users/gugul/AppData/Roaming/MetaQuotes/Terminal/BB16F565FAAA6B23A20C26C49416FF05/PARAMETER_PROVENANCE.md)**: Provenance and contamination risk analysis for all frozen parameters.
4. **[`REVALIDATION_V2_RESULTS.md`](file:///C:/Users/gugul/AppData/Roaming/MetaQuotes/Terminal/BB16F565FAAA6B23A20C26C49416FF05/REVALIDATION_V2_RESULTS.md)**: Complete benchmark comparisons, true ablations, and bootstrap confidence intervals.
5. **Machine-Readable Outputs**:
   - `AlphaLab_Antigravity/reports/revalidation_v2_trades.csv`
   - `AlphaLab_Antigravity/reports/revalidation_v2_quarters.csv`
   - `AlphaLab_Antigravity/reports/revalidation_v2_summary.json`
