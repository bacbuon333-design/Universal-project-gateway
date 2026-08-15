"""
USER 3-LAYER M5 GOLD REALTIME TICK VOLUME SYSTEM BENCHMARK
=========================================================
Implements the 3-Layer M5 Tick Volume Architecture:
1. Layer 1: Trend Filter (Price > EMA 200 & VWMA 20)
2. Layer 2: Volume & Momentum Confirmation (Waddah Attar Explosion WAE > Deadzone)
3. Layer 3: Price Action Rejection Filter (Wick Ratio >= 60% / 0.60)

Risk Sizing:
- Dynamic lot calculation ($ risk / SL pips)
- Stop Loss: ATR 14 x 3.0 dynamic multiplier
- Take Profit: 1:1.5 Risk-to-Reward Ratio
- Broker Costs: Spread 25p + Comm $7/lot + Slippage 5p ($0.37/0.01 lot)

Dataset: MT5 Direct GOLD M5 (50,000 Bars, Nov 2025 - Jul 2026, 8.5 Months)
"""

import os, sys
sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None
import numpy as np
import pandas as pd
import MetaTrader5 as mt5

PIP = 0.01
PTVAL = 0.01

def fetch_m5_data():
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

def run_3layer_m5_system(df, risk_pct=0.01):
    c = df['close'].values; h = df['high'].values; l = df['low'].values; o = df['open'].values
    v = df['tick_volume'].values if 'tick_volume' in df.columns else df['vol'].values
    n = len(df)
    
    tr = np.maximum(h[1:]-l[1:], np.maximum(abs(h[1:]-c[:-1]), abs(l[1:]-c[:-1])))
    tr = np.insert(tr, 0, tr[0])
    atr14 = pd.Series(tr).rolling(14).mean().bfill().values
    
    # Layer 1: Trend Filter (EMA 200 & VWMA 20)
    ema200 = pd.Series(c).ewm(span=200, adjust=False).mean().values
    vwma20 = pd.Series(c * v).rolling(20).sum() / (pd.Series(v).rolling(20).sum() + 1e-9)
    vwma20 = vwma20.bfill().values
    
    # Layer 2: Waddah Attar Explosion (WAE)
    ema12 = pd.Series(c).ewm(span=12, adjust=False).mean().values
    ema26 = pd.Series(c).ewm(span=26, adjust=False).mean().values
    macd = ema12 - ema26
    macd_delta = macd - np.roll(macd, 1)
    
    mid20 = pd.Series(c).rolling(20).mean().bfill().values
    std20 = pd.Series(c).rolling(20).std().bfill().values
    bb_width = 2.0 * std20
    
    wae_t1 = macd_delta * 150.0
    deadzone = pd.Series(tr).rolling(100).mean().bfill().values * 0.5
    
    wae_buy_explosion  = (wae_t1 > 0) & (wae_t1 > deadzone)
    wae_sell_explosion = (wae_t1 < 0) & (abs(wae_t1) > deadzone)
    
    # Layer 3: Price Action Wick Ratio >= 60% (0.60)
    range_hl = h - l + 1e-9
    lwick = np.minimum(o, c) - l
    uwick = h - np.maximum(o, c)
    
    wick_ratio_l = lwick / range_hl
    wick_ratio_u = uwick / range_hl
    
    buy_sig  = np.zeros(n, dtype=bool)
    sell_sig = np.zeros(n, dtype=bool)
    
    for i in range(200, n):
        # 1. Trend
        trend_bull = (c[i] > ema200[i]) and (c[i] > vwma20[i])
        trend_bear = (c[i] < ema200[i]) and (c[i] < vwma20[i])
        
        # 2. Volume & Momentum WAE
        vol_buy  = wae_buy_explosion[i]
        vol_sell = wae_sell_explosion[i]
        
        # 3. Wick Ratio >= 60% (0.60)
        rejection_buy  = wick_ratio_l[i] >= 0.60
        rejection_sell = wick_ratio_u[i] >= 0.60
        
        if trend_bull and vol_buy and rejection_buy and c[i] > o[i]:
            buy_sig[i] = True
        elif trend_bear and vol_sell and rejection_sell and c[i] < o[i]:
            sell_sig[i] = True

    # Simulation Engine
    bal = 1000.0; pk = 1000.0; max_dd = 0.0
    trades = []
    last_trade = -9999; cooldown = 6 # 30 mins cooldown
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
                sl_pts = (av * 3.0 / PIP) + sp # ATR x 3.0 SL
                tp_pts = sl_pts * 1.5           # R:R 1:1.5
                
                risk_amt = bal * risk_pct
                risk_per_001 = sl_pts * 0.01
                lot = max(0.01, min(round((risk_amt / risk_per_001) * 0.01, 2), 10.0))
                
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
    df_m5 = fetch_m5_data()
    if df_m5 is None: return
    
    print("="*105)
    print("USER 3-LAYER M5 GOLD REALTIME TICK VOLUME SYSTEM BENCHMARK")
    print("Dataset: MT5 Realtime GOLD M5 (50,000 Bars, Nov 2025 - Jul 2026) | Initial Capital: $1,000.00 USD")
    print("="*105)
    
    res = run_3layer_m5_system(df_m5, risk_pct=0.01)
    s = "✅" if res['pnl_pct'] > 0 else "❌"
    
    print(f"{'System Name':<48} | {'Final $':<11} {'PnL %':<9} {'MaxDD %':<8} {'Trades':<6} {'WR %':<6} {'PF':<5}")
    print("-" * 105)
    print(f"{'User 3-Layer M5 Tick Volume System (WAE+Wick60%)':<48} | ${res['bal']:<10,.2f} {res['pnl_pct']:>+7.1f}%  {res['max_dd']:<8.1f} {res['trades']:<6} {res['wr']:<6.1f} {res['pf']:<5.2f} {s}")

if __name__ == '__main__':
    main()
