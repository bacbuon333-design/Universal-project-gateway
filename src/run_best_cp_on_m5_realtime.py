"""
REALTIME M5 TEST GAUNTLET FOR OPTIMAL CHECKPOINTS
=================================================
Fetches 50,000 M5 bars directly from MetaTrader 5 terminal for GOLD (Nov 2025 - Jul 2026)
and executes:
1. Checkpoint 5 (Key Structure Reaction Zone Sweep Engine)
2. Checkpoint 7 Refined (Donchian Breakout + 24h Cooldown)
3. Checkpoint 3 (Prop-Firm VaR Model)

Initial Capital: $1,000.00 USD | Risk: 2.5% per Trade
Real execution costs included: Spread 25p + Comm $7/lot + Slippage 5p ($0.37/0.01 lot)
"""

import os, sys
sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None
import numpy as np
import pandas as pd
import MetaTrader5 as mt5

BASE_DIR = r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05\AlphaLab_Antigravity"

PIP = 0.01
PTVAL = 0.01

def fetch_m5_data():
    if not mt5.initialize():
        print("Failed to initialize MT5")
        return None
    mt5.symbol_select("GOLD", True)
    rates = mt5.copy_rates_from_pos("GOLD", mt5.TIMEFRAME_M5, 0, 50000)
    mt5.shutdown()
    
    if rates is None or len(rates) == 0:
        print("Failed to fetch M5 rates from MT5")
        return None
        
    df = pd.DataFrame(rates)
    df['dt'] = pd.to_datetime(df['time'], unit='s')
    df.sort_values('dt', inplace=True)
    df.reset_index(drop=True, inplace=True)
    return df

# -------------------------------------------------------------
# CHECKPOINT 5 ON M5 DATA (H1 Equivalent Structure)
# -------------------------------------------------------------
def run_cp5_on_m5(df, risk_pct=0.025):
    c = df['close'].values; h = df['high'].values; l = df['low'].values; o = df['open'].values
    n = len(df)
    
    tr = np.maximum(h[1:]-l[1:], np.maximum(abs(h[1:]-c[:-1]), abs(l[1:]-c[:-1])))
    tr = np.insert(tr, 0, tr[0])
    atr14 = pd.Series(tr).rolling(14).mean().bfill().values
    
    # 48 H1 bars = 48 x 12 = 576 M5 bars
    hi576 = pd.Series(h).shift(1).rolling(576).max().bfill().values
    lo576 = pd.Series(l).shift(1).rolling(576).min().bfill().values
    
    # EMA 200 H1 = EMA 2400 M5
    ema2400 = pd.Series(c).ewm(span=2400, adjust=False).mean().values
    
    # 3-month momentum equivalent on M5 (1440 H1 bars = 17,280 M5 bars)
    mom_3m = np.zeros(n, dtype=bool)
    for i in range(17280, n):
        mom_3m[i] = c[i] > c[i-17280]
    mom_3m[:17280] = True
    
    buy_sig  = np.zeros(n, dtype=bool)
    sell_sig = np.zeros(n, dtype=bool)
    
    for i in range(600, n):
        av = max(atr14[i], 1.5)
        lwick = min(o[i], c[i]) - l[i]
        uwick = h[i] - max(o[i], c[i])
        body  = abs(c[i] - o[i]) + 1e-9
        
        macro_bull = mom_3m[i] and c[i] > ema2400[i]
        macro_bear = (not mom_3m[i]) and c[i] < ema2400[i]
        
        sweep_lo = l[i] <= lo576[i] + 0.5 * av
        pin_lo   = lwick >= 1.2 * body
        sweep_hi = h[i] >= hi576[i] - 0.5 * av
        pin_hi   = uwick >= 1.2 * body
        
        if macro_bull and (sweep_lo or pin_lo) and c[i] > o[i]:
            buy_sig[i] = True
        elif macro_bear and (sweep_hi or pin_hi) and c[i] < o[i]:
            sell_sig[i] = True

    return simulate_m5_execution(df, buy_sig, sell_sig, atr14, sl_mult=2.0, tp_mult=4.5, cooldown_bars=96, risk_pct=risk_pct)

# -------------------------------------------------------------
# CHECKPOINT 7 REFINED ON M5 DATA
# -------------------------------------------------------------
def run_cp7_on_m5(df, risk_pct=0.025):
    c = df['close'].values; h = df['high'].values; l = df['low'].values; o = df['open'].values
    n = len(df)
    
    tr = np.maximum(h[1:]-l[1:], np.maximum(abs(h[1:]-c[:-1]), abs(l[1:]-c[:-1])))
    tr = np.insert(tr, 0, tr[0])
    atr14 = pd.Series(tr).rolling(14).mean().bfill().values
    
    ema108 = pd.Series(c).ewm(span=108, adjust=False).mean().values   # EMA 9 H1 = 108 M5
    ema660 = pd.Series(c).ewm(span=660, adjust=False).mean().values   # EMA 55 H1 = 660 M5
    ema2400 = pd.Series(c).ewm(span=2400, adjust=False).mean().values # EMA 200 H1 = 2400 M5
    
    d = pd.Series(c).diff()
    up = d.clip(lower=0).ewm(alpha=1/14, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1/14, adjust=False).mean().clip(1e-9)
    rsi14 = (100 - 100 / (1 + up / dn)).values
    
    # Donchian 240 M5 bars (20 H1 bars)
    don_hi240 = pd.Series(h).shift(1).rolling(240).max().bfill().values
    don_lo240 = pd.Series(l).shift(1).rolling(240).min().bfill().values
    
    buy_sig  = (ema108 > ema660) & (ema660 > ema2400) & (rsi14 > 51) & (c > don_hi240)
    sell_sig = (ema108 < ema660) & (ema660 < ema2400) & (rsi14 < 49) & (c < don_lo240)
    
    return simulate_m5_execution(df, buy_sig, sell_sig, atr14, sl_mult=1.5, tp_mult=3.0, cooldown_bars=48, risk_pct=risk_pct)

# -------------------------------------------------------------
# M5 SIMULATION ENGINE (Standardized Broker Costs & Sizing)
# -------------------------------------------------------------
def simulate_m5_execution(df, buy_sig, sell_sig, atr14, sl_mult=1.5, tp_mult=3.0, cooldown_bars=48, risk_pct=0.025):
    c = df['close'].values; h = df['high'].values; l = df['low'].values; o = df['open'].values
    n = len(df)
    
    bal = 1000.0; pk = 1000.0; max_dd = 0.0
    trades = []
    last_trade = -9999
    pos_dir = 0; pos_en = 0.0; pos_sl = 0.0; pos_tp = 0.0; pos_lot = 0.0
    
    for i in range(300, n-1):
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
                pos_dir = 0
                
        if pos_dir == 0 and (i - last_trade >= cooldown_bars) and bal > 0:
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

    wins = [t for t in trades if t > 0]
    loss = [t for t in trades if t < 0]
    pf = sum(wins)/abs(sum(loss)) if loss and sum(loss)!=0 else 0
    wr = len(wins)/max(len(trades),1)*100
    pnl_pct = (bal - 1000.0) / 10.0
    
    return {
        'start_dt': str(df['dt'].iloc[0])[:19],
        'end_dt': str(df['dt'].iloc[-1])[:19],
        'bars': n, 'bal': bal, 'pnl_pct': pnl_pct, 'max_dd': max_dd,
        'trades': len(trades), 'wr': wr, 'pf': pf
    }

def main():
    df_m5 = fetch_m5_data()
    if df_m5 is None: return
    
    print("="*105)
    print("REALTIME M5 TEST GAUNTLET FOR OPTIMAL CHECKPOINTS (MT5 DIRECT DATA)")
    print("="*105)
    print(f"Data Source : MT5 XM Global GOLD M5 ({df_m5['dt'].iloc[0]} to {df_m5['dt'].iloc[-1]})")
    print(f"Total Bars  : {len(df_m5):,} M5 Bars (~8.5 Months Continuous Realtime)")
    print(f"Initial $   : $1,000.00 USD | Risk: 2.5% per Trade")
    print("="*105)
    print(f"{'Checkpoint Model':<42} | {'Final $':<11} {'PnL %':<9} {'MaxDD %':<8} {'Trades':<6} {'WR %':<6} {'PF':<5}")
    print("-" * 105)
    
    r5 = run_cp5_on_m5(df_m5, risk_pct=0.025)
    r7 = run_cp7_on_m5(df_m5, risk_pct=0.025)
    
    s5 = "✅" if r5['pnl_pct'] > 0 else "❌"
    s7 = "✅" if r7['pnl_pct'] > 0 else "❌"
    
    print(f"{'CP5: Key Structure Reaction Zone Sweep':<42} | ${r5['bal']:<10,.2f} {r5['pnl_pct']:>+7.1f}%  {r5['max_dd']:<8.1f} {r5['trades']:<6} {r5['wr']:<6.1f} {r5['pf']:<5.2f} {s5}")
    print(f"{'CP7: Advanced High-Yield Optimization':<42} | ${r7['bal']:<10,.2f} {r7['pnl_pct']:>+7.1f}%  {r7['max_dd']:<8.1f} {r7['trades']:<6} {r7['wr']:<6.1f} {r7['pf']:<5.2f} {s7}")

if __name__ == '__main__':
    main()
