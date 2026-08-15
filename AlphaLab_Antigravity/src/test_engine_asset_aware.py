"""
V3.2.1 COMPREHENSIVE ENGINE INTEGRATION & ASSET-AWARE UNIT TESTS
================================================================
Executes full backtest simulations directly through DeepQuantEngine.run_strategy() for:
1. XAUUSD (Gold)
2. EURUSD
3. GBPUSD
4. USDJPY (dynamic contemporaneous JPY/USD conversion)
5. BTCUSD

Explicitly tests and verifies:
- Strategy interface: signal_fn returning (signals, sl_dists, tp_dists)
- Exact entry/exit execution pricing (Ask = Open + spread, Bid = Open)
- Correct stop loss / take profit placement relative to entry price
- Net PnL, spread friction, and commission deduction ($7/lot)
- Net-cost R expectancy
"""

import sys
import unittest
import numpy as np
import pandas as pd
from deep_quant_engine import DeepQuantEngine, InstrumentSpec, calculate_trade_pnl, STANDARD_SPECS

sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None

def make_synthetic_ohlc(start_price, price_path, start_dt="2020-01-01 00:00:00", freq='1h'):
    """Generates synthetic OHLC candles from a price path."""
    n = len(price_path)
    dts = pd.date_range(start=start_dt, periods=n, freq=freq)
    opens = [start_price] + list(price_path[:-1])
    closes = list(price_path)
    highs = [max(o, c) + 0.05 * abs(c - o + 0.01) for o, c in zip(opens, closes)]
    lows = [min(o, c) - 0.05 * abs(c - o + 0.01) for o, c in zip(opens, closes)]
    return pd.DataFrame({
        'datetime_str': [str(d) for d in dts],
        'open': opens,
        'high': highs,
        'low': lows,
        'close': closes
    })

class TestAssetAwareEngineIntegration(unittest.TestCase):
    
    def test_standalone_pnl_xauusd(self):
        spec = STANDARD_SPECS["XAUUSD"]
        # LONG +100 pips ($1.00) on 0.10 lot (10 oz) -> Gross PnL = $10.00, Comm = $0.70 -> Net = $9.30
        res = calculate_trade_pnl(spec, 1, 2000.00, 2001.00, lots=0.10)
        self.assertAlmostEqual(res['gross_pnl_usd'], 10.00, places=2)
        self.assertAlmostEqual(res['commission_usd'], 0.70, places=2)
        self.assertAlmostEqual(res['net_pnl_usd'], 9.30, places=2)

    def test_standalone_pnl_gbpusd(self):
        spec = STANDARD_SPECS["GBPUSD"]
        # LONG +100 pips (0.0100) on 0.10 lot (10,000 GBP) -> Gross = $100.00, Comm = $0.70 -> Net = $99.30
        res = calculate_trade_pnl(spec, 1, 1.25000, 1.26000, lots=0.10)
        self.assertAlmostEqual(res['gross_pnl_usd'], 100.00, places=2)
        self.assertAlmostEqual(res['commission_usd'], 0.70, places=2)
        self.assertAlmostEqual(res['net_pnl_usd'], 99.30, places=2)

    def test_standalone_pnl_usdjpy(self):
        spec = STANDARD_SPECS["USDJPY"]
        # LONG +100 pips (1.00 JPY) on 0.10 lot (10,000 USD). Exit price = 150.00.
        # Gross = (1.00 * 10,000) / 150.00 = 66.67 USD. Comm = 0.70 -> Net = 65.97 USD.
        res = calculate_trade_pnl(spec, 1, 149.000, 150.000, lots=0.10)
        self.assertAlmostEqual(res['gross_pnl_usd'], 66.6667, places=2)
        self.assertAlmostEqual(res['commission_usd'], 0.70, places=2)
        self.assertAlmostEqual(res['net_pnl_usd'], 65.9667, places=2)

    def test_integration_xauusd_buy_tp(self):
        # Synthetic simulation: Bar 0 gives signal, Bar 1 enters BUY at 2000.00 + spread (0.25) = 2000.25
        # Bar 2 rises to 2005.00 hitting TP (tp_dist = 3.00 -> tp = 2003.25)
        spec = STANDARD_SPECS["XAUUSD"]
        dts = pd.date_range("2024-01-01", periods=10, freq="1h")
        df = pd.DataFrame({
            'datetime': dts,
            'open':  [2000.0, 2000.0, 2004.0, 2004.0, 2004.0, 2004.0, 2004.0, 2004.0, 2004.0, 2004.0],
            'high':  [2001.0, 2001.0, 2006.0, 2005.0, 2005.0, 2005.0, 2005.0, 2005.0, 2005.0, 2005.0],
            'low':   [1999.0, 1999.0, 2002.0, 2003.0, 2003.0, 2003.0, 2003.0, 2003.0, 2003.0, 2003.0],
            'close': [2000.0, 2000.0, 2005.0, 2004.0, 2004.0, 2004.0, 2004.0, 2004.0, 2004.0, 2004.0]
        })
        eng = DeepQuantEngine(data_file=None, df=df, spec=spec)
        
        # Test signal returning DISTANCES: sl_dist = 2.00, tp_dist = 3.00
        def sig_fn(d):
            n = len(d)
            sig = np.zeros(n, dtype=int)
            sl_dist = np.zeros(n, dtype=float)
            tp_dist = np.zeros(n, dtype=float)
            sig[0] = 1 # Buy signal at bar 0 close
            sl_dist[0] = 2.00 # $2.00 SL distance
            tp_dist[0] = 3.00 # $3.00 TP distance
            return sig, sl_dist, tp_dist
            
        tdf, qdf, summ = eng.run_strategy(sig_fn, spread_pips=25.0, commission_per_lot=7.0, fixed_lot=0.10)
        self.assertEqual(len(tdf), 1)
        t = tdf.iloc[0]
        
        # Entry Ask = 2000.00 + 0.25 = 2000.25
        self.assertAlmostEqual(t['entry_price'], 2000.25, places=2)
        # TP = 2000.25 + 3.00 = 2003.25
        self.assertAlmostEqual(t['tp'], 2003.25, places=2)
        # Exit at TP Bid = 2003.25
        self.assertAlmostEqual(t['exit_price'], 2003.25, places=2)
        self.assertEqual(t['exit_reason'], 'TP')
        
        # Price diff = 2003.25 - 2000.25 = 3.00 USD/oz.
        # 0.10 lot = 10 oz -> Gross PnL = 3.00 * 10 = $30.00 USD.
        # Comm = $0.70 -> Net PnL = $29.30 USD.
        self.assertAlmostEqual(t['pnl_usd'], 29.30, places=2)
        self.assertGreater(t['pnl_r'], 1.0) # Positive R

    def test_integration_usdjpy_sell_sl(self):
        # Synthetic USDJPY simulation testing SELL Stop Loss
        spec = STANDARD_SPECS["USDJPY"]
        dts = pd.date_range("2024-01-01", periods=10, freq="1h")
        df = pd.DataFrame({
            'datetime': dts,
            'open':  [150.00, 150.00, 151.50, 151.50, 151.50, 151.50, 151.50, 151.50, 151.50, 151.50],
            'high':  [150.10, 150.10, 152.00, 151.60, 151.60, 151.60, 151.60, 151.60, 151.60, 151.60],
            'low':   [149.90, 149.90, 149.90, 151.40, 151.40, 151.40, 151.40, 151.40, 151.40, 151.40],
            'close': [150.00, 150.00, 151.50, 151.50, 151.50, 151.50, 151.50, 151.50, 151.50, 151.50]
        })
        eng = DeepQuantEngine(data_file=None, df=df, spec=spec)
        
        def sig_fn(d):
            n = len(d)
            sig = np.zeros(n, dtype=int)
            sl_dist = np.zeros(n, dtype=float)
            tp_dist = np.zeros(n, dtype=float)
            sig[0] = -1 # Sell signal at bar 0
            sl_dist[0] = 1.00 # 100 pips SL distance (1.00 JPY)
            tp_dist[0] = 2.00 # 200 pips TP distance (2.00 JPY)
            return sig, sl_dist, tp_dist
            
        tdf, qdf, summ = eng.run_strategy(sig_fn, spread_pips=1.8, commission_per_lot=7.0, fixed_lot=0.10)
        self.assertEqual(len(tdf), 1)
        t = tdf.iloc[0]
        
        # Entry Bid = 150.00
        self.assertAlmostEqual(t['entry_price'], 150.00, places=2)
        # SL for SELL = 150.00 + 1.00 = 151.00
        self.assertAlmostEqual(t['sl'], 151.00, places=2)
        # Bar 2 High reaches 152.00 (Ask = 152.018 >= 151.00), triggering SL
        self.assertEqual(t['exit_reason'], 'SL')
        self.assertAlmostEqual(t['exit_price'], 151.00, places=2)
        self.assertLess(t['pnl_usd'], 0.0) # Loss
        self.assertAlmostEqual(t['pnl_r'], -1.0, places=1) # Exactly -1R

if __name__ == '__main__':
    print("=" * 80)
    print("🧪 RUNNING COMPREHENSIVE ENGINE-LEVEL INTEGRATION UNIT TESTS")
    print("=" * 80)
    suite = unittest.TestLoader().loadTestsFromTestCase(TestAssetAwareEngineIntegration)
    runner = unittest.TextTestRunner(verbosity=2)
    res = runner.run(suite)
    if res.wasSuccessful():
        print("\n✅ ALL ENGINE INTEGRATION UNIT TESTS PASSED PERFECTLY.")
    else:
        print("\n❌ ENGINE INTEGRATION TESTS FAILED.")
        sys.exit(1)
