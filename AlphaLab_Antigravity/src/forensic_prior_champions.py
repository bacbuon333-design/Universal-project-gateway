import os
import sys
import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')

DATA_DIR = r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05\AlphaLab_Antigravity\data"

def load_data(filename):
    path = os.path.join(DATA_DIR, filename)
    df = pd.read_csv(path)
    dt_col = 'datetime_str' if 'datetime_str' in df.columns else 'dt'
    df['dt'] = pd.to_datetime(df[dt_col])
    df = df.sort_values('dt').reset_index(drop=True)
    return df

def test_cp101_engine_on_data(df, name="GOLD_H1", pip_size=0.01, spread=25.0, pessimistic_fill=True):
    # df has dt, open, high, low, close, tick_volume
    o = df['open'].values
    h = df['high'].values
    l = df['low'].values
    c = df['close'].values
    v = df['tick_volume'].values
    dt = df['dt']
    n = len(c)
    
    if n < 250:
        return None
        
    ema9 = pd.Series(c).ewm(span=9, adjust=False).mean().values
    ema20 = pd.Series(c).ewm(span=20, adjust=False).mean().values
    ema55 = pd.Series(c).ewm(span=55, adjust=False).mean().values
    ema200 = pd.Series(c).ewm(span=200, adjust=False).mean().values
    
    # Volume Z-score
    v_s = pd.Series(v)
    vol_mean = v_s.rolling(48).mean().values
    vol_std = v_s.rolling(48).std().values
    vol_zscore = (v - vol_mean) / (vol_std + 1e-9)
    
    # RSI 14
    delta = pd.Series(c).diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / (loss + 1e-9)
    rsi = (100 - (100 / (1 + rs))).values
    
    # ATR 14 & ATR 50
    tr = np.maximum(h - l, np.maximum(np.abs(h - np.roll(c, 1)), np.abs(l - np.roll(c, 1))))
    atr14 = pd.Series(tr).rolling(14).mean().values
    atr50 = pd.Series(tr).rolling(50).mean().values
    
    # Donchian & Keltner
    don_hi5 = pd.Series(h).shift(1).rolling(5).max().values
    kelt_upper = ema20 + 1.5 * atr14
    
    # ADX 14
    up_move = pd.Series(h).diff()
    down_move = -pd.Series(l).diff()
    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)
    atr_s = pd.Series(tr)
    plus_di = 100 * (pd.Series(plus_dm).rolling(14).mean() / (atr_s.rolling(14).mean() + 1e-9))
    minus_di = 100 * (pd.Series(minus_dm).rolling(14).mean() / (atr_s.rolling(14).mean() + 1e-9))
    dx = 100 * (np.abs(plus_di - minus_di) / (plus_di + minus_di + 1e-9))
    adx = dx.rolling(14).mean().values
    
    hours = dt.dt.hour.values
    quarters = dt.dt.to_period('Q').astype(str).values
    
    trades = []
    
    # Let's track positions properly with a non-overlapping or single active position model
    active_trade = None
    
    for i in range(200, n - 1):
        # 1. Manage active trade
        if active_trade is not None:
            # Check exit on bar i
            entry = active_trade['entry']
            sl = active_trade['sl']
            tp = active_trade['tp']
            
            # Pessimistic execution: If both SL and TP in bar range, SL hit first
            hit_sl = (l[i] <= sl)
            hit_tp = (h[i] >= tp)
            
            closed = False
            exit_price = 0.0
            exit_reason = ''
            
            if hit_sl and hit_tp:
                if pessimistic_fill:
                    exit_price = sl
                    exit_reason = 'SL (Ambiguous Bar -> Pessimistic SL)'
                    closed = True
                else:
                    exit_price = tp
                    exit_reason = 'TP (Optimistic)'
                    closed = True
            elif hit_sl:
                exit_price = sl
                exit_reason = 'SL'
                closed = True
            elif hit_tp:
                exit_price = tp
                exit_reason = 'TP'
                closed = True
            elif i - active_trade['entry_bar'] >= 120:
                exit_price = c[i]
                exit_reason = 'TIME_EXIT'
                closed = True
                
            if closed:
                pnl_pts = (exit_price - entry) / pip_size
                pnl_usd = (pnl_pts * 0.01 * (active_trade['lots'] / 0.01)) - (active_trade['lots'] / 0.01) * 0.07
                active_trade['exit_bar'] = i
                active_trade['exit_dt'] = dt.iloc[i]
                active_trade['exit_price'] = exit_price
                active_trade['exit_reason'] = exit_reason
                active_trade['pnl'] = pnl_usd
                active_trade['pnl_pts'] = pnl_pts
                trades.append(active_trade)
                active_trade = None
                
        # 2. Check entry signal at close of bar i (executed at open of i+1)
        if active_trade is None and i < n - 1:
            macro_bull = (ema9[i] > ema20[i]) and (ema20[i] > ema55[i]) and (ema55[i] > ema200[i])
            adx_ultra = (adx[i] >= 18.0)
            vol_z_ultra = (vol_zscore[i] >= 0.1)
            vol_exp = (atr14[i] >= atr50[i] * 1.0)
            consec_bull = (c[i] > o[i]) and (c[i-1] > o[i-1])
            body = abs(c[i] - o[i]) + 1e-5
            lwick = min(o[i], c[i]) - l[i]
            wick_ok = (lwick >= 0.8 * body)
            
            sig = False
            # London rule
            hr = hours[i]
            if (hr >= 7 and hr <= 10) and macro_bull and adx_ultra and vol_z_ultra and vol_exp and (c[i] > don_hi5[i]) and (rsi[i] > 50) and wick_ok and consec_bull:
                sig = True
                tp_mult = 2.10
                sl_mult = 1.0
            # NY rule
            elif (hr >= 13 and hr <= 16) and macro_bull and adx_ultra and vol_z_ultra and vol_exp and (c[i] > kelt_upper[i]) and (rsi[i] > 50) and wick_ok and consec_bull:
                sig = True
                tp_mult = 2.20
                sl_mult = 1.0
                
            if sig:
                av = max(atr14[i], 1.5)
                entry_p = o[i+1] + (spread * pip_size) # Account for spread on buy entry
                sl_dist = av * sl_mult
                tp_dist = av * tp_mult
                sl_p = entry_p - sl_dist
                tp_p = entry_p + tp_dist
                
                lots = 0.10 # Standardized fixed lot for clean signal expectancy measurement
                
                active_trade = {
                    'entry_bar': i + 1,
                    'entry_dt': dt.iloc[i+1],
                    'quarter': quarters[i+1],
                    'entry': entry_p,
                    'sl': sl_p,
                    'tp': tp_p,
                    'lots': lots,
                    'year': dt.iloc[i+1].year
                }

    tdf = pd.DataFrame(trades)
    return tdf

def analyze_trades(tdf, title="Strategy"):
    print(f"\n=======================================================")
    print(f"RESULTS FOR: {title}")
    print(f"=======================================================")
    if tdf is None or len(tdf) == 0:
        print("Zero trades generated.")
        return
        
    n_trades = len(tdf)
    wins = tdf[tdf['pnl'] > 0]
    losses = tdf[tdf['pnl'] < 0]
    wr = len(wins) / n_trades * 100
    tot_pnl = tdf['pnl'].sum()
    gross_win = wins['pnl'].sum()
    gross_loss = abs(losses['pnl'].sum())
    pf = gross_win / gross_loss if gross_loss > 0 else 999.0
    avg_trade = tdf['pnl'].mean()
    
    print(f"Total Trades : {n_trades}")
    print(f"Win Rate     : {wr:.2f}% ({len(wins)} wins / {len(losses)} losses)")
    print(f"Total PnL    : ${tot_pnl:,.2f}")
    print(f"Profit Factor: {pf:.3f}")
    print(f"Avg Trade PnL: ${avg_trade:.2f}")
    
    # Quarterly breakdown
    print(f"\n--- QUARTERLY BREAKDOWN ---")
    q_stats = []
    for q, grp in tdf.groupby('quarter'):
        q_n = len(grp)
        q_w = len(grp[grp['pnl'] > 0])
        q_wr = q_w / q_n * 100 if q_n > 0 else 0
        q_pnl = grp['pnl'].sum()
        q_gw = grp[grp['pnl'] > 0]['pnl'].sum()
        q_gl = abs(grp[grp['pnl'] < 0]['pnl'].sum())
        q_pf = q_gw / q_gl if q_gl > 0 else (999.0 if q_gw > 0 else 0.0)
        q_stats.append({
            'Quarter': q,
            'Trades': q_n,
            'WR%': f"{q_wr:.1f}%",
            'PnL ($)': f"${q_pnl:+,.2f}",
            'PF': f"{q_pf:.2f}",
            'Verdict': 'PASS' if q_pnl > 0 else 'FAIL'
        })
    qdf = pd.DataFrame(q_stats)
    print(qdf.to_string(index=False))
    
    pass_count = sum(1 for q in q_stats if q['Verdict'] == 'PASS')
    total_q = len(q_stats)
    print(f"\nQuarterly Robustness: {pass_count}/{total_q} quarters profitable ({pass_count/total_q*100:.1f}%)")

def main():
    # 1. Test on GOLD_H1_2001_2026 (Full 25-year history)
    df_gold_h1 = load_data("GOLD_H1_2001_2026.csv")
    print(f"Loaded GOLD_H1_2001_2026: {len(df_gold_h1):,} bars from {df_gold_h1['dt'].min()} to {df_gold_h1['dt'].max()}")
    
    tdf_gold_full = test_cp101_engine_on_data(df_gold_h1, "GOLD_H1_2001_2026 (Full History)")
    analyze_trades(tdf_gold_full, "CP-101 Style Strategy on GOLD_H1 (2001-2026 Full History)")
    
    # 2. Test specifically on In-Sample (2022-2026) vs Out-Of-Sample (2001-2021)
    if tdf_gold_full is not None and len(tdf_gold_full) > 0:
        tdf_is = tdf_gold_full[tdf_gold_full['year'] >= 2022]
        tdf_oos = tdf_gold_full[tdf_gold_full['year'] < 2022]
        analyze_trades(tdf_is, "CP-101 Style on In-Sample Period (2022-2026)")
        analyze_trades(tdf_oos, "CP-101 Style on True Out-Of-Sample Period (2001-2021)")
        
    # 3. Test on other assets (EURUSD, GBPUSD, USDJPY)
    for fx in ["EURUSD_H1.csv", "GBPUSD_H1.csv", "USDJPY_H1.csv"]:
        df_fx = load_data(fx)
        pip = 0.0001 if 'JPY' not in fx else 0.01
        spr = 15.0 if 'JPY' not in fx else 18.0
        tdf_fx = test_cp101_engine_on_data(df_fx, fx, pip_size=pip, spread=spr)
        analyze_trades(tdf_fx, f"CP-101 Style Strategy on {fx} (Cross-Asset OOS)")

if __name__ == '__main__':
    main()
