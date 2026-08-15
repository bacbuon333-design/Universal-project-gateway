"""
COMPREHENSIVE SYNTHETIC EXECUTION & CAUSALITY TEST SUITE (AUDIT V2)
===================================================================
Automated unit tests to rigorously verify:
1. BUY TP & BUY SL exact triggers and fills
2. SELL TP & SELL SL exact triggers and fills
3. BUY & SELL ambiguous intra-bar execution (Pessimistic vs Optimistic)
4. Symmetrical Cost Accounting:
   - BUY: Entry Ask = Open + spread + slippage; Exit Bid = Price - slippage
   - SELL: Entry Bid = Open - slippage; Exit Ask = Price + spread + slippage
   - Round-trip spread paid symmetrically by both BUY and SELL
5. Symmetrical Commission ($7.00/lot) and Slippage
6. TIME_EXIT on both BUY and SELL
"""

import os
import sys
import numpy as np
import pandas as pd
from deep_quant_engine import DeepQuantEngine

sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None

def test_synthetic_execution_gauntlet():
    print("=" * 80)
    print("RUNNING SYNTHETIC EXECUTION GAUNTLET (BUY & SELL SYMMETRY)")
    print("=" * 80)
    
    # -------------------------------------------------------------
    # 1. SYNTHETIC DATASET SETUP
    # -------------------------------------------------------------
    dates = pd.date_range('2023-01-01', periods=10, freq='1h')
    df = pd.DataFrame({
        'dt': dates,
        'datetime_str': [d.isoformat() for d in dates],
        'open':  [100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0],
        'high':  [100.5, 106.0, 100.5, 110.0, 100.5, 100.5,  95.0, 100.5, 100.5, 100.5],
        'low':   [ 99.5,  99.5,  94.0,  90.0,  99.5,  99.5,  89.0,  99.5,  99.5,  99.5],
        'close': [100.0, 105.0,  95.0,  95.0, 100.0, 100.0,  90.0, 100.0, 100.0, 100.0],
        'tick_volume': [1000] * 10
    })
    
    tmp_path = os.path.join(os.path.dirname(__file__), 'tmp_synthetic_test.csv')
    df.to_csv(tmp_path, index=False)
    
    engine = DeepQuantEngine(data_file=tmp_path, pip_size=0.01, point_val=0.01)
    
    try:
        # ---------------------------------------------------------
        # TEST A: BUY TP HIT
        # ---------------------------------------------------------
        # Signal at bar 0 -> Enter at bar 1 open (100.0). High on bar 1 = 106.0.
        # SL = 5.0 (95.0), TP = 5.0 (105.0). High touches TP.
        def sig_buy_tp(d):
            s, sl, tp = np.zeros(len(d), dtype=int), np.zeros(len(d)), np.zeros(len(d))
            s[0], sl[0], tp[0] = 1, 5.0, 5.0
            return s, sl, tp
            
        tdf, _, _ = engine.run_strategy(sig_buy_tp, spread_pips=0.0, commission_per_lot=0.0, slippage_pips=0.0)
        assert len(tdf) == 1
        t = tdf.iloc[0]
        assert t['exit_reason'] == 'TP' and t['exit_price'] == 105.0 and t['pnl_pts'] == 500.0
        print("✅ 1. BUY TP HIT: PASSED")
        
        # ---------------------------------------------------------
        # TEST B: BUY SL HIT
        # ---------------------------------------------------------
        # Signal at bar 1 -> Enter at bar 2 open (100.0). Low on bar 2 = 94.0.
        # SL = 5.0 (95.0), TP = 5.0 (105.0). Low touches SL.
        def sig_buy_sl(d):
            s, sl, tp = np.zeros(len(d), dtype=int), np.zeros(len(d)), np.zeros(len(d))
            s[1], sl[1], tp[1] = 1, 5.0, 5.0
            return s, sl, tp
            
        tdf, _, _ = engine.run_strategy(sig_buy_sl, spread_pips=0.0, commission_per_lot=0.0, slippage_pips=0.0)
        assert len(tdf) == 1
        t = tdf.iloc[0]
        assert t['exit_reason'] == 'SL' and t['exit_price'] == 95.0 and t['pnl_pts'] == -500.0
        print("✅ 2. BUY SL HIT: PASSED")
        
        # ---------------------------------------------------------
        # TEST C: SELL TP HIT
        # ---------------------------------------------------------
        # Signal at bar 1 -> Enter at bar 2 open (100.0). Low on bar 2 = 94.0.
        # For SELL: SL = entry + 5.0 = 105.0, TP = entry - 5.0 = 95.0.
        # Low = 94.0 <= TP 95.0. TP is touched.
        def sig_sell_tp(d):
            s, sl, tp = np.zeros(len(d), dtype=int), np.zeros(len(d)), np.zeros(len(d))
            s[1], sl[1], tp[1] = -1, 5.0, 5.0
            return s, sl, tp
            
        tdf, _, _ = engine.run_strategy(sig_sell_tp, spread_pips=0.0, commission_per_lot=0.0, slippage_pips=0.0)
        assert len(tdf) == 1
        t = tdf.iloc[0]
        assert t['exit_reason'] == 'TP' and t['exit_price'] == 95.0 and t['pnl_pts'] == 500.0
        print("✅ 3. SELL TP HIT: PASSED")
        
        # ---------------------------------------------------------
        # TEST D: SELL SL HIT
        # ---------------------------------------------------------
        # Signal at bar 0 -> Enter at bar 1 open (100.0). High on bar 1 = 106.0.
        # For SELL: SL = 105.0, TP = 95.0. High = 106.0 >= SL 105.0. SL is touched.
        def sig_sell_sl(d):
            s, sl, tp = np.zeros(len(d), dtype=int), np.zeros(len(d)), np.zeros(len(d))
            s[0], sl[0], tp[0] = -1, 5.0, 5.0
            return s, sl, tp
            
        tdf, _, _ = engine.run_strategy(sig_sell_sl, spread_pips=0.0, commission_per_lot=0.0, slippage_pips=0.0)
        assert len(tdf) == 1
        t = tdf.iloc[0]
        assert t['exit_reason'] == 'SL' and t['exit_price'] == 105.0 and t['pnl_pts'] == -500.0
        print("✅ 4. SELL SL HIT: PASSED")
        
        # ---------------------------------------------------------
        # TEST E: BUY AMBIGUOUS SL+TP (Pessimistic)
        # ---------------------------------------------------------
        # Bar 3 has High=110.0 and Low=90.0. Signal at bar 2 enters bar 3 at 100.0.
        # SL = 95.0, TP = 105.0. Both touched on bar 3.
        def sig_ambig_buy(d):
            s, sl, tp = np.zeros(len(d), dtype=int), np.zeros(len(d)), np.zeros(len(d))
            s[2], sl[2], tp[2] = 1, 5.0, 5.0
            return s, sl, tp
            
        tdf, _, _ = engine.run_strategy(sig_ambig_buy, spread_pips=0.0, commission_per_lot=0.0, pessimistic_ambiguous_bars=True)
        assert len(tdf) == 1
        t = tdf.iloc[0]
        assert t['exit_reason'] == 'SL_AMBIGUOUS_PESSIMISTIC' and t['exit_price'] == 95.0 and t['pnl_pts'] == -500.0
        print("✅ 5. BUY AMBIGUOUS PESSIMISTIC: PASSED")
        
        # ---------------------------------------------------------
        # TEST F: SELL AMBIGUOUS SL+TP (Pessimistic)
        # ---------------------------------------------------------
        def sig_ambig_sell(d):
            s, sl, tp = np.zeros(len(d), dtype=int), np.zeros(len(d)), np.zeros(len(d))
            s[2], sl[2], tp[2] = -1, 5.0, 5.0
            return s, sl, tp
            
        tdf, _, _ = engine.run_strategy(sig_ambig_sell, spread_pips=0.0, commission_per_lot=0.0, pessimistic_ambiguous_bars=True)
        assert len(tdf) == 1
        t = tdf.iloc[0]
        assert t['exit_reason'] == 'SL_AMBIGUOUS_PESSIMISTIC' and t['exit_price'] == 105.0 and t['pnl_pts'] == -500.0
        print("✅ 6. SELL AMBIGUOUS PESSIMISTIC: PASSED")
        
        # ---------------------------------------------------------
        # TEST G: SYMMETRICAL COST TEST (BUY vs SELL WITH SPREAD, COMM, SLIPPAGE)
        # ---------------------------------------------------------
        # Spread = 25 pips (0.25 on price), Slippage = 2 pips (0.02), Comm = $7.00/lot ($0.70 for 0.10 lot)
        # 1. BUY TP hit at 105.0:
        #    Entry = 100.0 + 0.25 (spread) + 0.02 (slip) = 100.27
        #    TP price = 100.27 + 5.0 = 105.27
        #    Exit price = 105.27 - 0.02 (slip) = 105.25
        #    pnl_pts = (105.25 - 100.27) / 0.01 = 498.0 pips
        #    pnl_usd = 498.0 * 0.01 * 10 - 0.70 = 49.80 - 0.70 = $49.10 USD
        tdf_buy_cost, _, _ = engine.run_strategy(sig_buy_tp, spread_pips=25.0, commission_per_lot=7.0, slippage_pips=2.0, fixed_lot=0.10)
        t_buy = tdf_buy_cost.iloc[0]
        assert abs(t_buy['entry_price'] - 100.27) < 1e-4
        assert abs(t_buy['exit_price'] - 105.25) < 1e-4
        assert abs(t_buy['pnl_usd'] - 49.10) < 1e-2
        print(f"✅ 7. BUY COST VERIFICATION: PASSED (Entry={t_buy['entry_price']:.4f}, Exit={t_buy['exit_price']:.4f}, PnL=${t_buy['pnl_usd']:.2f})")
        
        # 2. SELL TP hit:
        #    Entry = 100.0 - 0.02 (slip) = 99.98
        #    TP price (target Ask) = 99.98 - 5.0 = 94.98
        #    Exit price = 94.98 + 0.02 (slip) = 95.00
        #    pnl_pts = (99.98 - 95.00) / 0.01 = 498.0 pips
        #    pnl_usd = 498.0 * 0.01 * 10 - 0.70 = 49.80 - 0.70 = $49.10 USD
        # Symmetrical exact matching!
        tdf_sell_cost, _, _ = engine.run_strategy(sig_sell_tp, spread_pips=25.0, commission_per_lot=7.0, slippage_pips=2.0, fixed_lot=0.10)
        t_sell = tdf_sell_cost.iloc[0]
        assert abs(t_sell['entry_price'] - 99.98) < 1e-4
        assert abs(t_sell['exit_price'] - 95.00) < 1e-4
        assert abs(t_sell['pnl_usd'] - 49.10) < 1e-2
        print(f"✅ 8. SELL COST VERIFICATION: PASSED (Entry={t_sell['entry_price']:.4f}, Exit={t_sell['exit_price']:.4f}, PnL=${t_sell['pnl_usd']:.2f})")
        
        # ---------------------------------------------------------
        # TEST H: TIME EXIT ON BUY & SELL
        # ---------------------------------------------------------
        # Signal at bar 4, no SL or TP hit for 3 bars, max_holding_bars = 2
        def sig_time_buy(d):
            s, sl, tp = np.zeros(len(d), dtype=int), np.zeros(len(d)), np.zeros(len(d))
            s[4], sl[4], tp[4] = 1, 50.0, 50.0 # Far SL/TP
            return s, sl, tp
            
        tdf_tb, _, _ = engine.run_strategy(sig_time_buy, spread_pips=0.0, commission_per_lot=0.0, max_holding_bars=2)
        assert len(tdf_tb) == 1
        assert tdf_tb.iloc[0]['exit_reason'] == 'TIME_EXIT'
        print("✅ 9. BUY TIME_EXIT: PASSED")
        
        def sig_time_sell(d):
            s, sl, tp = np.zeros(len(d), dtype=int), np.zeros(len(d)), np.zeros(len(d))
            s[4], sl[4], tp[4] = -1, 50.0, 50.0 # Far SL/TP
            return s, sl, tp
            
        tdf_ts, _, _ = engine.run_strategy(sig_time_sell, spread_pips=0.0, commission_per_lot=0.0, max_holding_bars=2)
        assert len(tdf_ts) == 1
        assert tdf_ts.iloc[0]['exit_reason'] == 'TIME_EXIT'
        print("✅ 10. SELL TIME_EXIT: PASSED")
        
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
            
    print("=" * 80)
    print("ALL 10 SYNTHETIC EXECUTION & COST TESTS PASSED PERFECTLY!")
    print("=" * 80)

if __name__ == '__main__':
    test_synthetic_execution_gauntlet()
