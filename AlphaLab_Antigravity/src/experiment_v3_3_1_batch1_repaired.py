"""
V3.3.1 REPAIRED BATCH-1 DISCOVERY RUNNER
========================================
Repairs:
1. Evaluation-Window Consistency: All metrics computed exclusively from evaluation_trades (2018Q2 <= entry_quarter <= 2026Q2).
2. Profit Concentration Estimator: Exact positive profit pool denominator.
3. Cost Contract: Explicit baseline slippage = 0.0 pips.
4. Signal logic 100% frozen from V3.3.
"""

import os
import sys
import json
import numpy as np
import pandas as pd
from deep_quant_engine import DeepQuantEngine

sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None

def gini(x):
    x = np.array(x, dtype=float)
    if len(x) == 0 or np.mean(x) == 0:
        return 0.0
    mad = np.abs(np.subtract.outer(x, x)).mean()
    rmad = mad / np.mean(x)
    return 0.5 * rmad

# -------------------------------------------------------------
# EXACT FROZEN SIGNAL GENERATORS (BYTE-FOR-BYTE IDENTICAL TO V3.3)
# -------------------------------------------------------------
def make_h209_signals(df, sl_mult=1.5, tp_rr=2.0):
    c, h, l = df['close'].values, df['high'].values, df['low'].values
    n = len(c)
    c_s = pd.Series(c)
    tr = np.maximum(h - l, np.maximum(np.abs(h - np.roll(c, 1)), np.abs(l - np.roll(c, 1))))
    atr14 = pd.Series(tr).rolling(14).mean().values
    ema20 = c_s.ewm(span=20, adjust=False).mean().values
    ema50 = c_s.ewm(span=50, adjust=False).mean().values
    ema100 = c_s.ewm(span=100, adjust=False).mean().values
    l_s, h_s = pd.Series(l), pd.Series(h)
    bull_macro = (ema50 > ema100)
    bear_macro = (ema50 < ema100)
    prev_l = l_s.shift(1).values
    prev_h = h_s.shift(1).values
    prev_ema20 = pd.Series(ema20).shift(1).values
    bull_trigger = bull_macro & (prev_l < prev_ema20) & (c > ema20)
    bear_trigger = bear_macro & (prev_h > prev_ema20) & (c < ema20)
    sig = np.zeros(n, dtype=int)
    sl = np.zeros(n, dtype=float)
    tp = np.zeros(n, dtype=float)
    for i in range(100, n):
        cur_atr = max(atr14[i], 0.50)
        if bull_trigger[i]:
            sig[i] = 1; sl[i] = sl_mult * cur_atr; tp[i] = sl_mult * tp_rr * cur_atr
        elif bear_trigger[i]:
            sig[i] = -1; sl[i] = sl_mult * cur_atr; tp[i] = sl_mult * tp_rr * cur_atr
    return sig, sl, tp

def make_h210_signals(df, k_atr=2.5, sl_mult=1.5, tp_rr=1.5):
    c, h, l = df['close'].values, df['high'].values, df['low'].values
    n = len(c)
    c_s = pd.Series(c)
    tr = np.maximum(h - l, np.maximum(np.abs(h - np.roll(c, 1)), np.abs(l - np.roll(c, 1))))
    atr14 = pd.Series(tr).rolling(14).mean().values
    ema50 = c_s.ewm(span=50, adjust=False).mean().values
    dist = c - ema50
    long_trigger = (dist < -k_atr * atr14)
    short_trigger = (dist > k_atr * atr14)
    sig = np.zeros(n, dtype=int)
    sl = np.zeros(n, dtype=float)
    tp = np.zeros(n, dtype=float)
    for i in range(50, n):
        cur_atr = max(atr14[i], 0.50)
        if long_trigger[i]:
            sig[i] = 1; sl[i] = sl_mult * cur_atr; tp[i] = sl_mult * tp_rr * cur_atr
        elif short_trigger[i]:
            sig[i] = -1; sl[i] = sl_mult * cur_atr; tp[i] = sl_mult * tp_rr * cur_atr
    return sig, sl, tp

def make_h211_signals(df, lookback=20, sl_mult=1.5, tp_rr=2.0):
    c, h, l = df['close'].values, df['high'].values, df['low'].values
    n = len(c)
    tr = np.maximum(h - l, np.maximum(np.abs(h - np.roll(c, 1)), np.abs(l - np.roll(c, 1))))
    atr14 = pd.Series(tr).rolling(14).mean().values
    donch_h = pd.Series(h).rolling(lookback).max().shift(1).values
    donch_l = pd.Series(l).rolling(lookback).min().shift(1).values
    failed_high = (h > donch_h) & (c < donch_h)
    failed_low = (l < donch_l) & (c > donch_l)
    sig = np.zeros(n, dtype=int)
    sl = np.zeros(n, dtype=float)
    tp = np.zeros(n, dtype=float)
    for i in range(lookback + 5, n):
        cur_atr = max(atr14[i], 0.50)
        if failed_low[i]:
            sig[i] = 1; sl[i] = sl_mult * cur_atr; tp[i] = sl_mult * tp_rr * cur_atr
        elif failed_high[i]:
            sig[i] = -1; sl[i] = sl_mult * cur_atr; tp[i] = sl_mult * tp_rr * cur_atr
    return sig, sl, tp

def make_h212_signals(df, ema_len=50, sl_mult=1.5, tp_rr=2.0):
    c, h, l = df['close'].values, df['high'].values, df['low'].values
    n = len(c)
    c_s = pd.Series(c)
    dt = pd.to_datetime(df['datetime_str'] if 'datetime_str' in df.columns else df['datetime'])
    hour = dt.dt.hour.values
    day = dt.dt.date.values
    tr = np.maximum(h - l, np.maximum(np.abs(h - np.roll(c, 1)), np.abs(l - np.roll(c, 1))))
    atr14 = pd.Series(tr).rolling(14).mean().values
    ema = c_s.ewm(span=ema_len, adjust=False).mean().values
    df_temp = pd.DataFrame({'date': day, 'hour': hour, 'high': h, 'low': l})
    asia_mask = (df_temp['hour'] >= 0) & (df_temp['hour'] < 8)
    asia_stats = df_temp[asia_mask].groupby('date').agg({'high': 'max', 'low': 'min'}).rename(columns={'high': 'asia_h', 'low': 'asia_l'})
    df_temp = df_temp.join(asia_stats, on='date')
    asia_h = df_temp['asia_h'].values
    asia_l = df_temp['asia_l'].values
    in_trade_window = (hour >= 8) & (hour <= 16)
    bull_exp = in_trade_window & (c > asia_h) & (c > ema)
    bear_exp = in_trade_window & (c < asia_l) & (c < ema)
    sig = np.zeros(n, dtype=int)
    sl = np.zeros(n, dtype=float)
    tp = np.zeros(n, dtype=float)
    for i in range(ema_len + 5, n):
        cur_atr = max(atr14[i], 0.50)
        if bull_exp[i]:
            sig[i] = 1; sl[i] = sl_mult * cur_atr; tp[i] = sl_mult * tp_rr * cur_atr
        elif bear_exp[i]:
            sig[i] = -1; sl[i] = sl_mult * cur_atr; tp[i] = sl_mult * tp_rr * cur_atr
    return sig, sl, tp

def make_h213_signals(df, channel_len=50, th_upper=0.75, th_lower=0.25, sl_mult=1.5, tp_rr=2.0):
    c, h, l = df['close'].values, df['high'].values, df['low'].values
    n = len(c)
    tr = np.maximum(h - l, np.maximum(np.abs(h - np.roll(c, 1)), np.abs(l - np.roll(c, 1))))
    atr14 = pd.Series(tr).rolling(14).mean().values
    ch_h = pd.Series(h).rolling(channel_len).max().shift(1).values
    ch_l = pd.Series(l).rolling(channel_len).min().shift(1).values
    loc = (c - ch_l) / (ch_h - ch_l + 1e-9)
    roc10 = (pd.Series(c) - pd.Series(c).shift(10)).values
    bull_loc = (loc > th_upper) & (roc10 > 0)
    bear_loc = (loc < th_lower) & (roc10 < 0)
    sig = np.zeros(n, dtype=int)
    sl = np.zeros(n, dtype=float)
    tp = np.zeros(n, dtype=float)
    for i in range(channel_len + 15, n):
        cur_atr = max(atr14[i], 0.50)
        if bull_loc[i]:
            sig[i] = 1; sl[i] = sl_mult * cur_atr; tp[i] = sl_mult * tp_rr * cur_atr
        elif bear_loc[i]:
            sig[i] = -1; sl[i] = sl_mult * cur_atr; tp[i] = sl_mult * tp_rr * cur_atr
    return sig, sl, tp

def make_h214_signals(df, ratio_th=1.20, sl_mult=1.5, tp_rr=2.0):
    c, h, l = df['close'].values, df['high'].values, df['low'].values
    n = len(c)
    c_s = pd.Series(c)
    tr = np.maximum(h - l, np.maximum(np.abs(h - np.roll(c, 1)), np.abs(l - np.roll(c, 1))))
    atr7 = pd.Series(tr).rolling(7).mean().values
    atr28 = pd.Series(tr).rolling(28).mean().values
    atr14 = pd.Series(tr).rolling(14).mean().values
    vol_accel = (atr7 / (atr28 + 1e-9) > ratio_th)
    h3 = pd.Series(h).rolling(3).max().shift(1).values
    l3 = pd.Series(l).rolling(3).min().shift(1).values
    ema50 = c_s.ewm(span=50, adjust=False).mean().values
    bull_acc = vol_accel & (c > h3) & (c > ema50)
    bear_acc = vol_accel & (c < l3) & (c < ema50)
    sig = np.zeros(n, dtype=int)
    sl = np.zeros(n, dtype=float)
    tp = np.zeros(n, dtype=float)
    for i in range(50, n):
        cur_atr = max(atr14[i], 0.50)
        if bull_acc[i]:
            sig[i] = 1; sl[i] = sl_mult * cur_atr; tp[i] = sl_mult * tp_rr * cur_atr
        elif bear_acc[i]:
            sig[i] = -1; sl[i] = sl_mult * cur_atr; tp[i] = sl_mult * tp_rr * cur_atr
    return sig, sl, tp

# -------------------------------------------------------------
# REPAIRED EVALUATION PIPELINE
# -------------------------------------------------------------
def run_repaired_evaluation():
    print("=" * 95)
    print("🔬 RUNNING V3.3.1 BATCH-1 REPAIRED EVALUATION & REPRODUCTION")
    print("=" * 95)
    
    eng = DeepQuantEngine("GOLD_M30.csv")
    
    configs = [
        ("H-209-C1", "MHTP", "Trend Persistence (EMA50/100, EMA20 Pullback, SL1.5, TP3.0)", lambda df: make_h209_signals(df, sl_mult=1.5, tp_rr=2.0)),
        ("H-209-C2", "MHTP", "Trend Persistence (EMA50/100, EMA20 Pullback, SL1.5, TP3.75)", lambda df: make_h209_signals(df, sl_mult=1.5, tp_rr=2.5)),
        ("H-209-C3", "MHTP", "Trend Persistence (EMA50/100, EMA20 Pullback, SL2.0, TP4.0)", lambda df: make_h209_signals(df, sl_mult=2.0, tp_rr=2.0)),
        ("H-209-C4", "MHTP", "Trend Persistence (EMA50/100, EMA20 Pullback, SL2.0, TP5.0)", lambda df: make_h209_signals(df, sl_mult=2.0, tp_rr=2.5)),
        ("H-210-C1", "EDMR", "Displacement MR (EMA50 Dist > 2.5 ATR, SL1.5, TP2.25)", lambda df: make_h210_signals(df, k_atr=2.5, sl_mult=1.5, tp_rr=1.5)),
        ("H-210-C2", "EDMR", "Displacement MR (EMA50 Dist > 2.5 ATR, SL1.5, TP3.0)", lambda df: make_h210_signals(df, k_atr=2.5, sl_mult=1.5, tp_rr=2.0)),
        ("H-210-C3", "EDMR", "Displacement MR (EMA50 Dist > 3.0 ATR, SL1.5, TP2.25)", lambda df: make_h210_signals(df, k_atr=3.0, sl_mult=1.5, tp_rr=1.5)),
        ("H-210-C4", "EDMR", "Displacement MR (EMA50 Dist > 3.0 ATR, SL1.5, TP3.0)", lambda df: make_h210_signals(df, k_atr=3.0, sl_mult=1.5, tp_rr=2.0)),
        ("H-211-C1", "FBRLT", "Failed Breakout Trap (Donchian 20, SL1.5, TP3.0)", lambda df: make_h211_signals(df, lookback=20, sl_mult=1.5, tp_rr=2.0)),
        ("H-211-C2", "FBRLT", "Failed Breakout Trap (Donchian 20, SL1.5, TP3.75)", lambda df: make_h211_signals(df, lookback=20, sl_mult=1.5, tp_rr=2.5)),
        ("H-211-C3", "FBRLT", "Failed Breakout Trap (Donchian 40, SL1.5, TP3.0)", lambda df: make_h211_signals(df, lookback=40, sl_mult=1.5, tp_rr=2.0)),
        ("H-211-C4", "FBRLT", "Failed Breakout Trap (Donchian 40, SL1.5, TP3.75)", lambda df: make_h211_signals(df, lookback=40, sl_mult=1.5, tp_rr=2.5)),
        ("H-212-C1", "SORE", "Session Expansion (Asian 00-07, Lon 08-16 + EMA50, SL1.5, TP3.0)", lambda df: make_h212_signals(df, ema_len=50, sl_mult=1.5, tp_rr=2.0)),
        ("H-212-C2", "SORE", "Session Expansion (Asian 00-07, Lon 08-16 + EMA50, SL1.5, TP3.75)", lambda df: make_h212_signals(df, ema_len=50, sl_mult=1.5, tp_rr=2.5)),
        ("H-212-C3", "SORE", "Session Expansion (Asian 00-07, Lon 08-16 + EMA100, SL1.5, TP3.0)", lambda df: make_h212_signals(df, ema_len=100, sl_mult=1.5, tp_rr=2.0)),
        ("H-212-C4", "SORE", "Session Expansion (Asian 00-07, Lon 08-16 + EMA100, SL1.5, TP3.75)", lambda df: make_h212_signals(df, ema_len=100, sl_mult=1.5, tp_rr=2.5)),
        ("H-213-C1", "MRLM", "Range Loc Momentum (Channel 50, Th 0.75/0.25, SL1.5, TP3.0)", lambda df: make_h213_signals(df, channel_len=50, th_upper=0.75, th_lower=0.25, sl_mult=1.5, tp_rr=2.0)),
        ("H-213-C2", "MRLM", "Range Loc Momentum (Channel 50, Th 0.75/0.25, SL1.5, TP3.75)", lambda df: make_h213_signals(df, channel_len=50, th_upper=0.75, th_lower=0.25, sl_mult=1.5, tp_rr=2.5)),
        ("H-213-C3", "MRLM", "Range Loc Momentum (Channel 100, Th 0.80/0.20, SL1.5, TP3.0)", lambda df: make_h213_signals(df, channel_len=100, th_upper=0.80, th_lower=0.20, sl_mult=1.5, tp_rr=2.0)),
        ("H-213-C4", "MRLM", "Range Loc Momentum (Channel 100, Th 0.80/0.20, SL1.5, TP3.75)", lambda df: make_h213_signals(df, channel_len=100, th_upper=0.80, th_lower=0.20, sl_mult=1.5, tp_rr=2.5)),
        ("H-214-C1", "VRA", "Vol Acceleration (ATR7/28 > 1.20 + 3b Breakout + EMA50, SL1.5, TP3.0)", lambda df: make_h214_signals(df, ratio_th=1.20, sl_mult=1.5, tp_rr=2.0)),
        ("H-214-C2", "VRA", "Vol Acceleration (ATR7/28 > 1.20 + 3b Breakout + EMA50, SL1.5, TP3.75)", lambda df: make_h214_signals(df, ratio_th=1.20, sl_mult=1.5, tp_rr=2.5)),
        ("H-214-C3", "VRA", "Vol Acceleration (ATR7/28 > 1.30 + 3b Breakout + EMA50, SL1.5, TP3.0)", lambda df: make_h214_signals(df, ratio_th=1.30, sl_mult=1.5, tp_rr=2.0)),
        ("H-214-C4", "VRA", "Vol Acceleration (ATR7/28 > 1.30 + 3b Breakout + EMA50, SL1.5, TP3.75)", lambda df: make_h214_signals(df, ratio_th=1.30, sl_mult=1.5, tp_rr=2.5))
    ]
    
    out_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "reports", "v3_3_1"))
    os.makedirs(out_dir, exist_ok=True)
    
    # Generate complete list of 33 quarters
    all_33_quarters = []
    for y in range(2018, 2027):
        for q in range(1, 5):
            q_str = f"{y}Q{q}"
            if "2018Q2" <= q_str <= "2026Q2":
                all_33_quarters.append(q_str)
    assert len(all_33_quarters) == 33, f"Expected 33 complete quarters, got {len(all_33_quarters)}"
    
    summary_rows = []
    
    for cfg_id, fam, desc, s_fn in configs:
        tdf_raw, _, _ = eng.run_strategy(s_fn, spread_pips=25.0, slippage_pips=0.0, commission_per_lot=7.0, fixed_lot=0.10)
        
        # 1. Authoritative Evaluation Population: Strictly trades whose ENTRY quarter is within [2018Q2, 2026Q2]
        tdf_raw['entry_dt'] = pd.to_datetime(tdf_raw['entry_time'])
        tdf_raw['entry_quarter'] = tdf_raw['entry_dt'].dt.to_period('Q').astype(str)
        
        eval_trades = tdf_raw[(tdf_raw['entry_quarter'] >= '2018Q2') & (tdf_raw['entry_quarter'] <= '2026Q2')].copy().reset_index(drop=True)
        tot_tr = len(eval_trades)
        
        # 2. Rebuild 33-Quarter Table directly from eval_trades
        q_records = []
        for q_str in all_33_quarters:
            q_sub = eval_trades[eval_trades['entry_quarter'] == q_str]
            q_tr = len(q_sub)
            q_pnl = float(q_sub['pnl_usd'].sum()) if q_tr > 0 else 0.0
            q_gp = float(q_sub[q_sub['pnl_usd'] > 0]['pnl_usd'].sum()) if q_tr > 0 else 0.0
            q_gl = float(np.abs(q_sub[q_sub['pnl_usd'] < 0]['pnl_usd'].sum())) if q_tr > 0 else 0.0
            q_pf = q_gp / q_gl if q_gl > 0 else (999.0 if q_gp > 0 else 0.0)
            q_exp = float(q_sub['pnl_usd'].mean()) if q_tr > 0 else 0.0
            
            q_records.append({
                'quarter': q_str,
                'trades': q_tr,
                'net_pnl_usd': q_pnl,
                'gross_profit_usd': q_gp,
                'gross_loss_usd': q_gl,
                'pf': q_pf,
                'expectancy_usd': q_exp
            })
        qdf = pd.DataFrame(q_records)
        assert len(qdf) == 33, f"Expected 33 quarters, got {len(qdf)}"
        assert qdf['trades'].sum() == tot_tr, f"Quarter trade sum {qdf['trades'].sum()} != eval_trades {tot_tr}"
        
        # Frequency metrics
        trades_arr = qdf['trades'].values
        min_tr = int(np.min(trades_arr))
        med_tr = float(np.median(trades_arr))
        max_tr = int(np.max(trades_arr))
        max_share = (max_tr / tot_tr * 100.0) if tot_tr > 0 else 0.0
        max_med_ratio = (max_tr / med_tr) if med_tr > 0 else 999.0
        t_gini = gini(trades_arr)
        
        # 3. Overall Economic Metrics exclusively from eval_trades
        gp = float(eval_trades[eval_trades['pnl_usd'] > 0]['pnl_usd'].sum()) if tot_tr > 0 else 0.0
        gl = float(np.abs(eval_trades[eval_trades['pnl_usd'] < 0]['pnl_usd'].sum())) if tot_tr > 0 else 0.0
        overall_pf = gp / gl if gl > 0 else (999.0 if gp > 0 else 0.0)
        net_pnl = float(eval_trades['pnl_usd'].sum()) if tot_tr > 0 else 0.0
        avg_exp = float(eval_trades['pnl_usd'].mean()) if tot_tr > 0 else 0.0
        wr = float((eval_trades['pnl_usd'] > 0).mean() * 100.0) if tot_tr > 0 else 0.0
        
        # 4. Long / Short Diagnostics exclusively from eval_trades
        long_sub = eval_trades[eval_trades['direction'] == 'BUY']
        short_sub = eval_trades[eval_trades['direction'] == 'SELL']
        
        assert len(long_sub) + len(short_sub) == tot_tr, "Long + Short trade count mismatch"
        
        l_gp = float(long_sub[long_sub['pnl_usd'] > 0]['pnl_usd'].sum()) if len(long_sub) > 0 else 0.0
        l_gl = float(np.abs(long_sub[long_sub['pnl_usd'] < 0]['pnl_usd'].sum())) if len(long_sub) > 0 else 0.0
        l_pf = l_gp / l_gl if l_gl > 0 else (999.0 if l_gp > 0 else 0.0)
        l_exp = float(long_sub['pnl_usd'].mean()) if len(long_sub) > 0 else 0.0
        
        s_gp = float(short_sub[short_sub['pnl_usd'] > 0]['pnl_usd'].sum()) if len(short_sub) > 0 else 0.0
        s_gl = float(np.abs(short_sub[short_sub['pnl_usd'] < 0]['pnl_usd'].sum())) if len(short_sub) > 0 else 0.0
        s_pf = s_gp / s_gl if s_gl > 0 else (999.0 if s_gp > 0 else 0.0)
        s_exp = float(short_sub['pnl_usd'].mean()) if len(short_sub) > 0 else 0.0
        
        # 5. Exact Positive Profit Concentration Estimator
        pos_q_pnls = qdf[qdf['net_pnl_usd'] > 0]['net_pnl_usd'].values
        total_pos_q_pnl = float(np.sum(pos_q_pnls))
        
        if total_pos_q_pnl > 0 and len(pos_q_pnls) > 0:
            sorted_pos_pnls = np.sort(pos_q_pnls)[::-1]
            top1_share = float(sorted_pos_pnls[0] / total_pos_q_pnl * 100.0)
            top3_share = float(np.sum(sorted_pos_pnls[:min(3, len(sorted_pos_pnls))]) / total_pos_q_pnl * 100.0)
            top5_share = float(np.sum(sorted_pos_pnls[:min(5, len(sorted_pos_pnls))]) / total_pos_q_pnl * 100.0)
            top10_share = float(np.sum(sorted_pos_pnls[:min(10, len(sorted_pos_pnls))]) / total_pos_q_pnl * 100.0)
            profit_pool_applicable = True
        else:
            top1_share = np.nan
            top3_share = np.nan
            top5_share = np.nan
            top10_share = np.nan
            profit_pool_applicable = False
            
        # 6. Rolling 4Q Windows (Exactly 30 windows)
        r4_pos, r4_pf12 = [], []
        r4_records = []
        for i in range(30):
            sub = qdf.iloc[i:i+4]
            r_pnl = float(sub['net_pnl_usd'].sum())
            r_gp = float(sub['gross_profit_usd'].sum())
            r_gl = float(sub['gross_loss_usd'].sum())
            r_pf = r_gp / r_gl if r_gl > 0 else (999.0 if r_gp > 0 else 0.0)
            is_pos = bool(r_pnl > 0)
            is_pf12 = bool(r_pf >= 1.20)
            r4_pos.append(is_pos)
            r4_pf12.append(is_pf12)
            r4_records.append({
                'window': f"{qdf.iloc[i]['quarter']}->{qdf.iloc[i+3]['quarter']}",
                'net_pnl_usd': r_pnl,
                'pf': r_pf,
                'is_positive': is_pos,
                'is_pf_ge_120': is_pf12
            })
            
        assert len(r4_pos) == 30, f"Expected 30 rolling 4Q windows, got {len(r4_pos)}"
        r4_pos_pct = float(np.mean(r4_pos) * 100.0)
        r4_pf12_pct = float(np.mean(r4_pf12) * 100.0)
        
        # 7. Exact Hard Gates
        gate_A1 = bool(min_tr >= 5)
        gate_A2 = bool(max_share <= 5.0)
        gate_A3 = bool(max_med_ratio <= 3.0)
        gate_A4 = bool(t_gini < 0.30)
        gate_B1 = bool(top3_share <= 40.0) if profit_pool_applicable else False
        gate_B2 = bool(top5_share <= 60.0) if profit_pool_applicable else False
        gate_D1 = bool(r4_pos_pct >= 70.0)
        gate_D2 = bool(r4_pf12_pct >= 65.0)
        gate_E1 = bool(overall_pf >= 1.25)
        gate_E2 = bool(net_pnl > 0.0)
        
        all_pass = bool(
            gate_A1 and gate_A2 and gate_A3 and gate_A4 and
            gate_B1 and gate_B2 and gate_D1 and gate_D2 and
            gate_E1 and gate_E2
        )
        
        if not gate_A1:
            primary_fail = f"Gate A1 (Min Trades/Q = {min_tr} < 5)"
        elif not gate_A2:
            primary_fail = f"Gate A2 (Max Q Share = {max_share:.1f}% > 5.0%)"
        elif not gate_A3:
            primary_fail = f"Gate A3 (Max/Med = {max_med_ratio:.2f} > 3.0)"
        elif not gate_A4:
            primary_fail = f"Gate A4 (Gini = {t_gini:.3f} >= 0.30)"
        elif not gate_E1:
            primary_fail = f"Gate E1 (PF = {overall_pf:.3f} < 1.25)"
        elif not gate_E2:
            primary_fail = f"Gate E2 (Expectancy = ${avg_exp:+.2f} <= $0.00)"
        elif not gate_D1:
            primary_fail = f"Gate D1 (R4 Pos = {r4_pos_pct:.1f}% < 70.0%)"
        elif not gate_D2:
            primary_fail = f"Gate D2 (R4 PF12 = {r4_pf12_pct:.1f}% < 65.0%)"
        elif not gate_B1:
            primary_fail = f"Gate B1 (Top3 Positive PnL = {top3_share:.1f}% > 40.0%)" if profit_pool_applicable else "Gate B1 (No positive profit pool)"
        elif not gate_B2:
            primary_fail = f"Gate B2 (Top5 Positive PnL = {top5_share:.1f}% > 60.0%)" if profit_pool_applicable else "Gate B2 (No positive profit pool)"
        else:
            primary_fail = "NONE (ALL GATES PASSED)"
            
        final_status = "HISTORICAL DISTRIBUTED SURVIVOR — REQUIRES PRECOMMITTED STABILITY BATCH" if all_pass else "REJECTED"
        
        # Save raw per-config files
        cfg_tag = cfg_id.lower().replace("-", "_")
        eval_trades.to_csv(os.path.join(out_dir, f"{cfg_tag}_evaluation_trades.csv"), index=False)
        qdf.to_csv(os.path.join(out_dir, f"{cfg_tag}_quarters.csv"), index=False)
        pd.DataFrame(r4_records).to_csv(os.path.join(out_dir, f"{cfg_tag}_rolling4q.csv"), index=False)
        
        dir_dict = {
            'long_trades': int(len(long_sub)),
            'long_gross_profit': l_gp,
            'long_gross_loss': l_gl,
            'long_pf': l_pf,
            'long_net_pnl': float(long_sub['pnl_usd'].sum()) if len(long_sub) > 0 else 0.0,
            'long_expectancy': l_exp,
            'short_trades': int(len(short_sub)),
            'short_gross_profit': s_gp,
            'short_gross_loss': s_gl,
            'short_pf': s_pf,
            'short_net_pnl': float(short_sub['pnl_usd'].sum()) if len(short_sub) > 0 else 0.0,
            'short_expectancy': s_exp
        }
        with open(os.path.join(out_dir, f"{cfg_tag}_directional.json"), 'w') as f:
            json.dump(dir_dict, f, indent=2)
            
        diag_dict = {
            'config_id': cfg_id,
            'mechanism_family': fam,
            'description': desc,
            'total_positive_quarter_pnl': total_pos_q_pnl,
            'top1_positive_q_share': top1_share,
            'top3_positive_q_share': top3_share,
            'top5_positive_q_share': top5_share,
            'top10_positive_q_share': top10_share,
            'profit_pool_applicable': profit_pool_applicable,
            'primary_failure_reason': primary_fail,
            'final_status': final_status
        }
        with open(os.path.join(out_dir, f"{cfg_tag}_diagnostics.json"), 'w') as f:
            json.dump(diag_dict, f, indent=2)
            
        summary_rows.append({
            'config_id': cfg_id,
            'family': fam,
            'description': desc,
            'evaluation_start': '2018Q2',
            'evaluation_end': '2026Q2',
            'total_trades': tot_tr,
            'min_trades_q': min_tr,
            'median_trades_q': med_tr,
            'max_trades_q': max_tr,
            'max_q_share': max_share,
            'max_median': max_med_ratio,
            'gini': t_gini,
            'net_pnl': net_pnl,
            'gross_profit': gp,
            'gross_loss': gl,
            'pf': overall_pf,
            'expectancy': avg_exp,
            'win_rate_pct': wr,
            'long_trades': int(len(long_sub)),
            'long_pf': l_pf,
            'long_expectancy': l_exp,
            'short_trades': int(len(short_sub)),
            'short_pf': s_pf,
            'short_expectancy': s_exp,
            'top1_positive_q_share': top1_share,
            'top3_positive_q_share': top3_share,
            'top5_positive_q_share': top5_share,
            'top10_positive_q_share': top10_share,
            'profit_pool_applicable': profit_pool_applicable,
            'rolling4_positive_pct': r4_pos_pct,
            'rolling4_pf120_pct': r4_pf12_pct,
            'gate_A1': gate_A1,
            'gate_A2': gate_A2,
            'gate_A3': gate_A3,
            'gate_A4': gate_A4,
            'gate_B1': gate_B1,
            'gate_B2': gate_B2,
            'gate_D1': gate_D1,
            'gate_D2': gate_D2,
            'gate_E1': gate_E1,
            'gate_E2': gate_E2,
            'all_gates_pass': all_pass,
            'primary_failure_reason': primary_fail,
            'final_status': final_status
        })

    sum_df = pd.DataFrame(summary_rows)
    sum_csv_path = os.path.join(out_dir, "batch1_repaired_summary.csv")
    sum_df.to_csv(sum_csv_path, index=False)
    print(f"Saved Authoritative Repaired Summary CSV to: {sum_csv_path}")
    
    # -------------------------------------------------------------
    # BUILD V3_3_1_BEFORE_AFTER_RECONCILIATION.CSV
    # -------------------------------------------------------------
    old_csv_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "reports", "v3_3", "batch1_summary.csv"))
    old_df = pd.read_csv(old_csv_path)
    
    recon_rows = []
    for _, new_r in sum_df.iterrows():
        cfg = new_r['config_id']
        old_r = old_df[old_df['config_id'] == cfg].iloc[0]
        
        status_changed = (old_r['final_status'] != new_r['final_status'])
        top3_new_str = f"{new_r['top3_positive_q_share']:.1f}%" if new_r['profit_pool_applicable'] else "NaN (No Profit Pool)"
        top5_new_str = f"{new_r['top5_positive_q_share']:.1f}%" if new_r['profit_pool_applicable'] else "NaN (No Profit Pool)"
        top3_old_str = f"{old_r['top3_q_pnl_share_pct']:.1f}%" if old_r['top3_q_pnl_share_pct'] >= 0 else "N/A (-999)"
        top5_old_str = f"{old_r['top5_q_pnl_share_pct']:.1f}%" if old_r['top5_q_pnl_share_pct'] >= 0 else "N/A (-999)"
        
        recon_rows.append({
            'config_id': cfg,
            'old_total_trades': old_r['total_trades'],
            'new_total_trades': new_r['total_trades'],
            'old_pf': old_r['overall_pf'],
            'new_pf': new_r['pf'],
            'old_expectancy': old_r['avg_expectancy_usd'],
            'new_expectancy': new_r['expectancy'],
            'old_long_pf': old_r['long_pf'],
            'new_long_pf': new_r['long_pf'],
            'old_short_pf': old_r['short_pf'],
            'new_short_pf': new_r['short_pf'],
            'old_top3': top3_old_str,
            'new_top3': top3_new_str,
            'old_top5': top5_old_str,
            'new_top5': top5_new_str,
            'old_final_status': old_r['final_status'],
            'new_final_status': new_r['final_status'],
            'status_changed': status_changed,
            'reason': "Evaluation window cleanly restricted to 2018Q2-2026Q2; profit pool denominator repaired"
        })
    recon_df = pd.DataFrame(recon_rows)
    recon_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "V3_3_1_BEFORE_AFTER_RECONCILIATION.csv"))
    recon_df.to_csv(recon_path, index=False)
    print(f"Saved Before/After Reconciliation CSV to: {recon_path}")
    return sum_df

if __name__ == '__main__':
    run_repaired_evaluation()
