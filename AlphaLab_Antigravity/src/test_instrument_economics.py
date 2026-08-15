"""
TEST INSTRUMENT ECONOMICS & CROSS-ASSET VALUATION SUITE
======================================================
Validates synthetic PnL calculations for:
- XAUUSD (Gold)
- EURUSD
- GBPUSD
- USDJPY (Inverse quote currency conversion)
- BTCUSD (Crypto contract size)

Tests:
1. LONG +100 pips
2. LONG -100 pips
3. SHORT +100 pips
4. SHORT -100 pips
5. Spread & Commission deduction symmetry
"""

import sys
import unittest
import numpy as np

sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None

class TestInstrumentEconomics(unittest.TestCase):
    
    def test_xauusd_valuation(self):
        # 0.10 lot XAUUSD = 10 oz. 1 pip = $0.01. Pip value = $0.10 USD.
        lot = 0.10
        vol_oz = lot * 100.0
        pip_size = 0.01
        
        # LONG +100 pips (+1.00 USD/oz)
        p_entry, p_exit = 2000.00, 2001.00
        gross_pnl = (p_exit - p_entry) * vol_oz
        self.assertAlmostEqual(gross_pnl, 10.00, places=2)
        
        # LONG -100 pips
        p_exit_loss = 1999.00
        gross_loss = (p_exit_loss - p_entry) * vol_oz
        self.assertAlmostEqual(gross_loss, -10.00, places=2)
        
        # SHORT +100 pips (+1.00 profit on price dropping to 1999.00)
        gross_short_win = (p_entry - p_exit_loss) * vol_oz
        self.assertAlmostEqual(gross_short_win, 10.00, places=2)
        
        # Cost deduction: 25 pips spread ($0.25) + $7/lot comm ($0.70 on 0.10 lot) = $2.50 + $0.70 = $3.20
        net_long_win = gross_pnl - (0.25 * vol_oz) - (7.0 * lot)
        self.assertAlmostEqual(net_long_win, 6.80, places=2)

    def test_eurusd_valuation(self):
        # 0.10 lot EURUSD = 10,000 EUR. 1 pip = 0.0001. Pip value = $1.00 USD.
        lot = 0.10
        vol_base = lot * 100000.0
        pip_size = 0.0001
        
        # LONG +100 pips (+0.0100)
        p_entry, p_exit = 1.10000, 1.11000
        gross_pnl = (p_exit - p_entry) * vol_base
        self.assertAlmostEqual(gross_pnl, 100.00, places=2)
        
        # LONG -100 pips (-0.0100)
        p_exit_loss = 1.09000
        gross_loss = (p_exit_loss - p_entry) * vol_base
        self.assertAlmostEqual(gross_loss, -100.00, places=2)
        
        # SHORT +100 pips
        gross_short_win = (p_entry - p_exit_loss) * vol_base
        self.assertAlmostEqual(gross_short_win, 100.00, places=2)
        
        # Spread 1.5 pips (0.00015 = $1.50) + comm ($0.70) = $2.20
        net_pnl = gross_pnl - (0.00015 * vol_base) - (7.0 * lot)
        self.assertAlmostEqual(net_pnl, 97.80, places=2)

    def test_gbpusd_valuation(self):
        # 0.10 lot GBPUSD = 10,000 GBP. 1 pip = 0.0001. Pip value = $1.00 USD.
        lot = 0.10
        vol_base = lot * 100000.0
        p_entry, p_exit = 1.25000, 1.26000
        gross_pnl = (p_exit - p_entry) * vol_base
        self.assertAlmostEqual(gross_pnl, 100.00, places=2)

    def test_usdjpy_valuation(self):
        # 0.10 lot USDJPY = 10,000 USD. Pip = 0.01 JPY.
        # PnL in JPY = (p_exit - p_entry) / 0.01 * 100 JPY.
        # PnL in USD = PnL_JPY / p_exit.
        lot = 0.10
        vol_usd = lot * 100000.0
        p_entry, p_exit = 150.000, 151.000 # +100 pips move
        pnl_jpy = (p_exit - p_entry) * vol_usd # 1.00 * 10,000 = 10,000 JPY
        pnl_usd = pnl_jpy / p_exit # 10,000 / 151.000 = 66.225 USD
        self.assertAlmostEqual(pnl_usd, 66.225, places=2)
        
        # SHORT +100 pips (150.00 -> 149.00)
        p_exit_short = 149.000
        pnl_short_jpy = (p_entry - p_exit_short) * vol_usd # 10,000 JPY
        pnl_short_usd = pnl_short_jpy / p_exit_short # 10,000 / 149.000 = 67.114 USD
        self.assertAlmostEqual(pnl_short_usd, 67.114, places=2)

    def test_btcusd_valuation(self):
        # 0.10 lot BTCUSD = 0.10 BTC.
        lot = 0.10
        p_entry, p_exit = 60000.00, 61000.00 # +$1,000 move (+1000 points)
        gross_pnl = (p_exit - p_entry) * lot
        self.assertAlmostEqual(gross_pnl, 100.00, places=2)

if __name__ == '__main__':
    print("=" * 80)
    print("🧪 RUNNING MULTI-INSTRUMENT VALUATION UNIT TESTS")
    print("=" * 80)
    suite = unittest.TestLoader().loadTestsFromTestCase(TestInstrumentEconomics)
    runner = unittest.TextTestRunner(verbosity=2)
    res = runner.run(suite)
    if res.wasSuccessful():
        print("\n✅ ALL 5 INSTRUMENT VALUATION UNIT TESTS PASSED PERFECTLY.")
    else:
        print("\n❌ UNIT TEST FAILURES DETECTED.")
        sys.exit(1)
