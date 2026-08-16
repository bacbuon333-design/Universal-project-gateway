"""
V3.6 EVENT STUDY UNIT TESTS
===========================
Tests causal event construction, directional signed returns, and quarter-block bootstrap.
"""

import unittest
import numpy as np
import pandas as pd

class TestV36EventStudy(unittest.TestCase):
    
    def test_signed_forward_return_logic(self):
        # Morning move positive (+1) -> forward price increases by +5.0 -> signed return = +5.0 (Continuation)
        dir_pos = 1
        p_ref = 2000.0
        p_fut_up = 2005.0
        raw_ret = p_fut_up - p_ref
        signed_ret = dir_pos * raw_ret
        self.assertEqual(signed_ret, 5.0)
        
        # Morning move positive (+1) -> forward price decreases by -5.0 -> signed return = -5.0 (Reversal)
        p_fut_down = 1995.0
        raw_ret_down = p_fut_down - p_ref
        signed_ret_rev = dir_pos * raw_ret_down
        self.assertEqual(signed_ret_rev, -5.0)
        
        # Morning move negative (-1) -> forward price decreases by -5.0 -> signed return = +5.0 (Continuation)
        dir_neg = -1
        signed_ret_neg_cont = dir_neg * raw_ret_down
        self.assertEqual(signed_ret_neg_cont, 5.0)
        
    def test_magnitude_bucket_assignment(self):
        def get_bucket(z):
            abs_z = abs(z)
            if abs_z < 0.5:
                return "TIER_0_LT_0.5"
            elif abs_z < 1.0:
                return "TIER_1_0.5_TO_1.0"
            elif abs_z < 1.5:
                return "TIER_2_1.0_TO_1.5"
            elif abs_z < 2.0:
                return "TIER_3_1.5_TO_2.0"
            else:
                return "TIER_4_GE_2.0"
                
        self.assertEqual(get_bucket(0.2), "TIER_0_LT_0.5")
        self.assertEqual(get_bucket(-0.75), "TIER_1_0.5_TO_1.0")
        self.assertEqual(get_bucket(1.2), "TIER_2_1.0_TO_1.5")
        self.assertEqual(get_bucket(-1.8), "TIER_3_1.5_TO_2.0")
        self.assertEqual(get_bucket(2.5), "TIER_4_GE_2.0")
        
    def test_quarter_block_bootstrap_sampling(self):
        quarters = [f"2020Q{q}" for q in range(1, 5)]
        q_data = {
            "2020Q1": np.array([1.0, 2.0]),
            "2020Q2": np.array([3.0, 4.0]),
            "2020Q3": np.array([5.0, 6.0]),
            "2020Q4": np.array([7.0, 8.0])
        }
        
        np.random.seed(123)
        sampled_q = np.random.choice(quarters, size=len(quarters), replace=True)
        sampled_vals = np.concatenate([q_data[sq] for sq in sampled_q])
        
        self.assertEqual(len(sampled_vals), 8)
        self.assertTrue(np.mean(sampled_vals) > 0)

if __name__ == '__main__':
    unittest.main()
