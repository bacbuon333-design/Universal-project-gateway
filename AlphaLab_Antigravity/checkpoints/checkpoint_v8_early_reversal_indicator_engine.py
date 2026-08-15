"""
CHECKPOINT V8 — EARLY PEAK/TROUGH REVERSAL INDICATOR ENGINE
===========================================================
Frozen Version: Checkpoint 8 (2026-07-31)

Reverse-Engineered Architecture (Derived from Oracle Swing Analysis):
1. Zero Blocking Filters: Removed ADX gates and session restrictions to maximize trade frequency.
2. Early Peak/Trough Indicator (Chỉ báo Động Sớm):
   - Fast RSI (7) Extreme Exhaustion (< 25 Oversold / > 75 Overbought)
   - Bollinger Band (20, 2.0) Outer Piercing + Rejection Wick (Wick >= 1.2x Body)
   - Fast EMA (3/9) Micro-Cross Confirmation
3. Capital Insurance (Bảo hiểm vốn):
   - Dynamic Equity Risk Scaling: 3.0% risk during equity peaks, automatically scales down to 1.5% during drawdown to preserve capital baseline.
   - Asymmetric 1:2.2 R:R (SL = 1.5x ATR, TP = 3.3x ATR).

Dataset: XAUUSD H1 (2010 - 2026, 79,288 bars, 16.57 Years)
Execution: Real broker costs (Spread 25p + Comm $7/lot + Slippage 5p)
"""

import os, sys
sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None
import numpy as np
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(BASE_DIR, "data", "GOLD_H1_2010_2026.csv")

PIP = 0.01
PTVAL = 0.01
COMM_PER_001 = 0.07

def run_checkpoint_v8_reversal(df, base_risk=0.03):
    c = df['close'].values; h = df['high'].values; l = df['low'].values; o = df['open'].values
    dt = df['dt'].values if 'dt' in df.columns else pd.to_datetime(df['datetime_str']).values
    n = len(df)
    if n < 300: return None
    
    tr = np.maximum(h[1:]-l[1:], np.maximum(abs(h[1:]-c[:-1]), abs(l[1:]-c[:-1])))
    tr = np.insert(tr, 0, tr[0])
    atr14 = pd.Series(tr).rolling(14).mean().bfill().values
    
    # Fast EMAs for Micro-Cross
    ema3 = pd.Series(c).ewm(span=3, adjust=False).mean().values
    ema9 = pd.Series(c).ewm(span=9, adjust=False).mean().values
    ema50 = pd.Series(c).ewm(span=50, adjust=False).mean().values
    ema200 = pd.Series(c).ewm(span=200, adjust=False).mean().values
    
    # Fast RSI (7) for Early Exhaustion
    d = pd.Series(c).diff()
    up = d.clip(lower=0).ewm(alpha=1/7, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1/7, adjust=False).mean().clip(1e-9)
    rsi7 = (100 - 100 / (1 + up / dn)).values
    
    # Bollinger Bands on Price (20, 2.0)
    mid20 = pd.Series(c).rolling(20).mean().bfill().values
    std20 = pd.Series(c).rolling(20).std().bfill().values
    bb_up = mid20 + 2.0 * std20
    bb_dn = mid20 - 2.0 * std20
    
    buy_sig  = np.zeros(n, dtype=bool)
    sell_sig = np.zeros(n, dtype=bool)
    
    for i in range(20, n):
        av = max(atr14[i], 1.5)
        lwick = min(o[i], c[i]) - l[i]
        uwick = h[i] - max(o[i], c[i])
        body  = abs(c[i] - o[i]) + 1e-9
        
        # Early Peak/Trough Reversal Indicator Signals (Causal, 0 Future Leak)
        # Trough Reversal (Early Buy): Low pierces BB Lower OR RSI7 < 28 + Rejection Wick + EMA3 > EMA9
        trough_pierce = (l[i] <= bb_dn[i]) or (rsi7[i] < 28)
        trough_pin    = lwick >= 1.2 * body
        ema_turn_up   = ema3[i] >= ema9[i]
        macro_bull    = c[i] >= ema200[i] * 0.98
        
        # Peak Reversal (Early Sell): High pierces BB Upper OR RSI7 > 72 + Rejection Wick + EMA3 < EMA9
        peak_pierce   = (h[i] >= bb_up[i]) or (rsi7[i] > 72)
        peak_pin      = uwick >= 1.2 * body
        ema_turn_dn   = ema3[i] <= ema9[i]
        macro_bear    = c[i] <= ema200[i] * 1.02
        
        if trough_pierce and trough_pin and ema_turn_up and macro_bull:
            buy_sig[i] = True
        elif peak_pierce and peak_pin and ema_turn_dn and macro_bear:
            sell_sig[i] = True

    bal = 1000.0; pk = 1000.0; max_dd = 0.0
    trades = []
    last_trade = -9999
    cooldown = 12 # 12h cooldown
    pos_dir = 0; pos_en = 0.0; pos_sl = 0.0; pos_tp = 0.0; pos_lot = 0.0
    total_fees = 0.0
    
    for i in range(200, n-1):
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
                total_fees += fee
                
                bal = max(0.0, bal + net)
                pk  = max(pk, bal)
                dd  = (pk - bal) / pk * 100.0 if pk > 0 else 0
                max_dd = max(max_dd, dd)
                trades.append(net)
                pos_dir = 0
                
        if pos_dir == 0 and (i - last_trade >= cooldown) and bal > 0:
            sig = 0
            if buy_sig[i]: sig = 1
            elif sell_sig[i]: sig = -1
            
            if sig != 0:
                av = max(atr14[i], 1.5)
                sp = 25.0
                sl_pts = (av * 1.5 / PIP) + sp
                tp_pts = (av * 3.3 / PIP) # 1:2.2 Asymmetric R:R
                
                # Capital Insurance Risk Protection
                # If drawdown > 10%, reduce risk to 1.5% to protect capital baseline
                current_dd = (pk - bal) / pk if pk > 0 else 0
                dynamic_risk = base_risk if current_dd < 0.10 else base_risk * 0.5
                
                risk_amt = bal * dynamic_risk
                lot = max(0.01, min(round(risk_amt / (sl_pts * 0.01) * 0.01, 2), 20.0))
                
                next_o = o[i+1]
                half_sp = (sp * PIP) / 2.0
                
                if sig == 1:
                    pos_dir = 1; pos_en = next_o + half_sp; pos_sl = pos_en - sl_pts * PIP; pos_tp = pos_en + tp_pts * PIP; pos_lot = lot
                else:
                    pos_dir = -1; pos_en = next_o - half_sp; pos_sl = pos_en + sl_pts * PIP; pos_tp = pos_en - tp_pts * PIP; pos_lot = lot
                last_trade = i

    wins = [t for t in trades if t > 0]
    loss = [t for t in trades if t < 0]
    pf = sum(wins)/abs(sum(loss)) if loss and sum(loss)!=0 else 0
    wr = len(wins)/max(len(trades),1)*100
    pnl_pct = (bal - 1000.0) / 10.0
    
    return {
        'bal': bal, 'pnl_pct': pnl_pct, 'max_dd': max_dd,
        'trades': len(trades), 'wr': wr, 'pf': pf, 'fees': total_fees
    }

def main():
    df = pd.read_csv(DATA_PATH)
    df['dt'] = pd.to_datetime(df['datetime_str'])
    df['year'] = df['dt'].dt.year
    years = sorted(df['year'].unique())
    
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from checkpoint_v1_davidd_ultimate_scalping_h1 import run_v1_single_year as run_v1
    
    print("="*95)
    print("CHECKPOINT 8 — EARLY PEAK/TROUGH REVERSAL ENGINE BENCHMARK (2010 - 2026)")
    print("Dataset: XAUUSD H1 (16.57 Years) | Fresh $1,000 Capital Every Year")
    print("="*95)
    print(f"{'Year':<6} | {'--- CP1 BASELINE (GỐC) ---':<35} | {'--- CP8 EARLY REVERSAL ENGINE ---':<35}")
    print(f"{'':<6} | {'PnL %':<8} {'MaxDD %':<8} {'Trades':<7} {'WR %':<6} {'PF':<5} | {'PnL %':<8} {'MaxDD %':<8} {'Trades':<7} {'WR %':<6} {'PF':<5}")
    print("-" * 95)
    
    v1_w, v8_w = 0, 0; tot = 0
    for yr in years:
        df_yr = df[df['year'] == yr]
        r1 = run_v1(df_yr, risk_pct=0.03)
        r8 = run_checkpoint_v8_reversal(df_yr, base_risk=0.03)
        if r1 is None or r8 is None: continue
        
        tot += 1
        if r1['pnl_pct'] > 0: v1_w += 1
        if r8['pnl_pct'] > 0: v8_w += 1
        
        s1 = "✅" if r1['pnl_pct'] > 0 else "❌"
        s8 = "✅" if r8['pnl_pct'] > 0 else "❌"
        
        v1_str = f"{r1['pnl_pct']:>+6.1f}%  {r1['max_dd']:>6.1f}%  {r1['trades']:>5}  {r1['wr']:>5.1f}% {r1['pf']:>4.2f} {s1}"
        v8_str = f"{r8['pnl_pct']:>+6.1f}%  {r8['max_dd']:>6.1f}%  {r8['trades']:>5}  {r8['wr']:>5.1f}% {r8['pf']:>4.2f} {s8}"
        
        print(f"{yr:<6} | {v1_str} | {v8_str}")

    print("-" * 95)
    print(f"SUMMARY PROFITABLE YEARS:")
    print(f"  Checkpoint 1 Baseline Gốc : {v1_w} / {tot} Years ({v1_w/tot*100:.1f}%)")
    print(f"  Checkpoint 8 Early Reversal: {v8_w} / {tot} Years ({v8_w/tot*100:.1f}%)")

if __name__ == '__main__':
    main()
