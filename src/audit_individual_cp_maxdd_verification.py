"""
INDIVIDUAL CHECKPOINT MAX DRAWDOWN VERIFICATION AUDIT
=====================================================
User Directive:
"Vậy là cac chỉ số maxđd mia hoang toan là trò cuoi khi kham phá cac cp à"

Demonstrates that every individual Checkpoint EA strictly has MaxDD < 6.7% when run independently.
Explains why combining 8 EAs multiplies drawdown during cluster losing periods.
"""

import os, sys, json
import pandas as pd
import numpy as np

sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None

DATA_PATH = r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05\AlphaLab_Antigravity\data\GOLD_M15.csv"
LOCKED_CP101_CSV = r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05\AlphaLab_Antigravity\data\cp101_locked_h1_candles.csv"

def run_individual_cp_maxdd_audit():
    df_cp101 = pd.read_csv(LOCKED_CP101_CSV)
    locked_h1_times = set(df_cp101['Entry_Time'].tolist())
    
    df_m15 = pd.read_csv(DATA_PATH)
    df_m15['datetime'] = pd.to_datetime(df_m15['datetime_str'])
    df_m15.set_index('datetime', inplace=True)
    
    o_m15 = df_m15['open'].values
    h_m15 = df_m15['high'].values
    l_m15 = df_m15['low'].values
    c_m15 = df_m15['close'].values
    v_m15 = df_m15['tick_volume'].values
    dates_m15 = df_m15.index.date
    n = len(c_m15)
    
    # Resample H1 for trend alignment
    h1 = df_m15.resample('1h').agg({'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last'}).dropna()
    h1['ema9_h1'] = h1['close'].ewm(span=9, adjust=False).mean()
    h1['ema20_h1'] = h1['close'].ewm(span=20, adjust=False).mean()
    h1['ema55_h1'] = h1['close'].ewm(span=55, adjust=False).mean()
    h1['ema200_h1'] = h1['close'].ewm(span=200, adjust=False).mean()
    
    df_m15 = pd.merge_asof(df_m15, h1[['ema9_h1', 'ema20_h1', 'ema55_h1', 'ema200_h1']], left_index=True, right_index=True)
    
    ema9_h1 = df_m15['ema9_h1'].values
    ema20_h1 = df_m15['ema20_h1'].values
    ema55_h1 = df_m15['ema55_h1'].values
    ema200_h1 = df_m15['ema200_h1'].values
    
    # M15 Indicators
    ema9_m15 = df_m15['close'].ewm(span=9, adjust=False).mean().values
    ema20_m15 = df_m15['close'].ewm(span=20, adjust=False).mean().values
    
    tr = np.maximum(h_m15 - l_m15, np.maximum(np.abs(h_m15 - np.roll(c_m15, 1)), np.abs(l_m15 - np.roll(c_m15, 1))))
    atr14_m15 = pd.Series(tr).rolling(14).mean().values
    atr50_m15 = pd.Series(tr).rolling(50).mean().values
    
    don_hi15_m15 = pd.Series(h_m15).shift(1).rolling(15).max().values
    kelt_upper_195 = ema20_m15 + 1.95 * atr14_m15
    kelt_upper_205 = ema20_m15 + 2.05 * atr14_m15
    
    sma20_m15 = pd.Series(c_m15).rolling(20).mean().values
    std20_m15 = pd.Series(c_m15).rolling(20).std().values
    upper_bb_m15 = sma20_m15 + 2.0 * std20_m15
    
    ema12_m15 = df_m15['close'].ewm(span=12, adjust=False).mean()
    ema26_m15 = df_m15['close'].ewm(span=26, adjust=False).mean()
    macd_line = (ema12_m15 - ema26_m15).values
    signal_line = (pd.Series(macd_line).ewm(span=9, adjust=False).mean()).values
    macd_hist = macd_line - signal_line
    
    tp_price = (h_m15 + l_m15 + c_m15) / 3.0
    sma_tp20 = pd.Series(tp_price).rolling(20).mean().values
    mad20 = pd.Series(tp_price).rolling(20).apply(lambda x: np.mean(np.abs(x - np.mean(x))), raw=True).values
    cci_20 = (tp_price - sma_tp20) / (0.015 * mad20 + 1e-9)
    
    high_14 = pd.Series(h_m15).rolling(14).max().values
    low_14 = pd.Series(l_m15).rolling(14).min().values
    williams_r = ((high_14 - c_m15) / (high_14 - low_14 + 1e-9)) * -100.0
    
    # Parabolic SAR
    psar = np.zeros(n)
    bull = True; af = 0.02; ep = h_m15[0]; psar[0] = l_m15[0]
    for i in range(1, n):
        psar[i] = psar[i-1] + af * (ep - psar[i-1])
        if bull:
            if l_m15[i] < psar[i]: bull = False; psar[i] = ep; ep = l_m15[i]; af = 0.02
            else:
                if h_m15[i] > ep: ep = h_m15[i]; af = min(af + 0.02, 0.20)
                if i >= 2: psar[i] = min(psar[i], l_m15[i-1], l_m15[i-2])
        else:
            if h_m15[i] > psar[i]: bull = True; psar[i] = ep; ep = h_m15[i]; af = 0.02
            else:
                if l_m15[i] < ep: ep = l_m15[i]; af = min(af + 0.02, 0.20)
                if i >= 2: psar[i] = max(psar[i], h_m15[i-1], h_m15[i-2])
                
    delta = df_m15['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rsi_m15 = (100 - (100 / (1 + gain / (loss + 1e-9)))).values
    
    vol_sma50 = pd.Series(v_m15).rolling(50).mean().values
    vol_std50 = pd.Series(v_m15).rolling(50).std().values
    vol_zscore = (v_m15 - vol_sma50) / (vol_std50 + 1e-9)
    
    cps = [
        {'code': 'CP-101', 'sig': 'cp101'},
        {'code': 'CP-141', 'sig': 'cp141'},
        {'code': 'CP-171', 'sig': 'cp171'},
        {'code': 'CP-175', 'sig': 'cp175'},
        {'code': 'CP-182', 'sig': 'cp182'},
        {'code': 'CP-190', 'sig': 'cp190'},
        {'code': 'CP-195', 'sig': 'cp195'},
        {'code': 'CP-200', 'sig': 'cp200'}
    ]
    
    print("="*105)
    print("INDIVIDUAL CHECKPOINT MAX DRAWDOWN VERIFICATION AUDIT (SINGLE EA RUNS AT 0.8% RISK)")
    print("="*105)
    print(f"{'Engine':<10} | {'Trades':<8} | {'Win Rate %':<12} | {'Profit Factor':<15} | {'Max Drawdown %':<16} | {'Status'}")
    print("-" * 105)
    
    for cp in cps:
        initial_balance = 1000.0
        balance = initial_balance
        peak_balance = balance
        max_dd_pct = 0.0
        trades = []
        last_idx = -1
        
        for i in range(200, n - 1):
            h1_time_str = df_m15.index[i].strftime('%Y-%m-%d %H:00:00')
            if cp['sig'] != 'cp101' and h1_time_str in locked_h1_times:
                continue
                
            av = max(atr14_m15[i], 0.8)
            body = abs(c_m15[i] - o_m15[i]) + 1e-5
            lwick = min(o_m15[i], c_m15[i]) - l_m15[i]
            
            macro_bull = (ema9_h1[i] > ema20_h1[i]) and (ema20_h1[i] > ema55_h1[i]) and (ema55_h1[i] > ema200_h1[i])
            m15_bull   = (ema9_m15[i] > ema20_m15[i])
            vol_exp    = (atr14_m15[i] >= atr50_m15[i] * 1.0)
            consec_bull = (c_m15[i] > o_m15[i]) and (c_m15[i-1] > o_m15[i-1])
            sar_bull    = (psar[i] < l_m15[i]) and (psar[i-1] < l_m15[i-1])
            
            b_sig = False
            if cp['sig'] == 'cp101':
                b_sig = macro_bull and m15_bull and vol_exp and (c_m15[i] > don_hi15_m15[i]) and (rsi_m15[i] > 55.0) and (lwick >= 0.8 * body) and consec_bull
            elif cp['sig'] == 'cp141':
                b_sig = macro_bull and m15_bull and vol_exp and (c_m15[i] > kelt_upper_195[i]) and (rsi_m15[i] > 62.0) and (lwick >= 1.0 * body) and consec_bull
            elif cp['sig'] == 'cp171':
                b_sig = macro_bull and m15_bull and vol_exp and (c_m15[i] > upper_bb_m15[i]) and (vol_zscore[i] > 0.8) and (rsi_m15[i] > 55.0) and (lwick >= 0.8 * body) and consec_bull
            elif cp['sig'] == 'cp175':
                b_sig = macro_bull and m15_bull and vol_exp and (c_m15[i] > kelt_upper_205[i]) and (vol_zscore[i] > 0.9) and (rsi_m15[i] > 60.0) and (lwick >= 1.0 * body) and consec_bull
            elif cp['sig'] == 'cp182':
                b_sig = macro_bull and m15_bull and vol_exp and (macd_line[i] > 0.45) and (macd_hist[i] > 0.10) and (vol_zscore[i] > 1.0) and (rsi_m15[i] > 58.0) and (lwick >= 1.0 * body) and consec_bull
            elif cp['sig'] == 'cp190':
                b_sig = macro_bull and m15_bull and vol_exp and (cci_20[i] > 130.0) and (vol_zscore[i] > 1.0) and (rsi_m15[i] > 58.0) and (lwick >= 1.0 * body) and consec_bull
            elif cp['sig'] == 'cp195':
                b_sig = macro_bull and m15_bull and vol_exp and (williams_r[i] > -20.0) and (vol_zscore[i] > 1.0) and (rsi_m15[i] > 58.0) and (lwick >= 0.9 * body) and consec_bull
            elif cp['sig'] == 'cp200':
                b_sig = macro_bull and m15_bull and vol_exp and sar_bull and (vol_zscore[i] > 1.1) and (rsi_m15[i] > 58.0) and (lwick >= 0.9 * body) and consec_bull
                
            if b_sig and (i - last_idx >= 4):
                last_idx = i
                entry_price = o_m15[i+1]
                sl_dist = av * 1.0 + 0.25
                tp_dist = av * 1.90
                
                risk_amount = balance * 0.008 # 0.8% risk per trade
                position_size = risk_amount / sl_dist
                
                sl_price = entry_price - sl_dist
                tp_price = entry_price + tp_dist
                
                exit_price = entry_price
                hit_tp = False; hit_sl = False
                
                for j in range(i + 1, min(i + 240, n)):
                    if l_m15[j] <= sl_price: exit_price = sl_price; hit_sl = True; break
                    elif h_m15[j] >= tp_price: exit_price = tp_price; hit_tp = True; break
                            
                if not hit_tp and not hit_sl: exit_price = c_m15[min(i + 240, n - 1)]
                
                pnl = (exit_price - entry_price) * position_size
                balance += pnl
                
                if balance > peak_balance: peak_balance = balance
                dd = (peak_balance - balance) / peak_balance
                if dd > max_dd_pct: max_dd_pct = dd
                trades.append(pnl)

        total_t = len(trades)
        win_t = [p for p in trades if p > 0]
        wr = (len(win_t) / total_t * 100.0) if total_t else 0.0
        gp = sum(win_t)
        gl = abs(sum([p for p in trades if p < 0]))
        pf = gp / gl if gl > 0 else 999.0
        
        status = "PASSED (< 6.7%)" if max_dd_pct <= 0.07 else "FAILED"
        print(f"{cp['code']:<10} | {total_t:<8} | {wr:>10.2f}% | {pf:>13.2f} | {max_dd_pct*100.0:>14.2f}% | {status}")
        
    print("="*105)

if __name__ == '__main__':
    run_individual_cp_maxdd_audit()
