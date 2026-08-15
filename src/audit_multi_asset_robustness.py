"""
MULTI-ASSET CROSS-VALIDATION & HYBRID ROBUSTNESS AUDIT
======================================================
User Directive:
"Tiếp tục nghiên cứu các CP khác kết hợp mix biến thể hỗn thể. Tôi đang tổng hợp các CP tốt nếu backtest qua các thị trường khác ngoài vàng mà kết quả k tốt thì cần xem lại"

Validates structural breakout engines across 5 major financial assets:
1. XAUUSD (Gold)
2. EURUSD (Euro / US Dollar)
3. GBPUSD (British Pound / US Dollar)
4. USDJPY (US Dollar / Japanese Yen)
5. BTCUSD (Bitcoin / US Dollar)
"""

import os, sys
import pandas as pd
import numpy as np

sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None

DATA_DIR = r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05\AlphaLab_Antigravity\data"

ASSETS = {
    'XAUUSD (Gold)': os.path.join(DATA_DIR, 'GOLD_H1_2010_2026.csv'),
    'EURUSD (Euro)': os.path.join(DATA_DIR, 'EURUSD_H1.csv'),
    'GBPUSD (Pound)': os.path.join(DATA_DIR, 'GBPUSD_H1.csv'),
    'USDJPY (Yen)': os.path.join(DATA_DIR, 'USDJPY_H1.csv'),
    'BTCUSD (Bitcoin)': os.path.join(DATA_DIR, 'BTCUSD_H1.csv')
}

def backtest_hybrid_engine_on_asset(asset_name, file_path):
    if not os.path.exists(file_path):
        return None
        
    df = pd.read_csv(file_path)
    
    # Standardize datetime column
    date_col = 'datetime_str' if 'datetime_str' in df.columns else ('datetime' if 'datetime' in df.columns else 'time')
    df['datetime'] = pd.to_datetime(df[date_col])
    df.set_index('datetime', inplace=True)
    df.sort_index(inplace=True)
    
    o = df['open'].values
    h = df['high'].values
    l = df['low'].values
    c = df['close'].values
    n = len(c)
    
    if n < 500:
        return None
        
    # Indicators
    ema9 = df['close'].ewm(span=9, adjust=False).mean().values
    ema20 = df['close'].ewm(span=20, adjust=False).mean().values
    ema55 = df['close'].ewm(span=55, adjust=False).mean().values
    ema200 = df['close'].ewm(span=200, adjust=False).mean().values
    
    tr = np.maximum(h - l, np.maximum(np.abs(h - np.roll(c, 1)), np.abs(l - np.roll(c, 1))))
    atr14 = pd.Series(tr).rolling(14).mean().values
    atr50 = pd.Series(tr).rolling(50).mean().values
    
    don_hi20 = pd.Series(h).shift(1).rolling(20).max().values
    
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rsi = (100 - (100 / (1 + gain / (loss + 1e-9)))).values
    
    initial_balance = 1000.0
    balance = initial_balance
    peak_balance = balance
    max_dd_pct = 0.0
    
    trades = []
    last_trade_idx = -1
    
    for i in range(200, n - 1):
        current_dd = (peak_balance - balance) / peak_balance if peak_balance > 0 else 0.0
        
        if current_dd >= 0.05:
            risk_pct = 0.005
        else:
            if balance >= 3000.0:
                risk_pct = 0.012
            elif balance >= 1800.0:
                risk_pct = 0.010
            else:
                risk_pct = 0.008
                
        av = max(atr14[i], 0.0005 if 'USD' in asset_name and 'XAU' not in asset_name and 'BTC' not in asset_name else 0.8)
        body = abs(c[i] - o[i]) + 1e-5
        lwick = min(o[i], c[i]) - l[i]
        
        macro_bull = (ema9[i] > ema20[i]) and (ema20[i] > ema55[i]) and (ema55[i] > ema200[i])
        vol_exp    = (atr14[i] >= atr50[i] * 0.95)
        consec_bull = (c[i] > o[i]) and (c[i-1] > o[i-1])
        
        # Hybrid Asset-Agnostic Breakout Signal
        b_sig = macro_bull and vol_exp and (c[i] > don_hi20[i]) and (rsi[i] > 52.0) and (lwick >= 0.7 * body) and consec_bull
        
        if b_sig and (i - last_trade_idx >= 4): # 4-hour cooldown
            last_trade_idx = i
            entry_price = o[i+1]
            sl_dist = av * 1.2
            tp_dist = av * 2.20
            
            risk_amount = balance * risk_pct
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
            
            if balance > peak_balance: peak_balance = balance
            dd = (peak_balance - balance) / peak_balance
            if dd > max_dd_pct: max_dd_pct = dd
                
            trades.append({'pnl': pnl, 'balance': balance})
            
    win_trades = [t for t in trades if t['pnl'] > 0]
    win_rate = (len(win_trades) / len(trades)) * 100.0 if trades else 0
    gross_profit = sum([t['pnl'] for t in win_trades])
    gross_loss = abs(sum([t['pnl'] for t in trades if t['pnl'] < 0]))
    pf = gross_profit / gross_loss if gross_loss > 0 else 999.0
    net_yield_pct = ((balance - initial_balance) / initial_balance) * 100.0
    
    return {
        'asset': asset_name,
        'trades': len(trades),
        'net_pnl_pct': net_yield_pct,
        'win_rate': win_rate,
        'pf': pf,
        'max_dd': max_dd_pct * 100.0,
        'final_balance': balance
    }

def run_multi_asset_robustness_audit():
    results = []
    print("="*105)
    print("MULTI-ASSET CROSS-VALIDATION ROBUSTNESS AUDIT REPORT")
    print("="*105)
    
    for name, path in ASSETS.items():
        res = backtest_hybrid_engine_on_asset(name, path)
        if res:
            results.append(res)
            print(f"Asset: {res['asset']:<20} | Trades: {res['trades']:>4} | Net PnL: {res['net_pnl_pct']:>+7.2f}% | WR: {res['win_rate']:>5.2f}% | PF: {res['pf']:>4.2f} | MaxDD: {res['max_dd']:>5.2f}%")
            
    print("-" * 105)
    
    df_res = pd.DataFrame(results)
    profitable_assets = df_res[df_res['net_pnl_pct'] > 0]
    pass_wr_assets = df_res[df_res['win_rate'] >= 45.0]
    
    print(f"Total Assets Tested               : {len(results)} ASSETS")
    print(f"Assets with Positive Net Profit   : {len(profitable_assets)} / {len(results)} ASSETS ({len(profitable_assets)/len(results)*100:.1f}%)")
    print(f"Assets with Win Rate >= 45.0%     : {len(pass_wr_assets)} / {len(results)} ASSETS ({len(pass_wr_assets)/len(results)*100:.1f}%)")
    print("="*105)

if __name__ == '__main__':
    run_multi_asset_robustness_audit()
