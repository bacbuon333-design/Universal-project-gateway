"""
DAVIDDTECH STRATEGY GAUNTLET — Python Backtest Engine
======================================================
Tests the 4 featured DaviddTech strategies from NotebookLM extract:
1. Triple SuperTrend & Volume (M15)
2. Ultimate Scalping EMA + MACD + RSI (M15 adaptation)
3. Gold Peak Momentum (M15 adaptation with ATR 3x SL, 1:1.3 R:R)
4. McDavidd (McGinley Dynamic + BB + Waddah Attar Explosion proxy)

All tests use REALISTIC BROKER EXECUTION:
- Entry at NEXT bar open
- Spread = 25 pips ($0.25/oz) base
- Commission = $0.07 / 0.01 lot ($7/lot)
- Slippage = 5 pips ($0.05/oz)
- Account floor at 0
"""

import os, sys
sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None
import numpy as np
import pandas as pd

BASE = r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05\AlphaLab_Antigravity"
DATA = os.path.join(BASE, "data", "GOLD_M15.csv")

df = pd.read_csv(DATA)
df['dt'] = pd.to_datetime(df['datetime_str'])
df.set_index('dt', inplace=True)
df.sort_index(inplace=True)

c = df['close'].values
h = df['high'].values
l = df['low'].values
o = df['open'].values
v = df['tick_volume'].values
n = len(df)

PIP = 0.01
PTVAL = 0.01
COMM = 0.07

# ── COMMON INDICATORS ────────────────────────────────────────────────────────
tr = np.maximum(h[1:]-l[1:], np.maximum(abs(h[1:]-c[:-1]), abs(l[1:]-c[:-1])))
tr = np.insert(tr, 0, tr[0])
atr10 = pd.Series(tr).rolling(10).mean().bfill().values
atr11 = pd.Series(tr).rolling(11).mean().bfill().values
atr12 = pd.Series(tr).rolling(12).mean().bfill().values
atr14 = pd.Series(tr).rolling(14).mean().bfill().values

ema9   = pd.Series(c).ewm(span=9,   adjust=False).mean().values
ema55  = pd.Series(c).ewm(span=55,  adjust=False).mean().values
ema200 = pd.Series(c).ewm(span=200, adjust=False).mean().values

# RSI 14
d = pd.Series(c).diff()
up = d.clip(lower=0).ewm(alpha=1/14, adjust=False).mean()
dn = (-d.clip(upper=0)).ewm(alpha=1/14, adjust=False).mean().clip(1e-9)
rsi = (100 - 100 / (1 + up / dn)).values

# SuperTrend helper
def calc_supertrend(h, l, c, atr, mult):
    n = len(c)
    st = np.zeros(n)
    dir_ = np.ones(n, dtype=int) # 1 = green (up), -1 = red (down)
    
    upper = (h + l) / 2 + mult * atr
    lower = (h + l) / 2 - mult * atr
    
    for i in range(1, n):
        if c[i-1] > upper[i-1]:
            upper[i] = min(upper[i], upper[i-1])
        if c[i-1] < lower[i-1]:
            lower[i] = max(lower[i], lower[i-1])
            
        if dir_[i-1] == 1:
            if c[i] < lower[i]:
                dir_[i] = -1
            else:
                dir_[i] = 1
        else:
            if c[i] > upper[i]:
                dir_[i] = 1
            else:
                dir_[i] = -1
    return dir_

st1 = calc_supertrend(h, l, c, atr10, 1.0)
st2 = calc_supertrend(h, l, c, atr11, 2.0)
st3 = calc_supertrend(h, l, c, atr12, 3.0)

# McGinley Dynamic helper
def calc_mcginley(c, period=14):
    n = len(c)
    mg = np.zeros(n)
    mg[0] = c[0]
    for i in range(1, n):
        ratio = (c[i] / max(mg[i-1], 1e-5)) ** 4
        mg[i] = mg[i-1] + (c[i] - mg[i-1]) / (period * ratio)
    return mg

mcginley = calc_mcginley(c, 14)

# Waddah Attar Explosion proxy (MACD diff * Volatility)
ema12 = pd.Series(c).ewm(span=12, adjust=False).mean().values
ema26 = pd.Series(c).ewm(span=26, adjust=False).mean().values
macd  = ema12 - ema26
wae_trend = (macd - pd.Series(macd).shift(1).fillna(0).values) * 150.0
deadzone  = atr14 * 100.0

# Bollinger Bands (20, 2)
bb_mid = pd.Series(c).rolling(20).mean().bfill().values
bb_std = pd.Series(c).rolling(20).std().bfill().values
bb_up  = bb_mid + 2.0 * bb_std
bb_dn  = bb_mid - 2.0 * bb_std

# ── SIMULATOR FUNCTION ───────────────────────────────────────────────────────
def run_backtest(signals_buy, signals_sell, sl_mode='atr', sl_mult=2.0, rr=2.0, max_rr=3.0, cooldown=12):
    bal = 1000.0; pk = 1000.0; max_dd = 0.0
    trades = []
    last_trade = -9999
    
    pos_dir = 0; pos_en = 0.0; pos_sl = 0.0; pos_tp = 0.0; pos_lot = 0.0
    
    for i in range(250, n-1):
        if pos_dir != 0:
            done = False
            ep = c[i]
            
            if pos_dir == 1:
                if l[i] <= pos_sl:
                    ep = pos_sl - 5.0 * PIP # 5 pip slippage
                    done = True
                elif h[i] >= pos_tp:
                    ep = pos_tp
                    done = True
            else:
                if h[i] >= pos_sl:
                    ep = pos_sl + 5.0 * PIP
                    done = True
                elif l[i] <= pos_tp:
                    ep = pos_tp
                    done = True
                    
            if done:
                pts = (ep - pos_en)/PIP if pos_dir==1 else (pos_en - ep)/PIP
                net = pts * PTVAL * (pos_lot / 0.01) - (pos_lot / 0.01) * COMM
                bal = max(0.0, bal + net)
                pk  = max(pk, bal)
                dd  = (pk - bal) / pk * 100.0 if pk > 0 else 0
                max_dd = max(max_dd, dd)
                trades.append(net)
                pos_dir = 0
                
        if pos_dir == 0 and (i - last_trade >= cooldown) and bal > 0:
            sig = 0
            if signals_buy[i]: sig = 1
            elif signals_sell[i]: sig = -1
            
            if sig != 0:
                av = max(atr14[i], 1.5)
                sp = 25.0 # pips
                
                if sl_mode == 'atr':
                    sl_pts = (av * sl_mult / PIP) + sp
                else:
                    sl_pts = 150.0 # 150 pips fixed
                    
                risk_amt = bal * 0.03 # 3% risk
                lot = max(0.01, min(round(risk_amt / (sl_pts * 0.01) * 0.01, 2), 20.0))
                
                next_o = o[i+1]
                half_sp = (sp * PIP) / 2.0
                
                if sig == 1:
                    pos_dir = 1
                    pos_en  = next_o + half_sp
                    pos_sl  = pos_en - sl_pts * PIP
                    pos_tp  = pos_en + sl_pts * rr * PIP
                    pos_lot = lot
                else:
                    pos_dir = -1
                    pos_en  = next_o - half_sp
                    pos_sl  = pos_en + sl_pts * PIP
                    pos_tp  = pos_en - sl_pts * rr * PIP
                    pos_lot = lot
                last_trade = i

    wins = [t for t in trades if t > 0]
    loss = [t for t in trades if t < 0]
    pf = sum(wins)/abs(sum(loss)) if loss and sum(loss)!=0 else 0
    wr = len(wins)/max(len(trades),1)*100
    
    return bal, (bal-1000)/10.0, max_dd, len(trades), wr, pf

# ── STRATEGY DEFINITIONS ─────────────────────────────────────────────────────

# 1. Triple SuperTrend & Volume
# Buy: Price > EMA200, sum(st1, st2, st3 == 1) >= 2, RSI < 40 (or dip), Volume > Vol_SMA
vol_sma = pd.Series(v).rolling(20).mean().bfill().values
st_sum = (st1 == 1).astype(int) + (st2 == 1).astype(int) + (st3 == 1).astype(int)

s1_buy  = (c > ema200) & (st_sum >= 2) & (rsi < 40) & (v > vol_sma)
s1_sell = (c < ema200) & (st_sum <= 1) & (rsi > 60) & (v > vol_sma)

# 2. Ultimate Scalping (EMA9 > EMA55 > EMA200 + RSI > 51 + MACD histogram > 0)
s2_buy  = (ema9 > ema55) & (ema55 > ema200) & (rsi > 51) & (wae_trend > 0)
s2_sell = (ema9 < ema55) & (ema55 < ema200) & (rsi < 49) & (wae_trend < 0)

# 3. Gold Peak Momentum (ATR SL 3x, RR 1:1.3)
s3_buy  = (c > ema200) & (c > bb_mid) & (rsi > 55) & (v > vol_sma * 1.2)
s3_sell = (c < ema200) & (c < bb_mid) & (rsi < 45) & (v > vol_sma * 1.2)

# 4. McDavidd Strategy
s4_buy  = (c > bb_up) & (c > mcginley) & (wae_trend > deadzone)
s4_sell = (c < bb_dn) & (c < mcginley) & (abs(wae_trend) > deadzone)

# ── RUN BENCHMARKS ───────────────────────────────────────────────────────────
print("="*75)
print("DAVIDDTECH STRATEGIES BACKTEST ON XAUUSD (2022 - 2026)")
print("="*75)

strats = [
    ("1. Triple SuperTrend & Vol (M15)", s1_buy, s1_sell, 'atr', 2.0, 2.0, 16),
    ("2. Ultimate Scalping (EMA+RSI+MACD)", s2_buy, s2_sell, 'atr', 1.5, 1.5, 12),
    ("3. Gold Peak Momentum (ATR 3x, RR 1:1.3)", s3_buy, s3_sell, 'atr', 3.0, 1.3, 16),
    ("4. McDavidd (McGinley+BB+WAE)", s4_buy, s4_sell, 'atr', 2.0, 2.5, 16),
]

windows = {
    '2022-2023': ('2022-05-02', '2023-05-01'),
    '2023-2024': ('2023-05-01', '2024-05-01'),
    '2024-2025': ('2024-05-01', '2025-05-01'),
    '2025-2026': ('2025-05-01', '2026-07-24')
}

for sname, sb, ss, sl_m, sl_v, rr_v, cd in strats:
    print(f"\n--- Strategy: {sname} ---")
    print(f"{'Period':<12} {'PnL%':>8} {'MaxDD%':>8} {'Trades':>7} {'WR%':>7} {'PF':>6}")
    print("-" * 55)
    tot_pnl = 0
    for yr, (s_date, e_date) in windows.items():
        mask = (df.index >= s_date) & (df.index < e_date)
        if mask.sum() == 0: continue
        
        sb_sub = sb[mask]
        ss_sub = ss[mask]
        c_sub  = c[mask]
        h_sub  = h[mask]
        l_sub  = l[mask]
        o_sub  = o[mask]
        v_sub  = v[mask]
        atr_sub= atr14[mask]
        
        # Save global override for window backtest
        old_c, old_h, old_l, old_o, old_v, old_atr, old_n = c, h, l, o, v, atr14, n
        c, h, l, o, v, atr14, n = c_sub, h_sub, l_sub, o_sub, v_sub, atr_sub, len(c_sub)
        
        bal, pct, dd, n_tr, wr, pf = run_backtest(sb_sub, ss_sub, sl_mode=sl_m, sl_mult=sl_v, rr=rr_v, cooldown=cd)
        print(f"{yr:<12} {pct:>+7.1f}% {dd:>7.1f}% {n_tr:>7} {wr:>6.1f}% {pf:>6.2f}")
        tot_pnl += pct
        
        c, h, l, o, v, atr14, n = old_c, old_h, old_l, old_o, old_v, old_atr, old_n
    print(f"Total 4-Year PnL: {tot_pnl:+.1f}%")
