"""
FORENSIC ANALYSIS OF CP1 LOSING TRADES (2024 - 2026)
===================================================
Analyzes immediate drawdown (MAE - Maximum Adverse Excursion) upon entry
for all losing trades executed by Checkpoint 1 (Baseline) in recent years (2024 - 2026).

Questions answered:
1. Did the trade go negative immediately upon entering (due to spread + immediate adverse move)?
2. How many pips/dollars of immediate drawdown occurred in bars 1, 2, and 3 after entry?
3. How long was the position held before hitting Stop Loss?
"""

import os, sys
sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None
import numpy as np
import pandas as pd

BASE_DIR = r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05\AlphaLab_Antigravity"
DATA_PATH = os.path.join(BASE_DIR, "data", "GOLD_H1_2010_2026.csv")

PIP = 0.01
PTVAL = 0.01
COMM_PER_001 = 0.07

def analyze_losing_trades():
    df = pd.read_csv(DATA_PATH)
    df['dt'] = pd.to_datetime(df['datetime_str'])
    df.sort_values('dt', inplace=True)
    df.reset_index(drop=True, inplace=True)
    
    c = df['close'].values; h = df['high'].values; l = df['low'].values; o = df['open'].values
    dt = df['dt'].values; n = len(df)
    
    tr = np.maximum(h[1:]-l[1:], np.maximum(abs(h[1:]-c[:-1]), abs(l[1:]-c[:-1])))
    tr = np.insert(tr, 0, tr[0])
    atr14 = pd.Series(tr).rolling(14).mean().bfill().values
    
    ema9   = pd.Series(c).ewm(span=9,   adjust=False).mean().values
    ema55  = pd.Series(c).ewm(span=55,  adjust=False).mean().values
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
    
    buy_sig  = (ema9 > ema55) & (ema55 > ema200) & (rsi > 51) & (macd_hist > hist_bb_up)
    sell_sig = (ema9 < ema55) & (ema55 < ema200) & (rsi < 49) & (macd_hist < hist_bb_dn)
    
    bal = 1000.0; pk = 1000.0; max_dd = 0.0
    last_trade = -9999
    cooldown = 12
    pos_dir = 0; pos_en = 0.0; pos_sl = 0.0; pos_tp = 0.0; pos_lot = 0.0
    entry_idx = 0; entry_dt = ""
    
    losing_analysis = []
    
    for i in range(250, n-1):
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
                bal   = max(0.0, bal + net)
                
                # If losing trade in 2024 - 2026, perform immediate MAE analysis
                yr = pd.Timestamp(dt[i]).year
                if net < 0 and yr >= 2024:
                    holding_bars = i - entry_idx
                    
                    # MAE in bar 1, 2, 3 right after entry
                    bar1_idx = min(entry_idx + 1, n - 1)
                    bar2_idx = min(entry_idx + 2, n - 1)
                    bar3_idx = min(entry_idx + 3, n - 1)
                    
                    if pos_dir == 1: # BUY
                        adv1 = pos_en - l[bar1_idx]
                        adv2 = pos_en - min(l[entry_idx:bar2_idx+1])
                        adv3 = pos_en - min(l[entry_idx:bar3_idx+1])
                    else: # SELL
                        adv1 = h[bar1_idx] - pos_en
                        adv2 = max(h[entry_idx:bar2_idx+1]) - pos_en
                        adv3 = max(h[entry_idx:bar3_idx+1]) - pos_en
                        
                    losing_analysis.append({
                        'entry_dt': entry_dt,
                        'exit_dt': dt[i],
                        'dir': 'BUY' if pos_dir == 1 else 'SELL',
                        'lot': pos_lot,
                        'entry_price': pos_en,
                        'sl_price': pos_sl,
                        'exit_price': ep,
                        'loss_usd': net,
                        'holding_h': holding_bars,
                        'mae_bar1_pips': adv1 / PIP,
                        'mae_bar3_pips': adv3 / PIP,
                        'immediate_negative': adv1 > 0 # Did it drop immediately below entry?
                    })
                    
                pos_dir = 0
                
        if pos_dir == 0 and (i - last_trade >= cooldown) and bal > 0:
            sig = 0
            if buy_sig[i]: sig = 1
            elif sell_sig[i]: sig = -1
            
            if sig != 0:
                av = max(atr14[i], 1.5)
                sp = 25.0
                sl_pts = (av * 1.5 / PIP) + sp
                risk_amt = bal * 0.03
                lot = max(0.01, min(round(risk_amt / (sl_pts * 0.01) * 0.01, 2), 20.0))
                
                next_o = o[i+1]
                half_sp = (sp * PIP) / 2.0
                
                pos_dir = sig
                pos_en  = next_o + half_sp if sig==1 else next_o - half_sp
                pos_sl  = pos_en - sl_pts * PIP if sig==1 else pos_en + sl_pts * PIP
                pos_tp  = pos_en + sl_pts * 2.0 * PIP if sig==1 else pos_en - sl_pts * 2.0 * PIP
                pos_lot = lot
                entry_idx = i + 1
                entry_dt  = str(dt[i+1])
                last_trade = i

    df_loss = pd.DataFrame(losing_analysis)
    
    print("="*90)
    print("FORENSIC ANALYSIS: CP1 LOSING TRADES (2024 - 2026)")
    print("="*90)
    print(f"Total Losing Trades Analyzed (2024-2026) : {len(df_loss)}")
    
    immediate_neg = df_loss['immediate_negative'].sum()
    print(f"Trades Negative IMMEDIATELY at Bar 1      : {immediate_neg} / {len(df_loss)} ({immediate_neg/len(df_loss)*100:.1f}%)")
    print(f"Average Immediate Drawdown in Bar 1      : {df_loss['mae_bar1_pips'].mean():.1f} pips (${df_loss['mae_bar1_pips'].mean()*0.01:.2f}/oz)")
    print(f"Average Drawdown within First 3 Hours    : {df_loss['mae_bar3_pips'].mean():.1f} pips (${df_loss['mae_bar3_pips'].mean()*0.01:.2f}/oz)")
    print(f"Average Holding Time Before Hit SL       : {df_loss['holding_h'].mean():.1f} hours")

    print("\n📋 SAMPLE RECENT LOSING TRADES WITH IMMEDIATE DRAWDOWN METRICS:")
    print(f"{'Entry Time':<19} {'Dir':<5} {'Entry':<8} {'SL':<8} {'Loss $':<8} {'Hold(h)':<7} {'Bar1 MAE(p)':<12} {'Bar3 MAE(p)':<12} {'Immediate Red?'}")
    print("-" * 105)
    for idx, r in df_loss.tail(12).iterrows():
        is_red = "YES 🔴" if r['immediate_negative'] else "NO 🟢"
        print(f"{r['entry_dt']:<19} {r['dir']:<5} {r['entry_price']:<8.2f} {r['sl_price']:<8.2f} ${r['loss_usd']:<7.2f} {r['holding_h']:<7} {r['mae_bar1_pips']:<12.1f} {r['mae_bar3_pips']:<12.1f} {is_red}")

if __name__ == '__main__':
    analyze_losing_trades()
