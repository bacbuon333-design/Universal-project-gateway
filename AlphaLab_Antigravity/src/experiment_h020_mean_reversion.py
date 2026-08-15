"""
EXPERIMENT H-020: STRUCTURAL MEAN REVERSION & LIQUIDITY SWEEPS
===============================================================
Evaluates symmetrical Mean Reversion (Bollinger Band Stretch + RSI Overbought/Oversold + Mean Reversion Exit) across:
1. Gold H1 (2001 - 2026, 100 Quarters)
2. Gold M30 (2018 - 2026, 34 Quarters)
3. Gold M15 (2022 - 2026, 17 Quarters)
4. Cross-Asset: EURUSD H1, USDJPY H1, GBPUSD H1
"""

import os
import sys
import numpy as np
import pandas as pd
from deep_quant_engine import DeepQuantEngine, print_backtest_report

sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None

def make_mean_reversion_signals(df: pd.DataFrame, bb_period: int = 20, bb_std: float = 2.5, rsi_period: int = 14, sl_atr_mult: float = 1.5):
    h = df['high'].values
    l = df['low'].values
    c = df['close'].values
    o = df['open'].values
    n = len(c)
    
    # ATR 14
    tr = np.maximum(h - l, np.maximum(np.abs(h - np.roll(c, 1)), np.abs(l - np.roll(c, 1))))
    atr14 = pd.Series(tr).rolling(14).mean().values
    
    # Bollinger Bands
    c_s = pd.Series(c)
    mid = c_s.rolling(bb_period).mean().values
    std = c_s.rolling(bb_period).std().values
    upper_bb = mid + (bb_std * std)
    lower_bb = mid - (bb_std * std)
    
    # RSI
    delta = c_s.diff()
    gain = (delta.where(delta > 0, 0)).rolling(rsi_period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(rsi_period).mean()
    rs = gain / (loss + 1e-9)
    rsi = (100 - (100 / (1 + rs))).values
    
    signals = np.zeros(n, dtype=int)
    sl_dists = np.zeros(n)
    tp_dists = np.zeros(n)
    
    warmup = max(bb_period + 5, rsi_period + 5, 60)
    for i in range(warmup, n):
        av = max(atr14[i], 0.1)
        
        # BUY signal: Price dipped below Lower BB, RSI oversold (< 30), and current candle forms bullish rejection (close > open)
        if l[i] <= lower_bb[i] and rsi[i] < 30.0 and c[i] > o[i]:
            signals[i] = 1
            sl_dists[i] = av * sl_atr_mult
            # TP targeted at Mid BB or 1.5x SL distance
            tp_dist_bb = abs(mid[i] - c[i])
            tp_dists[i] = max(tp_dist_bb, av * 1.5)
            
        # SELL signal: Price spiked above Upper BB, RSI overbought (> 70), and current candle forms bearish rejection (close < open)
        elif h[i] >= upper_bb[i] and rsi[i] > 70.0 and c[i] < o[i]:
            signals[i] = -1
            sl_dists[i] = av * sl_atr_mult
            tp_dist_bb = abs(c[i] - mid[i])
            tp_dists[i] = max(tp_dist_bb, av * 1.5)
            
    return signals, sl_dists, tp_dists

def run_experiment():
    print("="*95)
    print("EXPERIMENT H-020: STRUCTURAL MEAN REVERSION & LIQUIDITY SWEEPS")
    print("="*95)
    
    engine_gold_h1 = DeepQuantEngine("GOLD_H1_2001_2026.csv")
    
    bb_stds = [2.0, 2.5, 3.0]
    rsi_lens = [7, 14]
    sl_mults = [1.0, 1.5, 2.0]
    
    results = []
    
    for b_std in bb_stds:
        for r_len in rsi_lens:
            for sl_m in sl_mults:
                sig_fn = lambda d, bs=b_std, rl=r_len, sm=sl_m: make_mean_reversion_signals(d, bb_period=20, bb_std=bs, rsi_period=rl, sl_atr_mult=sm)
                tdf, qdf, summ = engine_gold_h1.run_strategy(sig_fn, spread_pips=25.0, commission_per_lot=7.0)
                
                tdf_oos = tdf[tdf['year'] < 2022] if len(tdf) > 0 else pd.DataFrame()
                oos_trades = len(tdf_oos)
                oos_pnl = tdf_oos['pnl_usd'].sum() if oos_trades > 0 else 0.0
                oos_wins = len(tdf_oos[tdf_oos['pnl_usd'] > 0])
                oos_wr = oos_wins / oos_trades * 100 if oos_trades > 0 else 0.0
                oos_gp = tdf_oos[tdf_oos['pnl_usd'] > 0]['pnl_usd'].sum() if oos_wins > 0 else 0.0
                oos_gl = abs(tdf_oos[tdf_oos['pnl_usd'] < 0]['pnl_usd'].sum()) if (oos_trades - oos_wins) > 0 else 0.0
                oos_pf = oos_gp / oos_gl if oos_gl > 0 else (999.0 if oos_gp > 0 else 0.0)
                
                results.append({
                    'bb_std': b_std,
                    'rsi_len': r_len,
                    'sl_atr': sl_m,
                    'tot_trades': summ['total_trades'],
                    'tot_pnl': summ['total_pnl_usd'],
                    'tot_pf': summ['overall_pf'],
                    'q_pass_pct': summ['robustness_ratio_pct'],
                    'oos_trades': oos_trades,
                    'oos_pnl': oos_pnl,
                    'oos_pf': oos_pf,
                    'oos_wr': oos_wr
                })
                
    res_df = pd.DataFrame(results)
    print("\n--- PARAMETER SWEEP RESULTS (GOLD H1 2001-2026) ---")
    print(res_df.to_string(index=False))
    
    best_row = res_df.sort_values('oos_pf', ascending=False).iloc[0]
    print(f"\nTop Config: BB_Std={best_row['bb_std']}, RSI_Len={best_row['rsi_len']}, SL={best_row['sl_atr']} ATR -> OOS PF={best_row['oos_pf']:.3f}, Total PnL=${best_row['tot_pnl']:+,.2f}")
    
    best_sig_fn = lambda d: make_mean_reversion_signals(d, bb_period=20, bb_std=best_row['bb_std'], rsi_period=int(best_row['rsi_len']), sl_atr_mult=best_row['sl_atr'])
    tdf, qdf, summ = engine_gold_h1.run_strategy(best_sig_fn, spread_pips=25.0, commission_per_lot=7.0)
    print_backtest_report("H-020 Best Config on GOLD H1 (2001-2026)", tdf, qdf, summ)
    
    # Test on M30, M15, and FX
    for tf_file in ["GOLD_M30.csv", "GOLD_M15.csv", "EURUSD_H1.csv", "GBPUSD_H1.csv", "USDJPY_H1.csv"]:
        pip = 0.01 if 'GOLD' in tf_file or 'JPY' in tf_file else 0.0001
        spr = 25.0 if 'GOLD' in tf_file else (18.0 if 'JPY' in tf_file else 15.0)
        eng = DeepQuantEngine(tf_file, pip_size=pip)
        t_df, q_df, s_dict = eng.run_strategy(best_sig_fn, spread_pips=spr, commission_per_lot=7.0)
        print_backtest_report(f"H-020 Transfer Test on {tf_file}", t_df, q_df, s_dict)

if __name__ == '__main__':
    run_experiment()
