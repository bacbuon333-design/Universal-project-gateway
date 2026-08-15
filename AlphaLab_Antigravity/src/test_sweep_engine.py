"""
TEST: Causal Structural Sweep & Risk-Friction Dilution Engine (v34 Core)
========================================================================
Hypothesis:
1. Breakout strategies fail because broker friction ($3.5 - $4.5/oz) eats up the small +$1.0/oz breakout edge.
2. Structural Liquidity Sweeps (buying low 48-bar sweep in bull, selling high 48-bar sweep in bear) have a raw edge of +$5.26/oz, which easily beats broker friction.
3. Wider stops (2.0x ATR) + Larger targets (4.0x ATR) dilute fixed costs per trade down to < 5% of total PnL.
4. Dynamic Position Sizing based on Volatility/Drawdown guarantees MaxDD < 20%.
"""
import os, sys
sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None
import numpy as np
import pandas as pd
from dataclasses import dataclass

BASE = r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05\AlphaLab_Antigravity"
DATA = os.path.join(BASE, "data", "GOLD_M15.csv")

df = pd.read_csv(DATA)
df['dt'] = pd.to_datetime(df['datetime_str'])
df.set_index('dt', inplace=True)
df.sort_index(inplace=True)

# 4-bar aggregation (Method B)
c = df['close'].values; h = df['high'].values; l = df['low'].values; o = df['open'].values
n = len(df); seg = n // 4
h1c = np.array([c[i*4+3] for i in range(seg)])
h1h = np.array([max(h[i*4:i*4+4]) for i in range(seg)])
h1l = np.array([min(l[i*4:i*4+4]) for i in range(seg)])
h1o = np.array([o[i*4] for i in range(seg)])
h1dt = [df.index[i*4+3] for i in range(seg)]
N = len(h1c)

# Indicators (Causal)
tr = np.maximum(h1h[1:]-h1l[1:], np.maximum(abs(h1h[1:]-h1c[:-1]), abs(h1l[1:]-h1c[:-1])))
tr = np.insert(tr, 0, tr[0])
atr14 = pd.Series(tr).rolling(14).mean().bfill().values
atr240 = pd.Series(tr).rolling(240).mean().bfill().values

ema50 = pd.Series(h1c).ewm(span=50, adjust=False).mean().values
ema200 = pd.Series(h1c).ewm(span=200, adjust=False).mean().values

# 48-bar structure (shift=1, no future leak)
hi48 = pd.Series(h1h).shift(1).rolling(48).max().values
lo48 = pd.Series(h1l).shift(1).rolling(48).min().values

# 3-month momentum
mom3m = np.zeros(N, bool)
for i in range(1440, N): mom3m[i] = h1c[i] > h1c[i-1440]

# Variable spread (25 pips base, 35 if volatile)
spr = np.where(atr14 > atr240 * 1.4, 35.0, 25.0)

PIP = 0.01; PTVAL = 0.01; COMM = 0.07

def run_simulation(cooldown=72, sl_atr=2.0, tp_atr=5.0, risk_pct=0.04):
    bal = 1000.0; pk = 1000.0; max_dd = 0.0
    trades = []
    last_trade = -9999
    
    pos_dir = 0; pos_en = 0.0; pos_sl = 0.0; pos_tp = 0.0; pos_lot = 0.0; pos_sl_pts = 0.0
    
    for i in range(1440, N-1):
        # Update trailing / exit if position open
        if pos_dir != 0:
            done = False; exit_p = h1c[i]
            av = max(atr14[i], 1.5)
            
            if pos_dir == 1: # LONG
                if h1l[i] <= pos_sl:
                    exit_p = pos_sl - 5.0 * PIP # 5 pip slippage
                    done = True
                elif h1h[i] >= pos_tp:
                    exit_p = pos_tp
                    done = True
            else: # SHORT
                if h1h[i] >= pos_sl:
                    exit_p = pos_sl + 5.0 * PIP
                    done = True
                elif h1l[i] <= pos_tp:
                    exit_p = pos_tp
                    done = True
                    
            if done:
                pts = (exit_p - pos_en)/PIP if pos_dir==1 else (pos_en - exit_p)/PIP
                net = pts * PTVAL * (pos_lot / 0.01) - (pos_lot / 0.01) * COMM
                bal = max(0.0, bal + net)
                pk  = max(pk, bal)
                dd  = (pk - bal) / pk * 100.0 if pk > 0 else 0
                max_dd = max(max_dd, dd)
                trades.append(net)
                pos_dir = 0
                
        # Signal Generation (Causal Liquidity Sweep)
        if pos_dir == 0 and (i - last_trade >= cooldown) and bal > 0:
            av = max(atr14[i], 1.5)
            sp = spr[i]
            
            macro_bull = mom3m[i] and h1c[i] > ema200[i]
            macro_bear = (not mom3m[i]) and h1c[i] < ema200[i]
            
            # LONG SWEEP: Price swept near or below 48-bar low in macro bull regime + lower wick rejection
            lwick = min(h1o[i], h1c[i]) - h1l[i]
            body  = abs(h1c[i] - h1o[i]) + 1e-9
            sweep_lo = h1l[i] <= lo48[i] + 0.5 * av
            pin_lo   = lwick >= 1.5 * body
            
            # SHORT SWEEP: Price swept near or above 48-bar high in macro bear regime + upper wick rejection
            uwick = h1h[i] - max(h1o[i], h1c[i])
            sweep_hi = h1h[i] >= hi48[i] - 0.5 * av
            pin_hi   = uwick >= 1.5 * body
            
            sig = 0
            if macro_bull and (sweep_lo or (pin_lo and h1l[i] <= ema50[i])):
                sig = 1
            elif macro_bear and (sweep_hi or (pin_hi and h1h[i] >= ema50[i])):
                sig = -1
                
            if sig != 0:
                dd_pct = (pk - bal) / max(pk, 1e-9) * 100.0
                r_scale = 0.2 if dd_pct >= 15 else (0.5 if dd_pct >= 10 else 1.0)
                sl_pts = (av * sl_atr / PIP) + sp
                lot = max(0.01, min(round(bal * risk_pct * r_scale / (sl_pts * 0.01) * 0.01, 2), 20.0))
                
                next_open = h1o[i+1]
                half_sp = (sp * PIP) / 2.0
                
                if sig == 1:
                    pos_dir = 1
                    pos_en  = next_open + half_sp
                    pos_sl  = pos_en - sl_pts * PIP
                    pos_tp  = pos_en + (av * tp_atr)
                    pos_lot = lot
                else:
                    pos_dir = -1
                    pos_en  = next_open - half_sp
                    pos_sl  = pos_en + sl_pts * PIP
                    pos_tp  = pos_en - (av * tp_atr)
                    pos_lot = lot
                last_trade = i

    wins = [t for t in trades if t > 0]
    loss = [t for t in trades if t < 0]
    pf = sum(wins)/abs(sum(loss)) if loss and sum(loss)!=0 else 0
    wr = len(wins)/max(len(trades),1)*100
    
    return bal, (bal-1000)/10.0, max_dd, len(trades), wr, pf

print("=== SWEEP & COST DILUTION ENGINE TEST ===")
windows = {
    '2022-2023': ('2022-05-02', '2023-05-01'),
    '2023-2024': ('2023-05-01', '2024-05-01'),
    '2024-2025': ('2024-05-01', '2025-05-01'),
    '2025-2026': ('2025-05-01', '2026-07-24')
}

tot_pnl = 0
for yr, (s, e) in windows.items():
    wsd, wed = pd.Timestamp(s), pd.Timestamp(e)
    si = next(i for i,t in enumerate(h1dt) if t >= wsd)
    ei = next(i for i,t in enumerate(h1dt) if t >= wed)
    
    # Run slice
    # Save original globals for slice
    old_h1c, old_h1h, old_h1l, old_h1o, old_h1dt, old_N = h1c, h1h, h1l, h1o, h1dt, N
    old_atr14, old_atr240, old_ema50, old_ema200, old_hi48, old_lo48, old_mom3m, old_spr = atr14, atr240, ema50, ema200, hi48, lo48, mom3m, spr
    
    h1c, h1h, h1l, h1o, h1dt, N = h1c[si:ei], h1h[si:ei], h1l[si:ei], h1o[si:ei], h1dt[si:ei], ei-si
    atr14, atr240, ema50, ema200, hi48, lo48, mom3m, spr = atr14[si:ei], atr240[si:ei], ema50[si:ei], ema200[si:ei], hi48[si:ei], lo48[si:ei], mom3m[si:ei], spr[si:ei]
    
    bal, pct, dd, n_tr, wr, pf = run_simulation(cooldown=48, sl_atr=2.0, tp_atr=4.0, risk_pct=0.04)
    print(f"{yr}: PnL={pct:+.1f}%  MaxDD={dd:.1f}%  Trades={n_tr}  WR={wr:.1f}%  PF={pf:.2f}")
    tot_pnl += pct
    
    # Restore
    h1c, h1h, h1l, h1o, h1dt, N = old_h1c, old_h1h, old_h1l, old_h1o, old_h1dt, old_N
    atr14, atr240, ema50, ema200, hi48, lo48, mom3m, spr = old_atr14, old_atr240, old_ema50, old_ema200, old_hi48, old_lo48, old_mom3m, old_spr

print(f"\nTotal PnL sum across 4 years: {tot_pnl:+.1f}%")
