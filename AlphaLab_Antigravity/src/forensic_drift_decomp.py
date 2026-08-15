"""
Stage 1 — Forensic Audit: v22 Drift and Exposure Decomposition
"""
import pandas as pd, numpy as np, os

df = pd.read_csv('data/GOLD_M15.csv')
df['dt'] = pd.to_datetime(df['datetime_str'])
df.set_index('dt', inplace=True)
c = df['close'].values

v22 = {
    '2022-2023': {'pnl_pct': 29.0, 'pf': 1.536, 'maxdd': 14.05, 'trades': 20, 'wr': 55.0},
    '2023-2024': {'pnl_pct': 1.5,  'pf': 1.026, 'maxdd': 14.35, 'trades': 26, 'wr': 46.2},
    '2024-2025': {'pnl_pct': 96.2, 'pf': 2.051, 'maxdd': 13.46, 'trades': 36, 'wr': 58.3},
    '2025-2026': {'pnl_pct': 28.3, 'pf': 1.400, 'maxdd': 19.26, 'trades': 34, 'wr': 41.2},
}
drift = {
    '2022-2023': 5.23,
    '2023-2024': 14.82,
    '2024-2025': 43.69,
    '2025-2026': 23.60
}

# Estimate: avg holding 5 days per trade, trading year ~250 days
exposure = {yr: v22[yr]['trades'] * 5 / 250 * 100 for yr in v22}
drift_contrib = {yr: drift[yr] * exposure[yr] / 100 for yr in v22}
timing_alpha = {yr: v22[yr]['pnl_pct'] - drift_contrib[yr] for yr in v22}

print("=== v22 EXPOSURE AND DRIFT DECOMPOSITION ===")
for yr in v22:
    s = v22[yr]['pnl_pct']
    d = drift[yr]
    e = exposure[yr]
    dc = drift_contrib[yr]
    ta = timing_alpha[yr]
    md = v22[yr]['maxdd']
    print(f"{yr}: Strategy={s:+.1f}%  Drift={d:+.1f}%  Exposure~{e:.0f}%  DriftContrib~{dc:+.1f}%  TimingAlpha~{ta:+.1f}%  MaxDD={md:.1f}%")

total_strat = sum(v22[yr]['pnl_pct'] for yr in v22)
print(f"\nTotal 4-year sum of annual PnL%: {total_strat:+.1f}%")
print(f"2024-2025 contribution to total: {96.2/total_strat*100:.1f}%")

# v22 Parameter count
params_v22 = [
    'ema_span_8', 'ema_span_21', 'ema_span_50', 'ema_span_200',
    'atr_lookback_fast=14', 'atr_lookback_slow=240',
    'rsi_period=14', 'adx_period=14',
    'momentum_3m_lookback=1440', 'momentum_1m_lookback=480',
    'donchian_hi_period=20', 'pivot_lookback=100',
    'cooldown_bars=96', 'min_score=4',
    'zone_atr_multiplier=0.8',
    'parabolic_atr_ratio_threshold=1.4', 'parabolic_adx_threshold=28',
    'parabolic_di_threshold=10', 'parabolic_rsi_cap=72',
    'parabolic_rr_base=4.0', 'parabolic_rr_high=4.5',
    'pullback_adx_threshold=16', 'pullback_rsi_cap=68',
    'pullback_rr_low=2.5', 'pullback_rr_mid=3.0', 'pullback_rr_high=3.5',
    'sl_multiplier_parabolic=1.3', 'sl_multiplier_pullback=1.4',
    'trailing_activate_multiple=1.5', 'trailing_atr_distance=2.5',
    'risk_pct_base=0.055',
    'risk_scale_at_6pct_dd=0.68', 'risk_scale_at_10pct_dd=0.38',
    'risk_scale_at_15pct_dd=0.15',
    'conviction_mult_hi=1.3', 'conviction_mult_lo=0.8',
    'spread=25.0', 'commission=0.07',
]
print(f"\nTOTAL v22 TUNABLE PARAMETERS: {len(params_v22)}")

# Buy-and-hold comparison
print("\n=== BUY-AND-HOLD vs v22 ===")
windows = {
    '2022-2023': ('2022-05-02', '2023-05-01'),
    '2023-2024': ('2023-05-01', '2024-05-01'),
    '2024-2025': ('2024-05-01', '2025-05-01'),
    '2025-2026': ('2025-05-01', '2026-07-24')
}
for yr, (s, e) in windows.items():
    mask = (df.index >= s) & (df.index < e)
    sub = df[mask]
    if len(sub) > 0:
        bh = (sub['close'].iloc[-1] - sub['close'].iloc[0]) / sub['close'].iloc[0] * 100
        strat = v22[yr]['pnl_pct']
        edge = strat - bh
        print(f"{yr}: BuyHold={bh:+.1f}%  Strategy={strat:+.1f}%  Edge={edge:+.1f}%")
