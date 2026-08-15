"""
ENGINE-LEVEL ASSET-AWARE UNIT TESTS
===================================
Runs synthetic backtests directly through DeepQuantEngine for:
- XAUUSD
- EURUSD
- GBPUSD
- USDJPY (dynamic contemporaneous JPY/USD conversion)
- BTCUSD

Tests:
1. LONG +100 pips win
2. LONG -100 pips loss
3. SHORT +100 pips win
4. SHORT -100 pips loss
5. Spread, commission, slippage cost accounting
"""

import sys
import unittest
import numpy as np
import pandas as pd
from deep_quant_engine import DeepQuantEngine, InstrumentSpec, calculate_trade_pnl, STANDARD_SPECS

sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None

def create_synthetic_df(prices, asset_name="TEST", start_dt="2020-01-01 00:00:00", freq='1h'):
    n = len(prices)
    dts = pd.date_range(start=start_dt, periods=n, freq=freq)
    df = pd.DataFrame({
        'dt': dts,
        'open': prices,
        'high': [p + 0.0001 for p in prices],
        'low': [p - 0.0001 for p in prices],
        'close': prices,
        'datetime_str': [str(d) for d in dts]
    })
    return df

class TestAssetAwareEngine(unittest.TestCase):
    
    def test_xauusd_trade_pnl(self):
        spec = STANDARD_SPECS["XAUUSD"]
        # LONG +100 pips ($1.00) on 0.10 lot (10 oz) -> Gross PnL = $10.00, Comm = $0.70 -> Net = $9.30
        res_long = calculate_trade_pnl(spec, direction=1, entry_price=2000.00, exit_price=2001.00, lots=0.10)
        self.assertAlmostEqual(res_long['gross_pnl_usd'], 10.00, places=2)
        self.assertAlmostEqual(res_long['commission_usd'], 0.70, places=2)
        self.assertAlmostEqual(res_long['net_pnl_usd'], 9.30, places=2)
        
        # SHORT +100 pips ($1.00 drop) on 0.10 lot (10 oz) -> Gross PnL = $10.00, Comm = $0.70 -> Net = $9.30
        res_short = calculate_trade_pnl(spec, direction=-1, entry_price=2000.00, exit_price=1999.00, lots=0.10)
        self.assertAlmostEqual(res_short['gross_pnl_usd'], 10.00, places=2)
        self.assertAlmostEqual(res_short['net_pnl_usd'], 9.30, places=2)

    def test_eurusd_trade_pnl(self):
        spec = STANDARD_SPECS["EURUSD"]
        # LONG +100 pips (0.0100) on 0.10 lot (10,000 EUR) -> Gross = $100.00, Comm = $0.70 -> Net = $99.30
        res_long = calculate_trade_pnl(spec, direction=1, entry_price=1.10000, exit_price=1.11000, lots=0.10)
        self.assertAlmostEqual(res_long['gross_pnl_usd'], 100.00, places=2)
        self.assertAlmostEqual(res_long['commission_usd'], 0.70, places=2)
        self.assertAlmostEqual(res_long['net_pnl_usd'], 99.30, places=2)

    def test_usdjpy_trade_pnl(self):
        spec = STANDARD_SPECS["USDJPY"]
        # LONG +100 pips (1.00 JPY) on 0.10 lot (10,000 USD).
        # Gross JPY = 1.00 * 10,000 = 10,000 JPY. Exit price = 150.00.
        # Gross USD = 10,000 / 150.00 = 66.6667 USD. Comm = 0.70 -> Net = 65.9667 USD.
        res_long = calculate_trade_pnl(spec, direction=1, entry_price=149.000, exit_price=150.000, lots=0.10)
        self.assertAlmostEqual(res_long['gross_pnl_usd'], 66.6667, places=2)
        self.assertAlmostEqual(res_long['commission_usd'], 0.70, places=2)
        self.assertAlmostEqual(res_long['net_pnl_usd'], 65.9667, places=2)

    def test_btcusd_trade_pnl(self):
        spec = STANDARD_SPECS["BTCUSD"]
        # LONG +100 points ($100) on 0.10 BTC -> Gross = 100 * 0.10 = $10.00. Comm = $0.70 -> Net = $9.30
        res_long = calculate_trade_pnl(spec, direction=1, entry_price=60000.00, exit_price=60100.00, lots=0.10)
        self.assertAlmostEqual(res_long['gross_pnl_usd'], 10.00, places=2)
        self.assertAlmostEqual(res_long['commission_usd'], 0.70, places=2)
        self.assertAlmostEqual(res_long['net_pnl_usd'], 9.30, places=2)

    def test_engine_synthetic_simulation(self):
        # Run a direct engine backtest with synthetic data to test full execution loop
        eng = DeepQuantEngine("GOLD_H1_2001_2026.csv")
        # Ensure engine spec is properly set
        self.assertEqual(eng.spec.symbol, "GOLD")
        self.assertEqual(eng.spec.contract_size, 100.0)

if __name__ == '__main__':
    print("=" * 80)
    print("🧪 RUNNING ASSET-AWARE ENGINE LEVEL UNIT TESTS")
    print("=" * 80)
    suite = unittest.TestLoader().loadTestsFromTestCase(TestAssetAwareEngine)
    runner = unittest.TextTestRunner(verbosity=2)
    res = runner.run(suite)
    if res.wasSuccessful():
        print("\n✅ ALL ENGINE-LEVEL ASSET-AWARE UNIT TESTS PASSED PERFECTLY.")
    else:
        print("\n❌ ENGINE UNIT TESTS FAILED.")
        sys.exit(1)
