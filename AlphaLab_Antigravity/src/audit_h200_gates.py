"""
DETAILED AUDIT OF H-200 AGAINST ALL V3.1 HARD GATES
====================================================
Evaluates H-200 (M30 Squeeze+EMA50) across:
- Gate 12A: Min trades/Q >= 5 (33 complete quarters 2018Q2-2026Q2)
- Gate 12B: Full years >= 20 trades
- Gate 14: Trade concentration (Gini, Max/Med ratio, No quarter > 5%)
- Gate 15: Profit distribution (Top 1/3/5 quarter PnL)
- Gate 16: Rolling 4Q (>=70% pos, >=65% PF>=1.20) & Rolling 8Q (>=75% pos, >=70% PF>=1.20)
- Gate 17: Profitable calendar years (>=70%)
"""

import os
import sys
import numpy as np
import pandas as pd
from deep_quant_engine import DeepQuantEngine
from experiment_h200_to_h203_high_frequency import make_h200_signals, gini

sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None

eng = DeepQuantEngine("GOLD_M30.csv", pip_size=0.01, point_val=0.01)
tdf, qdf, summ = eng.run_strategy(make_h200_signals, spread_pips=25.0, commission_per_lot=7.0)

comp_q = qdf[(qdf['quarter'] >= '2018Q2') & (qdf['quarter'] <= '2026Q2')].copy().reset_index(drop=True)
trades_arr = comp_q['trades'].values
n_q = len(comp_q)
tot_tr = np.sum(trades_arr)

# Trade concentration
max_tr = np.max(trades_arr)
med_tr = np.median(trades_arr)
max_share_pct = max_tr / tot_tr * 100.0
max_to_med = max_tr / med_tr
t_gini = gini(trades_arr)

# Annual
comp_y = comp_q.groupby('year').agg({'trades': 'sum', 'net_pnl_usd': 'sum'}).reset_index()
full_years = comp_y[(comp_y['year'] >= 2019) & (comp_y['year'] <= 2025)].copy()
n_fy = len(full_years)
fy_ge_20 = np.sum(full_years['trades'] >= 20)
fy_pos = np.sum(full_years['net_pnl_usd'] > 0)

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

# Profit concentration
sorted_q_pnl = np.sort(comp_q['net_pnl_usd'].values)[::-1]
tot_pnl = comp_q['net_pnl_usd'].sum()
top1_q = sorted_q_pnl[0] / tot_pnl * 100.0
top3_q = np.sum(sorted_q_pnl[:3]) / tot_pnl * 100.0
top5_q = np.sum(sorted_q_pnl[:5]) / tot_pnl * 100.0

print(f"H-200 AUDIT RESULTS (33 Complete Quarters):")
print(f"  Total Trades        : {tot_tr}")
print(f"  Min Trades/Q        : {np.min(trades_arr)} (Gate 12A >= 5: {'PASS' if np.min(trades_arr)>=5 else 'FAIL'})")
print(f"  Max Single Q Share  : {max_share_pct:.1f}% (Gate 14 <= 5%: {'PASS' if max_share_pct<=5.0 else 'FAIL'})")
print(f"  Max/Med Ratio       : {max_to_med:.2f} (Gate 14 <= 3.0: {'PASS' if max_to_med<=3.0 else 'FAIL'})")
print(f"  Trade Gini          : {t_gini:.3f}")
print(f"  Full Years >= 20tr  : {fy_ge_20}/{n_fy} ({fy_ge_20/n_fy*100:.1f}%)")
print(f"  Full Years Pos PnL  : {fy_pos}/{n_fy} ({fy_pos/n_fy*100:.1f}% - Gate 17 >= 70%: {'PASS' if fy_pos/n_fy>=0.70 else 'FAIL'})")
print(f"  Rolling 4Q Pos PnL  : {np.mean(r4_pos)*100:.1f}% (Gate 16 >= 70%: {'PASS' if np.mean(r4_pos)>=0.70 else 'FAIL'})")
print(f"  Rolling 4Q PF>=1.20 : {np.mean(r4_pf12)*100:.1f}% (Gate 16 >= 65%: {'PASS' if np.mean(r4_pf12)>=0.65 else 'FAIL'})")
print(f"  Rolling 8Q Pos PnL  : {np.mean(r8_pos)*100:.1f}% (Gate 16 >= 75%: {'PASS' if np.mean(r8_pos)>=0.75 else 'FAIL'})")
print(f"  Rolling 8Q PF>=1.20 : {np.mean(r8_pf12)*100:.1f}% (Gate 16 >= 70%: {'PASS' if np.mean(r8_pf12)>=0.70 else 'FAIL'})")
print(f"  Top 1/3/5 Q PnL     : {top1_q:.1f}% / {top3_q:.1f}% / {top5_q:.1f}%")
