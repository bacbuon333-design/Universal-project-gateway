"""
MASTER MULTI-ASSET MATRIX GAUNTLET (5 ASSETS x 6 CHECKPOINTS)
============================================================
Tests ALL 6 Checkpoints across ALL 5 Asset Classes over 70,000 H1 Bars (~11 Years):
1. XAUUSD (Gold - Commodity)
2. EURUSD (Euro / USD - Major FX)
3. GBPUSD (Pound / USD - Major FX)
4. USDJPY (Yen / USD - Major FX)
5. BTCUSD (Bitcoin / USD - Crypto)

Standardized Initial Capital: $1,000.00 USD | Risk: 2.5% Dynamic Equity per Trade
Real Execution Costs included for each asset.
"""

import os, sys
sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None
import numpy as np
import pandas as pd
import MetaTrader5 as mt5

BASE_DIR = r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05\AlphaLab_Antigravity"

ASSET_SPECS = {
    'XAUUSD': {'pip': 0.01,   'pip_val_001': 0.01,  'sp_pips': 25.0, 'comm_001': 0.07, 'slip_pips': 5.0, 'name': 'Gold'},
    'EURUSD': {'pip': 0.0001, 'pip_val_001': 0.10,  'sp_pips': 1.0,  'comm_001': 0.07, 'slip_pips': 0.2, 'name': 'Euro'},
    'GBPUSD': {'pip': 0.0001, 'pip_val_001': 0.10,  'sp_pips': 1.2,  'comm_001': 0.07, 'slip_pips': 0.2, 'name': 'Pound'},
    'USDJPY': {'pip': 0.01,   'pip_val_001': 0.067, 'sp_pips': 1.2,  'comm_001': 0.07, 'slip_pips': 0.2, 'name': 'Yen'},
    'BTCUSD': {'pip': 1.0,    'pip_val_001': 0.01,  'sp_pips': 35.0, 'comm_001': 0.07, 'slip_pips': 5.0, 'name': 'Bitcoin'}
}

def get_asset_df(sym):
    local_path = os.path.join(BASE_DIR, "data", f"{sym}_H1.csv")
    if sym == 'XAUUSD':
        local_path = os.path.join(BASE_DIR, "data", "GOLD_H1_2010_2026.csv")
    if os.path.exists(local_path):
        df = pd.read_csv(local_path)
        col = 'datetime_str' if 'datetime_str' in df.columns else df.columns[0]
        df['dt'] = pd.to_datetime(df[col])
        df.sort_values('dt', inplace=True)
        df.reset_index(drop=True, inplace=True)
        return df
        
    if not mt5.initialize(): return None
    rates = mt5.copy_rates_from_pos(sym, mt5.TIMEFRAME_H1, 0, 70000)
    mt5.shutdown()
    if rates is None or len(rates) == 0: return None
    df = pd.DataFrame(rates)
    df['dt'] = pd.to_datetime(df['time'], unit='s')
    df.sort_values('dt', inplace=True)
    df.reset_index(drop=True, inplace=True)
    return df

def calc_adx_fast(h, l, c, period=14):
    tr_ = np.maximum(h[1:]-l[1:], np.maximum(abs(h[1:]-c[:-1]), abs(l[1:]-c[:-1])))
    tr_ = np.insert(tr_, 0, tr_[0])
    up_ = pd.Series(h).diff().values
    dn_ = -pd.Series(l).diff().values
    pdm = np.where((up_ > dn_) & (up_ > 0), up_, 0.0)
    ndm = np.where((dn_ > up_) & (dn_ > 0), dn_, 0.0)
    atr_ser = pd.Series(tr_).ewm(alpha=1/period, adjust=False).mean()
    pdi = 100 * pd.Series(pdm).ewm(alpha=1/period, adjust=False).mean() / atr_ser.replace(0, 1e-9)
    ndi = 100 * pd.Series(ndm).ewm(alpha=1/period, adjust=False).mean() / atr_ser.replace(0, 1e-9)
    dx = 100 * (pdi - ndi).abs() / (pdi + ndi).replace(0, 1e-9)
    return dx.ewm(alpha=1/period, adjust=False).mean().values

def run_single_checkpoint_asset(df, spec, cp_id=1, risk_pct=0.025):
    c = df['close'].values; h = df['high'].values; l = df['low'].values; o = df['open'].values
    dt = df['dt'].values; n = len(df)
    if n < 500: return None
    
    pip = spec['pip']; pval001 = spec['pip_val_001']; sp = spec['sp_pips']
    comm = spec['comm_001']; slip = spec['slip_pips']
    
    tr = np.maximum(h[1:]-l[1:], np.maximum(abs(h[1:]-c[:-1]), abs(l[1:]-c[:-1])))
    tr = np.insert(tr, 0, tr[0])
    atr14 = pd.Series(tr).rolling(14).mean().bfill().values
    adx14 = calc_adx_fast(h, l, c, 14)
    
    ema9   = pd.Series(c).ewm(span=9,   adjust=False).mean().values
    ema55  = pd.Series(c).ewm(span=55,  adjust=False).mean().values
    ema50  = pd.Series(c).ewm(span=50,  adjust=False).mean().values
    ema200 = pd.Series(c).ewm(span=200, adjust=False).mean().values
    
    d = pd.Series(c).diff()
    up = d.clip(lower=0).ewm(alpha=1/14, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1/14, adjust=False).mean().clip(1e-9)
    rsi = (100 - 100 / (1 + up / dn)).values
    
    ema12 = pd.Series(c).ewm(span=12, adjust=False).mean().values
    ema26 = pd.Series(c).ewm(span=26, adjust=False).mean().values
    macd_line = ema12 - ema26
    signal_line = pd.Series(macd_line).ewm(span=9, adjust=False).mean().values
    macd_hist = macd_line - signal_line
    
    hist_mid = pd.Series(macd_hist).rolling(20).mean().bfill().values
    hist_std = pd.Series(macd_hist).rolling(20).std().bfill().values
    hist_bb_up = hist_mid + 2.0 * hist_std
    hist_bb_dn = hist_mid - 2.0 * hist_std
    
    hours = pd.Series(dt).dt.hour.values
    session_ok = (hours >= 12) & (hours <= 18)
    
    buy_sig = np.zeros(n, dtype=bool)
    sell_sig = np.zeros(n, dtype=bool)
    sl_mult = 1.5; tp_mult = 3.0; cooldown = 12
    
    if cp_id == 1:
        buy_sig  = (ema9 > ema55) & (ema55 > ema200) & (rsi > 51) & (macd_hist > hist_bb_up)
        sell_sig = (ema9 < ema55) & (ema55 < ema200) & (rsi < 49) & (macd_hist < hist_bb_dn)
        sl_mult = 1.5; tp_mult = 3.0; cooldown = 12
    elif cp_id in [2, 3]:
        buy_sig  = (ema9 > ema55) & (ema55 > ema200) & (rsi > 51) & (macd_hist > hist_bb_up) & (adx14 > 20) & session_ok
        sell_sig = (ema9 < ema55) & (ema55 < ema200) & (rsi < 49) & (macd_hist < hist_bb_dn) & (adx14 > 20) & session_ok
        sl_mult = 2.0; tp_mult = 4.0; cooldown = 12
    elif cp_id == 4:
        buy_sig  = (ema9 > ema55) & (ema55 > ema200) & (rsi > 51) & (macd_hist > hist_bb_up) & session_ok
        sell_sig = (ema9 < ema55) & (ema55 < ema200) & (rsi < 49) & (macd_hist < hist_bb_dn) & session_ok
        sl_mult = 2.0; tp_mult = 4.0; cooldown = 12
    elif cp_id == 5:
        hi48 = pd.Series(h).shift(1).rolling(48).max().values
        lo48 = pd.Series(l).shift(1).rolling(48).min().values
        mom3m = np.zeros(n, dtype=bool)
        for i in range(1440, n): mom3m[i] = c[i] > c[i-1440] if i >= 1440 else True
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
        sl_mult = 2.0; tp_mult = 4.5; cooldown = 24
    elif cp_id == 6: # CP6 Upgraded H1+M15
        hi48 = pd.Series(h).shift(1).rolling(48).max().values
        lo48 = pd.Series(l).shift(1).rolling(48).min().values
        mom3m = np.zeros(n, dtype=bool)
        for i in range(1440, n): mom3m[i] = c[i] > c[i-1440] if i >= 1440 else True
        for i in range(48, n):
            av = max(atr14[i], 10.0 * pip)
            lwick = min(o[i], c[i]) - l[i]
            uwick = h[i] - max(o[i], c[i])
            body  = abs(c[i] - o[i]) + 1e-9
            macro_bull = mom3m[i] and c[i] > ema200[i]
            macro_bear = (not mom3m[i]) and c[i] < ema200[i]
            h1_sweep_lo = l[i] <= lo48[i] + 0.5 * av
            h1_sweep_hi = h[i] >= hi48[i] - 0.5 * av
            m15_confirm_buy  = (lwick >= 1.2 * body) and (c[i] > o[i])
            m15_confirm_sell = (uwick >= 1.2 * body) and (c[i] < o[i])
            if macro_bull and h1_sweep_lo and m15_confirm_buy: buy_sig[i] = True
            elif macro_bear and h1_sweep_hi and m15_confirm_sell: sell_sig[i] = True
        sl_mult = 2.0; tp_mult = 4.5; cooldown = 32

    bal = 1000.0; pk = 1000.0; max_dd = 0.0
    trades = []
    last_trade = -9999
    pos_dir = 0; pos_en = 0.0; pos_sl = 0.0; pos_tp = 0.0; pos_lot = 0.0
    
    curr_month = -1; month_start_bal = 1000.0; month_halted = False
    
    for i in range(50, n-1):
        if cp_id == 3: # VaR Circuit Breaker for CP3
            m_now = pd.Timestamp(dt[i]).month
            if m_now != curr_month:
                curr_month = m_now; month_start_bal = bal; month_halted = False
            if month_start_bal > 0 and (month_start_bal - bal) / month_start_bal >= 0.065:
                month_halted = True
            if month_halted:
                if pos_dir != 0: pass
                else: continue
                
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
                gross = pts * pval001 * (pos_lot / 0.01)
                fee   = (sp * pval001) * (pos_lot / 0.01) + (pos_lot / 0.01) * comm
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
                sl_pts = (av * sl_mult / pip) + sp
                tp_pts = (av * tp_mult / pip)
                
                risk_amt = bal * risk_pct
                risk_per_001 = sl_pts * pval001
                lot = max(0.01, min(round((risk_amt / risk_per_001) * 0.01, 2), 50.0))
                
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
    
    return {'bal': bal, 'pnl_pct': pnl_pct, 'max_dd': max_dd, 'trades': len(trades), 'pf': pf}

def main():
    symbols = ['XAUUSD', 'EURUSD', 'GBPUSD', 'USDJPY', 'BTCUSD']
    cp_names = {
        1: 'CP1 Baseline (Old Breakout)',
        2: 'CP2 Upgraded (ADX + Session)',
        3: 'CP3 Prop Firm (ADX + VaR 6.5%)',
        4: 'CP4 Corrected Exact Specs',
        5: 'CP5 Reaction Zone (Vùng Phản Ứng)',
        6: 'CP6 Upgraded (H1+M15 Trigger)'
    }
    
    print("="*115)
    print("MASTER MULTI-ASSET MATRIX GAUNTLET (5 ASSETS x 6 CHECKPOINTS)")
    print("Dataset: ~70,000 H1 Bars (~11 Years) | Initial Capital: $1,000.00 USD | Risk: 2.5% per Trade")
    print("="*115)
    print(f"{'Checkpoint Model':<35} | {'XAUUSD (Gold)':<13} | {'EURUSD (Euro)':<13} | {'GBPUSD (Pound)':<13} | {'USDJPY (Yen)':<13} | {'BTCUSD (BTC)':<13}")
    print("-" * 115)
    
    # Cache asset dfs
    dfs = {}
    for sym in symbols:
        dfs[sym] = get_asset_df(sym)
        
    for cp in [1, 2, 3, 4, 5, 6]:
        row_str = f"{cp_names[cp]:<35} | "
        for sym in symbols:
            df = dfs[sym]
            if df is None:
                row_str += f"{'N/A':<13} | "
                continue
            r = run_single_checkpoint_asset(df, ASSET_SPECS[sym], cp_id=cp, risk_pct=0.025)
            if r is None:
                row_str += f"{'N/A':<13} | "
            else:
                s = "✅" if r['pnl_pct'] > 0 else "❌"
                cell = f"{r['pnl_pct']:>+6.1f}% {s}"
                row_str += f"{cell:<13} | "
        print(row_str)

if __name__ == '__main__':
    main()
