import unittest
import numpy as np
import pandas as pd

from distributed_edge_v35 import complete_quarters, build_rolling, positive_pool_shares
from experiment_v3_5_h218_to_h220 import build_configs, make_h218_signals


class TestV35Framework(unittest.TestCase):
    def test_quarter_and_rolling_window_counts(self):
        quarters = complete_quarters()
        self.assertEqual(len(quarters), 33)
        qdf = pd.DataFrame({
            "quarter": quarters,
            "net_pnl_usd": np.ones(33),
            "gross_profit_usd": np.ones(33),
            "gross_loss_usd": np.ones(33) * 0.5,
        })
        self.assertEqual(len(build_rolling(qdf, 4)), 30)
        self.assertEqual(len(build_rolling(qdf, 8)), 26)

    def test_positive_profit_pool_denominator(self):
        shares, applicable = positive_pool_shares([10.0, -100.0, 5.0, 0.0], ks=(1, 3))
        self.assertTrue(applicable)
        self.assertAlmostEqual(shares[1], 10.0 / 15.0 * 100.0)
        self.assertAlmostEqual(shares[3], 100.0)

    def test_frozen_config_budget(self):
        configs = build_configs()
        self.assertEqual(len(configs), 12)
        self.assertEqual(len({x[0] for x in configs}), 12)

    def test_h218_uses_same_current_day_previous_day_level(self):
        # Day 1 establishes a high of 100. Day 2 first closes below 100, then
        # closes through 100. The second Day-2 bar must produce a Long signal.
        times = list(pd.date_range("2026-01-01 00:00", periods=16, freq="30min"))
        times += list(pd.date_range("2026-01-02 00:00", periods=16, freq="30min"))
        n = len(times)
        close = np.full(n, 99.0)
        high = np.full(n, 99.5)
        low = np.full(n, 98.5)
        open_ = np.full(n, 99.0)

        high[:16] = 100.0
        close[16] = 99.0
        high[16] = 99.5
        close[17] = 101.0
        high[17] = 101.2
        low[17] = 98.8

        df = pd.DataFrame({
            "datetime": times,
            "open": open_,
            "high": high,
            "low": low,
            "close": close,
        })
        sig, sl, tp = make_h218_signals(df, 1.5, 2.0)
        self.assertEqual(sig[17], 1)
        self.assertGreater(sl[17], 0)
        self.assertAlmostEqual(tp[17] / sl[17], 2.0)


if __name__ == "__main__":
    unittest.main()
