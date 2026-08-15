"""
V3.3 BATCH-1 MARKET-MECHANISM DISCOVERY RUNNER
==============================================
Implements 24 precommitted configurations across 6 distinct mechanism families:
- H-209: Multi-Horizon Trend Persistence (MHTP)
- H-210: Extreme Displacement Mean Reversion (EDMR)
- H-211: Failed Breakout Reversal / Liquidity Trap (FBRLT)
- H-212: Session Opening Range Expansion (SORE)
- H-213: Medium-Range Location + Momentum (MRLM)
- H-214: Volatility Regime Acceleration (VRA - Non-Squeeze)

Executes on Gold M30 (2018Q2 to 2026Q2, 33 complete quarters) with full asset-aware engine.
Saves all raw outputs, summary tables, and evaluates primary hard temporal & economic gates.
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
# SIGNAL GENERATORS FOR THE 6 PRECOMMITTED FAMILIES
# -------------------------------------------------------------

# --- FAMILY 1: H-209 (MULTI-HORIZON TREND PERSISTENCE) ---
def make_h209_signals(df, sl_mult=1.5, tp_rr=2.0):
    c, h, l = df['close'].values, df['high'].values, df['low'].values
    n = len(c)
    c_s = pd.Series(c)
    
    tr = np.maximum(h - l, np.maximum(np.abs(h - np.roll(c, 1)), np.abs(l - np.roll(c, 1))))
    atr14 = pd.Series(tr).rolling(14).mean().values
    
    ema20 = c_s.ewm(span=20, adjust=False).mean().values
    ema50 = c_s.ewm(span=50, adjust=False).mean().values
    ema100 = c_s.ewm(span=100, adjust=False).mean().values
    
    l_s = pd.Series(l)
    h_s = pd.Series(h)
    
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
            sig[i] = 1
            sl[i] = sl_mult * cur_atr
            tp[i] = sl_mult * tp_rr * cur_atr
        elif bear_trigger[i]:
            sig[i] = -1
            sl[i] = sl_mult * cur_atr
            tp[i] = sl_mult * tp_rr * cur_atr
    return sig, sl, tp

# --- FAMILY 2: H-210 (EXTREME DISPLACEMENT MEAN REVERSION) ---
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
            sig[i] = 1
            sl[i] = sl_mult * cur_atr
            tp[i] = sl_mult * tp_rr * cur_atr
        elif short_trigger[i]:
            sig[i] = -1
            sl[i] = sl_mult * cur_atr
            tp[i] = sl_mult * tp_rr * cur_atr
    return sig, sl, tp

# --- FAMILY 3: H-211 (FAILED BREAKOUT REVERSAL / LIQUIDITY TRAP) ---
def make_h211_signals(df, lookback=20, sl_mult=1.5, tp_rr=2.0):
    c, h, l = df['close'].values, df['high'].values, df['low'].values
    n = len(c)
    
    tr = np.maximum(h - l, np.maximum(np.abs(h - np.roll(c, 1)), np.abs(l - np.roll(c, 1))))
    atr14 = pd.Series(tr).rolling(14).mean().values
    
    donch_h = pd.Series(h).rolling(lookback).max().shift(1).values
    donch_l = pd.Series(l).rolling(lookback).min().shift(1).values
    
    # Bear trap / Failed High Breakout -> Short
    failed_high = (h > donch_h) & (c < donch_h)
    # Bull trap / Failed Low Breakout -> Long
    failed_low = (l < donch_l) & (c > donch_l)
    
    sig = np.zeros(n, dtype=int)
    sl = np.zeros(n, dtype=float)
    tp = np.zeros(n, dtype=float)
    
    for i in range(lookback + 5, n):
        cur_atr = max(atr14[i], 0.50)
        if failed_low[i]:
            sig[i] = 1
            sl[i] = sl_mult * cur_atr
            tp[i] = sl_mult * tp_rr * cur_atr
        elif failed_high[i]:
            sig[i] = -1
            sl[i] = sl_mult * cur_atr
            tp[i] = sl_mult * tp_rr * cur_atr
    return sig, sl, tp

# --- FAMILY 4: H-212 (SESSION OPENING RANGE EXPANSION) ---
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
    
    # Compute Asian Session (00:00 to 07:00 UTC) High & Low per day
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
            sig[i] = 1
            sl[i] = sl_mult * cur_atr
            tp[i] = sl_mult * tp_rr * cur_atr
        elif bear_exp[i]:
            sig[i] = -1
            sl[i] = sl_mult * cur_atr
            tp[i] = sl_mult * tp_rr * cur_atr
    return sig, sl, tp

# --- FAMILY 5: H-213 (MEDIUM-RANGE LOCATION + MOMENTUM) ---
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
            sig[i] = 1
            sl[i] = sl_mult * cur_atr
            tp[i] = sl_mult * tp_rr * cur_atr
        elif bear_loc[i]:
            sig[i] = -1
            sl[i] = sl_mult * cur_atr
            tp[i] = sl_mult * tp_rr * cur_atr
    return sig, sl, tp

# --- FAMILY 6: H-214 (VOLATILITY REGIME ACCELERATION) ---
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
            sig[i] = 1
            sl[i] = sl_mult * cur_atr
            tp[i] = sl_mult * tp_rr * cur_atr
        elif bear_acc[i]:
            sig[i] = -1
            sl[i] = sl_mult * cur_atr
            tp[i] = sl_mult * tp_rr * cur_atr
    return sig, sl, tp

# -------------------------------------------------------------
# BATCH-1 EXECUTION ENGINE
# -------------------------------------------------------------
def run_batch1_discovery():
    print("=" * 95)
    print("🔬 RUNNING V3.3 BATCH-1 MARKET-MECHANISM DISCOVERY (H-209 TO H-214)")
    print("=" * 95)
    
    eng = DeepQuantEngine("GOLD_M30.csv")
    
    configs = [
        # H-209: Multi-Horizon Trend Persistence
        ("H-209-C1", "MHTP", "Trend Persistence (EMA50/100, EMA20 Pullback, SL1.5, TP3.0)", lambda df: make_h209_signals(df, sl_mult=1.5, tp_rr=2.0)),
        ("H-209-C2", "MHTP", "Trend Persistence (EMA50/100, EMA20 Pullback, SL1.5, TP3.75)", lambda df: make_h209_signals(df, sl_mult=1.5, tp_rr=2.5)),
        ("H-209-C3", "MHTP", "Trend Persistence (EMA50/100, EMA20 Pullback, SL2.0, TP4.0)", lambda df: make_h209_signals(df, sl_mult=2.0, tp_rr=2.0)),
        ("H-209-C4", "MHTP", "Trend Persistence (EMA50/100, EMA20 Pullback, SL2.0, TP5.0)", lambda df: make_h209_signals(df, sl_mult=2.0, tp_rr=2.5)),
        
        # H-210: Extreme Displacement Mean Reversion
        ("H-210-C1", "EDMR", "Displacement MR (EMA50 Dist > 2.5 ATR, SL1.5, TP2.25)", lambda df: make_h210_signals(df, k_atr=2.5, sl_mult=1.5, tp_rr=1.5)),
        ("H-210-C2", "EDMR", "Displacement MR (EMA50 Dist > 2.5 ATR, SL1.5, TP3.0)", lambda df: make_h210_signals(df, k_atr=2.5, sl_mult=1.5, tp_rr=2.0)),
        ("H-210-C3", "EDMR", "Displacement MR (EMA50 Dist > 3.0 ATR, SL1.5, TP2.25)", lambda df: make_h210_signals(df, k_atr=3.0, sl_mult=1.5, tp_rr=1.5)),
        ("H-210-C4", "EDMR", "Displacement MR (EMA50 Dist > 3.0 ATR, SL1.5, TP3.0)", lambda df: make_h210_signals(df, k_atr=3.0, sl_mult=1.5, tp_rr=2.0)),
        
        # H-211: Failed Breakout Reversal / Liquidity Trap
        ("H-211-C1", "FBRLT", "Failed Breakout Trap (Donchian 20, SL1.5, TP3.0)", lambda df: make_h211_signals(df, lookback=20, sl_mult=1.5, tp_rr=2.0)),
        ("H-211-C2", "FBRLT", "Failed Breakout Trap (Donchian 20, SL1.5, TP3.75)", lambda df: make_h211_signals(df, lookback=20, sl_mult=1.5, tp_rr=2.5)),
        ("H-211-C3", "FBRLT", "Failed Breakout Trap (Donchian 40, SL1.5, TP3.0)", lambda df: make_h211_signals(df, lookback=40, sl_mult=1.5, tp_rr=2.0)),
        ("H-211-C4", "FBRLT", "Failed Breakout Trap (Donchian 40, SL1.5, TP3.75)", lambda df: make_h211_signals(df, lookback=40, sl_mult=1.5, tp_rr=2.5)),
        
        # H-212: Session Opening Range Expansion
        ("H-212-C1", "SORE", "Session Expansion (Asian 00-07, Lon 08-16 + EMA50, SL1.5, TP3.0)", lambda df: make_h212_signals(df, ema_len=50, sl_mult=1.5, tp_rr=2.0)),
        ("H-212-C2", "SORE", "Session Expansion (Asian 00-07, Lon 08-16 + EMA50, SL1.5, TP3.75)", lambda df: make_h212_signals(df, ema_len=50, sl_mult=1.5, tp_rr=2.5)),
        ("H-212-C3", "SORE", "Session Expansion (Asian 00-07, Lon 08-16 + EMA100, SL1.5, TP3.0)", lambda df: make_h212_signals(df, ema_len=100, sl_mult=1.5, tp_rr=2.0)),
        ("H-212-C4", "SORE", "Session Expansion (Asian 00-07, Lon 08-16 + EMA100, SL1.5, TP3.75)", lambda df: make_h212_signals(df, ema_len=100, sl_mult=1.5, tp_rr=2.5)),
        
        # H-213: Medium-Range Location + Momentum
        ("H-213-C1", "MRLM", "Range Loc Momentum (Channel 50, Th 0.75/0.25, SL1.5, TP3.0)", lambda df: make_h213_signals(df, channel_len=50, th_upper=0.75, th_lower=0.25, sl_mult=1.5, tp_rr=2.0)),
        ("H-213-C2", "MRLM", "Range Loc Momentum (Channel 50, Th 0.75/0.25, SL1.5, TP3.75)", lambda df: make_h213_signals(df, channel_len=50, th_upper=0.75, th_lower=0.25, sl_mult=1.5, tp_rr=2.5)),
        ("H-213-C3", "MRLM", "Range Loc Momentum (Channel 100, Th 0.80/0.20, SL1.5, TP3.0)", lambda df: make_h213_signals(df, channel_len=100, th_upper=0.80, th_lower=0.20, sl_mult=1.5, tp_rr=2.0)),
        ("H-213-C4", "MRLM", "Range Loc Momentum (Channel 100, Th 0.80/0.20, SL1.5, TP3.75)", lambda df: make_h213_signals(df, channel_len=100, th_upper=0.80, th_lower=0.20, sl_mult=1.5, tp_rr=2.5)),
        
        # H-214: Volatility Regime Acceleration
        ("H-214-C1", "VRA", "Vol Acceleration (ATR7/28 > 1.20 + 3b Breakout + EMA50, SL1.5, TP3.0)", lambda df: make_h214_signals(df, ratio_th=1.20, sl_mult=1.5, tp_rr=2.0)),
        ("H-214-C2", "VRA", "Vol Acceleration (ATR7/28 > 1.20 + 3b Breakout + EMA50, SL1.5, TP3.75)", lambda df: make_h214_signals(df, ratio_th=1.20, sl_mult=1.5, tp_rr=2.5)),
        ("H-214-C3", "VRA", "Vol Acceleration (ATR7/28 > 1.30 + 3b Breakout + EMA50, SL1.5, TP3.0)", lambda df: make_h214_signals(df, ratio_th=1.30, sl_mult=1.5, tp_rr=2.0)),
        ("H-214-C4", "VRA", "Vol Acceleration (ATR7/28 > 1.30 + 3b Breakout + EMA50, SL1.5, TP3.75)", lambda df: make_h214_signals(df, ratio_th=1.30, sl_mult=1.5, tp_rr=2.5))
    ]
    
    out_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "reports", "v3_3"))
    os.makedirs(out_dir, exist_ok=True)
    
    summary_rows = []
    
    for cfg_id, fam, desc, s_fn in configs:
        tdf, qdf, summ = eng.run_strategy(s_fn, spread_pips=25.0, commission_per_lot=7.0, fixed_lot=0.10)
        
        comp_q = qdf[(qdf['quarter'] >= '2018Q2') & (qdf['quarter'] <= '2026Q2')].copy().reset_index(drop=True)
        trades_arr = comp_q['trades'].values
        n_q = len(comp_q)
        tot_tr = int(np.sum(trades_arr))
        
        min_tr = int(np.min(trades_arr)) if n_q > 0 else 0
        med_tr = float(np.median(trades_arr)) if n_q > 0 else 0.0
        max_tr = int(np.max(trades_arr)) if n_q > 0 else 0
        max_share = (max_tr / tot_tr * 100.0) if tot_tr > 0 else 0.0
        max_med_ratio = (max_tr / med_tr) if med_tr > 0 else 999.0
        t_gini = gini(trades_arr)
        
        tot_pnl = float(comp_q['net_pnl_usd'].sum())
        sorted_q_pnl = np.sort(comp_q['net_pnl_usd'].values)[::-1]
        
        if tot_pnl > 0:
            top3_q_pnl_share = float(np.sum(sorted_q_pnl[:3]) / tot_pnl * 100.0)
            top5_q_pnl_share = float(np.sum(sorted_q_pnl[:5]) / tot_pnl * 100.0)
        else:
            top3_q_pnl_share = np.nan
            top5_q_pnl_share = np.nan
            
        r4_pos, r4_pf12 = [], []
        for i in range(n_q - 3):
            sub = comp_q.iloc[i:i+4]
            pnl = sub['net_pnl_usd'].sum()
            gp = sub['gross_profit_usd'].sum()
            gl = sub['gross_loss_usd'].sum()
            pf = gp / gl if gl > 0 else (999.0 if gp > 0 else 0.0)
            r4_pos.append(bool(pnl > 0))
            r4_pf12.append(bool(pf >= 1.20))
            
        r4_pos_pct = float(np.mean(r4_pos) * 100.0) if len(r4_pos) > 0 else 0.0
        r4_pf12_pct = float(np.mean(r4_pf12) * 100.0) if len(r4_pf12) > 0 else 0.0
        
        # Diagnostics: Directional breakdown
        long_trades = tdf[tdf['direction'] == 1]
        short_trades = tdf[tdf['direction'] == -1]
        
        l_gp = float(long_trades[long_trades['net_pnl_usd'] > 0]['net_pnl_usd'].sum())
        l_gl = float(np.abs(long_trades[long_trades['net_pnl_usd'] < 0]['net_pnl_usd'].sum()))
        l_pf = l_gp / l_gl if l_gl > 0 else (999.0 if l_gp > 0 else 0.0)
        
        s_gp = float(short_trades[short_trades['net_pnl_usd'] > 0]['net_pnl_usd'].sum())
        s_gl = float(np.abs(short_trades[short_trades['net_pnl_usd'] < 0]['net_pnl_usd'].sum()))
        s_pf = s_gp / s_gl if s_gl > 0 else (999.0 if s_gp > 0 else 0.0)
        
        # Hard Gates
        gate_min_trades = bool(min_tr >= 5)
        gate_max_share  = bool(max_share <= 5.0)
        gate_max_median = bool(max_med_ratio <= 3.0)
        gate_gini       = bool(t_gini < 0.30)
        gate_top3_pnl   = bool(top3_q_pnl_share <= 40.0) if not np.isnan(top3_q_pnl_share) else False
        gate_top5_pnl   = bool(top5_q_pnl_share <= 60.0) if not np.isnan(top5_q_pnl_share) else False
        gate_r4_pos     = bool(r4_pos_pct >= 70.0)
        gate_r4_pf      = bool(r4_pf12_pct >= 65.0)
        gate_pf         = bool(summ['overall_pf'] >= 1.25)
        gate_expectancy = bool(summ['total_pnl_usd'] > 0.0)
        
        all_pass = bool(
            gate_min_trades and gate_max_share and gate_max_median and gate_gini and
            gate_top3_pnl and gate_top5_pnl and gate_r4_pos and gate_r4_pf and
            gate_pf and gate_expectancy
        )
        
        # Primary failure gate identification
        if not gate_min_trades:
            fail_reason = f"Gate A1 (Min Trades/Q = {min_tr} < 5)"
        elif not gate_max_share:
            fail_reason = f"Gate A2 (Max Q Share = {max_share:.1f}% > 5.0%)"
        elif not gate_max_median:
            fail_reason = f"Gate A3 (Max/Med = {max_med_ratio:.2f} > 3.0)"
        elif not gate_gini:
            fail_reason = f"Gate A4 (Gini = {t_gini:.3f} >= 0.30)"
        elif not gate_pf:
            fail_reason = f"Gate E1 (PF = {summ['overall_pf']:.3f} < 1.25)"
        elif not gate_expectancy:
            fail_reason = f"Gate E2 (Expectancy = ${summ['avg_expectancy_usd']:+.2f} <= $0.00)"
        elif not gate_r4_pos:
            fail_reason = f"Gate D1 (R4 Pos = {r4_pos_pct:.1f}% < 70.0%)"
        elif not gate_r4_pf:
            fail_reason = f"Gate D2 (R4 PF12 = {r4_pf12_pct:.1f}% < 65.0%)"
        elif not gate_top3_pnl:
            fail_reason = f"Gate B1 (Top3 PnL = {top3_q_pnl_share:.1f}% > 40.0%)"
        elif not gate_top5_pnl:
            fail_reason = f"Gate B2 (Top5 PnL = {top5_q_pnl_share:.1f}% > 60.0%)"
        else:
            fail_reason = "NONE (ALL GATES PASSED)"
            
        final_status = "HISTORICAL DISTRIBUTED SURVIVOR (REQUIRES STABILITY BATCH)" if all_pass else "REJECTED"
        
        # Save raw per-configuration files
        cfg_tag = cfg_id.lower().replace("-", "_")
        tdf.to_csv(os.path.join(out_dir, f"{cfg_tag}_trades.csv"), index=False)
        comp_q.to_csv(os.path.join(out_dir, f"{cfg_tag}_quarters.csv"), index=False)
        
        r_df = pd.DataFrame({
            'window_4q': [f"{comp_q.iloc[i]['quarter']}->{comp_q.iloc[i+3]['quarter']}" for i in range(n_q - 3)],
            'r4_positive': r4_pos,
            'r4_pf_ge_120': r4_pf12
        })
        r_df.to_csv(os.path.join(out_dir, f"{cfg_tag}_rolling4q.csv"), index=False)
        
        diag_dict = {
            'config_id': cfg_id,
            'mechanism_family': fam,
            'description': desc,
            'long_trades': int(len(long_trades)),
            'long_pf': float(l_pf),
            'short_trades': int(len(short_trades)),
            'short_pf': float(s_pf),
            'failure_reason': fail_reason,
            'final_status': final_status
        }
        with open(os.path.join(out_dir, f"{cfg_tag}_diagnostics.json"), 'w') as f:
            json.dump(diag_dict, f, indent=2)
            
        summary_rows.append({
            'config_id': cfg_id,
            'mechanism_family': fam,
            'description': desc,
            'total_trades': tot_tr,
            'min_trades_per_q': min_tr,
            'median_trades_per_q': med_tr,
            'max_trades_per_q': max_tr,
            'max_q_trade_share_pct': max_share,
            'max_to_median_ratio': max_med_ratio,
            'trade_count_gini': t_gini,
            'top3_q_pnl_share_pct': top3_q_pnl_share if not np.isnan(top3_q_pnl_share) else -999.0,
            'top5_q_pnl_share_pct': top5_q_pnl_share if not np.isnan(top5_q_pnl_share) else -999.0,
            'rolling_4q_pos_pct': r4_pos_pct,
            'rolling_4q_pf12_pct': r4_pf12_pct,
            'overall_pf': float(summ['overall_pf']),
            'overall_wr_pct': float(summ['overall_wr_pct']),
            'net_pnl_usd': float(summ['total_pnl_usd']),
            'avg_expectancy_usd': float(summ['avg_expectancy_usd']),
            'long_trades': int(len(long_trades)),
            'long_pf': float(l_pf),
            'short_trades': int(len(short_trades)),
            'short_pf': float(s_pf),
            'gate_min_trades': gate_min_trades,
            'gate_max_share': gate_max_share,
            'gate_max_median': gate_max_median,
            'gate_gini': gate_gini,
            'gate_top3_pnl': gate_top3_pnl,
            'gate_top5_pnl': gate_top5_pnl,
            'gate_r4_pos': gate_r4_pos,
            'gate_r4_pf': gate_r4_pf,
            'gate_pf': gate_pf,
            'gate_expectancy': gate_expectancy,
            'all_precommitted_gates_pass': all_pass,
            'primary_failure_reason': fail_reason,
            'final_status': final_status
        })

    sum_df = pd.DataFrame(summary_rows)
    sum_csv_path = os.path.join(out_dir, "batch1_summary.csv")
    sum_df.to_csv(sum_csv_path, index=False)
    
    # Also save root temporal distribution summary
    root_summary_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "V3_3_TEMPORAL_DISTRIBUTION_SUMMARY.csv"))
    sum_df.to_csv(root_summary_path, index=False)
    print(f"Saved Batch-1 Summary CSV to: {sum_csv_path}")
    print(f"Saved Root Summary CSV to: {root_summary_path}")
    return sum_df

if __name__ == '__main__':
    run_batch1_discovery()
