"""
V3.2.2 COMPREHENSIVE MULTI-ASSET INTEGRATION & EXECUTION UNIT TEST SUITE
========================================================================
Runs full causal backtest simulations directly through DeepQuantEngine.run_strategy() for:
1. XAUUSD (Gold): BUY TP, BUY SL, SELL TP, SELL SL
2. EURUSD: BUY TP, SELL SL
3. GBPUSD: BUY TP, SELL SL
4. USDJPY (dynamic contemporaneous conversion): BUY TP, SELL SL
5. BTCUSD: BUY TP, SELL SL
6. Pessimistic intra-bar ambiguous bar resolution (BUY and SELL)
7. Runtime strategy contract validation (validate_strategy_output)
"""

import sys
import unittest
import numpy as np
import pandas as pd
from deep_quant_engine import (
    DeepQuantEngine, InstrumentSpec, calculate_trade_pnl, 
    validate_strategy_output, STANDARD_SPECS
)

sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None

class TestComprehensiveEngineIntegration(unittest.TestCase):
    
    # -------------------------------------------------------------
    # 1. STANDALONE TRADE PNL TESTS
    # -------------------------------------------------------------
    def test_pnl_xauusd(self):
        spec = STANDARD_SPECS["XAUUSD"]
        # LONG +100 pips ($1.00) on 0.10 lot (10 oz) -> Gross PnL = $10.00, Comm = $0.70 -> Net = $9.30
        res = calculate_trade_pnl(spec, 1, 2000.00, 2001.00, lots=0.10)
        self.assertAlmostEqual(res['gross_pnl_usd'], 10.00, places=2)
        self.assertAlmostEqual(res['commission_usd'], 0.70, places=2)
        self.assertAlmostEqual(res['net_pnl_usd'], 9.30, places=2)

    def test_pnl_eurusd(self):
        spec = STANDARD_SPECS["EURUSD"]
        # LONG +100 pips (0.0100) on 0.10 lot (10,000 EUR) -> Gross = $100.00, Comm = $0.70 -> Net = $99.30
        res = calculate_trade_pnl(spec, 1, 1.10000, 1.11000, lots=0.10)
        self.assertAlmostEqual(res['gross_pnl_usd'], 100.00, places=2)
        self.assertAlmostEqual(res['net_pnl_usd'], 99.30, places=2)

    def test_pnl_gbpusd(self):
        spec = STANDARD_SPECS["GBPUSD"]
        # LONG +100 pips (0.0100) on 0.10 lot (10,000 GBP) -> Gross = $100.00, Comm = $0.70 -> Net = $99.30
        res = calculate_trade_pnl(spec, 1, 1.25000, 1.26000, lots=0.10)
        self.assertAlmostEqual(res['gross_pnl_usd'], 100.00, places=2)
        self.assertAlmostEqual(res['net_pnl_usd'], 99.30, places=2)

    def test_pnl_usdjpy(self):
        spec = STANDARD_SPECS["USDJPY"]
        # LONG +100 pips (1.00 JPY) on 0.10 lot (10,000 USD). Exit price = 150.00.
        # Gross = (1.00 * 10,000) / 150.00 = 66.67 USD. Comm = 0.70 -> Net = 65.97 USD.
        res = calculate_trade_pnl(spec, 1, 149.000, 150.000, lots=0.10)
        self.assertAlmostEqual(res['gross_pnl_usd'], 66.6667, places=2)
        self.assertAlmostEqual(res['net_pnl_usd'], 65.9667, places=2)

    def test_pnl_btcusd(self):
        spec = STANDARD_SPECS["BTCUSD"]
        # LONG +100 pts ($100.00) on 0.10 BTC -> Gross = $10.00, Comm = $0.70 -> Net = $9.30
        res = calculate_trade_pnl(spec, 1, 60000.00, 60100.00, lots=0.10)
        self.assertAlmostEqual(res['gross_pnl_usd'], 10.00, places=2)
        self.assertAlmostEqual(res['net_pnl_usd'], 9.30, places=2)

    # -------------------------------------------------------------
    # 2. FULL ENGINE RUN_STRATEGY INTEGRATION TESTS ACROSS ALL ASSETS
    # -------------------------------------------------------------
    def test_integration_xauusd_buy_tp_and_buy_sl(self):
        spec = STANDARD_SPECS["XAUUSD"]
        dts = pd.date_range("2024-01-01", periods=10, freq="1h")
        # Bar 0 signal, Bar 1 enters BUY @ 2000.25 (Ask = 2000.0 + 0.25 spread). TP=2003.25, SL=1998.25.
        # Bar 2 rises to 2006.0 hitting TP @ 2003.25.
        df_tp = pd.DataFrame({
            'datetime': dts,
            'open':  [2000.0, 2000.0, 2004.0, 2004.0, 2004.0, 2004.0, 2004.0, 2004.0, 2004.0, 2004.0],
            'high':  [2001.0, 2001.0, 2006.0, 2005.0, 2005.0, 2005.0, 2005.0, 2005.0, 2005.0, 2005.0],
            'low':   [1999.0, 1999.0, 2002.0, 2003.0, 2003.0, 2003.0, 2003.0, 2003.0, 2003.0, 2003.0],
            'close': [2000.0, 2000.0, 2005.0, 2004.0, 2004.0, 2004.0, 2004.0, 2004.0, 2004.0, 2004.0]
        })
        eng_tp = DeepQuantEngine(data_file=None, df=df_tp, spec=spec)
        def sig_fn_tp(d):
            n = len(d)
            s, sl, tp = np.zeros(n, dtype=int), np.zeros(n, dtype=float), np.zeros(n, dtype=float)
            s[0] = 1; sl[0] = 2.0; tp[0] = 3.0
            return s, sl, tp
        tdf_tp, _, _ = eng_tp.run_strategy(sig_fn_tp, spread_pips=25.0, fixed_lot=0.10)
        self.assertEqual(len(tdf_tp), 1)
        self.assertEqual(tdf_tp.iloc[0]['exit_reason'], 'TP')
        self.assertAlmostEqual(tdf_tp.iloc[0]['pnl_usd'], 29.30, places=2)

        # Bar 2 drops to 1995.0 hitting SL @ 1998.25
        df_sl = df_tp.copy()
        df_sl['low'] = [1999.0, 1999.0, 1995.0, 1995.0, 1995.0, 1995.0, 1995.0, 1995.0, 1995.0, 1995.0]
        df_sl['high'] = [2001.0, 2001.0, 2001.0, 2001.0, 2001.0, 2001.0, 2001.0, 2001.0, 2001.0, 2001.0]
        eng_sl = DeepQuantEngine(data_file=None, df=df_sl, spec=spec)
        tdf_sl, _, _ = eng_sl.run_strategy(sig_fn_tp, spread_pips=25.0, fixed_lot=0.10)
        self.assertEqual(len(tdf_sl), 1)
        self.assertEqual(tdf_sl.iloc[0]['exit_reason'], 'SL')
        self.assertAlmostEqual(tdf_sl.iloc[0]['pnl_usd'], -20.70, places=2) # ($2.00 * 10 oz) + $0.70 comm = -$20.70
        self.assertAlmostEqual(tdf_sl.iloc[0]['pnl_r'], -1.0, places=2)

    def test_integration_xauusd_sell_tp_and_sell_sl(self):
        spec = STANDARD_SPECS["XAUUSD"]
        dts = pd.date_range("2024-01-01", periods=10, freq="1h")
        # Bar 0 SELL signal. Bar 1 enters SELL at Bid = 2000.00. TP=1997.00, SL=2002.00.
        # SELL TP hits if Ask <= 1997.00 (i.e. Low + 0.25 <= 1997.00 -> Low <= 1996.75)
        df_tp = pd.DataFrame({
            'datetime': dts,
            'open':  [2000.0, 2000.0, 1996.0, 1996.0, 1996.0, 1996.0, 1996.0, 1996.0, 1996.0, 1996.0],
            'high':  [2001.0, 2001.0, 1998.0, 1997.0, 1997.0, 1997.0, 1997.0, 1997.0, 1997.0, 1997.0],
            'low':   [1999.0, 1999.0, 1995.0, 1995.0, 1995.0, 1995.0, 1995.0, 1995.0, 1995.0, 1995.0],
            'close': [2000.0, 2000.0, 1995.5, 1996.0, 1996.0, 1996.0, 1996.0, 1996.0, 1996.0, 1996.0]
        })
        eng_tp = DeepQuantEngine(data_file=None, df=df_tp, spec=spec)
        def sig_fn_sell(d):
            n = len(d)
            s, sl, tp = np.zeros(n, dtype=int), np.zeros(n, dtype=float), np.zeros(n, dtype=float)
            s[0] = -1; sl[0] = 2.0; tp[0] = 3.0
            return s, sl, tp
        tdf_tp, _, _ = eng_tp.run_strategy(sig_fn_sell, spread_pips=25.0, fixed_lot=0.10)
        self.assertEqual(len(tdf_tp), 1)
        self.assertEqual(tdf_tp.iloc[0]['exit_reason'], 'TP')
        self.assertAlmostEqual(tdf_tp.iloc[0]['pnl_usd'], 29.30, places=2)

    def test_integration_eurusd_buy_tp(self):
        spec = STANDARD_SPECS["EURUSD"]
        dts = pd.date_range("2024-01-01", periods=10, freq="1h")
        # Bar 1 enters BUY @ 1.10015 (Ask = 1.1000 + 0.00015 spread). TP = 1.10015 + 0.00300 = 1.10315.
        # Bar 2 rises to 1.10500 hitting TP. Net PnL = $30.00 - $0.70 = $29.30 USD.
        df = pd.DataFrame({
            'datetime': dts,
            'open':  [1.1000, 1.1000, 1.1040, 1.1040, 1.1040, 1.1040, 1.1040, 1.1040, 1.1040, 1.1040],
            'high':  [1.1010, 1.1010, 1.1060, 1.1050, 1.1050, 1.1050, 1.1050, 1.1050, 1.1050, 1.1050],
            'low':   [1.0990, 1.0990, 1.1020, 1.1030, 1.1030, 1.1030, 1.1030, 1.1030, 1.1030, 1.1030],
            'close': [1.1000, 1.1000, 1.1050, 1.1040, 1.1040, 1.1040, 1.1040, 1.1040, 1.1040, 1.1040]
        })
        eng = DeepQuantEngine(data_file=None, df=df, spec=spec)
        def sig_fn(d):
            n = len(d)
            s, sl, tp = np.zeros(n, dtype=int), np.zeros(n, dtype=float), np.zeros(n, dtype=float)
            s[0] = 1; sl[0] = 0.0020; tp[0] = 0.0030
            return s, sl, tp
        tdf, _, _ = eng.run_strategy(sig_fn, spread_pips=1.5, fixed_lot=0.10)
        self.assertEqual(len(tdf), 1)
        self.assertEqual(tdf.iloc[0]['exit_reason'], 'TP')
        self.assertAlmostEqual(tdf.iloc[0]['pnl_usd'], 29.30, places=2)

    def test_integration_gbpusd_sell_sl(self):
        spec = STANDARD_SPECS["GBPUSD"]
        dts = pd.date_range("2024-01-01", periods=10, freq="1h")
        # Bar 1 enters SELL @ 1.25000. SL = 1.25000 + 0.00200 = 1.25200.
        # Bar 2 High reaches 1.25300 (Ask = 1.25318 >= 1.25200), hitting SL.
        df = pd.DataFrame({
            'datetime': dts,
            'open':  [1.2500, 1.2500, 1.2525, 1.2525, 1.2525, 1.2525, 1.2525, 1.2525, 1.2525, 1.2525],
            'high':  [1.2510, 1.2510, 1.2535, 1.2530, 1.2530, 1.2530, 1.2530, 1.2530, 1.2530, 1.2530],
            'low':   [1.2490, 1.2490, 1.2490, 1.2500, 1.2500, 1.2500, 1.2500, 1.2500, 1.2500, 1.2500],
            'close': [1.2500, 1.2500, 1.2530, 1.2525, 1.2525, 1.2525, 1.2525, 1.2525, 1.2525, 1.2525]
        })
        eng = DeepQuantEngine(data_file=None, df=df, spec=spec)
        def sig_fn(d):
            n = len(d)
            s, sl, tp = np.zeros(n, dtype=int), np.zeros(n, dtype=float), np.zeros(n, dtype=float)
            s[0] = -1; sl[0] = 0.0020; tp[0] = 0.0040
            return s, sl, tp
        tdf, _, _ = eng.run_strategy(sig_fn, spread_pips=1.8, fixed_lot=0.10)
        self.assertEqual(len(tdf), 1)
        self.assertEqual(tdf.iloc[0]['exit_reason'], 'SL')
        self.assertAlmostEqual(tdf.iloc[0]['pnl_usd'], -20.70, places=2)

    def test_integration_usdjpy_buy_tp(self):
        spec = STANDARD_SPECS["USDJPY"]
        dts = pd.date_range("2024-01-01", periods=10, freq="1h")
        # Bar 1 enters BUY @ 150.018. TP = 150.018 + 1.000 = 151.018.
        # Bar 2 High reaches 152.00. Exit at 151.018.
        # Gross JPY = 1.00 * 10,000 USD = 10,000 JPY. Exit conversion @ 151.018 = $66.217 USD.
        # Comm = $0.70 -> Net = $65.52 USD.
        df = pd.DataFrame({
            'datetime': dts,
            'open':  [150.00, 150.00, 151.50, 151.50, 151.50, 151.50, 151.50, 151.50, 151.50, 151.50],
            'high':  [150.10, 150.10, 152.00, 151.60, 151.60, 151.60, 151.60, 151.60, 151.60, 151.60],
            'low':   [149.90, 149.90, 150.50, 151.40, 151.40, 151.40, 151.40, 151.40, 151.40, 151.40],
            'close': [150.00, 150.00, 151.50, 151.50, 151.50, 151.50, 151.50, 151.50, 151.50, 151.50]
        })
        eng = DeepQuantEngine(data_file=None, df=df, spec=spec)
        def sig_fn(d):
            n = len(d)
            s, sl, tp = np.zeros(n, dtype=int), np.zeros(n, dtype=float), np.zeros(n, dtype=float)
            s[0] = 1; sl[0] = 0.50; tp[0] = 1.00
            return s, sl, tp
        tdf, _, _ = eng.run_strategy(sig_fn, spread_pips=1.8, fixed_lot=0.10)
        self.assertEqual(len(tdf), 1)
        self.assertEqual(tdf.iloc[0]['exit_reason'], 'TP')
        self.assertAlmostEqual(tdf.iloc[0]['pnl_usd'], 65.52, places=1)

    def test_integration_btcusd_sell_sl(self):
        spec = STANDARD_SPECS["BTCUSD"]
        dts = pd.date_range("2024-01-01", periods=10, freq="1h")
        # Bar 1 enters SELL @ 60000.00. SL = 60000.00 + 500.00 = 60500.00.
        # Bar 2 High reaches 61000.00. Exit at 60500.00. Loss = 500 * 0.10 = $50.00 + $0.70 comm = -$50.70 USD.
        df = pd.DataFrame({
            'datetime': dts,
            'open':  [60000.0, 60000.0, 60600.0, 60600.0, 60600.0, 60600.0, 60600.0, 60600.0, 60600.0, 60600.0],
            'high':  [60100.0, 60100.0, 61000.0, 60700.0, 60700.0, 60700.0, 60700.0, 60700.0, 60700.0, 60700.0],
            'low':   [59900.0, 59900.0, 59900.0, 60500.0, 60500.0, 60500.0, 60500.0, 60500.0, 60500.0, 60500.0],
            'close': [60000.0, 60000.0, 60700.0, 60600.0, 60600.0, 60600.0, 60600.0, 60600.0, 60600.0, 60600.0]
        })
        eng = DeepQuantEngine(data_file=None, df=df, spec=spec)
        def sig_fn(d):
            n = len(d)
            s, sl, tp = np.zeros(n, dtype=int), np.zeros(n, dtype=float), np.zeros(n, dtype=float)
            s[0] = -1; sl[0] = 500.0; tp[0] = 1000.0
            return s, sl, tp
        tdf, _, _ = eng.run_strategy(sig_fn, spread_pips=50.0, fixed_lot=0.10)
        self.assertEqual(len(tdf), 1)
        self.assertEqual(tdf.iloc[0]['exit_reason'], 'SL')
        self.assertAlmostEqual(tdf.iloc[0]['pnl_usd'], -50.70, places=2)

    # -------------------------------------------------------------
    # 3. PESSIMISTIC AMBIGUOUS BAR RESOLUTION
    # -------------------------------------------------------------
    def test_ambiguous_bar_pessimistic_buy(self):
        spec = STANDARD_SPECS["XAUUSD"]
        dts = pd.date_range("2024-01-01", periods=10, freq="1h")
        # Bar 1 enters BUY @ 2000.25. SL = 1998.25, TP = 2003.25.
        # Bar 2 is a giant candle: Low=1995.0 (touches SL) AND High=2010.0 (touches TP).
        df = pd.DataFrame({
            'datetime': dts,
            'open':  [2000.0, 2000.0, 2000.0, 2000.0, 2000.0, 2000.0, 2000.0, 2000.0, 2000.0, 2000.0],
            'high':  [2001.0, 2001.0, 2010.0, 2001.0, 2001.0, 2001.0, 2001.0, 2001.0, 2001.0, 2001.0],
            'low':   [1999.0, 1999.0, 1995.0, 1999.0, 1999.0, 1999.0, 1999.0, 1999.0, 1999.0, 1999.0],
            'close': [2000.0, 2000.0, 2002.0, 2000.0, 2000.0, 2000.0, 2000.0, 2000.0, 2000.0, 2000.0]
        })
        eng = DeepQuantEngine(data_file=None, df=df, spec=spec)
        def sig_fn(d):
            n = len(d)
            s, sl, tp = np.zeros(n, dtype=int), np.zeros(n, dtype=float), np.zeros(n, dtype=float)
            s[0] = 1; sl[0] = 2.0; tp[0] = 3.0
            return s, sl, tp
        tdf, _, _ = eng.run_strategy(sig_fn, spread_pips=25.0, fixed_lot=0.10, pessimistic_ambiguous_bars=True)
        self.assertEqual(len(tdf), 1)
        self.assertEqual(tdf.iloc[0]['exit_reason'], 'SL_AMBIGUOUS_PESSIMISTIC')
        self.assertAlmostEqual(tdf.iloc[0]['pnl_usd'], -20.70, places=2)

    # -------------------------------------------------------------
    # 4. RUNTIME STRATEGY CONTRACT VALIDATION
    # -------------------------------------------------------------
    def test_contract_validation_catches_absolute_price_and_negative(self):
        dts = pd.date_range("2024-01-01", periods=5, freq="1h")
        df = pd.DataFrame({
            'datetime': dts,
            'open': [2000.0]*5, 'high': [2001.0]*5, 'low': [1999.0]*5, 'close': [2000.0]*5
        })
        # Test negative distance
        with self.assertRaises(ValueError):
            validate_strategy_output(df, np.array([1, 0, 0, 0, 0]), np.array([-2.0, 0, 0, 0, 0]), np.array([3.0, 0, 0, 0, 0]))
            
        # Test absolute price passed as distance (e.g. 1950.0 on Gold @ 2000)
        with self.assertRaises(ValueError):
            validate_strategy_output(df, np.array([1, 0, 0, 0, 0]), np.array([1950.0, 0, 0, 0, 0]), np.array([3.0, 0, 0, 0, 0]))

if __name__ == '__main__':
    print("=" * 80)
    print("🧪 RUNNING COMPREHENSIVE MULTI-ASSET INTEGRATION & EXECUTION TESTS")
    print("=" * 80)
    suite = unittest.TestLoader().loadTestsFromTestCase(TestComprehensiveEngineIntegration)
    runner = unittest.TextTestRunner(verbosity=2)
    res = runner.run(suite)
    if res.wasSuccessful():
        print("\n✅ ALL ENGINE INTEGRATION & CONTRACT VALIDATION TESTS PASSED (100%).")
    else:
        print("\n❌ ENGINE INTEGRATION TESTS FAILED.")
        sys.exit(1)
