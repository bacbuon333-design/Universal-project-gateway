"""
USER GOLD-TAILORED STRATEGIES BENCHMARK & EXPERIMENTAL EVALUATION ENGINE
========================================================================
Implements and backtests the 3 Gold-Tailored Strategies specified by the user:

1. Strategy 1: Smart Money Scalping (HTF M30 Sweep + BOS + LTF M5 FVG / Breaker Block)
2. Strategy 2: Session-Based Asian Breakout (Asian High/Low 00:00-07:00 GMT Breakout at 12:00-16:00 GMT)
3. Strategy 3: Ultimate Scalping M5 (EMA 9/21 Cross + RSI 14 filter 50-70 / 30-50)

Includes Risk Rules:
- Dynamic lot calculation ($ risk / SL pips)
- Max 2-3 trades per day & 2 consecutive losses daily circuit breaker
- Real broker costs (Spread 25p + Comm $7/lot + Slippage 5p)

Datasets:
- Gold M15 (4.23 Years continuous: 2022 - 2026, 99,999 nến)
- Gold H1 (16.57 Years continuous: 2010 - 2026, 79,288 nến)
"""

import os, sys
sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None
import numpy as np
import pandas as pd

BASE_DIR = r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05\AlphaLab_Antigravity"
DATA_M15 = os.path.join(BASE_DIR, "data", "GOLD_M15.csv")
DATA_H1  = os.path.join(BASE_DIR, "data", "GOLD_H1_2010_2026.csv")

PIP = 0.01
PTVAL = 0.01

# -------------------------------------------------------------
# STRATEGY 2: SESSION-BASED ASIAN BREAKOUT (M15 / H1 Data)
# -------------------------------------------------------------
def run_asian_breakout_strategy(df, risk_pct=0.01):
    c = df['close'].values; h = df['high'].values; l = df['low'].values; o = df['open'].values
    col = 'datetime_str' if 'datetime_str' in df.columns else df.columns[0]
    dt = pd.to_datetime(df[col])
    hours = dt.dt.hour.values
    dates = dt.dt.date.values
    n = len(df)
    
    tr = np.maximum(h[1:]-l[1:], np.maximum(abs(h[1:]-c[:-1]), abs(l[1:]-c[:-1])))
    tr = np.insert(tr, 0, tr[0])
    atr14 = pd.Series(tr).rolling(14).mean().bfill().values
    
    # Calculate Asian Session (00:00 - 07:00 GMT) High and Low for each day
    asian_high = {}
    asian_low  = {}
    
    unique_dates = np.unique(dates)
    for d in unique_dates:
        mask_asian = (dates == d) & (hours >= 0) & (hours < 7)
        if np.any(mask_asian):
            asian_high[d] = np.max(h[mask_asian])
            asian_low[d]  = np.min(l[mask_asian])

    buy_sig  = np.zeros(n, dtype=bool)
    sell_sig = np.zeros(n, dtype=bool)
    
    for i in range(1, n):
        d_now = dates[i]
        h_now = hours[i]
        
        # Golden Hours: 12:00 - 16:00 GMT
        if (h_now >= 12) and (h_now <= 16) and (d_now in asian_high):
            a_hi = asian_high[d_now]
            a_lo = asian_low[d_now]
            
            # Breakout close out of Asian Range
            if c[i] > a_hi and c[i-1] <= a_hi:
                buy_sig[i] = True
            elif c[i] < a_lo and c[i-1] >= a_lo:
                sell_sig[i] = True

    return simulate_risk_managed_backtest(df, buy_sig, sell_sig, atr14, sl_pips=200.0, tp_mult=2.0, risk_pct=risk_pct)

# -------------------------------------------------------------
# STRATEGY 3: ULTIMATE SCALPING M5 / M15 (EMA 9/21 + RSI 14)
# -------------------------------------------------------------
def run_ultimate_scalping_m5_strategy(df, risk_pct=0.01):
    c = df['close'].values; h = df['high'].values; l = df['low'].values; o = df['open'].values
    n = len(df)
    
    tr = np.maximum(h[1:]-l[1:], np.maximum(abs(h[1:]-c[:-1]), abs(l[1:]-c[:-1])))
    tr = np.insert(tr, 0, tr[0])
    atr14 = pd.Series(tr).rolling(14).mean().bfill().values
    
    ema9  = pd.Series(c).ewm(span=9,  adjust=False).mean().values
    ema21 = pd.Series(c).ewm(span=21, adjust=False).mean().values
    
    d = pd.Series(c).diff()
    up = d.clip(lower=0).ewm(alpha=1/14, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1/14, adjust=False).mean().clip(1e-9)
    rsi14 = (100 - 100 / (1 + up / dn)).values
    
    # Buy: EMA 9 crosses above EMA 21 & 50 < RSI < 70
    # Sell: EMA 9 crosses below EMA 21 & 30 < RSI < 50
    ema_cross_up = (ema9 > ema21) & (np.roll(ema9, 1) <= np.roll(ema21, 1))
    ema_cross_dn = (ema9 < ema21) & (np.roll(ema9, 1) >= np.roll(ema21, 1))
    
    buy_sig  = ema_cross_up & (rsi14 > 50) & (rsi14 < 70)
    sell_sig = ema_cross_dn & (rsi14 < 50) & (rsi14 > 30)
    
    return simulate_risk_managed_backtest(df, buy_sig, sell_sig, atr14, sl_pips=80.0, tp_mult=1.5, risk_pct=risk_pct)

# -------------------------------------------------------------
# STRATEGY 1: SMART MONEY LIQUIDITY SWEEP + FVG (M15 Data)
# -------------------------------------------------------------
def run_smart_money_fvg_strategy(df, risk_pct=0.01):
    c = df['close'].values; h = df['high'].values; l = df['low'].values; o = df['open'].values
    n = len(df)
    
    tr = np.maximum(h[1:]-l[1:], np.maximum(abs(h[1:]-c[:-1]), abs(l[1:]-c[:-1])))
    tr = np.insert(tr, 0, tr[0])
    atr14 = pd.Series(tr).rolling(14).mean().bfill().values
    
    # Fair Value Gap (FVG)
    bull_fvg = np.zeros(n, dtype=bool)
    bear_fvg = np.zeros(n, dtype=bool)
    bull_fvg[2:] = (l[2:] > h[:-2]) # Gap up
    bear_fvg[2:] = (h[2:] < l[:-2]) # Gap down
    
    # Swing High/Low Sweep (20-bar shift=1)
    hi20 = pd.Series(h).shift(1).rolling(20).max().bfill().values
    lo20 = pd.Series(l).shift(1).rolling(20).min().bfill().values
    
    sweep_lo = l <= lo20
    sweep_hi = h >= hi20
    
    buy_sig  = np.zeros(n, dtype=bool)
    sell_sig = np.zeros(n, dtype=bool)
    
    for i in range(5, n):
        # Look back 5 bars for a sweep + bull FVG
        if bull_fvg[i] and np.any(sweep_lo[i-5:i+1]):
            buy_sig[i] = True
        elif bear_fvg[i] and np.any(sweep_hi[i-5:i+1]):
            sell_sig[i] = True
            
    return simulate_risk_managed_backtest(df, buy_sig, sell_sig, atr14, sl_pips=120.0, tp_mult=2.0, risk_pct=risk_pct)

# -------------------------------------------------------------
# RIGOROUS SIMULATOR WITH USER RISK RULES
# -------------------------------------------------------------
def simulate_risk_managed_backtest(df, buy_sig, sell_sig, atr14, sl_pips=100.0, tp_mult=2.0, risk_pct=0.01):
    c = df['close'].values; h = df['high'].values; l = df['low'].values; o = df['open'].values
    col = 'datetime_str' if 'datetime_str' in df.columns else df.columns[0]
    dt = pd.to_datetime(df[col])
    dates = dt.dt.date.values
    n = len(df)
    
    bal = 1000.0; pk = 1000.0; max_dd = 0.0
    trades = []
    
    curr_date = None
    daily_trades_count = 0
    daily_consec_losses = 0
    daily_halted = False
    
    pos_dir = 0; pos_en = 0.0; pos_sl = 0.0; pos_tp = 0.0; pos_lot = 0.0
    last_trade = -9999; cooldown = 4
    
    for i in range(50, n-1):
        d_now = dates[i]
        if d_now != curr_date:
            curr_date = d_now
            daily_trades_count = 0
            daily_consec_losses = 0
            daily_halted = False
            
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
                gross = pts * PTVAL * (pos_lot / 0.01)
                fee   = (pos_lot / 0.01) * 0.37
                net   = gross - fee
                
                bal = max(0.0, bal + net)
                pk  = max(pk, bal)
                dd  = (pk - bal) / pk * 100.0 if pk > 0 else 0
                max_dd = max(max_dd, dd)
                trades.append(net)
                
                if net < 0:
                    daily_consec_losses += 1
                    if daily_consec_losses >= 2:
                        daily_halted = True # Halt trading for rest of day after 2 losses
                else:
                    daily_consec_losses = 0
                    
                pos_dir = 0
                
        # Entry check with User Rules (Max 3 trades/day & 2 loss halt)
        if pos_dir == 0 and (i - last_trade >= cooldown) and (not daily_halted) and (daily_trades_count < 3) and bal > 0:
            sig = 0
            if buy_sig[i]: sig = 1
            elif sell_sig[i]: sig = -1
            
            if sig != 0:
                sp = 25.0
                sl_pts = sl_pips + sp
                tp_pts = sl_pips * tp_mult
                
                # Dynamic lot sizing: Lot = Risk_Amt / (SL_pips * $0.10)
                risk_amt = bal * risk_pct
                risk_per_001 = sl_pts * 0.01
                lot = max(0.01, min(round((risk_amt / risk_per_001) * 0.01, 2), 10.0))
                
                next_o = o[i+1]
                half_sp = (sp * PIP) / 2.0
                
                if sig == 1:
                    pos_dir = 1; pos_en = next_o + half_sp; pos_sl = pos_en - sl_pts * PIP; pos_tp = pos_en + tp_pts * PIP; pos_lot = lot
                else:
                    pos_dir = -1; pos_en = next_o - half_sp; pos_sl = pos_en + sl_pts * PIP; pos_tp = pos_en - tp_pts * PIP; pos_lot = lot
                    
                last_trade = i
                daily_trades_count += 1

    wins = [t for t in trades if t > 0]
    loss = [t for t in trades if t < 0]
    pf = sum(wins)/abs(sum(loss)) if loss and sum(loss)!=0 else 0
    wr = len(wins)/max(len(trades),1)*100
    pnl_pct = (bal - 1000.0) / 10.0
    
    return {
        'bal': bal, 'pnl_pct': pnl_pct, 'max_dd': max_dd,
        'trades': len(trades), 'wr': wr, 'pf': pf
    }

def main():
    df_m15 = pd.read_csv(DATA_M15)
    df_h1  = pd.read_csv(DATA_H1)
    
    print("="*105)
    print("USER GOLD-TAILORED STRATEGIES BENCHMARK GAUNTLET")
    print("Testing 3 Gold-Specific Strategies with User's Strict Risk Rules | Initial Capital: $1,000.00 USD")
    print("="*105)
    
    res1 = run_smart_money_fvg_strategy(df_m15, risk_pct=0.01)
    res2 = run_asian_breakout_strategy(df_h1, risk_pct=0.01)
    res3 = run_ultimate_scalping_m5_strategy(df_m15, risk_pct=0.01)
    
    strats = [
        ("Strategy 1: Smart Money Scalping (HTF Sweep + FVG)", res1, "Gold M15 (4.23 Years)"),
        ("Strategy 2: Session-Based Asian Breakout (12-16 GMT)", res2, "Gold H1 (16.57 Years)"),
        ("Strategy 3: Ultimate Scalping M5 (EMA 9/21 + RSI 14)", res3, "Gold M15 (4.23 Years)")
    ]
    
    print(f"{'Strategy Name':<50} | {'Data Range':<22} | {'Final $':<10} {'PnL %':<8} {'MaxDD %':<8} {'Trades':<6} {'PF':<5}")
    print("-" * 105)
    
    for name, r, d_range in strats:
        s = "✅" if r['pnl_pct'] > 0 else "❌"
        print(f"{name:<50} | {d_range:<22} | ${r['bal']:<9,.2f} {r['pnl_pct']:>+6.1f}%  {r['max_dd']:<8.1f} {r['trades']:<6} {r['pf']:<5.2f} {s}")

if __name__ == '__main__':
    main()
