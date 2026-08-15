import sys, os
import pandas as pd
import numpy as np

# Load CP66 engine logic and inspect trades
from checkpoint_v66_flawless_4targets_victory import DATA_PATH

def audit_cp66_trade_overlap():
    df_m15 = pd.read_csv(DATA_PATH)
    df_m15['datetime'] = pd.to_datetime(df_m15['datetime_str'])
    df_m15.set_index('datetime', inplace=True)
    
    h1 = df_m15.resample('1h').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'tick_volume': 'sum'
    }).dropna()
    
    o = h1['open'].values
    h = h1['high'].values
    l = h1['low'].values
    c = h1['close'].values
    v = h1['tick_volume'].values
    times = h1.index.astype(str).values
    dates = h1.index.date
    n = len(c)
    
    # Indicators
    ema9 = h1['close'].ewm(span=9, adjust=False).mean().values
    ema20 = h1['close'].ewm(span=20, adjust=False).mean().values
    ema55 = h1['close'].ewm(span=55, adjust=False).mean().values
    ema200 = h1['close'].ewm(span=200, adjust=False).mean().values
    
    ema12 = h1['close'].ewm(span=12, adjust=False).mean()
    ema26 = h1['close'].ewm(span=26, adjust=False).mean()
    macd_line = ema12 - ema26
    signal_line = macd_line.ewm(span=9, adjust=False).mean()
    macd_hist = (macd_line - signal_line).values
    
    vol_mean = pd.Series(v).rolling(48).mean().values
    vol_std = pd.Series(v).rolling(48).std().values
    vol_zscore = (v - vol_mean) / (vol_std + 1e-9)
    
    delta = h1['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / (loss + 1e-9)
    rsi = (100 - (100 / (1 + rs))).values
    
    tr = np.maximum(h - l, np.maximum(np.abs(h - np.roll(c, 1)), np.abs(l - np.roll(c, 1))))
    atr14 = pd.Series(tr).rolling(14).mean().values
    atr50 = pd.Series(tr).rolling(50).mean().values
    
    kelt_upper = ema20 + 1.5 * atr14
    don_hi20 = pd.Series(h).shift(1).rolling(20).max().values
    don_hi5  = pd.Series(h).shift(1).rolling(5).max().values
    
    up_move = h1['high'].diff()
    down_move = -h1['low'].diff()
    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)
    
    atr_series = pd.Series(tr)
    plus_di = 100 * (pd.Series(plus_dm).rolling(14).mean() / atr_series.rolling(14).mean())
    minus_di = 100 * (pd.Series(minus_dm).rolling(14).mean() / atr_series.rolling(14).mean())
    dx = 100 * (np.abs(plus_di - minus_di) / (plus_di + minus_di + 1e-9))
    adx = dx.rolling(14).mean().values
    
    trades = []
    
    for i in range(200, n - 1):
        av = max(atr14[i], 1.5)
        body = abs(c[i] - o[i]) + 1e-5
        lwick = min(o[i], c[i]) - l[i]
        
        signal = 0
        sl_mult = 1.0
        tp_mult = 2.20
        engine_name = ""
        
        macro_bull = (ema9[i] > ema20[i]) and (ema20[i] > ema55[i]) and (ema55[i] > ema200[i])
        adx_ultra = (adx[i] >= 28.0)
        vol_z_ultra = (vol_zscore[i] >= 0.7)
        vol_exp = (atr14[i] >= atr50[i] * 1.02)
        macd_ok = (macd_hist[i] > 0.05)
        consec_bull = (c[i] > o[i]) and (c[i-1] > o[i-1])
        
        b1 = macro_bull and (adx[i] >= 24.0) and (vol_zscore[i] >= 0.3) and vol_exp and (c[i] > don_hi5[i]) and (rsi[i] > 54) and (lwick >= 0.8 * body)
        b2 = macro_bull and (adx[i] >= 26.0) and vol_z_ultra and vol_exp and macd_ok and (c[i] > kelt_upper[i]) and (rsi[i] > 58) and (lwick >= 1.0 * body) and consec_bull
        b3 = macro_bull and (adx[i] >= 26.0) and vol_exp and (c[i] > kelt_upper[i]) and (c[i] > don_hi20[i]) and (rsi[i] > 54) and (lwick >= 0.8 * body) and consec_bull
        pb_buy = (l[i] <= ema20[i] + 0.3 * av) and (c[i] >= ema20[i] - 0.2 * av) and (lwick >= 0.8 * body) and (rsi[i] > 56) and consec_bull
        b4 = macro_bull and (adx[i] >= 26.0) and vol_exp and pb_buy
        
        if b1:
            signal = 1; tp_mult = 2.10; sl_mult = 1.0; engine_name = "CP66_Donchian5Buy"
        elif b2:
            signal = 1; tp_mult = 2.20; sl_mult = 1.0; engine_name = "CP66_PinbarKeltnerBuy"
        elif b3:
            signal = 1; tp_mult = 2.40; sl_mult = 1.1; engine_name = "CP66_Donchian20Buy"
        elif b4:
            signal = 1; tp_mult = 2.25; sl_mult = 1.0; engine_name = "CP66_2CandlePullbackBuy"
            
        if signal == 1:
            trades.append({
                'index': i,
                'datetime': times[i],
                'date': str(dates[i]),
                'engine': engine_name
            })
            
    df_trades = pd.DataFrame(trades)
    
    print("="*80)
    print("AUDIT TRADING DATES & OVERLAPPING TRADES IN CP-66")
    print("="*80)
    print(f"Total Trades Generated: {len(df_trades)}")
    
    # Check trades per day
    daily_counts = df_trades.groupby('date').size()
    max_trades_per_day = daily_counts.max()
    days_with_multiple_trades = daily_counts[daily_counts > 1]
    
    print(f"Total Unique Trading Days: {len(daily_counts)}")
    print(f"Max Trades in Single Day: {max_trades_per_day}")
    print(f"Days with >1 Trade: {len(days_with_multiple_trades)} days out of {len(daily_counts)} trading days")
    print("-" * 80)
    
    if len(days_with_multiple_trades) > 0:
        print("Sample Days with >1 Trade:")
        for d in days_with_multiple_trades.index[:10]:
            day_t = df_trades[df_trades['date'] == d]
            print(f"  Date: {d} -> {len(day_t)} trades:")
            for _, r in day_t.iterrows():
                print(f"    - {r['datetime']} | Engine: {r['engine']}")
    else:
        print("PERFECT! ZERO duplicate trading days between entries!")
        
    print("="*80)

if __name__ == '__main__':
    audit_cp66_trade_overlap()
