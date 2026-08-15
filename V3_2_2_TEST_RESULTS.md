# V3.2.2 TEST RESULTS: MULTI-ASSET INTEGRATION & CONTRACT VERIFICATION

---

## 1. INTEGRATION TEST EXECUTION SUMMARY

| Test Name | Instrument | Scenario Tested | Expected Result | Actual Result | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`test_pnl_xauusd`** | XAUUSD | Standalone PnL calculation | Net PnL = +$9.30 USD | +$9.30 USD | **`PASSED`** |
| **`test_pnl_eurusd`** | EURUSD | Standalone PnL calculation | Net PnL = +$99.30 USD | +$99.30 USD | **`PASSED`** |
| **`test_pnl_gbpusd`** | GBPUSD | Standalone PnL calculation | Net PnL = +$99.30 USD | +$99.30 USD | **`PASSED`** |
| **`test_pnl_usdjpy`** | USDJPY | Standalone PnL calculation | Net PnL = +$65.97 USD | +$65.97 USD | **`PASSED`** |
| **`test_pnl_btcusd`** | BTCUSD | Standalone PnL calculation | Net PnL = +$9.30 USD | +$9.30 USD | **`PASSED`** |
| **`test_integration_xauusd_buy_tp_and_buy_sl`** | XAUUSD | Full causal `run_strategy` BUY TP & SL | TP Net = +$29.30, SL Net = -$20.70 | Exact match | **`PASSED`** |
| **`test_integration_xauusd_sell_tp_and_sell_sl`** | XAUUSD | Full causal `run_strategy` SELL TP & SL | TP Net = +$29.30 | Exact match | **`PASSED`** |
| **`test_integration_eurusd_buy_tp`** | EURUSD | Full causal `run_strategy` EURUSD BUY TP | TP Net = +$29.30 | Exact match | **`PASSED`** |
| **`test_integration_gbpusd_sell_sl`** | GBPUSD | Full causal `run_strategy` GBPUSD SELL SL | SL Net = -$20.70 | Exact match | **`PASSED`** |
| **`test_integration_usdjpy_buy_tp`** | USDJPY | Full causal `run_strategy` USDJPY BUY TP | TP Net = +$65.52 USD | Exact match | **`PASSED`** |
| **`test_integration_btcusd_sell_sl`** | BTCUSD | Full causal `run_strategy` BTCUSD SELL SL | SL Net = -$50.70 USD | Exact match | **`PASSED`** |
| **`test_ambiguous_bar_pessimistic_buy`** | XAUUSD | Ambiguous bar SL vs TP resolution | SL preferred pessimistically | Exit reason: `SL_AMBIGUOUS_PESSIMISTIC` | **`PASSED`** |
| **`test_contract_validation_catches_errors`** | ANY | Contract validator runtime enforcement | Throws `ValueError` on bad inputs | Exception correctly raised | **`PASSED`** |

* **Overall Test Suite Status**: **13/13 TESTS PASSED (100% SUCCESS)**.
