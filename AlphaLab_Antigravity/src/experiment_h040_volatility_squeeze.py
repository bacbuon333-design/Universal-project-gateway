"""
EXPERIMENT H-040: VOLATILITY COMPRESSION & DIRECTIONAL EXPANSION (SQUEEZE)
==========================================================================
Evaluates symmetrical Volatility Squeeze Breakout:
- Compression: Bollinger Bands inside Keltner Channel for >= min_squeeze_bars
- Expansion Trigger: Bollinger Bands expand outside Keltner Channel + Directional breakout
- Evaluated on Gold H1 (2001-2026), M30, M15, EURUSD, GBPUSD, USDJPY
"""

import os
import sys
import numpy as np
import pandas as pd
from deep_quant_engine import DeepQuantEngine, print_backtest_report

sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None

def make_squeeze_breakout_signals(df: pd.DataFrame, bb_period: int = 20, bb_mult: float = 2.0, kelt_mult: float = 1.5, min_squeeze_bars: int = 5, sl_atr_mult: float = 1.5, tp_rr: float = 2.5):
    h = df['high'].values
    l = df['low'].values
    c = df['close'].values
    o = df['open'].values
    n = len(c)
    
    # ATR 14 & ATR 20
    tr = np.maximum(h - l, np.maximum(np.abs(h - np.roll(c, 1)), np.abs(l - np.roll(c, 1))))
    atr14 = pd.Series(tr).rolling(14).mean().values
    atr20 = pd.Series(tr).rolling(20).mean().values
    
    # Bollinger Bands
    c_s = pd.Series(c)
    mid = c_s.rolling(bb_period).mean().values
    std = c_s.rolling(bb_period).std().values
    bb_upper = mid + (bb_mult * std)
    bb_lower = mid - (bb_mult * std)
    
    # Keltner Channels (using EMA20 + kelt_mult * ATR20)
    kelt_mid = c_s.ewm(span=bb_period, adjust=False).mean().values
    kelt_upper = kelt_mid + (kelt_mult * atr20)
    kelt_lower = kelt_mid - (kelt_mult * atr20)
    
    # Squeeze condition: BB is inside Keltner
    is_squeeze = (bb_upper < kelt_upper) & (bb_lower > kelt_lower)
    # Rolling sum of squeeze bars
    squeeze_count = pd.Series(is_squeeze.astype(int)).rolling(min_squeeze_bars).sum().values
    
    # Momentum (MACD Histogram)
    ema12 = c_s.ewm(span=12, adjust=False).mean()
    ema26 = c_s.ewm(span=26, adjust=False).mean()
    macd_line = ema12 - ema26
    signal_line = macd_line.ewm(span=9, adjust=False).mean()
    macd_hist = (macd_line - signal_line).values
    
    signals = np.zeros(n, dtype=int)
    sl_dists = np.zeros(n)
    tp_dists = np.zeros(n)
    
    warmup = max(bb_period + 10, 60)
    for i in range(warmup, n):
        av = max(atr14[i], 0.1)
        
        # Recent squeeze existed in previous 5 bars, and current bar breaks OUT of squeeze
        was_squeezing = (squeeze_count[i-1] >= min_squeeze_bars - 1)
        
        # Bullish Breakout: Was squeezing, now BB expands, Close > BB Upper and MACD Hist > 0
        if was_squeezing and c[i] > bb_upper[i] and macd_hist[i] > 0:
            signals[i] = 1
            sl_dists[i] = av * sl_atr_mult
            tp_dists[i] = sl_dists[i] * tp_rr
            
        # Bearish Breakout: Was squeezing, now BB expands, Close < BB Lower and MACD Hist < 0
        elif was_squeezing and c[i] < bb_lower[i] and macd_hist[i] < 0:
            signals[i] = -1
            sl_dists[i] = av * sl_atr_mult
            tp_dists[i] = sl_dists[i] * tp_rr
            
    return signals, sl_dists, tp_dists

def run_experiment():
    print("="*95)
    print("EXPERIMENT H-040: VOLATILITY SQUEEZE BREAKOUT")
    print("="*95)
    
    engine_gold_h1 = DeepQuantEngine("GOLD_H1_2001_2026.csv")
    
    kelt_mults = [1.2, 1.5, 1.8]
    sl_mults = [1.0, 1.5, 2.0]
    rr_ratios = [1.5, 2.0, 3.0]
    
    results = []
    
    for km in kelt_mults:
        for sl_m in sl_mults:
            for rr in rr_ratios:
                sig_fn = lambda d, k=km, sm=sl_m, r=rr: make_squeeze_breakout_signals(d, bb_period=20, bb_mult=2.0, kelt_mult=k, min_squeeze_bars=5, sl_atr_mult=sm, tp_rr=r)
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
                    'kelt_mult': km,
                    'sl_atr': sl_m,
                    'rr_ratio': rr,
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
    print(f"\nTop Config: Kelt_Mult={best_row['kelt_mult']}, SL={best_row['sl_atr']} ATR, RR={best_row['rr_ratio']} -> OOS PF={best_row['oos_pf']:.3f}, Total PnL=${best_row['tot_pnl']:+,.2f}")
    
    best_sig_fn = lambda d: make_squeeze_breakout_signals(d, bb_period=20, bb_mult=2.0, kelt_mult=best_row['kelt_mult'], min_squeeze_bars=5, sl_atr_mult=best_row['sl_atr'], tp_rr=best_row['rr_ratio'])
    tdf, qdf, summ = engine_gold_h1.run_strategy(best_sig_fn, spread_pips=25.0, commission_per_lot=7.0)
    print_backtest_report("H-040 Best Config on GOLD H1 (2001-2026)", tdf, qdf, summ)
    
    # Test on M30, M15, and FX
    for tf_file in ["GOLD_M30.csv", "GOLD_M15.csv", "EURUSD_H1.csv", "GBPUSD_H1.csv", "USDJPY_H1.csv"]:
        pip = 0.01 if 'GOLD' in tf_file or 'JPY' in tf_file else 0.0001
        spr = 25.0 if 'GOLD' in tf_file else (18.0 if 'JPY' in tf_file else 15.0)
        eng = DeepQuantEngine(tf_file, pip_size=pip)
        t_df, q_df, s_dict = eng.run_strategy(best_sig_fn, spread_pips=spr, commission_per_lot=7.0)
        print_backtest_report(f"H-040 Transfer Test on {tf_file}", t_df, q_df, s_dict)

if __name__ == '__main__':
    run_experiment()
