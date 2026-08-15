"""
HIGH WIN-RATE OPTIMIZATION LABORATORY TEST
==========================================
Tests adjusting Take Profit multiplier from 4.8x -> 1.8x ATR
to elevate Win Rate from 30% -> 55%+ while preserving Profit Factor and MaxDD <= 18.0%.
"""

import os, sys, math
import pandas as pd
import numpy as np

sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None

DATA_PATH = r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05\AlphaLab_Antigravity\data\GOLD_M15.csv"

def test_high_winrate():
    df_m15 = pd.read_csv(DATA_PATH)
    df_m15['datetime'] = pd.to_datetime(df_m15['datetime_str'])
    df_m15.set_index('datetime', inplace=True)
    
    # Resample to H1
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
    times = h1.index.astype(str).values
    n = len(c)
    
    # Indicators
    ema9 = h1['close'].ewm(span=9, adjust=False).mean().values
    ema20 = h1['close'].ewm(span=20, adjust=False).mean().values
    ema55 = h1['close'].ewm(span=55, adjust=False).mean().values
    ema200 = h1['close'].ewm(span=200, adjust=False).mean().values
    
    # RSI 14
    delta = h1['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / (loss + 1e-9)
    rsi = (100 - (100 / (1 + rs))).values
    
    # ATR 14 & ATR 50
    tr = np.maximum(h - l, np.maximum(np.abs(h - np.roll(c, 1)), np.abs(l - np.roll(c, 1))))
    atr14 = pd.Series(tr).rolling(14).mean().values
    atr50 = pd.Series(tr).rolling(50).mean().values
    
    # Keltner Upper / Lower
    kelt_upper = ema20 + 1.5 * atr14
    kelt_lower = ema20 - 1.5 * atr14
    
    # ADX 14
    up_move = h1['high'].diff()
    down_move = -h1['low'].diff()
    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)
    
    atr_series = pd.Series(tr)
    plus_di = 100 * (pd.Series(plus_dm).rolling(14).mean() / atr_series.rolling(14).mean())
    minus_di = 100 * (pd.Series(minus_dm).rolling(14).mean() / atr_series.rolling(14).mean())
    dx = 100 * (np.abs(plus_di - minus_di) / (plus_di + minus_di + 1e-9))
    adx = dx.rolling(14).mean().values
    
    # Donchian Channels
    don_hi20 = pd.Series(h).shift(1).rolling(20).max().values
    don_lo20 = pd.Series(l).shift(1).rolling(20).min().values
    don_hi48 = pd.Series(h).shift(1).rolling(48).max().values
    don_lo48 = pd.Series(l).shift(1).rolling(48).min().values
    don_hi10 = pd.Series(h).shift(1).rolling(10).max().values
    don_lo10 = pd.Series(l).shift(1).rolling(10).min().values
    
    engines = ['CP14_HighWR', 'CP15_HighWR', 'CP16_HighWR']
    trades_by_engine = {e: [] for e in engines}
    
    initial_balance = 1000.0
    balance = initial_balance
    peak_balance = balance
    max_dd_pct = 0.0
    
    last_cp14_date = ""
    last_cp15_date = ""
    
    for i in range(200, n - 1):
        curr_date = times[i][:10]
        av = max(atr14[i], 1.5)
        body = abs(c[i] - o[i]) + 1e-5
        lwick = min(o[i], c[i]) - l[i]
        uwick = h[i] - max(o[i], c[i])
        
        signal = 0
        tp_mult = 1.8 # Target high win rate TP!
        sl_mult = 1.2
        engine_name = ""
        
        macro_bull = (ema9[i] > ema55[i]) and (ema55[i] > ema200[i])
        macro_bear = (ema9[i] < ema55[i]) and (ema55[i] < ema200[i])
        adx_ok = (adx[i] >= 22.0)
        
        # 1. Strategy 1 (CP-14 High WR Trend Breakout)
        b1 = macro_bull and adx_ok and (c[i] > kelt_upper[i]) and (c[i] > don_hi20[i]) and (rsi[i] > 54) and (lwick >= 0.8 * body)
        s1 = macro_bear and adx_ok and (c[i] < kelt_lower[i]) and (c[i] < don_lo20[i]) and (rsi[i] < 46) and (uwick >= 0.8 * body)
        
        if b1:
            signal = 1; tp_mult = 1.8; engine_name = "CP14_HighWR"; last_cp14_date = curr_date
        elif s1:
            signal = -1; tp_mult = 1.8; engine_name = "CP14_HighWR"; last_cp14_date = curr_date
            
        # 2. Strategy 2 (CP-15 High WR Sweep Reversal)
        elif curr_date != last_cp14_date:
            sweep_lo = (l[i] <= don_lo48[i] + 0.8 * av) and (lwick >= 0.8 * body) and (c[i] > o[i])
            sweep_hi = (h[i] >= don_hi48[i] - 0.8 * av) and (uwick >= 0.8 * body) and (c[i] < o[i])
            
            b2 = (c[i] > ema200[i]) and sweep_lo and (rsi[i] > 40)
            s2 = (c[i] < ema200[i]) and sweep_hi and (rsi[i] < 60)
            
            if b2:
                signal = 1; tp_mult = 1.6; engine_name = "CP15_HighWR"; last_cp15_date = curr_date
            elif s2:
                signal = -1; tp_mult = 1.6; engine_name = "CP15_HighWR"; last_cp15_date = curr_date
                
            # 3. Strategy 3 (CP-16 High WR Squeeze Engine)
            elif curr_date != last_cp15_date:
                squeeze_ok = (atr14[i] <= atr50[i] * 0.95) and adx_ok
                break_hi10 = (c[i] > don_hi10[i]) and (c[i] > kelt_upper[i]) and (rsi[i] > 54)
                break_lo10 = (c[i] < don_lo10[i]) and (c[i] < kelt_lower[i]) and (rsi[i] < 46)
                
                b3 = (c[i] > ema200[i]) and squeeze_ok and break_hi10
                s3 = (c[i] < ema200[i]) and squeeze_ok and break_lo10
                
                if b3:
                    signal = 1; tp_mult = 1.8; engine_name = "CP16_HighWR"
                elif s3:
                    signal = -1; tp_mult = 1.8; engine_name = "CP16_HighWR"
                        
        if signal != 0:
            entry_price = o[i+1]
            sl_dist = av * sl_mult + 0.25 # 25pip spread
            tp_dist = av * tp_mult
            
            risk_amount = balance * 0.02
            position_size = risk_amount / sl_dist
            
            if signal == 1:
                sl_price = entry_price - sl_dist
                tp_price = entry_price + tp_dist
            else:
                sl_price = entry_price + sl_dist
                tp_price = entry_price - tp_dist
                
            exit_price = entry_price
            hit_tp = False
            hit_sl = False
            
            for j in range(i + 1, min(i + 120, n)):
                if signal == 1:
                    if l[j] <= sl_price:
                        exit_price = sl_price; hit_sl = True; break
                    elif h[j] >= tp_price:
                        exit_price = tp_price; hit_tp = True; break
                else:
                    if h[j] >= sl_price:
                        exit_price = sl_price; hit_sl = True; break
                    elif l[j] <= tp_price:
                        exit_price = tp_price; hit_tp = True; break
                        
            if not hit_tp and not hit_sl:
                exit_price = c[min(i + 120, n - 1)]
                
            pnl = (exit_price - entry_price) * position_size if signal == 1 else (entry_price - exit_price) * position_size
            balance += pnl
            
            if balance > peak_balance:
                peak_balance = balance
            dd = (peak_balance - balance) / peak_balance
            if dd > max_dd_pct:
                max_dd_pct = dd
                
            trades_by_engine[engine_name].append({
                'pnl': pnl,
                'sl_dist': sl_dist,
                'tp_dist': tp_dist,
                'hit_tp': hit_tp,
                'hit_sl': hit_sl
            })

    print("="*105)
    print("HIGH WIN-RATE OPTIMIZATION RESULTS (TP = 1.8x ATR)")
    print("="*105)
    print(f"Initial Deposit       : ${initial_balance:,.2f} USD")
    print(f"Final Balance         : ${balance:,.2f} USD")
    print(f"Net Profit %          : {((balance-initial_balance)/initial_balance)*100.0:>+8.2f}% Net Yield")
    print(f"Max Drawdown (MaxDD)  : {max_dd_pct * 100.0:.2f}%")
    print("="*105)
    
    for engine, tr_list in trades_by_engine.items():
        total = len(tr_list)
        wins = [t for t in tr_list if t['pnl'] > 0]
        losses = [t for t in tr_list if t['pnl'] < 0]
        
        wr = (len(wins) / total * 100.0) if total > 0 else 0
        avg_win = np.mean([t['pnl'] for t in wins]) if wins else 0.0
        avg_loss = abs(np.mean([t['pnl'] for t in losses])) if losses else 1e-5
        
        payoff_ratio = avg_win / avg_loss if avg_loss > 0 else 0
        total_profit = sum([t['pnl'] for t in wins])
        total_loss = abs(sum([t['pnl'] for t in losses]))
        pf = total_profit / total_loss if total_loss > 0 else 999.0
        
        print(f"ENGINE: {engine}")
        print(f"  - Total Trades  : {total:>5}")
        print(f"  - Win Rate %    : {wr:>5.2f}% ({len(wins)} Wins / {len(losses)} Losses)")
        print(f"  - Avg Win ($)   : ${avg_win:>+8.2f} USD")
        print(f"  - Avg Loss ($)  : ${avg_loss:>8.2f} USD")
        print(f"  - Payoff (R:R)  : 1 : {payoff_ratio:.2f}")
        print(f"  - Profit Factor : {pf:.2f}")
        print("-" * 105)

if __name__ == '__main__':
    test_high_winrate()
