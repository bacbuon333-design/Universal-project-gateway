"""
TOTAL DOLLAR PROFIT COMPARISON ($1,000 FRESH CAPITAL EVERY YEAR)
=================================================================
Calculates sum of ending balances, total net dollar profit ($),
and average profit per year if starting with fresh $1,000 capital
at the beginning of EACH of the 17 years (2010 - 2026).
"""
import os, sys
sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None
import numpy as np
import pandas as pd

BASE_DIR = r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05\AlphaLab_Antigravity"
sys.path.append(os.path.join(BASE_DIR, "checkpoints"))

from checkpoint_v1_davidd_ultimate_scalping_h1 import run_v1_single_year as run_v1
from checkpoint_v2_ultimate_scalping_upgraded import run_checkpoint_v2_year as run_v2

df = pd.read_csv(os.path.join(BASE_DIR, "data", "GOLD_H1_2010_2026.csv"))
df['dt'] = pd.to_datetime(df['datetime_str'])
df['year'] = df['dt'].dt.year
years = sorted(df['year'].unique())

v1_ending_balances = []
v1_dollar_pnls = []

v2_ending_balances = []
v2_dollar_pnls = []

print("="*95)
print("TOTAL DOLLAR PROFIT COMPARISON: FRESH $1,000 CAPITAL DEPOSITED EVERY YEAR")
print("Dataset: XAUUSD H1 (2010 - 2026, 17 Calendar Years)")
print("="*95)
print(f"{'Year':<6} | {'--- CP1 BASELINE ---':<28} | {'--- CP2 UPGRADED ---':<28} | {'Dollar Diff':<12}")
print(f"{'':<6} | {'End Bal':<10} {'Dollar PnL':<10} {'PnL %':<6} | {'End Bal':<10} {'Dollar PnL':<10} {'PnL %':<6} | {'CP2 vs CP1':<12}")
print("-" * 95)

for yr in years:
    df_yr = df[df['year'] == yr]
    r1 = run_v1(df_yr, risk_pct=0.03)
    r2 = run_v2(df_yr, risk_pct=0.025)
    if r1 is None or r2 is None: continue
    
    v1_bal = r1['bal']
    v1_pnl = r1['bal'] - 1000.0
    v1_pct = r1['pnl_pct']
    
    v2_bal = r2['bal']
    v2_pnl = r2['bal'] - 1000.0
    v2_pct = r2['pnl_pct']
    
    diff_pnl = v2_pnl - v1_pnl
    
    v1_ending_balances.append(v1_bal)
    v1_dollar_pnls.append(v1_pnl)
    
    v2_ending_balances.append(v2_bal)
    v2_dollar_pnls.append(v2_pnl)
    
    diff_str = f"${diff_pnl:>+8.2f}"
    
    print(f"{yr:<6} | ${v1_bal:<9.2f} ${v1_pnl:>+8.2f} {v1_pct:>+5.1f}% | ${v2_bal:<9.2f} ${v2_pnl:>+8.2f} {v2_pct:>+5.1f}% | {diff_str:<12}")

print("-" * 95)
v1_total_principal = len(v1_dollar_pnls) * 1000.0
v1_total_pnl = sum(v1_dollar_pnls)
v1_total_end = sum(v1_ending_balances)

v2_total_principal = len(v2_dollar_pnls) * 1000.0
v2_total_pnl = sum(v2_dollar_pnls)
v2_total_end = sum(v2_ending_balances)

print(f"\n📌 TOTAL PRINCIPAL DEPOSITED (17 Years x $1,000) : ${v1_total_principal:,.2f} USD")

print(f"\n🔴 --- CHECKPOINT 1 (BASELINE GỐC) ---")
print(f"Tổng số dư tài khoản thu về sau 17 năm     : ${v1_total_end:,.2f} USD")
print(f"Tổng Lợi Nhuận Ròng ($) kiếm được qua 17 năm : ${v1_total_pnl:+,.2f} USD")
print(f"Trung bình Lãi tiền mặt ($) mỗi năm         : ${v1_total_pnl/17:+,.2f} USD / năm")

print(f"\n🟢 --- CHECKPOINT 2 (CẢI TIẾN UPGRADED v2) ---")
print(f"Tổng số dư tài khoản thu về sau 17 năm     : ${v2_total_end:,.2f} USD")
print(f"Tổng Lợi Nhuận Ròng ($) kiếm được qua 17 năm : ${v2_total_pnl:+,.2f} USD")
print(f"Trung bình Lãi tiền mặt ($) mỗi năm         : ${v2_total_pnl/17:+,.2f} USD / năm")

print(f"\n🏆 === HIỆU SỐ TIỀN MẶT CẢI THIỆN CỦA CP2 VS CP1 ===")
print(f"CP2 kiếm THÊM tiền mặt ròng so với CP1      : ${v2_total_pnl - v1_total_pnl:+,.2f} USD")
