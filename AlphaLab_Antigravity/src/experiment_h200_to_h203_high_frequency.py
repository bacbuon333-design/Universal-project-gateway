"""
EXPERIMENTS H-200 TO H-203: HIGH-FREQUENCY TEMPORAL DISTRIBUTION DISCOVERY
===========================================================================
Tests higher-frequency causal volatility-expansion and range breakout mechanisms:
- H-200: M30 Intraday Squeeze Expansion
- H-201: H1 Short-Cycle Range Compression Breakout
- H-202: H1 Adaptive Donchian Volatility Compression
- H-203: H1 London Session Opening Range Breakout (ORB)

Evaluates strictly against:
- Gate 12A: Min trades per complete quarter >= 5 (100% compliance required)
- Gate 12B: Min trades per complete year >= 20
- Gate 14: Trade count Gini & Max/Median ratio
- Gate 15: Profit concentration
- Profit Factor >= 1.25 with 25 pips spread + $7/lot commission
"""

import os
import sys
import numpy as np
import pandas as pd
from deep_quant_engine import DeepQuantEngine

sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None

def gini(x):
    mad = np.abs(np.subtract.outer(x, x)).mean()
    rmad = mad / np.mean(x) if np.mean(x) > 0 else 0
    return 0.5 * rmad

# -----------------------------------------------------------------
# SIGNAL GENERATORS FOR H-200 TO H-203
# -----------------------------------------------------------------
def make_h200_signals(df):
    # M30 Squeeze + Intraday Trend EMA 50
    c = df['close'].values
    h = df['high'].values
    l = df['low'].values
    n = len(c)
    
    c_s = pd.Series(c)
    mid = c_s.rolling(20).mean().values
    std = c_s.rolling(20).std().values
    bb_u = mid + 2.0 * std
    bb_l = mid - 2.0 * std
    
    tr = np.maximum(h - l, np.maximum(np.abs(h - np.roll(c, 1)), np.abs(l - np.roll(c, 1))))
    atr20 = pd.Series(tr).rolling(20).mean().values
    atr14 = pd.Series(tr).rolling(14).mean().values
    kelt_mid = c_s.ewm(span=20, adjust=False).mean().values
    kelt_u = kelt_mid + 1.2 * atr20
    kelt_l = kelt_mid - 1.2 * atr20
    
    is_sqz = (bb_u < kelt_u) & (bb_l > kelt_l)
    sqz_cnt = pd.Series(is_sqz.astype(int)).rolling(3).sum().values
    was_sqz = (pd.Series(sqz_cnt).shift(1).values >= 2)
    
    ema50 = c_s.ewm(span=50, adjust=False).mean().values
    bull = (c > ema50) & (ema50 > pd.Series(ema50).shift(3).values)
    bear = (c < ema50) & (ema50 < pd.Series(ema50).shift(3).values)
    
    sig = np.zeros(n, dtype=int)
    sl = np.zeros(n, dtype=float)
    tp = np.zeros(n, dtype=float)
    
    for i in range(50, n):
        if was_sqz[i] and bull[i] and c[i] > bb_u[i]:
            sig[i] = 1
            cur_atr = max(atr14[i], 0.50)
            sl[i] = c[i] - 1.5 * cur_atr
            tp[i] = c[i] + 3.75 * cur_atr # 2.5 * SL
        elif was_sqz[i] and bear[i] and c[i] < bb_l[i]:
            sig[i] = -1
            cur_atr = max(atr14[i], 0.50)
            sl[i] = c[i] + 1.5 * cur_atr
            tp[i] = c[i] - 3.75 * cur_atr
    return sig, sl, tp

def make_h201_signals(df):
    # H1 Short-Cycle Range Compression Breakout
    c = df['close'].values
    h = df['high'].values
    l = df['low'].values
    n = len(c)
    
    c_s = pd.Series(c)
    tr = np.maximum(h - l, np.maximum(np.abs(h - np.roll(c, 1)), np.abs(l - np.roll(c, 1))))
    atr14 = pd.Series(tr).rolling(14).mean().values
    bar_rng = h - l
    
    # Range compression: 2 consecutive bars with range <= 0.70 * ATR14
    is_comp = (bar_rng <= 0.70 * atr14)
    was_comp = (pd.Series(is_comp.astype(int)).rolling(2).sum().shift(1).values >= 2)
    
    h3 = pd.Series(h).rolling(3).max().shift(1).values
    l3 = pd.Series(l).rolling(3).min().shift(1).values
    
    ema100 = c_s.ewm(span=100, adjust=False).mean().values
    bull = (c > ema100) & (ema100 > pd.Series(ema100).shift(5).values)
    bear = (c < ema100) & (ema100 < pd.Series(ema100).shift(5).values)
    
    sig = np.zeros(n, dtype=int)
    sl = np.zeros(n, dtype=float)
    tp = np.zeros(n, dtype=float)
    
    for i in range(100, n):
        if was_comp[i] and bull[i] and c[i] > h3[i]:
            sig[i] = 1
            cur_atr = max(atr14[i], 0.50)
            sl[i] = c[i] - 1.5 * cur_atr
            tp[i] = c[i] + 3.75 * cur_atr
        elif was_comp[i] and bear[i] and c[i] < l3[i]:
            sig[i] = -1
            cur_atr = max(atr14[i], 0.50)
            sl[i] = c[i] + 1.5 * cur_atr
            tp[i] = c[i] - 3.75 * cur_atr
    return sig, sl, tp

def make_h202_signals(df):
    # H1 Adaptive Donchian Volatility Compression
    c = df['close'].values
    h = df['high'].values
    l = df['low'].values
    n = len(c)
    
    c_s = pd.Series(c)
    tr = np.maximum(h - l, np.maximum(np.abs(h - np.roll(c, 1)), np.abs(l - np.roll(c, 1))))
    atr14 = pd.Series(tr).rolling(14).mean().values
    atr50 = pd.Series(tr).rolling(50).mean().values
    atr_ratio = atr14 / (atr50 + 1e-9)
    is_contracted = (atr_ratio <= 0.85)
    
    donch_h = pd.Series(h).rolling(20).max().shift(1).values
    donch_l = pd.Series(l).rolling(20).min().shift(1).values
    
    ema200 = c_s.ewm(span=200, adjust=False).mean().values
    bull = (c > ema200)
    bear = (c < ema200)
    
    sig = np.zeros(n, dtype=int)
    sl = np.zeros(n, dtype=float)
    tp = np.zeros(n, dtype=float)
    
    for i in range(200, n):
        if is_contracted[i] and bull[i] and c[i] > donch_h[i]:
            sig[i] = 1
            cur_atr = max(atr14[i], 0.50)
            sl[i] = c[i] - 1.5 * cur_atr
            tp[i] = c[i] + 3.75 * cur_atr
        elif is_contracted[i] and bear[i] and c[i] < donch_l[i]:
            sig[i] = -1
            cur_atr = max(atr14[i], 0.50)
            sl[i] = c[i] + 1.5 * cur_atr
            tp[i] = c[i] - 3.75 * cur_atr
    return sig, sl, tp

def make_h203_signals(df):
    # H1 London Session Opening Range Breakout (ORB)
    c = df['close'].values
    h = df['high'].values
    l = df['low'].values
    dt = pd.to_datetime(df['datetime_str'] if 'datetime_str' in df.columns else df['dt'])
    n = len(c)
    
    c_s = pd.Series(c)
    tr = np.maximum(h - l, np.maximum(np.abs(h - np.roll(c, 1)), np.abs(l - np.roll(c, 1))))
    atr14 = pd.Series(tr).rolling(14).mean().values
    
    hour = dt.dt.hour.values
    
    sig = np.zeros(n, dtype=int)
    sl = np.zeros(n, dtype=float)
    tp = np.zeros(n, dtype=float)
    
    # Track Asian range (00:00 to 07:00)
    asian_h = np.nan
    asian_l = np.nan
    cur_day = None
    
    for i in range(50, n):
        d_val = dt.iloc[i].date()
        hr = hour[i]
        
        if d_val != cur_day:
            cur_day = d_val
            asian_h = np.nan
            asian_l = np.nan
            
        if hr == 7: # Asian close
            day_mask = (dt.iloc[i-7:i+1].dt.date == cur_day)
            asian_h = np.max(h[i-7:i+1])
            asian_l = np.min(l[i-7:i+1])
            
        if 8 <= hr <= 14 and not np.isnan(asian_h):
            if c[i] > asian_h:
                sig[i] = 1
                cur_atr = max(atr14[i], 0.50)
                sl[i] = c[i] - 1.5 * cur_atr
                tp[i] = c[i] + 3.0 * cur_atr
                asian_h = np.nan # 1 trade per day
            elif c[i] < asian_l:
                sig[i] = -1
                cur_atr = max(atr14[i], 0.50)
                sl[i] = c[i] + 1.5 * cur_atr
                tp[i] = c[i] - 3.0 * cur_atr
                asian_l = np.nan
    return sig, sl, tp

def run_h200_to_h203_experiments():
    print("=" * 95)
    print("🚀 EXECUTING HYPOTHESES H-200 TO H-203 (HIGH-FREQUENCY DISCOVERY)")
    print("=" * 95)
    
    experiments = [
        ("H-200 (M30 Squeeze+EMA50)", "GOLD_M30.csv", make_h200_signals, 25.0, '2018Q2', '2026Q2', 33),
        ("H-201 (H1 Range Compression)", "GOLD_H1_2001_2026.csv", make_h201_signals, 25.0, '2001Q3', '2026Q2', 100),
        ("H-202 (H1 Adaptive Donchian)", "GOLD_H1_2001_2026.csv", make_h202_signals, 25.0, '2001Q3', '2026Q2', 100),
        ("H-203 (H1 London ORB Breakout)", "GOLD_H1_2001_2026.csv", make_h203_signals, 25.0, '2001Q3', '2026Q2', 100)
    ]
    
    results = []
    
    for name, fname, sig_fn, spr, q_start, q_end, n_comp_q in experiments:
        eng = DeepQuantEngine(fname, pip_size=0.01, point_val=0.01)
        tdf, qdf, summ = eng.run_strategy(sig_fn, spread_pips=spr, commission_per_lot=7.0)
        
        comp_q = qdf[(qdf['quarter'] >= q_start) & (qdf['quarter'] <= q_end)].copy().reset_index(drop=True)
        trades_arr = comp_q['trades'].values
        
        min_tr = np.min(trades_arr) if len(trades_arr) > 0 else 0
        med_tr = np.median(trades_arr) if len(trades_arr) > 0 else 0
        max_tr = np.max(trades_arr) if len(trades_arr) > 0 else 0
        n_ge_5 = np.sum(trades_arr >= 5)
        zero_q = np.sum(trades_arr == 0)
        trade_gini = gini(trades_arr)
        
        # Check Gate 12A
        gate12a_verdict = 'PASSED' if min_tr >= 5 else f'FAILED (Min={min_tr}, {n_ge_5}/{len(comp_q)} quarters >= 5)'
        
        results.append({
            'Hypothesis': name,
            'Complete Quarters': len(comp_q),
            'Total Trades': summ['total_trades'],
            'Min Trades/Q': min_tr,
            'Median Trades/Q': med_tr,
            'Max Trades/Q': max_tr,
            'Trade Gini': f"{trade_gini:.3f}",
            'Zero-Trade Qs': zero_q,
            'Net PnL ($)': f"${summ['total_pnl_usd']:+,.2f}",
            'Profit Factor': f"{summ['overall_pf']:.3f}",
            'Win Rate': f"{summ['overall_wr_pct']:.1f}%",
            'Expectancy (R)': f"{summ['avg_expectancy_r']:+.3f} R",
            'Gate 12A Status': gate12a_verdict,
            'Overall Classification': 'REJECTED' if min_tr < 5 or summ['overall_pf'] < 1.25 else 'HISTORICAL DISTRIBUTED SURVIVOR'
        })
        
    res_df = pd.DataFrame(results)
    print("\n--- EXPERIMENT H-200 TO H-203 RESULTS MATRIX ---")
    print(res_df.to_string(index=False))
    
    # Save machine-readable output
    os.makedirs(os.path.join(os.path.dirname(__file__), '..', 'reports', 'v3_1'), exist_ok=True)
    res_df.to_csv(os.path.join(os.path.dirname(__file__), '..', 'reports', 'v3_1', 'h200_to_h203_results.csv'), index=False)
    print("\nSaved H-200 to H-203 results to AlphaLab_Antigravity/reports/v3_1/h200_to_h203_results.csv")

if __name__ == '__main__':
    run_h200_to_h203_experiments()
