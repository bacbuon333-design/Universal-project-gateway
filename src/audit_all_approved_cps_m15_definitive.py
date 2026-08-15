"""
100% DEFINITIVE HIGH-PRECISION M15 BACKTEST MATRIX FOR ALL APPROVED CPS
========================================================================
User Directive:
"Ồ v thì mang toàn bộ các cp đi đánh giá lại lần nữa với M15 backtest để cho ra kết quả chính xác đi"

Evaluates all approved Checkpoints on high-precision M15 data (GOLD_M15.csv):
1. CP-101: Anchor Base Engine
2. CP-119: M15 Donchian Engine
3. CP-127: Strict 45%+ Win Rate Engine
4. CP-141: M15 Keltner Upper Envelope Engine
5. CP-151: High Volume Engine
6. CP-155: Victory Master Engine
7. CP-160: 50%+ Net Profit Master Engine
8. CP-163: 100%+ Net Profit Master Engine
9. CP-165: 150%+ Net Profit Master Engine
"""

import os, sys
import pandas as pd
import numpy as np

sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None

DATA_PATH = r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05\AlphaLab_Antigravity\data\GOLD_M15.csv"

def run_all_cps_m15_definitive_matrix():
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
    don_hi12_m15 = pd.Series(h_m15).shift(1).rolling(12).max().values
    kelt_upper_m15 = ema20_m15 + 1.95 * atr14_m15
    
    delta = df_m15['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rsi_m15 = (100 - (100 / (1 + gain / (loss + 1e-9)))).values
    
    cps = [
        {'code': 'CP-101', 'name': 'Anchor Base Engine', 'sig': 'don15_m15', 'rsi': 55.0, 'tp': 1.95, 'risk_type': 'fixed', 'base_risk': 0.008},
        {'code': 'CP-119', 'name': 'M15 Donchian Engine', 'sig': 'don15_m15', 'rsi': 55.0, 'tp': 1.95, 'risk_type': 'fixed', 'base_risk': 0.008},
        {'code': 'CP-127', 'name': 'Strict 45%+ WR Engine', 'sig': 'don15_m15', 'rsi': 53.0, 'tp': 1.95, 'risk_type': 'fixed', 'base_risk': 0.008},
        {'code': 'CP-141', 'name': 'M15 Keltner Upper Engine', 'sig': 'kelt_m15', 'rsi': 62.0, 'tp': 1.62, 'risk_type': 'fixed', 'base_risk': 0.008},
        {'code': 'CP-151', 'name': 'High Volume Engine', 'sig': 'don12_m15', 'rsi': 54.0, 'tp': 1.95, 'risk_type': 'fixed', 'base_risk': 0.008},
        {'code': 'CP-155', 'name': 'Victory Master Engine', 'sig': 'don15_m15', 'rsi': 55.0, 'tp': 1.95, 'risk_type': 'fixed', 'base_risk': 0.008},
        {'code': 'CP-160', 'name': '50%+ Net Profit Master', 'sig': 'don15_m15', 'rsi': 54.5, 'tp': 2.00, 'risk_type': 'compounding_50', 'base_risk': 0.012},
        {'code': 'CP-163', 'name': '100%+ Net Profit Master', 'sig': 'don15_m15', 'rsi': 54.5, 'tp': 2.05, 'risk_type': 'compounding_100', 'base_risk': 0.020},
        {'code': 'CP-165', 'name': '150%+ Net Profit Master', 'sig': 'don15_m15', 'rsi': 54.5, 'tp': 2.05, 'risk_type': 'compounding_150', 'base_risk': 0.026}
    ]
    
    results = []
    
    print("="*105)
    print("100% DEFINITIVE HIGH-PRECISION M15 BACKTEST MATRIX REPORT FOR ALL APPROVED CPS")
    print("="*105)
    
    for cp in cps:
        initial_balance = 1000.0
        balance = initial_balance
        peak_balance = balance
        max_dd_pct = 0.0
        trades = []
        last_idx = -1
        
        for i in range(200, n - 1):
            current_dd = (peak_balance - balance) / peak_balance if peak_balance > 0 else 0.0
            
            # Risk Sizing Rules
            if cp['risk_type'] == 'fixed':
                if current_dd >= 0.05: risk_pct = 0.005
                else:
                    if balance >= 3000.0: risk_pct = 0.012
                    elif balance >= 1800.0: risk_pct = 0.010
                    else: risk_pct = 0.008
            elif cp['risk_type'] == 'compounding_50':
                if current_dd >= 0.06: risk_pct = 0.007
                else:
                    if balance >= 3000.0: risk_pct = 0.016
                    elif balance >= 1800.0: risk_pct = 0.014
                    else: risk_pct = 0.012
            elif cp['risk_type'] == 'compounding_100':
                if current_dd >= 0.08: risk_pct = 0.010
                else:
                    if balance >= 3000.0: risk_pct = 0.024
                    elif balance >= 1800.0: risk_pct = 0.022
                    else: risk_pct = 0.020
            elif cp['risk_type'] == 'compounding_150':
                if current_dd >= 0.10: risk_pct = 0.015
                else:
                    if balance >= 3500.0: risk_pct = 0.030
                    elif balance >= 2000.0: risk_pct = 0.028
                    else: risk_pct = 0.026
                    
            av = max(atr14_m15[i], 0.8)
            body = abs(c_m15[i] - o_m15[i]) + 1e-5
            lwick = min(o_m15[i], c_m15[i]) - l_m15[i]
            
            macro_bull = (ema9_h1[i] > ema20_h1[i]) and (ema20_h1[i] > ema55_h1[i]) and (ema55_h1[i] > ema200_h1[i])
            m15_bull   = (ema9_m15[i] > ema20_m15[i])
            vol_exp    = (atr14_m15[i] >= atr50_m15[i] * 1.0)
            consec_bull = (c_m15[i] > o_m15[i]) and (c_m15[i-1] > o_m15[i-1])
            
            b_sig = False
            if cp['sig'] == 'don15_m15':
                b_sig = macro_bull and m15_bull and vol_exp and (c_m15[i] > don_hi15_m15[i]) and (rsi_m15[i] > cp['rsi']) and (lwick >= 0.8 * body) and consec_bull
            elif cp['sig'] == 'don12_m15':
                b_sig = macro_bull and m15_bull and vol_exp and (c_m15[i] > don_hi12_m15[i]) and (rsi_m15[i] > cp['rsi']) and (lwick >= 0.8 * body) and consec_bull
            elif cp['sig'] == 'kelt_m15':
                b_sig = macro_bull and m15_bull and vol_exp and (c_m15[i] > kelt_upper_m15[i]) and (rsi_m15[i] > cp['rsi']) and (lwick >= 1.0 * body) and consec_bull
                
            if b_sig and (i - last_idx >= 4):
                last_idx = i
                entry_price = o_m15[i+1]
                sl_dist = av * 1.0 + 0.25
                tp_dist = av * cp['tp']
                
                risk_amount = balance * risk_pct
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
                
        win_trades = [p for p in trades if p > 0]
        win_rate = (len(win_trades) / len(trades)) * 100.0 if trades else 0
        gross_profit = sum(win_trades)
        gross_loss = abs(sum([p for p in trades if p < 0]))
        pf = gross_profit / gross_loss if gross_loss > 0 else 999.0
        net_yield_pct = ((balance - initial_balance) / initial_balance) * 100.0
        
        wr_status = "PASSED (>=45%)" if win_rate >= 45.0 else "FAIL (<45%)"
        pf_status = "PASSED (>=1.40)" if pf >= 1.40 else "FAIL (<1.40)"
        
        results.append({
            'code': cp['code'],
            'name': cp['name'],
            'trades': len(trades),
            'balance': balance,
            'net_pnl_pct': net_yield_pct,
            'win_rate': win_rate,
            'pf': pf,
            'max_dd': max_dd_pct * 100.0
        })
        
        print(f"CP: {cp['code']:<7} ({cp['name']:<24}) | Trades: {len(trades):>4} | Bal: ${balance:>8,.2f} | PnL: {net_yield_pct:>+8.2f}% | WR: {win_rate:>5.2f}% ({wr_status}) | PF: {pf:>4.2f} | MaxDD: {max_dd_pct*100.0:>5.2f}%")
        
    print("="*105)

if __name__ == '__main__':
    run_all_cps_m15_definitive_matrix()
