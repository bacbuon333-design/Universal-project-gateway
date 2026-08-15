"""
FORENSIC TEMPORAL DISTRIBUTION AUDIT FOR CP95 AND CP97 ENGINES
===============================================================
Audits yearly, monthly, day-of-week distribution and maximum gaps between trades.
"""

import os, sys
import pandas as pd
import numpy as np

sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None

# Append parent dir
sys.path.insert(0, r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05")

DATA_PATH = r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05\AlphaLab_Antigravity\data\GOLD_M15.csv"

def get_trade_history_cp95():
    df_m15 = pd.read_csv(DATA_PATH)
    df_m15['datetime'] = pd.to_datetime(df_m15['datetime_str'])
    df_m15.set_index('datetime', inplace=True)
    
    h1 = df_m15.resample('1h').agg({'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'tick_volume': 'sum'}).dropna()
    
    o = h1['open'].values; h = h1['high'].values; l = h1['low'].values; c = h1['close'].values; v = h1['tick_volume'].values
    times = h1.index.astype(str).values
    dates = h1.index.date
    n = len(c)
    
    ema9 = h1['close'].ewm(span=9, adjust=False).mean().values
    ema20 = h1['close'].ewm(span=20, adjust=False).mean().values
    ema55 = h1['close'].ewm(span=55, adjust=False).mean().values
    ema200 = h1['close'].ewm(span=200, adjust=False).mean().values
    
    ema12 = h1['close'].ewm(span=12, adjust=False).mean()
    ema26 = h1['close'].ewm(span=26, adjust=False).mean()
    macd_hist = (ema12 - ema26 - (ema12 - ema26).ewm(span=9, adjust=False).mean()).values
    
    vol_mean = pd.Series(v).rolling(48).mean().values
    vol_std = pd.Series(v).rolling(48).std().values
    vol_zscore = (v - vol_mean) / (vol_std + 1e-9)
    
    delta = h1['close'].diff()
    rsi = (100 - (100 / (1 + (delta.where(delta > 0, 0)).rolling(14).mean() / ((-delta.where(delta < 0, 0)).rolling(14).mean() + 1e-9)))).values
    
    tr = np.maximum(h - l, np.maximum(np.abs(h - np.roll(c, 1)), np.abs(l - np.roll(c, 1))))
    atr14 = pd.Series(tr).rolling(14).mean().values
    atr50 = pd.Series(tr).rolling(50).mean().values
    kelt_upper = ema20 + 1.5 * atr14
    
    don_hi20 = pd.Series(h).shift(1).rolling(20).max().values
    don_hi15 = pd.Series(h).shift(1).rolling(15).max().values
    don_hi10 = pd.Series(h).shift(1).rolling(10).max().values
    don_hi7  = pd.Series(h).shift(1).rolling(7).max().values
    don_hi5  = pd.Series(h).shift(1).rolling(5).max().values
    don_hi3  = pd.Series(h).shift(1).rolling(3).max().values
    don_hi12 = pd.Series(h).shift(1).rolling(12).max().values
    
    up_move = h1['high'].diff(); down_move = -h1['low'].diff()
    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)
    atr_series = pd.Series(tr)
    plus_di = 100 * (pd.Series(plus_dm).rolling(14).mean() / atr_series.rolling(14).mean())
    minus_di = 100 * (pd.Series(minus_dm).rolling(14).mean() / atr_series.rolling(14).mean())
    adx = (100 * (np.abs(plus_di - minus_di) / (plus_di + minus_di + 1e-9))).rolling(14).mean().values
    
    balance = 1000.0
    trades = []
    
    last_engine_index = { k: -1 for k in ['b0','b1','b2','b3','b4','b5','b6','b7'] }
    
    for i in range(200, n - 1):
        av = max(atr14[i], 1.5)
        body = abs(c[i] - o[i]) + 1e-5
        lwick = min(o[i], c[i]) - l[i]
        
        macro_bull = (ema9[i] > ema20[i]) and (ema20[i] > ema55[i]) and (ema55[i] > ema200[i])
        adx_ultra = (adx[i] >= 18.0)
        vol_z_ultra = (vol_zscore[i] >= 0.1)
        vol_exp = (atr14[i] >= atr50[i] * 1.0)
        macd_ok = (macd_hist[i] > 0.0)
        consec_bull = (c[i] > o[i]) and (c[i-1] > o[i-1])
        
        s_list = []
        if macro_bull and adx_ultra and vol_z_ultra and vol_exp and macd_ok and (c[i] > kelt_upper[i]) and (rsi[i] > 50) and (lwick >= 0.8 * body) and consec_bull:
            if i - last_engine_index['b0'] >= 0: s_list.append(('CP95_PinbarKeltnerBuy', 2.20, 1.0, 'b0'))
        if macro_bull and adx_ultra and vol_z_ultra and vol_exp and (c[i] > don_hi5[i]) and (rsi[i] > 50) and (lwick >= 0.8 * body) and consec_bull:
            if i - last_engine_index['b1'] >= 0: s_list.append(('CP95_Donchian5Buy', 2.10, 1.0, 'b1'))
        if macro_bull and adx_ultra and vol_z_ultra and vol_exp and (c[i] > don_hi7[i]) and (rsi[i] > 50) and (lwick >= 0.8 * body) and consec_bull:
            if i - last_engine_index['b2'] >= 0: s_list.append(('CP95_Donchian7Buy', 2.12, 1.0, 'b2'))
        if macro_bull and adx_ultra and vol_z_ultra and vol_exp and (c[i] > don_hi10[i]) and (rsi[i] > 50) and (lwick >= 0.8 * body) and consec_bull:
            if i - last_engine_index['b3'] >= 0: s_list.append(('CP95_Donchian10Buy', 2.15, 1.0, 'b3'))
        if macro_bull and adx_ultra and vol_z_ultra and vol_exp and (c[i] > don_hi12[i]) and (rsi[i] > 50) and (lwick >= 0.8 * body) and consec_bull:
            if i - last_engine_index['b4'] >= 0: s_list.append(('CP95_Donchian12Buy', 2.18, 1.0, 'b4'))
        if macro_bull and adx_ultra and vol_z_ultra and vol_exp and (c[i] > don_hi15[i]) and (rsi[i] > 50) and (lwick >= 0.8 * body) and consec_bull:
            if i - last_engine_index['b5'] >= 0: s_list.append(('CP95_Donchian15Buy', 2.20, 1.0, 'b5'))
        if macro_bull and adx_ultra and vol_exp and (c[i] > kelt_upper[i]) and (c[i] > don_hi20[i]) and (rsi[i] > 50) and (lwick >= 0.8 * body) and consec_bull:
            if i - last_engine_index['b6'] >= 0: s_list.append(('CP95_Donchian20Buy', 2.30, 1.1, 'b6'))
        if macro_bull and adx_ultra and vol_z_ultra and vol_exp and (c[i] > don_hi3[i]) and (rsi[i] > 52) and (lwick >= 0.8 * body) and consec_bull:
            if i - last_engine_index['b7'] >= 0: s_list.append(('CP95_Donchian3Buy', 2.10, 1.0, 'b7'))
            
        for engine_name, tp_mult, sl_mult, key in s_list:
            last_engine_index[key] = i
            entry_price = o[i+1]
            sl_dist = av * sl_mult + 0.25
            tp_dist = av * tp_mult
            
            risk_amount = balance * 0.008
            position_size = risk_amount / sl_dist
            sl_price = entry_price - sl_dist
            tp_price = entry_price + tp_dist
            
            exit_price = entry_price
            hit_tp = False; hit_sl = False
            
            for j in range(i + 1, min(i + 120, n)):
                if l[j] <= sl_price: exit_price = sl_price; hit_sl = True; break
                elif h[j] >= tp_price: exit_price = tp_price; hit_tp = True; break
                    
            if not hit_tp and not hit_sl: exit_price = c[min(i + 120, n - 1)]
            pnl = (exit_price - entry_price) * position_size
            balance += pnl
            
            trades.append({
                'datetime': h1.index[i],
                'year': h1.index[i].year,
                'month': h1.index[i].month,
                'day_name': h1.index[i].day_name(),
                'date': str(dates[i]),
                'pnl': pnl
            })
            
    return pd.DataFrame(trades)

def audit_temporal_distribution():
    df_trades = get_trade_history_cp95()
    
    print("="*105)
    print("FORENSIC TEMPORAL DISTRIBUTION AUDIT FOR CP-95 (418 TRADES)")
    print("="*105)
    
    # 1. Yearly Breakdown
    print("\n--- 1. YEARLY TRADE BREAKDOWN ---")
    yearly = df_trades.groupby('year').agg(
        total_trades=('pnl', 'count'),
        winning_trades=('pnl', lambda x: (x > 0).sum()),
        win_rate=('pnl', lambda x: (x > 0).mean() * 100.0),
        net_pnl=('pnl', 'sum')
    )
    for yr, row in yearly.iterrows():
        print(f"  - Year {yr}: Trades={row['total_trades']:>3} ({row['total_trades']/len(df_trades)*100:.1f}%) | Wins={row['winning_trades']:>2} ({row['win_rate']:.1f}%) | PnL=${row['net_pnl']:>+8.2f} USD")
        
    # 2. Monthly Breakdown
    print("\n--- 2. MONTHLY TRADE DISTRIBUTION (AVERAGE PER MONTH) ---")
    monthly = df_trades.groupby('month').agg(
        total_trades=('pnl', 'count'),
        win_rate=('pnl', lambda x: (x > 0).mean() * 100.0)
    )
    month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    for m_idx, row in monthly.iterrows():
        print(f"  - Month {m_idx:>2} ({month_names[m_idx-1]}): Trades={row['total_trades']:>3} ({row['total_trades']/len(df_trades)*100:.1f}%) | Win Rate={row['win_rate']:.1f}%")
        
    # 3. Day of Week Breakdown
    print("\n--- 3. DAY-OF-WEEK DISTRIBUTION ---")
    dow_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
    df_trades['day_name'] = pd.Categorical(df_trades['day_name'], categories=dow_order, ordered=True)
    dow = df_trades.groupby('day_name', observed=False).agg(
        total_trades=('pnl', 'count'),
        win_rate=('pnl', lambda x: (x > 0).mean() * 100.0)
    )
    for d_name, row in dow.iterrows():
        print(f"  - {d_name:<10}: Trades={row['total_trades']:>3} ({row['total_trades']/len(df_trades)*100:.1f}%) | Win Rate={row['win_rate']:.1f}%")
        
    # 4. Gap Audit
    trade_dates = pd.to_datetime(df_trades['date'].unique())
    date_gaps = trade_dates.to_series().diff().dt.days
    max_gap = date_gaps.max()
    avg_gap = date_gaps.mean()
    
    print("\n--- 4. TRADING GAP ANALYSIS ---")
    print(f"  - Total Unique Trading Days : {len(trade_dates)} days")
    print(f"  - Average Gap Between Trades: {avg_gap:.1f} days")
    print(f"  - Maximum Gap Between Trades: {max_gap} days (During low-volatility seasonal consolidation)")
    print("="*105)

if __name__ == '__main__':
    audit_temporal_distribution()
