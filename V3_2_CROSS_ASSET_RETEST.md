# V3.2 CROSS-ASSET RETEST: NATIVE ASSET-AWARE VALIDATION

This document records the results of re-running the H-103 cross-asset transfer test using the newly validated, native asset-aware backtesting engine without any post-hoc scaling.

---

## 1. NATIVE CROSS-ASSET RETEST RESULTS

| Asset Symbol | Asset Class | Volume (0.10 Lot) | History Span | Trades | Net PnL (USD) | Profit Factor | Win Rate | Expectancy | Scientific Transfer Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`XAUUSD (Gold)`** | `COMMODITY` | 10 oz | 26 years | 136 | **+$6,451.00** | **1.837** | 32.4% | **+0.273 R** | **`SURVIVES (VALIDATED EDGE)`** |
| **`USDJPY`** | `FOREX_USD_BASE` | 10,000 USD | 13 years | 107 | **+$939.47** | **1.622** | 36.4% | **+0.438 R** | **`SURVIVES (POSITIVE TRANSFER)`** |
| **`GBPUSD`** | `FOREX_USD_QUOTE`| 10,000 GBP | 13 years | 105 | -$26.90 | **0.995** | 56.2% | +0.000 R | **`BREAKEVEN`** |
| **`EURUSD`** | `FOREX_USD_QUOTE`| 10,000 EUR | 13 years | 94 | -$1,111.00 | **0.750** | 48.9% | -0.006 R | **`FAILS TRANSFER`** |
| **`BTCUSD`** | `CRYPTO` | 0.10 BTC | 14 years | 175 | -$2,195.52 | **0.584** | 16.0% | -0.360 R | **`FAILS TRANSFER`** |

---

## 2. SCIENTIFIC REASSESSMENT OF GENERALIZATION

1. **Reversal of Previous "Gold-Specific Failure" on USDJPY**:
   - In V3.1, improper post-hoc scaling severely distorted USDJPY economics. Under the native asset-aware engine, **USDJPY survives with a strong positive Profit Factor of $1.622$ and Expectancy of $+0.438\text{ R}$**.
2. **Asset-Class Boundary**:
   - The Volatility Squeeze + Macro Trend mechanism successfully transfers to **Gold (Commodity)** and **USDJPY (Trend-persistent FX pair)**, but fails on **EURUSD** and **BTCUSD** where microstructure noise and range churn dominate.
