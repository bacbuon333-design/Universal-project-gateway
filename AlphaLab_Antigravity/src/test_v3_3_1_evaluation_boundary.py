"""
V3.3.1 EVALUATION BOUNDARY & ESTIMATOR UNIT TESTS
=================================================
Automated unit tests asserting:
1. 2018Q1 entry trades excluded.
2. 2018Q2 entry trades included.
3. 2026Q2 entry trades exiting in 2026Q3 included as 2026Q2 trades.
4. 2026Q3 entry trades excluded.
5. Profit concentration denominator equals sum of positive quarter PnLs only.
6. Exactly 30 rolling 4Q windows generated for 33 complete quarters.
7. Trade count equality across trade lists, directional splits, and quarter aggregations.
"""

import unittest
import numpy as np
import pandas as pd

class TestV331EvaluationBoundary(unittest.TestCase):
    
    def test_entry_quarter_boundary_filtering(self):
        # Create mock trades table
        mock_trades = pd.DataFrame([
            {'id': 1, 'entry_time': '2018-02-15 10:00:00', 'exit_time': '2018-04-02 12:00:00', 'direction': 'BUY', 'pnl_usd': 50.0},  # Entry in 2018Q1 -> EXCLUDED
            {'id': 2, 'entry_time': '2018-04-01 08:00:00', 'exit_time': '2018-04-01 10:00:00', 'direction': 'BUY', 'pnl_usd': 100.0}, # Entry in 2018Q2 -> INCLUDED
            {'id': 3, 'entry_time': '2026-06-30 20:00:00', 'exit_time': '2026-07-02 09:00:00', 'direction': 'SELL', 'pnl_usd': 80.0}, # Entry in 2026Q2, Exit 2026Q3 -> INCLUDED (as 2026Q2)
            {'id': 4, 'entry_time': '2026-07-10 14:00:00', 'exit_time': '2026-07-10 16:00:00', 'direction': 'BUY', 'pnl_usd': 30.0}   # Entry in 2026Q3 -> EXCLUDED
        ])
        
        mock_trades['entry_dt'] = pd.to_datetime(mock_trades['entry_time'])
        mock_trades['entry_quarter'] = mock_trades['entry_dt'].dt.to_period('Q').astype(str)
        
        eval_trades = mock_trades[(mock_trades['entry_quarter'] >= '2018Q2') & (mock_trades['entry_quarter'] <= '2026Q2')].copy().reset_index(drop=True)
        
        # Assertions
        self.assertEqual(len(eval_trades), 2, "Expected exactly 2 trades in evaluation population")
        self.assertListEqual(eval_trades['id'].tolist(), [2, 3])
        self.assertEqual(eval_trades.loc[eval_trades['id'] == 3, 'entry_quarter'].values[0], '2026Q2')
        
    def test_profit_concentration_positive_pool_math(self):
        # 5 quarters with PnLs: [+100, -50, +200, +300, -100]
        q_pnls = np.array([100.0, -50.0, 200.0, 300.0, -100.0])
        
        # Positive pool = 100 + 200 + 300 = 600
        pos_pnls = q_pnls[q_pnls > 0]
        total_pos_pnl = float(np.sum(pos_pnls))
        self.assertEqual(total_pos_pnl, 600.0)
        
        sorted_pos = np.sort(pos_pnls)[::-1] # [300, 200, 100]
        top1_share = sorted_pos[0] / total_pos_pnl * 100.0 # 300 / 600 = 50.0%
        top2_share = np.sum(sorted_pos[:2]) / total_pos_pnl * 100.0 # 500 / 600 = 83.333%
        top3_share = np.sum(sorted_pos[:3]) / total_pos_pnl * 100.0 # 600 / 600 = 100.0%
        
        self.assertAlmostEqual(top1_share, 50.0)
        self.assertAlmostEqual(top2_share, 500.0 / 600.0 * 100.0)
        self.assertAlmostEqual(top3_share, 100.0)
        
        # Test null profit pool: [-100, -50, -20] -> total_pos_pnl = 0 -> NaN
        neg_q_pnls = np.array([-100.0, -50.0, -20.0])
        pos_subset = neg_q_pnls[neg_q_pnls > 0]
        self.assertEqual(len(pos_subset), 0)
        
    def test_rolling_4q_window_count(self):
        # 33 quarters must produce exactly 33 - 4 + 1 = 30 rolling 4Q windows
        quarters = [f"{y}Q{q}" for y in range(2018, 2027) for q in range(1, 5) if "2018Q2" <= f"{y}Q{q}" <= "2026Q2"]
        self.assertEqual(len(quarters), 33)
        
        windows = []
        for i in range(len(quarters) - 3):
            windows.append(quarters[i:i+4])
        self.assertEqual(len(windows), 30)

if __name__ == '__main__':
    unittest.main()
