"""
EXPERIMENTS H-204 TO H-208: M30 DISTRIBUTED EDGE DISCOVERY (REPAIRED V3.2.1)
=============================================================================
Executes precommitted hypotheses on Gold M30 (2018Q2 to 2026Q2, 33 complete quarters)
using the CORRECT distance interface for sl_dists and tp_dists:
- H-204: Light Trend Squeeze (EMA 20 vs EMA 50)
- H-205: Volatility Ratio Contraction Breakout (ATR14 / ATR50 <= 0.80)
- H-206: Normalized Range Compression (Range <= 0.65 * ATR14)
- H-207: Session-Aware Squeeze (London/NY 07:00-17:00 UTC)
- H-208A: Long-Only Squeeze + Bull Trend
- H-208B: Short-Only Squeeze + Bear Trend
- H-208C: Asymmetric Squeeze (Long RR=2.0, Short RR=3.0)

Generates exact machine-readable outputs for quarters, years, rolling windows, and summary tables.
"""

import os
import sys
import numpy as np
import pandas as pd
from deep_quant_engine import DeepQuantEngine, STANDARD_SPECS

sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None

def gini(x):
    mad = np.abs(np.subtract.outer(x, x)).mean()
    rmad = mad / np.mean(x) if np.mean(x) > 0 else 0
    return 0.5 * rmad

# -------------------------------------------------------------
# SIGNAL GENERATORS WITH REPAIRED DISTANCE INTERFACE
# -------------------------------------------------------------
def make_h204_signals(df):
    # H-204: Light Trend Squeeze (EMA 20 vs EMA 50)
    c, h, l = df['close'].values, df['high'].values, df['low'].values
    n = len(c)
    c_s = pd.Series(c)
    
    mid = c_s.rolling(20).mean().values
    std = c_s.rolling(20).std().values
    bb_u, bb_l = mid + 2.0 * std, mid - 2.0 * std
    
    tr = np.maximum(h - l, np.maximum(np.abs(h - np.roll(c, 1)), np.abs(l - np.roll(c, 1))))
    atr20 = pd.Series(tr).rolling(20).mean().values
    atr14 = pd.Series(tr).rolling(14).mean().values
    kelt_mid = c_s.ewm(span=20, adjust=False).mean().values
    kelt_u, kelt_l = kelt_mid + 1.2 * atr20, kelt_mid - 1.2 * atr20
    
    is_sqz = (bb_u < kelt_u) & (bb_l > kelt_l)
    was_sqz = (pd.Series(is_sqz.astype(int)).rolling(3).sum().shift(1).values >= 2)
    
    ema20 = c_s.ewm(span=20, adjust=False).mean().values
    ema50 = c_s.ewm(span=50, adjust=False).mean().values
    bull = (ema20 > ema50) & (c > ema20)
    bear = (ema20 < ema50) & (c < ema20)
    
    sig = np.zeros(n, dtype=int)
    sl_dists = np.zeros(n, dtype=float)
    tp_dists = np.zeros(n, dtype=float)
    
    for i in range(50, n):
        cur_atr = max(atr14[i], 0.50)
        if was_sqz[i] and bull[i] and c[i] > bb_u[i]:
            sig[i] = 1
            sl_dists[i] = 1.5 * cur_atr
            tp_dists[i] = 3.75 * cur_atr # 2.5 * SL
        elif was_sqz[i] and bear[i] and c[i] < bb_l[i]:
            sig[i] = -1
            sl_dists[i] = 1.5 * cur_atr
            tp_dists[i] = 3.75 * cur_atr # 2.5 * SL
    return sig, sl_dists, tp_dists

def make_h205_signals(df):
    # H-205: Volatility Ratio Contraction Breakout (ATR14 / ATR50 <= 0.80)
    c, h, l = df['close'].values, df['high'].values, df['low'].values
    n = len(c)
    c_s = pd.Series(c)
    
    tr = np.maximum(h - l, np.maximum(np.abs(h - np.roll(c, 1)), np.abs(l - np.roll(c, 1))))
    atr14 = pd.Series(tr).rolling(14).mean().values
    atr50 = pd.Series(tr).rolling(50).mean().values
    is_contracted = (atr14 / (atr50 + 1e-9) <= 0.80)
    was_contracted = (pd.Series(is_contracted.astype(int)).rolling(3).sum().shift(1).values >= 2)
    
    donch10_h = pd.Series(h).rolling(10).max().shift(1).values
    donch10_l = pd.Series(l).rolling(10).min().shift(1).values
    
    ema50 = c_s.ewm(span=50, adjust=False).mean().values
    bull = (c > ema50)
    bear = (c < ema50)
    
    sig = np.zeros(n, dtype=int)
    sl_dists = np.zeros(n, dtype=float)
    tp_dists = np.zeros(n, dtype=float)
    
    for i in range(50, n):
        cur_atr = max(atr14[i], 0.50)
        if was_contracted[i] and bull[i] and c[i] > donch10_h[i]:
            sig[i] = 1
            sl_dists[i] = 1.5 * cur_atr
            tp_dists[i] = 3.75 * cur_atr
        elif was_contracted[i] and bear[i] and c[i] < donch10_l[i]:
            sig[i] = -1
            sl_dists[i] = 1.5 * cur_atr
            tp_dists[i] = 3.75 * cur_atr
    return sig, sl_dists, tp_dists

def make_h206_signals(df):
    # H-206: Normalized Range Compression (Range <= 0.65 * ATR14)
    c, h, l = df['close'].values, df['high'].values, df['low'].values
    n = len(c)
    c_s = pd.Series(c)
    
    tr = np.maximum(h - l, np.maximum(np.abs(h - np.roll(c, 1)), np.abs(l - np.roll(c, 1))))
    atr14 = pd.Series(tr).rolling(14).mean().values
    is_comp = ((h - l) <= 0.65 * atr14)
    was_comp = (pd.Series(is_comp.astype(int)).rolling(2).sum().shift(1).values >= 2)
    
    h3 = pd.Series(h).rolling(3).max().shift(1).values
    l3 = pd.Series(l).rolling(3).min().shift(1).values
    
    ema50 = c_s.ewm(span=50, adjust=False).mean().values
    bull = (c > ema50) & (ema50 > pd.Series(ema50).shift(3).values)
    bear = (c < ema50) & (ema50 < pd.Series(ema50).shift(3).values)
    
    sig = np.zeros(n, dtype=int)
    sl_dists = np.zeros(n, dtype=float)
    tp_dists = np.zeros(n, dtype=float)
    
    for i in range(50, n):
        cur_atr = max(atr14[i], 0.50)
        if was_comp[i] and bull[i] and c[i] > h3[i]:
            sig[i] = 1
            sl_dists[i] = 1.5 * cur_atr
            tp_dists[i] = 3.75 * cur_atr
        elif was_comp[i] and bear[i] and c[i] < l3[i]:
            sig[i] = -1
            sl_dists[i] = 1.5 * cur_atr
            tp_dists[i] = 3.75 * cur_atr
    return sig, sl_dists, tp_dists

def make_h207_signals(df):
    # H-207: Session-Aware Squeeze Breakout (London/NY 07:00-17:00 UTC)
    c, h, l = df['close'].values, df['high'].values, df['low'].values
    n = len(c)
    c_s = pd.Series(c)
    dt = pd.to_datetime(df['datetime_str'] if 'datetime_str' in df.columns else df['dt'])
    hour = dt.dt.hour.values
    
    mid = c_s.rolling(20).mean().values
    std = c_s.rolling(20).std().values
    bb_u, bb_l = mid + 2.0 * std, mid - 2.0 * std
    
    tr = np.maximum(h - l, np.maximum(np.abs(h - np.roll(c, 1)), np.abs(l - np.roll(c, 1))))
    atr20 = pd.Series(tr).rolling(20).mean().values
    atr14 = pd.Series(tr).rolling(14).mean().values
    kelt_mid = c_s.ewm(span=20, adjust=False).mean().values
    kelt_u, kelt_l = kelt_mid + 1.2 * atr20, kelt_mid - 1.2 * atr20
    
    is_sqz = (bb_u < kelt_u) & (bb_l > kelt_l)
    was_sqz = (pd.Series(is_sqz.astype(int)).rolling(3).sum().shift(1).values >= 2)
    
    ema50 = c_s.ewm(span=50, adjust=False).mean().values
    bull = (c > ema50)
    bear = (c < ema50)
    in_session = (hour >= 7) & (hour <= 17)
    
    sig = np.zeros(n, dtype=int)
    sl_dists = np.zeros(n, dtype=float)
    tp_dists = np.zeros(n, dtype=float)
    
    for i in range(50, n):
        cur_atr = max(atr14[i], 0.50)
        if was_sqz[i] and in_session[i] and bull[i] and c[i] > bb_u[i]:
            sig[i] = 1
            sl_dists[i] = 1.5 * cur_atr
            tp_dists[i] = 3.75 * cur_atr
        elif was_sqz[i] and in_session[i] and bear[i] and c[i] < bb_l[i]:
            sig[i] = -1
            sl_dists[i] = 1.5 * cur_atr
            tp_dists[i] = 3.75 * cur_atr
    return sig, sl_dists, tp_dists

def make_h208a_signals(df):
    # H-208A: Long-Only Squeeze + Bull Trend
    sig, sl, tp = make_h204_signals(df)
    sig[sig == -1] = 0
    return sig, sl, tp

def make_h208b_signals(df):
    # H-208B: Short-Only Squeeze + Bear Trend
    sig, sl, tp = make_h204_signals(df)
    sig[sig == 1] = 0
    return sig, sl, tp

def make_h208c_signals(df):
    # H-208C: Asymmetric Squeeze (Long RR=2.0, Short RR=3.0)
    c, h, l = df['close'].values, df['high'].values, df['low'].values
    n = len(c)
    c_s = pd.Series(c)
    
    mid = c_s.rolling(20).mean().values
    std = c_s.rolling(20).std().values
    bb_u, bb_l = mid + 2.0 * std, mid - 2.0 * std
    
    tr = np.maximum(h - l, np.maximum(np.abs(h - np.roll(c, 1)), np.abs(l - np.roll(c, 1))))
    atr20 = pd.Series(tr).rolling(20).mean().values
    atr14 = pd.Series(tr).rolling(14).mean().values
    kelt_mid = c_s.ewm(span=20, adjust=False).mean().values
    kelt_u, kelt_l = kelt_mid + 1.2 * atr20, kelt_mid - 1.2 * atr20
    
    is_sqz = (bb_u < kelt_u) & (bb_l > kelt_l)
    was_sqz = (pd.Series(is_sqz.astype(int)).rolling(3).sum().shift(1).values >= 2)
    
    ema50 = c_s.ewm(span=50, adjust=False).mean().values
    bull = (c > ema50) & (ema50 > pd.Series(ema50).shift(3).values)
    bear = (c < ema50) & (ema50 < pd.Series(ema50).shift(3).values)
    
    sig = np.zeros(n, dtype=int)
    sl_dists = np.zeros(n, dtype=float)
    tp_dists = np.zeros(n, dtype=float)
    
    for i in range(50, n):
        cur_atr = max(atr14[i], 0.50)
        if was_sqz[i] and bull[i] and c[i] > bb_u[i]:
            sig[i] = 1
            sl_dists[i] = 1.5 * cur_atr
            tp_dists[i] = 3.0 * cur_atr # 2.0 * SL
        elif was_sqz[i] and bear[i] and c[i] < bb_l[i]:
            sig[i] = -1
            sl_dists[i] = 1.5 * cur_atr
            tp_dists[i] = 4.5 * cur_atr # 3.0 * SL
    return sig, sl_dists, tp_dists

def run_all_m30_experiments():
    print("=" * 95)
    print("🚀 EXECUTING EXPERIMENTS H-204 TO H-208 ON GOLD M30 (REPAIRED V3.2.1 DISTANCE INTERFACE)")
    print("=" * 95)
    
    eng = DeepQuantEngine("GOLD_M30.csv")
    
    hypotheses = [
        ("H-204", "Light Trend Squeeze (EMA 20/50)", make_h204_signals),
        ("H-205", "Volatility Ratio Contraction", make_h205_signals),
        ("H-206", "Range Compression (0.65*ATR)", make_h206_signals),
        ("H-207", "Session-Aware Squeeze (07-17 UTC)", make_h207_signals),
        ("H-208A", "Long-Only Squeeze", make_h208a_signals),
        ("H-208B", "Short-Only Squeeze", make_h208b_signals),
        ("H-208C", "Asymmetric Squeeze (Long RR=2, Short RR=3)", make_h208c_signals)
    ]
    
    out_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "reports", "v3_2"))
    os.makedirs(out_dir, exist_ok=True)
    
    summary_records = []
    
    for h_id, desc, s_fn in hypotheses:
        tdf, qdf, summ = eng.run_strategy(s_fn, spread_pips=25.0, commission_per_lot=7.0, fixed_lot=0.10)
        
        # Complete quarters 2018Q2 to 2026Q2 = 33 complete quarters
        comp_q = qdf[(qdf['quarter'] >= '2018Q2') & (qdf['quarter'] <= '2026Q2')].copy().reset_index(drop=True)
        trades_arr = comp_q['trades'].values
        n_q = len(comp_q)
        tot_tr = np.sum(trades_arr)
        
        min_tr = int(np.min(trades_arr)) if n_q > 0 else 0
        med_tr = float(np.median(trades_arr)) if n_q > 0 else 0.0
        max_tr = int(np.max(trades_arr)) if n_q > 0 else 0
        max_share = (max_tr / tot_tr * 100.0) if tot_tr > 0 else 0.0
        max_med_ratio = (max_tr / med_tr) if med_tr > 0 else 999.0
        t_gini = gini(trades_arr)
        zero_q = int(np.sum(trades_arr == 0))
        
        # Annual analysis (2019 to 2025 = 7 full calendar years)
        comp_y = comp_q.groupby('year').agg({'trades': 'sum', 'net_pnl_usd': 'sum', 'gross_profit_usd': 'sum', 'gross_loss_usd': 'sum'}).reset_index()
        full_years = comp_y[(comp_y['year'] >= 2019) & (comp_y['year'] <= 2025)].copy()
        n_fy = len(full_years)
        fy_ge_20 = int(np.sum(full_years['trades'] >= 20))
        fy_pos = int(np.sum(full_years['net_pnl_usd'] > 0))
        pct_pos_years = (fy_pos / n_fy * 100.0) if n_fy > 0 else 0.0
        
        # Rolling 4Q and 8Q
        r4_pos, r4_pf12 = [], []
        for i in range(n_q - 3):
            sub = comp_q.iloc[i:i+4]
            pnl = sub['net_pnl_usd'].sum()
            gp = sub['gross_profit_usd'].sum()
            gl = sub['gross_loss_usd'].sum()
            pf = gp / gl if gl > 0 else (999.0 if gp > 0 else 0.0)
            r4_pos.append(pnl > 0)
            r4_pf12.append(pf >= 1.20)
            
        r8_pos, r8_pf12 = [], []
        for i in range(n_q - 7):
            sub = comp_q.iloc[i:i+8]
            pnl = sub['net_pnl_usd'].sum()
            gp = sub['gross_profit_usd'].sum()
            gl = sub['gross_loss_usd'].sum()
            pf = gp / gl if gl > 0 else (999.0 if gp > 0 else 0.0)
            r8_pos.append(pnl > 0)
            r8_pf12.append(pf >= 1.20)
            
        r4_pos_pct = np.mean(r4_pos) * 100.0 if len(r4_pos) > 0 else 0.0
        r4_pf12_pct = np.mean(r4_pf12) * 100.0 if len(r4_pf12) > 0 else 0.0
        r8_pos_pct = np.mean(r8_pos) * 100.0 if len(r8_pos) > 0 else 0.0
        r8_pf12_pct = np.mean(r8_pf12) * 100.0 if len(r8_pf12) > 0 else 0.0
        
        # Profit concentration
        sorted_q_pnl = np.sort(comp_q['net_pnl_usd'].values)[::-1]
        tot_pnl = comp_q['net_pnl_usd'].sum()
        top1_q_pct = (sorted_q_pnl[0] / tot_pnl * 100.0) if tot_pnl > 0 else 0.0
        top3_q_pct = (np.sum(sorted_q_pnl[:3]) / tot_pnl * 100.0) if tot_pnl > 0 else 0.0
        top5_q_pct = (np.sum(sorted_q_pnl[:5]) / tot_pnl * 100.0) if tot_pnl > 0 else 0.0
        
        # 100 pips spread stress
        _, _, sum_stress = eng.run_strategy(s_fn, spread_pips=100.0, commission_per_lot=7.0, fixed_lot=0.10)
        
        # Verdict logic
        all_gates_pass = (
            min_tr >= 5 and
            max_share <= 5.0 and
            max_med_ratio <= 3.0 and
            pct_pos_years >= 70.0 and
            r4_pos_pct >= 70.0 and
            r4_pf12_pct >= 65.0 and
            r8_pos_pct >= 75.0 and
            r8_pf12_pct >= 70.0 and
            top3_q_pct <= 40.0 and
            summ['overall_pf'] >= 1.25 and
            summ['total_pnl_usd'] > 0
        )
        
        classification = 'DISTRIBUTED SURVIVOR' if all_gates_pass else 'REJECTED'
        
        summary_records.append({
            'Hypothesis': h_id,
            'Description': desc,
            'Total Trades': tot_tr,
            'Min Trades/Q': min_tr,
            'Median Trades/Q': med_tr,
            'Max Trades/Q': max_tr,
            'Max Q Share (%)': f"{max_share:.1f}%",
            'Max/Med Ratio': f"{max_med_ratio:.2f}",
            'Trade Gini': f"{t_gini:.3f}",
            'Zero-Trade Qs': zero_q,
            'Years >=20tr': f"{fy_ge_20}/{n_fy}",
            'Profitable Years': f"{pct_pos_years:.1f}%",
            'Rolling 4Q Pos': f"{r4_pos_pct:.1f}%",
            'Rolling 4Q PF>=1.2': f"{r4_pf12_pct:.1f}%",
            'Rolling 8Q Pos': f"{r8_pos_pct:.1f}%",
            'Rolling 8Q PF>=1.2': f"{r8_pf12_pct:.1f}%",
            'Top 1/3/5 Q PnL': f"{top1_q_pct:.1f}% / {top3_q_pct:.1f}% / {top5_q_pct:.1f}%",
            'Net PnL ($)': f"${summ['total_pnl_usd']:+,.2f}",
            'Profit Factor': f"{summ['overall_pf']:.3f}",
            'Win Rate': f"{summ['overall_wr_pct']:.1f}%",
            'Expectancy (R)': f"{summ['avg_expectancy_r']:+.3f} R",
            '100-Pip Stress PF': f"{sum_stress['overall_pf']:.3f}",
            'V3.2.1 Classification': classification
        })
        
        # Save detailed CSV files for each hypothesis
        comp_q.to_csv(os.path.join(out_dir, f"{h_id.lower()}_quarters.csv"), index=False)
        comp_y.to_csv(os.path.join(out_dir, f"{h_id.lower()}_years.csv"), index=False)
        
        # Rolling windows table
        r_df = pd.DataFrame({
            'window_4q': [f"{comp_q.iloc[i]['quarter']}->{comp_q.iloc[i+3]['quarter']}" for i in range(n_q - 3)],
            'r4_pos': r4_pos,
            'r4_pf12': r4_pf12
        })
        r_df.to_csv(os.path.join(out_dir, f"{h_id.lower()}_rolling.csv"), index=False)
        
    sum_df = pd.DataFrame(summary_records)
    print("\n--- V3.2.1 REPAIRED M30 DISCOVERY SUMMARY MATRIX ---")
    print(sum_df[['Hypothesis', 'Total Trades', 'Min Trades/Q', 'Max/Med Ratio', 'Trade Gini', 'Rolling 4Q Pos', 'Rolling 4Q PF>=1.2', 'Profit Factor', 'Win Rate', 'V3.2.1 Classification']].to_string(index=False))
    
    sum_csv = os.path.join(out_dir, "h204_to_h208_summary.csv")
    sum_df.to_csv(sum_csv, index=False)
    print(f"\nSaved repaired summary to {sum_csv}")
    return sum_df

if __name__ == '__main__':
    run_all_m30_experiments()
