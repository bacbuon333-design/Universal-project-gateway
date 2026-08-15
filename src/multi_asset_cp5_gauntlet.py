"""
MULTI-ASSET CROSS-VALIDATION GAUNTLET FOR CHECKPOINT 5
======================================================
Tests Checkpoint 5 (Key Structure Reaction Zone Sweep Engine) across multiple asset classes:
1. XAUUSD (Gold - Commodities)
2. EURUSD (Euro / US Dollar - Major FX)
3. GBPUSD (British Pound / US Dollar - Major FX)
4. USDJPY (US Dollar / Japanese Yen - Major FX)
5. BTCUSD (Bitcoin / US Dollar - Crypto)

Objective: Verify structural alpha across diverse asset regimes (Zero Overfitting Test).
Execution includes full realistic spread + commission + slippage for each asset.
"""

import os, sys
sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None
import numpy as np
import pandas as pd
import MetaTrader5 as mt5

BASE_DIR = r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05\AlphaLab_Antigravity"

ASSET_SPECS = {
    'XAUUSD': {'pip': 0.01,   'ptval': 0.01,    'sp_pips': 25.0, 'comm_001': 0.07, 'slip_pips': 5.0},
    'EURUSD': {'pip': 0.0001, 'ptval': 0.00010, 'sp_pips': 1.0,  'comm_001': 0.07, 'slip_pips': 0.2},
    'GBPUSD': {'pip': 0.0001, 'ptval': 0.00010, 'sp_pips': 1.2,  'comm_001': 0.07, 'slip_pips': 0.2},
    'USDJPY': {'pip': 0.01,   'ptval': 0.00067, 'sp_pips': 1.2,  'comm_001': 0.07, 'slip_pips': 0.2},
    'BTCUSD': {'pip': 1.0,    'ptval': 0.01,    'sp_pips': 35.0, 'comm_001': 0.07, 'slip_pips': 5.0}
}

def fetch_asset_data(symbol):
    local_path = os.path.join(BASE_DIR, "data", f"{symbol}_H1.csv")
    if os.path.exists(local_path):
        df = pd.read_csv(local_path)
        col = 'datetime_str' if 'datetime_str' in df.columns else df.columns[0]
        df['dt'] = pd.to_datetime(df[col])
        df.sort_values('dt', inplace=True)
        df.reset_index(drop=True, inplace=True)
        return df
        
    # Otherwise fetch from MT5
    if not mt5.initialize(): return None
    rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H1, 0, 75000)
    mt5.shutdown()
    if rates is None or len(rates) == 0: return None
    
    df = pd.DataFrame(rates)
    df['dt'] = pd.to_datetime(df['time'], unit='s')
    df['datetime_str'] = df['dt'].astype(str)
    df.sort_values('dt', inplace=True)
    df.reset_index(drop=True, inplace=True)
    
    # Save locally
    os.makedirs(os.path.join(BASE_DIR, "data"), exist_ok=True)
    df.to_csv(local_path, index=False)
    return df

def run_cp5_asset(df, spec, risk_pct=0.025):
    c = df['close'].values; h = df['high'].values; l = df['low'].values; o = df['open'].values
    dt = df['dt'].values; n = len(df)
    if n < 500: return None
    
    pip = spec['pip']; ptval = spec['ptval']; sp = spec['sp_pips']
    comm = spec['comm_001']; slip = spec['slip_pips']
    
    tr = np.maximum(h[1:]-l[1:], np.maximum(abs(h[1:]-c[:-1]), abs(l[1:]-c[:-1])))
    tr = np.insert(tr, 0, tr[0])
    atr14 = pd.Series(tr).rolling(14).mean().bfill().values
    
    ema50  = pd.Series(c).ewm(span=50,  adjust=False).mean().values
    ema200 = pd.Series(c).ewm(span=200, adjust=False).mean().values
    
    hi48 = pd.Series(h).shift(1).rolling(48).max().values
    lo48 = pd.Series(l).shift(1).rolling(48).min().values
    
    mom3m = np.zeros(n, dtype=bool)
    for i in range(1440, n): mom3m[i] = c[i] > c[i-1440] if i >= 1440 else True
    
    buy_sig  = np.zeros(n, dtype=bool)
    sell_sig = np.zeros(n, dtype=bool)
    
    for i in range(48, n):
        av = max(atr14[i], 10.0 * pip)
        lwick = min(o[i], c[i]) - l[i]
        uwick = h[i] - max(o[i], c[i])
        body  = abs(c[i] - o[i]) + 1e-9
        
        macro_bull = mom3m[i] and c[i] > ema200[i]
        macro_bear = (not mom3m[i]) and c[i] < ema200[i]
        
        sweep_lo = l[i] <= lo48[i] + 0.5 * av
        pin_lo   = lwick >= 1.5 * body
        sweep_hi = h[i] >= hi48[i] - 0.5 * av
        pin_hi   = uwick >= 1.5 * body
        
        if macro_bull and (sweep_lo or (pin_lo and l[i] <= ema50[i])): buy_sig[i] = True
        elif macro_bear and (sweep_hi or (pin_hi and h[i] >= ema50[i])): sell_sig[i] = True

    bal = 1000.0; pk = 1000.0; max_dd = 0.0
    trades = []
    last_trade = -9999
    cooldown = 24
    pos_dir = 0; pos_en = 0.0; pos_sl = 0.0; pos_tp = 0.0; pos_lot = 0.0
    
    for i in range(50, n-1):
        if pos_dir != 0:
            done = False; ep = c[i]
            if pos_dir == 1:
                if l[i] <= pos_sl: ep = pos_sl - slip * pip; done = True
                elif h[i] >= pos_tp: ep = pos_tp; done = True
            else:
                if h[i] >= pos_sl: ep = pos_sl + slip * pip; done = True
                elif l[i] <= pos_tp: ep = pos_tp; done = True
                    
            if done:
                pts = (ep - pos_en)/pip if pos_dir==1 else (pos_en - ep)/pip
                gross = pts * ptval * (pos_lot / 0.01)
                fee   = (sp * pip/pip) * ptval * (pos_lot/0.01) + (pos_lot/0.01)*comm
                net   = gross - fee
                bal   = max(0.0, bal + net)
                pk    = max(pk, bal)
                dd    = (pk - bal) / pk * 100.0 if pk > 0 else 0
                max_dd = max(max_dd, dd)
                trades.append(net)
                pos_dir = 0
                
        if pos_dir == 0 and (i - last_trade >= cooldown) and bal > 0:
            sig = 0
            if buy_sig[i]: sig = 1
            elif sell_sig[i]: sig = -1
            
            if sig != 0:
                av = max(atr14[i], 10.0 * pip)
                sl_pts = (av * 2.0 / pip) + sp
                tp_pts = (av * 4.5 / pip)
                
                risk_amt = bal * risk_pct
                lot = max(0.01, min(round(risk_amt / (sl_pts * ptval) * 0.01, 2), 20.0))
                
                next_o = o[i+1]
                half_sp = (sp * pip) / 2.0
                
                if sig == 1:
                    pos_dir = 1; pos_en = next_o + half_sp; pos_sl = pos_en - sl_pts * pip; pos_tp = pos_en + tp_pts * pip; pos_lot = lot
                else:
                    pos_dir = -1; pos_en = next_o - half_sp; pos_sl = pos_en + sl_pts * pip; pos_tp = pos_en - tp_pts * pip; pos_lot = lot
                last_trade = i

    wins = [t for t in trades if t > 0]
    loss = [t for t in trades if t < 0]
    pf = sum(wins)/abs(sum(loss)) if loss and sum(loss)!=0 else 0
    wr = len(wins)/max(len(trades),1)*100
    pnl_pct = (bal - 1000.0) / 10.0
    
    return {
        'start_dt': str(df['dt'].iloc[0])[:10],
        'end_dt': str(df['dt'].iloc[-1])[:10],
        'bars': n, 'bal': bal, 'pnl_pct': pnl_pct, 'max_dd': max_dd,
        'trades': len(trades), 'wr': wr, 'pf': pf
    }

def main():
    print("="*105)
    print("MULTI-ASSET CROSS-VALIDATION GAUNTLET FOR CHECKPOINT 5 (REACTION ZONE SWEEP ENGINE)")
    print("Testing Structural Alpha across 5 Asset Classes | Initial Capital: $1,000.00 USD | Risk: 2.5%")
    print("="*105)
    print(f"{'Symbol':<8} | {'Asset Class':<14} | {'Data Range':<23} | {'Bars':<6} | {'Final $':<10} {'PnL %':<9} {'MaxDD %':<8} {'Trades':<6} {'PF':<5}")
    print("-" * 105)
    
    asset_types = {
        'XAUUSD': 'Commodities (Gold)',
        'EURUSD': 'Major Forex (Euro)',
        'GBPUSD': 'Major Forex (Pound)',
        'USDJPY': 'Major Forex (Yen)',
        'BTCUSD': 'Crypto (Bitcoin)'
    }
    
    for sym in ['XAUUSD', 'EURUSD', 'GBPUSD', 'USDJPY', 'BTCUSD']:
        df = fetch_asset_data(sym)
        if df is None:
            print(f"{sym:<8} | {asset_types[sym]:<14} | Data Fetch Error / Symbol Unavailable")
            continue
            
        res = run_cp5_asset(df, ASSET_SPECS[sym], risk_pct=0.025)
        if res is None: continue
        
        status = "✅" if res['pnl_pct'] > 0 else "❌"
        range_str = f"{res['start_dt']} to {res['end_dt']}"
        print(f"{sym:<8} | {asset_types[sym]:<14} | {range_str:<23} | {res['bars']:<6} | ${res['bal']:<9,.2f} {res['pnl_pct']:>+7.1f}%  {res['max_dd']:<8.1f} {res['trades']:<6} {res['pf']:<5.2f} {status}")

if __name__ == '__main__':
    main()
