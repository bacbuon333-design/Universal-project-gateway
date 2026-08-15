"""
DEEP MARKET MECHANICS AUDIT & QUANTITATIVE STRATEGY BENCHMARK TOURNAMENT
========================================================================
1. Implements 4 Famous Quantitative Strategies:
   - Strategy A: Supertrend ATR Momentum (10, 3.0)
   - Strategy B: Keltner Channel Volatility Squeeze (20, 2.0 / 1.5)
   - Strategy C: VWAP Deviation Band Mean-Reversion (20, 2.0-std)
   - Strategy D: Order Block + Fair Value Gap (FVG) Liquidity Sweep

2. Implements Deep Market Mechanics Code:
   - Volatility Compression-Expansion Cycle Analysis
   - Order Flow / Tick Volume Imbalance Mechanics
   - Asymmetric Tail Risk & Return Skewness Audit

3. Benchmarks all 4 external strategies against CP1, CP3, CP5, CP7, CP8 over 16.57 Years of Gold H1 data.
"""

import os, sys
sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None
import numpy as np
import pandas as pd
from scipy.stats import skew, kurtosis

BASE_DIR = r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05\AlphaLab_Antigravity"
DATA_PATH = os.path.join(BASE_DIR, "data", "GOLD_H1_2010_2026.csv")

PIP = 0.01
PTVAL = 0.01

def load_data():
    df = pd.read_csv(DATA_PATH)
    col = 'datetime_str' if 'datetime_str' in df.columns else df.columns[0]
    df['dt'] = pd.to_datetime(df[col])
    df['year'] = df['dt'].dt.year
    df.sort_values('dt', inplace=True)
    df.reset_index(drop=True, inplace=True)
    return df

# -------------------------------------------------------------
# 1. EXTERNAL POPULAR QUANT STRATEGIES IMPLEMENTATION
# -------------------------------------------------------------
def run_supertrend_strategy(df, risk_pct=0.025):
    c = df['close'].values; h = df['high'].values; l = df['low'].values; o = df['open'].values
    n = len(df)
    
    tr = np.maximum(h[1:]-l[1:], np.maximum(abs(h[1:]-c[:-1]), abs(l[1:]-c[:-1])))
    tr = np.insert(tr, 0, tr[0])
    atr10 = pd.Series(tr).rolling(10).mean().bfill().values
    
    st = np.zeros(n); st_dir = np.ones(n, dtype=int)
    for i in range(1, n):
        hl2 = (h[i] + l[i]) / 2.0
        up = hl2 + 3.0 * atr10[i]
        dn = hl2 - 3.0 * atr10[i]
        
        if c[i-1] > st[i-1]: dn = max(dn, st[i-1])
        if c[i-1] < st[i-1]: up = min(up, st[i-1])
        
        if c[i] > up: st_dir[i] = 1; st[i] = dn
        elif c[i] < dn: st_dir[i] = -1; st[i] = up
        else:
            st_dir[i] = st_dir[i-1]
            st[i] = dn if st_dir[i] == 1 else up

    buy_sig = (st_dir == 1) & (np.roll(st_dir, 1) == -1)
    sell_sig = (st_dir == -1) & (np.roll(st_dir, 1) == 1)
    
    return simulate_backtest(df, buy_sig, sell_sig, sl_mult=1.5, tp_mult=3.0, risk_pct=risk_pct)

def run_keltner_squeeze_strategy(df, risk_pct=0.025):
    c = df['close'].values; h = df['high'].values; l = df['low'].values; o = df['open'].values
    n = len(df)
    
    tr = np.maximum(h[1:]-l[1:], np.maximum(abs(h[1:]-c[:-1]), abs(l[1:]-c[:-1])))
    tr = np.insert(tr, 0, tr[0])
    atr20 = pd.Series(tr).rolling(20).mean().bfill().values
    
    mid20 = pd.Series(c).rolling(20).mean().bfill().values
    std20 = pd.Series(c).rolling(20).std().bfill().values
    bb_up = mid20 + 2.0 * std20
    bb_dn = mid20 - 2.0 * std20
    
    kc_up = mid20 + 1.5 * atr20
    kc_dn = mid20 - 1.5 * atr20
    
    squeeze = (bb_up <= kc_up) & (bb_dn >= kc_dn)
    squeeze_release = (np.roll(squeeze, 1) == True) & (squeeze == False)
    
    buy_sig = squeeze_release & (c > kc_up)
    sell_sig = squeeze_release & (c < kc_dn)
    
    return simulate_backtest(df, buy_sig, sell_sig, sl_mult=1.5, tp_mult=3.0, risk_pct=risk_pct)

def run_vwap_mean_reversion_strategy(df, risk_pct=0.025):
    c = df['close'].values; h = df['high'].values; l = df['low'].values; o = df['open'].values
    v = df['tick_volume'].values if 'tick_volume' in df.columns else df['vol'].values
    n = len(df)
    
    pv = c * v
    vwap = pd.Series(pv).rolling(24).sum() / (pd.Series(v).rolling(24).sum() + 1e-9)
    vwap_std = pd.Series(c).rolling(24).std().bfill().values
    
    vwap_up = vwap.values + 2.0 * vwap_std
    vwap_dn = vwap.values - 2.0 * vwap_std
    
    lwick = np.minimum(o, c) - l
    uwick = h - np.maximum(o, c)
    body  = np.abs(c - o) + 1e-9
    
    buy_sig = (l <= vwap_dn) & (lwick >= 1.2 * body) & (c > o)
    sell_sig = (h >= vwap_up) & (uwick >= 1.2 * body) & (c < o)
    
    return simulate_backtest(df, buy_sig, sell_sig, sl_mult=1.5, tp_mult=3.0, risk_pct=risk_pct)

def run_fvg_order_block_strategy(df, risk_pct=0.025):
    c = df['close'].values; h = df['high'].values; l = df['low'].values; o = df['open'].values
    n = len(df)
    
    bull_fvg = (l[2:] > h[:-2])
    bear_fvg = (h[2:] < l[:-2])
    
    bull_fvg = np.insert(bull_fvg, [0, 0], False)
    bear_fvg = np.insert(bear_fvg, [0, 0], False)
    
    ema200 = pd.Series(c).ewm(span=200, adjust=False).mean().values
    
    buy_sig = bull_fvg & (c > ema200)
    sell_sig = bear_fvg & (c < ema200)
    
    return simulate_backtest(df, buy_sig, sell_sig, sl_mult=1.5, tp_mult=3.0, risk_pct=risk_pct)

# -------------------------------------------------------------
# SIMULATOR ENGINE (Standardized Broker Costs & Sizing)
# -------------------------------------------------------------
def simulate_backtest(df, buy_sig, sell_sig, sl_mult=1.5, tp_mult=3.0, risk_pct=0.025):
    c = df['close'].values; h = df['high'].values; l = df['low'].values; o = df['open'].values
    n = len(df)
    
    tr = np.maximum(h[1:]-l[1:], np.maximum(abs(h[1:]-c[:-1]), abs(l[1:]-c[:-1])))
    tr = np.insert(tr, 0, tr[0])
    atr14 = pd.Series(tr).rolling(14).mean().bfill().values
    
    years = sorted(df['year'].unique())
    total_cash = 0; winning_years = 0; total_trades_all = 0
    annual_pnl = {}
    
    for yr in years:
        sub = df[df['year'] == yr]
        idx_sub = sub.index.values
        if len(idx_sub) < 100: continue
        
        bal = 1000.0; pk = 1000.0; max_dd = 0.0
        last_trade = -9999; cooldown = 16
        pos_dir = 0; pos_en = 0.0; pos_sl = 0.0; pos_tp = 0.0; pos_lot = 0.0
        trades = []
        
        for idx in idx_sub:
            i = idx
            if i >= n-1: continue
            if pos_dir != 0:
                done = False; ep = c[i]
                if pos_dir == 1:
                    if l[i] <= pos_sl: ep = pos_sl - 5.0 * PIP; done = True
                    elif h[i] >= pos_tp: ep = pos_tp; done = True
                else:
                    if h[i] >= pos_sl: ep = pos_sl + 5.0 * PIP; done = True
                    elif l[i] <= pos_tp: ep = pos_tp; done = True
                if done:
                    pts = (ep - pos_en)/PIP if pos_dir==1 else (pos_en - ep)/PIP
                    net = pts * PTVAL * (pos_lot / 0.01) - (pos_lot / 0.01) * 0.37
                    bal = max(0.0, bal + net)
                    trades.append(net)
                    pos_dir = 0
                    
            if pos_dir == 0 and (i - last_trade >= cooldown) and bal > 0:
                sig = 0
                if buy_sig[i]: sig = 1
                elif sell_sig[i]: sig = -1
                if sig != 0:
                    av = max(atr14[i], 1.5); sp = 25.0
                    sl_pts = (av * sl_mult / PIP) + sp
                    tp_pts = (av * tp_mult / PIP)
                    risk_amt = bal * risk_pct
                    lot = max(0.01, min(round(risk_amt / (sl_pts * 0.01) * 0.01, 2), 20.0))
                    next_o = o[i+1]; half_sp = (sp * PIP) / 2.0
                    if sig == 1: pos_dir = 1; pos_en = next_o + half_sp; pos_sl = pos_en - sl_pts * PIP; pos_tp = pos_en + tp_pts * PIP; pos_lot = lot
                    else: pos_dir = -1; pos_en = next_o - half_sp; pos_sl = pos_en + sl_pts * PIP; pos_tp = pos_en - tp_pts * PIP; pos_lot = lot
                    last_trade = i
                    
        pnl_pct = (bal - 1000.0) / 10.0
        annual_pnl[yr] = pnl_pct
        total_cash += bal
        total_trades_all += len(trades)
        if pnl_pct > 0: winning_years += 1
        
    return {
        'winning_years': winning_years, 'total_years': len(annual_pnl),
        'cumulative_cash': total_cash, 'total_trades': total_trades_all,
        'annual_pnl': annual_pnl
    }

# -------------------------------------------------------------
# 2. MARKET MECHANICS DEEP AUDIT CODE
# -------------------------------------------------------------
def analyze_market_mechanics(df):
    c = df['close'].values; h = df['high'].values; l = df['low'].values; o = df['open'].values
    v = df['tick_volume'].values if 'tick_volume' in df.columns else df['vol'].values
    
    log_rets = np.diff(np.log(c))
    
    ret_skew = skew(log_rets)
    ret_kurt = kurtosis(log_rets)
    
    tr = np.maximum(h[1:]-l[1:], np.maximum(abs(h[1:]-c[:-1]), abs(l[1:]-c[:-1])))
    tr = np.insert(tr, 0, tr[0])
    atr14 = pd.Series(tr).rolling(14).mean().bfill().values
    atr100 = pd.Series(tr).rolling(100).mean().bfill().values
    vol_ratio = atr14 / (atr100 + 1e-9)
    
    squeeze_count = np.sum(vol_ratio < 0.8)
    expansion_count = np.sum(vol_ratio > 1.2)
    
    vol_mean = pd.Series(v).rolling(50).mean().bfill().values
    vol_std = pd.Series(v).rolling(50).std().bfill().values + 1e-9
    vol_z = (v - vol_mean) / vol_std
    
    high_vol_spikes = np.sum(vol_z > 2.0)
    
    print("="*95)
    print("DEEP MARKET MECHANICS & RETURN DISTRIBUTION AUDIT (XAUUSD H1)")
    print("="*95)
    print(f"Total Log Return Skewness (Độ lệch vệt) : {ret_skew:+.4f} (Chỉ ra Thiên vị Mua lệch Phải)")
    print(f"Total Return Kurtosis (Độ nhọn đuôi rủi ro): {ret_kurt:+.4f} (Fat Tails - Biến động đuôi dày)")
    print(f"Chu kỳ Nén biến động (Vol Compression) : {squeeze_count:,} nến ({squeeze_count/len(df)*100:.1f}%)")
    print(f"Chu kỳ Bùng nổ biến động (Vol Expansion): {expansion_count:,} nến ({expansion_count/len(df)*100:.1f}%)")
    print(f"Cú bứt phá Khối lượng Tick Vol Spike (>2σ): {high_vol_spikes:,} nến ({high_vol_spikes/len(df)*100:.1f}%)")

# -------------------------------------------------------------
# MAIN TOURNAMENT RUNNER
# -------------------------------------------------------------
def main():
    df = load_data()
    analyze_market_mechanics(df)
    
    print("\n" + "="*115)
    print("MASTER STRATEGY TOURNAMENT & CRITIQUE: 4 EXTERNAL QUANT STRATEGIES VS ALAB CHECKPOINTS")
    print("Dataset: XAUUSD H1 (16.57 Years) | Fresh $1,000 Capital Every Year | Risk 2.5% per Trade")
    print("="*115)
    print(f"{'Strategy Name / Architecture':<42} | {'Win Years':<12} | {'Cumulative Cash ($)':<22} | {'Status':<8}")
    print("-" * 115)
    
    st_res = run_supertrend_strategy(df)
    kc_res = run_keltner_squeeze_strategy(df)
    vw_res = run_vwap_mean_reversion_strategy(df)
    ob_res = run_fvg_order_block_strategy(df)
    
    ext_strats = [
        ('Strategy A: Supertrend ATR Momentum (10, 3.0)', st_res),
        ('Strategy B: Keltner Volatility Squeeze', kc_res),
        ('Strategy C: VWAP Deviation Band Mean-Reversion', vw_res),
        ('Strategy D: Order Block + Fair Value Gap (FVG)', ob_res)
    ]
    
    for name, r in ext_strats:
        w_str = f"{r['winning_years']} / {r['total_years']} ({r['winning_years']/r['total_years']*100:.0f}%)"
        s = "✅" if r['winning_years'] >= 8 else "❌"
        print(f"{name:<42} | {w_str:<12} | ${r['cumulative_cash']:<21,.2f} | {s:<8}")

    print("-" * 115)
    print("ALAB INTERNAL CHECKPOINTS (BENCHMARK BASELINES):")
    
    sys.path.append(os.path.join(BASE_DIR, 'checkpoints'))
    from checkpoint_v1_davidd_ultimate_scalping_h1 import run_v1_single_year as run_v1
    from checkpoint_v3_anti_overfitting_dsr import run_checkpoint_v3_prop_firm as run_v3
    from checkpoint_v5_reaction_zone_sweep import run_v5_single_year as run_v5
    from checkpoint_v7_cp1_high_yield_optimization import run_v7_refined as run_v7
    from checkpoint_v8_early_reversal_indicator_engine import run_checkpoint_v8_reversal as run_v8
    
    years = sorted(df['year'].unique())
    
    def eval_internal(func, name, risk=0.025):
        w = 0; tot = 0; cash = 0
        for yr in years:
            df_yr = df[df['year'] == yr]
            r = func(df_yr, risk_pct=risk) if 'risk_pct' in func.__code__.co_varnames else func(df_yr)
            if r is None: continue
            tot += 1
            if r['pnl_pct'] > 0: w += 1
            cash += r['bal']
        w_str = f"{w} / {tot} ({w/tot*100:.0f}%)"
        s = "✅" if w >= 8 else "❌"
        print(f"{name:<42} | {w_str:<12} | ${cash:<21,.2f} | {s:<8}")

    eval_internal(run_v1, "ALAB CP1: Davidd Baseline Gốc (1:2 RR)", 0.025)
    eval_internal(run_v3, "ALAB CP3: Prop-Firm VaR Model (MaxDD < 9.9%)", 0.025)
    eval_internal(run_v5, "ALAB CP5: Key Structure Reaction Zone Sweep", 0.025)
    eval_internal(run_v7, "ALAB CP7: Advanced High-Yield Optimization", 0.025)
    eval_internal(run_v8, "ALAB CP8: Early Reversal Indicator Engine", 0.025)

if __name__ == '__main__':
    main()
