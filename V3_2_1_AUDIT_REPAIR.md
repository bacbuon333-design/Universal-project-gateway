# V3.2.1 AUDIT REPAIR REPORT: SL/TP DISTANCE INTERFACE FIX & REPRODUCTION

---

## 1. AUDIT DEFECTS IDENTIFIED & RESOLVED

1. **Defect 1 (Critical Interface Mismatch)**:
   - **Root Cause**: In V3.2, signal generators for H-204 through H-208 returned absolute price levels (`c[i] - 1.5*ATR`) instead of distances (`1.5*ATR`). Because `DeepQuantEngine` interprets the return value as `sl_dists` and adds/subtracts it from `entry_price`, SL was placed near zero ($25) and TP near $5000+, trapping trades until the 120-bar `TIME_EXIT`.
   - **Correction**: All signal generators in `experiment_h204_to_h208_m30_discovery.py` were corrected to return exact price distances (`sl_dists[i] = 1.5 * cur_atr`, `tp_dists[i] = 3.75 * cur_atr` or respective RR ratios).
2. **Defect 2 (Unit & Integration Test Coverage)**:
   - **Correction**: `test_engine_asset_aware.py` was expanded to run full end-to-end backtest simulations through `run_strategy()` asserting exact Ask/Bid entry prices, SL/TP price placement, trade closure on ambiguous bars, spread deduction, and commission accounting across all supported assets (XAUUSD, EURUSD, GBPUSD, USDJPY, BTCUSD).
   - **Test Result**: 5/5 integration tests passed (100% success).
3. **Defect 3 (Cost-Adjusted Expectancy R)**:
   - **Correction**: Updated `DeepQuantEngine` to compute $1R$ risk in USD net of all costs (`sl_risk_usd`), ensuring `pnl_r = net_pnl_usd / sl_risk_usd` accounts for spread and commission.
4. **Defect 4 (USDJPY Classification)**:
   - Reclassified USDJPY in H-103 as: `POSITIVE HISTORICAL ZERO-TUNING TRANSFER — NOT A DISTRIBUTED SURVIVOR` (107 trades across 13 years does not meet the $\ge 5$ trades/quarter gate).

---

## 2. REPAIRED V3.2.1 EXPERIMENT RESULTS (ZERO PARAMETER MODIFICATION)

All 7 precommitted hypotheses were re-executed on Gold M30 (`2018Q2` to `2026Q2`, 33 complete quarters) with frozen parameters:

| Hypothesis | Total Trades | Min Trades/Q | Max/Med Ratio | Trade Gini | Profitable Full Years (%) | Rolling 4Q Pos (%) | Rolling 4Q PF $\ge$ 1.20 (%) | Profit Factor | Win Rate | V3.2.1 Verdict |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`H-204`** | 311 | **4** (FAIL) | 2.11 | 0.217 | 71.4% (5/7) | 73.3% | 53.3% (FAIL) | **1.256** | 34.1% | **`REJECTED`** |
| **`H-205`** | 2,545 | **50** (PASS) | 1.24 | **0.100** | 14.3% (1/7) | 6.7% | 3.3% (FAIL) | **0.962** (FAIL) | 26.7% | **`REJECTED`** |
| **`H-206`** | 1,492 | **30** (PASS) | 1.26 | **0.072** | 42.9% (3/7) | 43.3% | 16.7% (FAIL) | **1.117** (FAIL) | 29.0% | **`REJECTED`** |
| **`H-207`** | 277 | **2** (FAIL) | 2.50 | 0.268 | 71.4% (5/7) | 56.7% | 43.3% (FAIL) | **1.164** (FAIL) | 32.3% | **`REJECTED`** |
| **`H-208A`**| 161 | **1** (FAIL) | 3.25 | 0.312 | 71.4% (5/7) | 66.7% | 46.7% (FAIL) | **1.444** | 34.1% | **`REJECTED`** |
| **`H-208B`**| 151 | **1** (FAIL) | 2.75 | 0.320 | 57.1% (4/7) | 66.7% | 56.7% (FAIL) | **1.081** (FAIL) | 33.8% | **`REJECTED`** |
| **`H-208C`**| 420 | **5** (PASS) | 1.92 | 0.202 | 71.4% (5/7) | 73.3% | 40.0% (FAIL) | **1.070** (FAIL) | 33.5% | **`REJECTED`** |

---

## 3. SCIENTIFIC VALIDATION & FINAL VERDICT

With the interface bug completely resolved and confirmed via end-to-end integration unit tests:

### **NO HISTORICAL CANDIDATE PASSED V3.2 DISTRIBUTED EDGE STANDARD**
