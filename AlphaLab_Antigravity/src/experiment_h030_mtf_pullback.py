"""
EXPERIMENT H-030: MULTI-TIMEFRAME TREND CONTINUATION WITH STRUCTURAL PULLBACK
=============================================================================
Evaluates symmetrical Multi-Timeframe Trend Following:
- Macro Trend on H4/D1 (Strict causal alignment)
- Pullback exhaustion & resumption trigger on H1
- Evaluated on Gold H1 (2001-2026), M30, M15, EURUSD, GBPUSD, USDJPY
"""

import os
import sys
import numpy as np
import pandas as pd
from deep_quant_engine import DeepQuantEngine, print_backtest_report

sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None

def make_mtf_pullback_signals(df: pd.DataFrame, macro_ema_len: int = 200, pullback_lb: int = 10, sl_atr_mult: float = 1.5, tp_rr: float = 2.0):
    h = df['high'].values
    l = df['low'].values
    c = df['close'].values
    o = df['open'].values
    n = len(c)
    
    # ATR 14
    tr = np.maximum(h - l, np.maximum(np.abs(h - np.roll(c, 1)), np.abs(l - np.roll(c, 1))))
    atr14 = pd.Series(tr).rolling(14).mean().values
    
    # Macro Trend EMA (e.g. 200 bars on H1 corresponds to ~33 bars on H4)
    macro_ema = pd.Series(c).ewm(span=macro_ema_len, adjust=False).mean().values
    # Fast EMA for pullback reference
    fast_ema = pd.Series(c).ewm(span=21, adjust=False).mean().values
    
    # Pullback Low/High over prior N bars (shifted by 1 for strict causality)
    pb_lo = pd.Series(l).shift(1).rolling(pullback_lb).min().values
    pb_hi = pd.Series(h).shift(1).rolling(pullback_lb).max().values
    
    signals = np.zeros(n, dtype=int)
    sl_dists = np.zeros(n)
    tp_dists = np.zeros(n)
    
    warmup = max(macro_ema_len + 10, pullback_lb + 10, 60)
    for i in range(warmup, n):
        av = max(atr14[i], 0.1)
        
        # Macro Bullish: Close > Macro EMA and Macro EMA is sloping upward
        macro_bull = (c[i] > macro_ema[i]) and (macro_ema[i] > macro_ema[i-5])
        # Macro Bearish: Close < Macro EMA and Macro EMA is sloping downward
        macro_bear = (c[i] < macro_ema[i]) and (macro_ema[i] < macro_ema[i-5])
        
        # BUY Trigger: Macro Bull + Price pulled back below Fast EMA within last N bars, but current bar closes back ABOVE Fast EMA with bullish candle
        if macro_bull:
            pulled_back = (l[i-1] <= fast_ema[i-1] or l[i-2] <= fast_ema[i-2])
            resumed = (c[i] > fast_ema[i]) and (c[i] > o[i])
            if pulled_back and resumed:
                signals[i] = 1
                sl_dists[i] = av * sl_atr_mult
                tp_dists[i] = sl_dists[i] * tp_rr
                
        # SELL Trigger: Macro Bear + Price pulled back above Fast EMA within last N bars, but current bar closes back BELOW Fast EMA with bearish candle
        elif macro_bear:
            pulled_back = (h[i-1] >= fast_ema[i-1] or h[i-2] >= fast_ema[i-2])
            resumed = (c[i] < fast_ema[i]) and (c[i] < o[i])
            if pulled_back and resumed:
                signals[i] = -1
                sl_dists[i] = av * sl_atr_mult
                tp_dists[i] = sl_dists[i] * tp_rr
                
    return signals, sl_dists, tp_dists

def run_experiment():
    print("="*95)
    print("EXPERIMENT H-030: MULTI-TIMEFRAME TREND CONTINUATION WITH PULLBACK")
    print("="*95)
    
    engine_gold_h1 = DeepQuantEngine("GOLD_H1_2001_2026.csv")
    
    macro_lens = [100, 200, 400]
    sl_mults = [1.0, 1.5, 2.0]
    rr_ratios = [1.5, 2.0, 3.0]
    
    results = []
    
    for m_len in macro_lens:
        for sl_m in sl_mults:
            for rr in rr_ratios:
                sig_fn = lambda d, ml=m_len, sm=sl_m, r=rr: make_mtf_pullback_signals(d, macro_ema_len=ml, pullback_lb=10, sl_atr_mult=sm, tp_rr=r)
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
                    'macro_len': m_len,
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
    print(f"\nTop Config: Macro_EMA={best_row['macro_len']}, SL={best_row['sl_atr']} ATR, RR={best_row['rr_ratio']} -> OOS PF={best_row['oos_pf']:.3f}, Total PnL=${best_row['tot_pnl']:+,.2f}")
    
    best_sig_fn = lambda d: make_mtf_pullback_signals(d, macro_ema_len=int(best_row['macro_len']), pullback_lb=10, sl_atr_mult=best_row['sl_atr'], tp_rr=best_row['rr_ratio'])
    tdf, qdf, summ = engine_gold_h1.run_strategy(best_sig_fn, spread_pips=25.0, commission_per_lot=7.0)
    print_backtest_report("H-030 Best Config on GOLD H1 (2001-2026)", tdf, qdf, summ)
    
    # Test on M30, M15, and FX
    for tf_file in ["GOLD_M30.csv", "GOLD_M15.csv", "EURUSD_H1.csv", "GBPUSD_H1.csv", "USDJPY_H1.csv"]:
        pip = 0.01 if 'GOLD' in tf_file or 'JPY' in tf_file else 0.0001
        spr = 25.0 if 'GOLD' in tf_file else (18.0 if 'JPY' in tf_file else 15.0)
        eng = DeepQuantEngine(tf_file, pip_size=pip)
        t_df, q_df, s_dict = eng.run_strategy(best_sig_fn, spread_pips=spr, commission_per_lot=7.0)
        print_backtest_report(f"H-030 Transfer Test on {tf_file}", t_df, q_df, s_dict)

if __name__ == '__main__':
    run_experiment()
