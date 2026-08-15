"""
EXPERIMENT H-060: ADAPTIVE MACRO-REGIME VOLATILITY SQUEEZE (AUDIT V2)
======================================================================
Implements CAND-001 with explicit component boolean flags:
- use_squeeze: bool (default True)
- use_macro: bool (default True)
- use_er: bool (default True)
- use_macd: bool (default True)
"""

import os
import sys
import numpy as np
import pandas as pd
from deep_quant_engine import DeepQuantEngine, print_backtest_report

sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None

def make_adaptive_squeeze_signals(df: pd.DataFrame, 
                                  bb_period: int = 20, 
                                  bb_mult: float = 2.0, 
                                  kelt_mult: float = 1.2, 
                                  macro_ema_len: int = 200, 
                                  min_er: float = 0.20, 
                                  sl_atr_mult: float = 2.0, 
                                  tp_rr: float = 3.0,
                                  use_squeeze: bool = True,
                                  use_macro: bool = True,
                                  use_er: bool = True,
                                  use_macd: bool = True):
    h = df['high'].values
    l = df['low'].values
    c = df['close'].values
    n = len(c)
    
    # ATR 14 & ATR 20
    tr = np.maximum(h - l, np.maximum(np.abs(h - np.roll(c, 1)), np.abs(l - np.roll(c, 1))))
    atr14 = pd.Series(tr).rolling(14).mean().values
    atr20 = pd.Series(tr).rolling(20).mean().values
    
    c_s = pd.Series(c)
    
    # 1. Bollinger Bands
    mid = c_s.rolling(bb_period).mean().values
    std = c_s.rolling(bb_period).std().values
    bb_upper = mid + (bb_mult * std)
    bb_lower = mid - (bb_mult * std)
    
    # 2. Keltner Channels & Squeeze
    kelt_mid = c_s.ewm(span=bb_period, adjust=False).mean().values
    kelt_upper = kelt_mid + (kelt_mult * atr20)
    kelt_lower = kelt_mid - (kelt_mult * atr20)
    
    is_squeeze = (bb_upper < kelt_upper) & (bb_lower > kelt_lower)
    squeeze_count = pd.Series(is_squeeze.astype(int)).rolling(5).sum().values
    
    # 3. Macro EMA (Trend direction)
    macro_ema = c_s.ewm(span=macro_ema_len, adjust=False).mean().values
    
    # 4. Kaufman Efficiency Ratio (ER) over 10 bars
    net_chg = c_s.diff(10).abs()
    sum_chg = c_s.diff(1).abs().rolling(10).sum()
    er = (net_chg / (sum_chg + 1e-9)).values
    
    # 5. Momentum (MACD Histogram)
    ema12 = c_s.ewm(span=12, adjust=False).mean()
    ema26 = c_s.ewm(span=26, adjust=False).mean()
    macd_line = ema12 - ema26
    signal_line = macd_line.ewm(span=9, adjust=False).mean()
    macd_hist = (macd_line - signal_line).values
    
    signals = np.zeros(n, dtype=int)
    sl_dists = np.zeros(n)
    tp_dists = np.zeros(n)
    
    warmup = max(macro_ema_len + 10, 60)
    for i in range(warmup, n):
        av = max(atr14[i], 0.1)
        
        # Squeeze Flag
        if use_squeeze:
            was_squeezing = (squeeze_count[i-1] >= 4)
            break_up = (c[i] > bb_upper[i])
            break_down = (c[i] < bb_lower[i])
        else:
            was_squeezing = True
            break_up = (c[i] > bb_upper[i]) # still directional excursion trigger
            break_down = (c[i] < bb_lower[i])
            
        # Macro Flag
        if use_macro:
            macro_bull = (c[i] > macro_ema[i]) and (macro_ema[i] > macro_ema[i-5])
            macro_bear = (c[i] < macro_ema[i]) and (macro_ema[i] < macro_ema[i-5])
        else:
            macro_bull = True
            macro_bear = True
            
        # ER Flag
        if use_er:
            er_ok = (er[i] >= min_er)
        else:
            er_ok = True
            
        # MACD Flag
        if use_macd:
            macd_bull = (macd_hist[i] > 0)
            macd_bear = (macd_hist[i] < 0)
        else:
            macd_bull = True
            macd_bear = True
        
        # BUY Trigger
        if was_squeezing and break_up and macd_bull and macro_bull and er_ok:
            signals[i] = 1
            sl_dists[i] = av * sl_atr_mult
            tp_dists[i] = sl_dists[i] * tp_rr
            
        # SELL Trigger
        elif was_squeezing and break_down and macd_bear and macro_bear and er_ok:
            signals[i] = -1
            sl_dists[i] = av * sl_atr_mult
            tp_dists[i] = sl_dists[i] * tp_rr
            
    return signals, sl_dists, tp_dists

def run_experiment():
    print("="*95)
    print("EXPERIMENT H-060: ADAPTIVE MACRO-REGIME VOLATILITY SQUEEZE (CAND-001)")
    print("="*95)
    
    engine_gold_h1 = DeepQuantEngine("GOLD_H1_2001_2026.csv")
    
    sig_fn = lambda d: make_adaptive_squeeze_signals(
        d, bb_period=20, bb_mult=2.0, kelt_mult=1.2, macro_ema_len=200, min_er=0.20, sl_atr_mult=2.0, tp_rr=3.0
    )
    
    tdf, qdf, summ = engine_gold_h1.run_strategy(sig_fn, spread_pips=25.0, commission_per_lot=7.0)
    print_backtest_report("CAND-001 Corrected Baseline (GOLD H1 2001-2026)", tdf, qdf, summ)

if __name__ == '__main__':
    run_experiment()
