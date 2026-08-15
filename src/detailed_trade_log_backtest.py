"""
DETAILED TRADE LOG & BROKER FEE BREAKDOWN BACKTEST
===================================================
Strategy: Davidd Anthony - 5-Minute Ultimate Scalping (H1 & M15)
Dataset: XAUUSD (2024 - 2025 Full Year & 2010-2026 Deep History)
Cost Parameters:
- Spread = 25 pips ($0.25/oz = $0.25 per 0.01 lot)
- Commission = $0.07 per 0.01 lot ($7 per 1.00 lot)
- Slippage = 5 pips ($0.05/oz = $0.05 per 0.01 lot)
- Total Fee per 0.01 lot = $0.37 USD per trade
"""

import os, sys
sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None
import numpy as np
import pandas as pd

BASE_DIR = r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05\AlphaLab_Antigravity"
H1_PATH  = os.path.join(BASE_DIR, "data", "GOLD_H1_2010_2026.csv")
M15_PATH = os.path.join(BASE_DIR, "data", "GOLD_M15.csv")

PIP = 0.01
PTVAL = 0.01
COMM_PER_001 = 0.07

def run_detailed_backtest(df, timeframe="H1", start_date="2024-05-01", end_date="2025-05-01", risk_mode="fixed_001"):
    mask = (df['datetime_str'] >= start_date) & (df['datetime_str'] < end_date)
    sub = df[mask].copy()
    if len(sub) == 0:
        return
        
    sub.reset_index(drop=True, inplace=True)
    c = sub['close'].values
    h = sub['high'].values
    l = sub['low'].values
    o = sub['open'].values
    dt = sub['datetime_str'].values
    n = len(sub)
    
    # Indicators
    tr = np.maximum(h[1:]-l[1:], np.maximum(abs(h[1:]-c[:-1]), abs(l[1:]-c[:-1])))
    tr = np.insert(tr, 0, tr[0])
    atr14 = pd.Series(tr).rolling(14).mean().bfill().values
    
    ema9   = pd.Series(c).ewm(span=9,   adjust=False).mean().values
    ema55  = pd.Series(c).ewm(span=55,  adjust=False).mean().values
    ema200 = pd.Series(c).ewm(span=200, adjust=False).mean().values
    
    # RSI 14
    d = pd.Series(c).diff()
    up = d.clip(lower=0).ewm(alpha=1/14, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1/14, adjust=False).mean().clip(1e-9)
    rsi = (100 - 100 / (1 + up / dn)).values
    
    # MACD (12, 26, 9)
    ema12 = pd.Series(c).ewm(span=12, adjust=False).mean().values
    ema26 = pd.Series(c).ewm(span=26, adjust=False).mean().values
    macd_line = ema12 - ema26
    signal_line = pd.Series(macd_line).ewm(span=9, adjust=False).mean().values
    macd_hist = macd_line - signal_line
    
    # Bollinger Bands on MACD Histogram (20, 2.0)
    hist_mid = pd.Series(macd_hist).rolling(20).mean().bfill().values
    hist_std = pd.Series(macd_hist).rolling(20).std().bfill().values
    hist_bb_up = hist_mid + 2.0 * hist_std
    hist_bb_dn = hist_mid - 2.0 * hist_std
    
    buy_sig  = (ema9 > ema55) & (ema55 > ema200) & (rsi > 51) & (macd_hist > hist_bb_up)
    sell_sig = (ema9 < ema55) & (ema55 < ema200) & (rsi < 49) & (macd_hist < hist_bb_dn)
    
    bal = 1000.0; pk = 1000.0; max_dd = 0.0
    trades_log = []
    last_trade = -9999
    cooldown = 12 if timeframe == "H1" else 24
    
    pos_dir = 0; pos_en = 0.0; pos_sl = 0.0; pos_tp = 0.0; pos_lot = 0.0
    pos_en_dt = ""; pos_sl_pts = 0.0
    
    total_spread_fee = 0.0
    total_comm_fee = 0.0
    total_slip_fee = 0.0
    
    for i in range(250, n-1):
        if pos_dir != 0:
            done = False
            ep = c[i]
            reason = ""
            
            if pos_dir == 1:
                if l[i] <= pos_sl:
                    ep = pos_sl - 5.0 * PIP # 5 pip slippage
                    done = True
                    reason = "STOP LOSS"
                elif h[i] >= pos_tp:
                    ep = pos_tp
                    done = True
                    reason = "TAKE PROFIT"
            else:
                if h[i] >= pos_sl:
                    ep = pos_sl + 5.0 * PIP
                    done = True
                    reason = "STOP LOSS"
                elif l[i] <= pos_tp:
                    ep = pos_tp
                    done = True
                    reason = "TAKE PROFIT"
                    
            if done:
                pts = (ep - pos_en)/PIP if pos_dir==1 else (pos_en - ep)/PIP
                gross_pnl = pts * PTVAL * (pos_lot / 0.01)
                
                spread_fee = (25.0 * PIP / PIP) * PTVAL * (pos_lot / 0.01) # $0.25 per 0.01 lot
                comm_fee   = (pos_lot / 0.01) * COMM_PER_001 # $0.07 per 0.01 lot
                slip_fee   = (5.0 * PIP / PIP) * PTVAL * (pos_lot / 0.01) # $0.05 per 0.01 lot
                total_fee  = spread_fee + comm_fee + slip_fee
                
                total_spread_fee += spread_fee
                total_comm_fee   += comm_fee
                total_slip_fee   += slip_fee
                
                net_pnl = gross_pnl - total_fee
                bal = max(0.0, bal + net_pnl)
                pk  = max(pk, bal)
                dd  = (pk - bal) / pk * 100.0 if pk > 0 else 0
                max_dd = max(max_dd, dd)
                
                trades_log.append({
                    'entry_dt': pos_en_dt,
                    'exit_dt': dt[i],
                    'dir': 'BUY' if pos_dir == 1 else 'SELL',
                    'lot': pos_lot,
                    'entry': pos_en,
                    'exit': ep,
                    'gross_pnl': gross_pnl,
                    'fee': total_fee,
                    'net_pnl': net_pnl,
                    'balance': bal,
                    'reason': reason
                })
                pos_dir = 0
                
        if pos_dir == 0 and (i - last_trade >= cooldown) and bal > 0:
            sig = 0
            if buy_sig[i]: sig = 1
            elif sell_sig[i]: sig = -1
            
            if sig != 0:
                av = max(atr14[i], 1.5)
                sp = 25.0 # pips
                sl_pts = (av * 1.5 / PIP) + sp
                
                if risk_mode == "fixed_001":
                    lot = 0.01
                else:
                    risk_amt = bal * 0.03 # 3% risk
                    lot = max(0.01, min(round(risk_amt / (sl_pts * 0.01) * 0.01, 2), 20.0))
                    
                next_o = o[i+1]
                half_sp = (sp * PIP) / 2.0
                
                if sig == 1:
                    pos_dir = 1
                    pos_en  = next_o + half_sp
                    pos_sl  = pos_en - sl_pts * PIP
                    pos_tp  = pos_en + sl_pts * 2.0 * PIP
                    pos_lot = lot
                    pos_en_dt = dt[i+1]
                else:
                    pos_dir = -1
                    pos_en  = next_o - half_sp
                    pos_sl  = pos_en + sl_pts * PIP
                    pos_tp  = pos_en - sl_pts * 2.0 * PIP
                    pos_lot = lot
                    pos_en_dt = dt[i+1]
                last_trade = i

    tdf = pd.DataFrame(trades_log)
    if len(tdf) == 0:
        return
        
    wins = tdf[tdf['net_pnl'] > 0]
    losses = tdf[tdf['net_pnl'] <= 0]
    
    gross_pnl_total = tdf['gross_pnl'].sum()
    total_fees_paid = tdf['fee'].sum()
    net_pnl_total   = tdf['net_pnl'].sum()
    
    print(f"\n==========================================================================")
    print(f"📊 BACKTEST RESULT: 5-MINUTE ULTIMATE SCALPING ({timeframe} | {start_date} to {end_date})")
    print(f"   Risk Mode: {risk_mode.upper()} | Initial Balance: $1,000.00")
    print(f"==========================================================================")
    print(f"Total Trades Executed : {len(tdf):,}")
    print(f"Winning Trades        : {len(wins):,} ({len(wins)/len(tdf)*100:.2f}%)")
    print(f"Losing Trades         : {len(losses):,} ({len(losses)/len(tdf)*100:.2f}%)")
    print(f"Final Balance         : ${bal:,.2f}")
    print(f"Net Return PnL%       : {(bal-1000)/10:+.2f}%")
    print(f"Max Drawdown          : {max_dd:.2f}%")
    print(f"-"*74)
    print(f"Gross PnL (Before Fees): ${gross_pnl_total:+,.2f}")
    print(f"TOTAL BROKER FEES PAID : ${total_fees_paid:,.2f}  <-- TOTAL COST PAID TO BROKER")
    print(f"  └─ Spread Fees (25 p) : ${total_spread_fee:,.2f}")
    print(f"  └─ Commission ($7/lot): ${total_comm_fee:,.2f}")
    print(f"  └─ Slippage (5 pips)  : ${total_slip_fee:,.2f}")
    print(f"NET PnL (After Fees)   : ${net_pnl_total:+,.2f}")
    print(f"Fee Impact Ratio       : {total_fees_paid/max(abs(gross_pnl_total),1)*100:.1f}% of gross PnL")

    print(f"\n📋 SAMPLE DETAILED TRADE LOG (FIRST 5 TRADES):")
    print(f"{'#':<3} {'Entry Time':<19} {'Dir':<5} {'Lot':<5} {'Entry':<8} {'Exit':<8} {'Gross':<8} {'Fee':<6} {'Net PnL':<8} {'Balance':<9} {'Result'}")
    print("-" * 105)
    for idx, row in tdf.head(5).iterrows():
        res = "WIN ✅" if row['net_pnl'] > 0 else "LOSS ❌"
        print(f"{idx+1:<3} {row['entry_dt']:<19} {row['dir']:<5} {row['lot']:<5.2f} {row['entry']:<8.2f} {row['exit']:<8.2f} ${row['gross_pnl']:<7.2f} ${row['fee']:<5.2f} ${row['net_pnl']:<7.2f} ${row['balance']:<8.2f} {res}")

    print(f"\n📋 SAMPLE DETAILED TRADE LOG (LAST 5 TRADES):")
    print(f"{'#':<3} {'Entry Time':<19} {'Dir':<5} {'Lot':<5} {'Entry':<8} {'Exit':<8} {'Gross':<8} {'Fee':<6} {'Net PnL':<8} {'Balance':<9} {'Result'}")
    print("-" * 105)
    for idx, row in tdf.tail(5).iterrows():
        res = "WIN ✅" if row['net_pnl'] > 0 else "LOSS ❌"
        print(f"{idx+1:<3} {row['entry_dt']:<19} {row['dir']:<5} {row['lot']:<5.2f} {row['entry']:<8.2f} {row['exit']:<8.2f} ${row['gross_pnl']:<7.2f} ${row['fee']:<5.2f} ${row['net_pnl']:<7.2f} ${row['balance']:<8.2f} {res}")

# Run for H1 (2024-2025)
df_h1 = pd.read_csv(H1_PATH)
run_detailed_backtest(df_h1, "H1", "2024-05-01", "2025-05-01", "risk_3pct")

# Run for M15 (2024-2025)
df_m15 = pd.read_csv(M15_PATH)
run_detailed_backtest(df_m15, "M15", "2024-05-01", "2025-05-01", "fixed_001")
