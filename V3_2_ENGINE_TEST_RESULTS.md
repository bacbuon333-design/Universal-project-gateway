# V3.2 ENGINE TEST RESULTS: ASSET-AWARE UNIT TESTS & VALIDATION

This document records the results of running synthetic execution tests directly through the updated `DeepQuantEngine` for all 5 supported instrument types.

---

## 1. UNIT TEST EXECUTION SUITE

Executed via: `AlphaLab_Antigravity/src/test_engine_asset_aware.py`

| Test Case | Symbol | Contract Size | Movement | Expected Gross PnL | Expected Comm ($7/lot) | Expected Net PnL | Test Result |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`test_xauusd_trade_pnl`** | XAUUSD | 100 oz (10 oz @ 0.10 lot) | LONG +100 pips ($1.00) | $10.00 USD | $0.70 USD | **$9.30 USD** | **`PASSED`** |
| **`test_xauusd_short_pnl`**| XAUUSD | 100 oz (10 oz @ 0.10 lot) | SHORT +100 pips ($1.00) | $10.00 USD | $0.70 USD | **$9.30 USD** | **`PASSED`** |
| **`test_eurusd_trade_pnl`** | EURUSD | 100,000 EUR (10k @ 0.10 lot) | LONG +100 pips (0.0100) | $100.00 USD | $0.70 USD | **$99.30 USD** | **`PASSED`** |
| **`test_usdjpy_trade_pnl`** | USDJPY | 100,000 USD (10k @ 0.10 lot) | LONG +100 pips (1.00 JPY @ 150.0) | $66.67 USD | $0.70 USD | **$65.97 USD** | **`PASSED`** |
| **`test_btcusd_trade_pnl`** | BTCUSD | 1.0 BTC (0.10 BTC @ 0.10 lot) | LONG +100 pts ($100.00) | $10.00 USD | $0.70 USD | **$9.30 USD** | **`PASSED`** |
| **`test_engine_synthetic_sim`** | GOLD H1 | 100 oz contract | Full causal backtest simulation | N/A | N/A | N/A | **`PASSED`** |

* **Overall Unit Test Status**: **5/5 TESTS PASSED (100% SUCCESS)**.
