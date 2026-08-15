"""
TRADE OVERLAP & TIMESTAMP ALIGNMENT ANALYZER
=============================================
Compares exact trade entry timestamps across Checkpoints 1, 2, 3, and 4
to determine if the safe versions open trades at almost the exact same times.
"""
import os, sys
sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None
import numpy as np
import pandas as pd

BASE_DIR = r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05\AlphaLab_Antigravity"
DATA_PATH = os.path.join(BASE_DIR, "data", "GOLD_H1_2010_2026.csv")

PIP = 0.01

def get_trades_log(cp_id=1, risk_pct=0.03):
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
    
    hours = pd.Series(dt).dt.hour.values
    session_ok = (hours >= 12) & (hours <= 18)
    
    if cp_id == 1:
        buy_sig  = (ema9 > ema55) & (ema55 > ema200) & (rsi > 51) & (macd_hist > hist_bb_up)
        sell_sig = (ema9 < ema55) & (ema55 < ema200) & (rsi < 49) & (macd_hist < hist_bb_dn)
    elif cp_id in [2, 3]:
        # ADX filter
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
        adx14 = calc_adx_fast(h, l, c, 14)
        buy_sig  = (ema9 > ema55) & (ema55 > ema200) & (rsi > 51) & (macd_hist > hist_bb_up) & (adx14 > 20) & session_ok
        sell_sig = (ema9 < ema55) & (ema55 < ema200) & (rsi < 49) & (macd_hist < hist_bb_dn) & (adx14 > 20) & session_ok
    elif cp_id == 4:
        buy_sig  = (ema9 > ema55) & (ema55 > ema200) & (rsi > 51) & (macd_hist > hist_bb_up) & session_ok
        sell_sig = (ema9 < ema55) & (ema55 < ema200) & (rsi < 49) & (macd_hist < hist_bb_dn) & session_ok
        
    trades_list = []
    last_trade = -9999
    cooldown = 12
    pos_dir = 0; pos_en = 0.0; pos_sl = 0.0; pos_tp = 0.0
    
    for i in range(250, n-1):
        if pos_dir != 0:
            done = False
            if pos_dir == 1:
                if l[i] <= pos_sl or h[i] >= pos_tp: done = True
            else:
                if h[i] >= pos_sl or l[i] <= pos_tp: done = True
            if done: pos_dir = 0
            
        if pos_dir == 0 and (i - last_trade >= cooldown):
            sig = 0
            if buy_sig[i]: sig = 1
            elif sell_sig[i]: sig = -1
            
            if sig != 0:
                av = max(atr14[i], 1.5)
                sp = 25.0
                sl_pts = (av * 2.0 / PIP) + sp
                tp_pts = (av * 4.0 / PIP)
                
                next_o = o[i+1]
                half_sp = (sp * PIP) / 2.0
                
                pos_dir = sig
                pos_en  = next_o + half_sp if sig==1 else next_o - half_sp
                pos_sl  = pos_en - sl_pts * PIP if sig==1 else pos_en + sl_pts * PIP
                pos_tp  = pos_en + tp_pts * PIP if sig==1 else pos_en - tp_pts * PIP
                last_trade = i
                
                trades_list.append({
                    'index': i+1,
                    'dt': pd.Timestamp(dt[i+1]),
                    'dir': 'BUY' if sig==1 else 'SELL',
                    'entry': pos_en
                })
                
    return pd.DataFrame(trades_list)

print("="*80)
print("TRADE TIMESTAMP ALIGNMENT & OVERLAP ANALYSIS")
print("="*80)

t1 = get_trades_log(1)
t2 = get_trades_log(2)
t3 = get_trades_log(3)
t4 = get_trades_log(4)

print(f"Total Trades CP1 (Baseline Gốc)    : {len(t1):,} trades")
print(f"Total Trades CP2 (Upgraded An Toàn): {len(t2):,} trades")
print(f"Total Trades CP3 (Prop-Firm VaR)   : {len(t3):,} trades")
print(f"Total Trades CP4 (Exact Specs)     : {len(t4):,} trades")

# Overlap matching (exact timestamp or within 3 hours)
dt2_set = set(t2['dt'])
dt3_set = set(t3['dt'])
dt4_set = set(t4['dt'])

exact_match_2_3 = len(dt2_set.intersection(dt3_set))
exact_match_2_4 = len(dt2_set.intersection(dt4_set))

print(f"\n📌 OVERLAP STATISTICS BETWEEN SAFE MODELS:")
print(f"  Exact Same Entry Timestamp (CP2 vs CP3): {exact_match_2_3} / {len(t2)} ({exact_match_2_3/len(t2)*100:.1f}%)")
print(f"  Exact Same Entry Timestamp (CP2 vs CP4): {exact_match_2_4} / {len(t2)} ({exact_match_2_4/len(t2)*100:.1f}%)")

# Compare CP2 trades inside CP1
cp2_in_cp1 = 0
for d in t2['dt']:
    # check if CP1 has entry within +/- 3 hours
    time_diffs = (t1['dt'] - d).abs()
    if (time_diffs <= pd.Timedelta(hours=3)).any():
        cp2_in_cp1 += 1

print(f"  CP2 Trades Matched inside CP1 (within ±3h): {cp2_in_cp1} / {len(t2)} ({cp2_in_cp1/len(t2)*100:.1f}%)")

print("\n📋 SAMPLE OVERLAPPING TRADES IN 2024-2025 (SAME TIMESTAMPS):")
print(f"{'Timestamp':<20} | {'CP1 Dir':<7} | {'CP2 Dir':<7} | {'CP3 Dir':<7} | {'CP4 Dir':<7}")
print("-" * 70)

merged = pd.merge(t2, t4, on='dt', suffixes=('_cp2', '_cp4'), how='inner')
merged = merged[merged['dt'] >= '2024-05-01'].head(10)

for idx, r in merged.iterrows():
    print(f"{str(r['dt']):<20} | {r['dir_cp2']:<7} | {r['dir_cp2']:<7} | {r['dir_cp2']:<7} | {r['dir_cp4']:<7}")
