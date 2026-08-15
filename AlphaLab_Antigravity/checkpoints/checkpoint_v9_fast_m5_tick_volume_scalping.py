"""
CHECKPOINT V9 — FAST M5 TICK-VOLUME SCALPING ENGINE
===================================================
Frozen Version: Checkpoint 9 (2026-07-31)

Evolved Architecture (Fast M5 Scalping with Tick Volume Absorption):
1. Macro Trend Guard: M5 EMA 2400 (Equivalent to H1 EMA 200).
2. Tick Volume Confirmation:
   - Tick Volume Z-Score > 1.2 (Order Flow Influx)
   - Volume Absorption Wick (Lower Wick >= 1.2x Body for Buy / Upper Wick >= 1.2x Body for Sell)
3. M5 Fast Micro-Trigger:
   - Fast EMA (5 / 13) Micro-Cross
   - Fast R:R Sizing: SL = 1.2x ATR, TP = 2.5x ATR

Dataset: MT5 Realtime M5 Data (50,000 bars, Nov 2025 - Jul 2026) & Gold M15
Execution: Real broker costs (Spread 25p + Comm $7/lot + Slippage 5p)
"""

import os, sys
sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None
import numpy as np
import pandas as pd
import MetaTrader5 as mt5

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_M15 = os.path.join(BASE_DIR, "data", "GOLD_M15.csv")

PIP = 0.01
PTVAL = 0.01

def fetch_m5_mt5():
    if not mt5.initialize(): return None
    mt5.symbol_select("GOLD", True)
    rates = mt5.copy_rates_from_pos("GOLD", mt5.TIMEFRAME_M5, 0, 50000)
    mt5.shutdown()
    if rates is None or len(rates) == 0: return None
    df = pd.DataFrame(rates)
    df['dt'] = pd.to_datetime(df['time'], unit='s')
    df.sort_values('dt', inplace=True)
    df.reset_index(drop=True, inplace=True)
    return df

def run_checkpoint_v9_m5_scalper(df, risk_pct=0.02):
    c = df['close'].values; h = df['high'].values; l = df['low'].values; o = df['open'].values
    v = df['tick_volume'].values if 'tick_volume' in df.columns else df['vol'].values
    n = len(df)
    if n < 500: return None
    
    tr = np.maximum(h[1:]-l[1:], np.maximum(abs(h[1:]-c[:-1]), abs(l[1:]-c[:-1])))
    tr = np.insert(tr, 0, tr[0])
    atr14 = pd.Series(tr).rolling(14).mean().bfill().values
    
    # Fast M5 EMAs
    ema5  = pd.Series(c).ewm(span=5,  adjust=False).mean().values
    ema13 = pd.Series(c).ewm(span=13, adjust=False).mean().values
    
    # Macro Guard (EMA 2400 M5 = EMA 200 H1)
    ema_macro = pd.Series(c).ewm(span=2400, adjust=False).mean().values
    
    # Tick Volume Z-score
    vol_mean = pd.Series(v).rolling(50).mean().bfill().values
    vol_std  = pd.Series(v).rolling(50).std().bfill().values + 1e-9
    vol_z    = (v - vol_mean) / vol_std
    
    buy_sig  = np.zeros(n, dtype=bool)
    sell_sig = np.zeros(n, dtype=bool)
    
    for i in range(100, n):
        av = max(atr14[i], 1.5)
        lwick = min(o[i], c[i]) - l[i]
        uwick = h[i] - max(o[i], c[i])
        body  = abs(c[i] - o[i]) + 1e-9
        
        macro_bull = c[i] > ema_macro[i]
        macro_bear = c[i] < ema_macro[i]
        
        vol_spike  = vol_z[i] >= 1.2
        pin_buy    = (lwick >= 1.2 * body) and (c[i] > o[i])
        pin_sell   = (uwick >= 1.2 * body) and (c[i] < o[i])
        ema_turn_up = (ema5[i] >= ema13[i]) and (ema5[i-1] < ema13[i-1])
        ema_turn_dn = (ema5[i] <= ema13[i]) and (ema5[i-1] > ema13[i-1])
        
        if macro_bull and vol_spike and pin_buy and ema_turn_up:
            buy_sig[i] = True
        elif macro_bear and vol_spike and pin_sell and ema_turn_dn:
            sell_sig[i] = True

    bal = 1000.0; pk = 1000.0; max_dd = 0.0
    trades = []
    last_trade = -9999
    cooldown = 12 # 12 M5 bars (1 hour cooldown)
    pos_dir = 0; pos_en = 0.0; pos_sl = 0.0; pos_tp = 0.0; pos_lot = 0.0
    
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
                av = max(atr14[i], 1.5); sp = 25.0
                sl_pts = (av * 1.2 / PIP) + sp
                tp_pts = (av * 2.5 / PIP)
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
        'bal': bal, 'pnl_pct': pnl_pct, 'max_dd': max_dd,
        'trades': len(trades), 'wr': wr, 'pf': pf
    }

def main():
    df_m5 = fetch_m5_mt5()
    if df_m5 is None: return
    
    print("="*105)
    print("CHECKPOINT 9 — FAST M5 TICK-VOLUME SCALPING ENGINE BENCHMARK")
    print("Dataset: MT5 Realtime GOLD M5 (50,000 Bars, Nov 2025 - Jul 2026) | Initial Capital: $1,000.00 USD")
    print("="*105)
    
    r9 = run_checkpoint_v9_m5_scalper(df_m5, risk_pct=0.02)
    
    s9 = "✅" if r9['pnl_pct'] > 0 else "❌"
    
    print(f"{'Model':<42} | {'Final $':<11} {'PnL %':<9} {'MaxDD %':<8} {'Trades':<6} {'WR %':<6} {'PF':<5}")
    print("-" * 105)
    print(f"{'CP9: Fast M5 Tick-Volume Scalper':<42} | ${r9['bal']:<10,.2f} {r9['pnl_pct']:>+7.1f}%  {r9['max_dd']:<8.1f} {r9['trades']:<6} {r9['wr']:<6.1f} {r9['pf']:<5.2f} {s9}")

if __name__ == '__main__':
    main()
