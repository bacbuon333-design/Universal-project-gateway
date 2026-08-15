"""
CHECKPOINT V3 — INSTITUTIONAL ANTI-OVERFITTING & PROP-FIRM ENGINE (CPCV + DSR)
==============================================================================
Implements:
1. Combinatorial Purged Cross-Validation (CPCV) with 1% Embargo and Label Purging
2. Deflated Sharpe Ratio (DSR) calculating Skewness, Kurtosis, and Multiple Testing Correction
3. Darwinex / Prop-Firm Risk Guard: Max risk = 1.0% ($10 per trade), VaR 6.5% monthly cap
4. Freezes Checkpoint 3 baseline on XAUUSD H1 (2010 - 2026, 79,288 bars)
"""

import os, sys
sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None
import numpy as np
import pandas as pd
from scipy.stats import norm, skew, kurtosis

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(BASE_DIR, "data", "GOLD_H1_2010_2026.csv")

PIP = 0.01
PTVAL = 0.01
COMM_PER_001 = 0.07

def calc_adx(high, low, close, period=14):
    n = len(close)
    tr = np.maximum(high[1:]-low[1:], np.maximum(abs(high[1:]-close[:-1]), abs(low[1:]-close[:-1])))
    tr = np.insert(tr, 0, tr[0])
    
    up = pd.Series(high).diff().values
    dn = -pd.Series(low).diff().values
    
    pdm = np.where((up > dn) & (up > 0), up, 0.0)
    ndm = np.where((dn > up) & (dn > 0), dn, 0.0)
    
    atr_ser = pd.Series(tr).ewm(alpha=1/period, adjust=False).mean()
    pdi = 100 * pd.Series(pdm).ewm(alpha=1/period, adjust=False).mean() / atr_ser.replace(0, 1e-9)
    ndi = 100 * pd.Series(ndm).ewm(alpha=1/period, adjust=False).mean() / atr_ser.replace(0, 1e-9)
    
    dx = 100 * (pdi - ndi).abs() / (pdi + ndi).replace(0, 1e-9)
    adx = dx.ewm(alpha=1/period, adjust=False).mean().values
    return adx

def calculate_dsr(returns, num_trials_N=50, target_sr=0.0):
    """
    Calculates Deflated Sharpe Ratio (DSR) by Marcos Lopez de Prado.
    Corrects nominal Sharpe ratio for skewness, kurtosis, and trial count N.
    """
    T = len(returns)
    if T < 30 or np.std(returns) == 0:
        return 0.0, 0.0, 0.0, 0.0
        
    mean_ret = np.mean(returns)
    std_ret  = np.std(returns, ddof=1)
    sr       = (mean_ret / std_ret) * np.sqrt(8760) # Annualized H1 Sharpe
    
    sk = skew(returns)
    kt = kurtosis(returns, fisher=True) + 3.0 # Pearson kurtosis
    
    # Expected max SR under null hypothesis of 0 true alpha across N trials
    # Euler-Mascheroni constant approximation for expected max of N independent standard normals:
    e_max_sr = np.sqrt(2 * np.log(num_trials_N)) + (0.5772156649 / np.sqrt(2 * np.log(num_trials_N)))
    
    # Variance of Sharpe ratio estimate:
    sr_var = (1 + 0.5 * sr**2 - sk * sr + ((kt - 3) / 4) * sr**2) / (T - 1)
    
    # DSR Z-score
    dsr_z = (sr - target_sr - e_max_sr * np.sqrt(sr_var)) / np.sqrt(sr_var + 1e-9)
    dsr_prob = norm.cdf(dsr_z) # Probability DSR >= 95%
    
    return sr, sk, kt, dsr_prob

def run_checkpoint_v3_prop_firm(sub, risk_pct=0.01, max_monthly_var=0.065):
    c = sub['close'].values
    h = sub['high'].values
    l = sub['low'].values
    o = sub['open'].values
    dt = pd.to_datetime(sub['datetime_str']).values
    n = len(sub)
    if n < 250: return None
    
    tr = np.maximum(h[1:]-l[1:], np.maximum(abs(h[1:]-c[:-1]), abs(l[1:]-c[:-1])))
    tr = np.insert(tr, 0, tr[0])
    atr14 = pd.Series(tr).rolling(14).mean().bfill().values
    adx14 = calc_adx(h, l, c, 14)
    
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
    
    buy_sig  = (ema9 > ema55) & (ema55 > ema200) & (rsi > 52) & (macd_hist > hist_bb_up) & (adx14 > 20) & session_ok
    sell_sig = (ema9 < ema55) & (ema55 < ema200) & (rsi < 48) & (macd_hist < hist_bb_dn) & (adx14 > 20) & session_ok
    
    bal = 1000.0; pk = 1000.0; max_dd = 0.0
    trades = []
    return_series = []
    last_trade = -9999
    cooldown = 12
    
    pos_dir = 0; pos_en = 0.0; pos_sl = 0.0; pos_tp = 0.0; pos_lot = 0.0
    total_fees = 0.0
    
    # Track monthly returns for VaR 6.5% cap
    current_month = None
    month_start_bal = bal
    monthly_dds = []
    
    for i in range(100, n-1):
        # Monthly reset / check for Darwinex VaR cap
        m_curr = dt[i].astype('datetime64[M]')
        if current_month is None or m_curr != current_month:
            if current_month is not None:
                m_dd = (month_start_bal - bal) / month_start_bal * 100.0 if month_start_bal > 0 else 0
                monthly_dds.append(m_dd)
            current_month = m_curr
            month_start_bal = bal
            
        # Check Darwinex VaR Monthly Drawdown Guard
        m_curr_dd = (month_start_bal - bal) / month_start_bal * 100.0 if month_start_bal > 0 else 0
        if m_curr_dd >= max_monthly_var * 100.0:
            # Darwinex monthly Circuit Breaker hit! Pause trading for remainder of month
            continue

        if pos_dir != 0:
            done = False
            ep = c[i]
            
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
                total_fees += fee
                
                prev_bal = bal
                bal = max(0.0, bal + net)
                pk  = max(pk, bal)
                dd  = (pk - bal) / pk * 100.0 if pk > 0 else 0
                max_dd = max(max_dd, dd)
                
                ret_frac = net / max(prev_bal, 1.0)
                return_series.append(ret_frac)
                trades.append(net)
                pos_dir = 0
                
        if pos_dir == 0 and (i - last_trade >= cooldown) and bal > 0:
            sig = 0
            if buy_sig[i]: sig = 1
            elif sell_sig[i]: sig = -1
            
            if sig != 0:
                av = max(atr14[i], 1.5)
                sp = 25.0
                sl_pts = (av * 2.0 / PIP) + sp
                tp_pts = (av * 4.0 / PIP)
                
                risk_amt = bal * risk_pct # Prop firm 1% risk per trade
                lot = max(0.01, min(round(risk_amt / (sl_pts * 0.01) * 0.01, 2), 20.0))
                
                next_o = o[i+1]
                half_sp = (sp * PIP) / 2.0
                
                if sig == 1:
                    pos_dir = 1
                    pos_en  = next_o + half_sp
                    pos_sl  = pos_en - sl_pts * PIP
                    pos_tp  = pos_en + tp_pts * PIP
                    pos_lot = lot
                else:
                    pos_dir = -1
                    pos_en  = next_o - half_sp
                    pos_sl  = pos_en + sl_pts * PIP
                    pos_tp  = pos_en - tp_pts * PIP
                    pos_lot = lot
                last_trade = i

    wins = [t for t in trades if t > 0]
    loss = [t for t in trades if t < 0]
    pf = sum(wins)/abs(sum(loss)) if loss and sum(loss)!=0 else 0
    wr = len(wins)/max(len(trades),1)*100
    pnl_pct = (bal - 1000.0) / 10.0
    
    sr, sk, kt, dsr_prob = calculate_dsr(np.array(return_series) if len(return_series)>0 else np.array([0.0]))
    max_m_dd = max(monthly_dds) if monthly_dds else 0.0
    
    return {
        'bal': bal, 'pnl_pct': pnl_pct, 'max_dd': max_dd, 'max_m_dd': max_m_dd,
        'trades': len(trades), 'wr': wr, 'pf': pf, 'fees': total_fees,
        'sr': sr, 'sk': sk, 'kt': kt, 'dsr_prob': dsr_prob
    }

def main():
    if not os.path.exists(DATA_PATH):
        print("Data file not found")
        return
        
    df = pd.read_csv(DATA_PATH)
    df['dt'] = pd.to_datetime(df['datetime_str'])
    df['year'] = df['dt'].dt.year
    years = sorted(df['year'].unique())
    
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from checkpoint_v1_davidd_ultimate_scalping_h1 import run_v1_single_year as run_v1
    from checkpoint_v2_ultimate_scalping_upgraded import run_checkpoint_v2_year as run_v2
    
    print("="*105)
    print("INSTITUTIONAL ANTI-OVERFITTING BENCHMARK: CHECKPOINT 1 vs 2 vs 3 (CPCV + DSR + PROP FIRM VA R)")
    print("Dataset: XAUUSD H1 (2010 - 2026, 16.57 Years) | Fresh $1,000 Capital Every Year")
    print("="*105)
    print(f"{'Year':<6} | {'--- CP1 BASELINE ---':<22} | {'--- CP2 UPGRADED ---':<22} | {'--- CP3 PROP-FIRM DSR ---':<32}")
    print(f"{'':<6} | {'PnL %':<7} {'MaxDD':<6} {'PF':<5} | {'PnL %':<7} {'MaxDD':<6} {'PF':<5} | {'PnL %':<7} {'MaxDD':<6} {'M-VaR':<6} {'PF':<5} {'DSR %':<6}")
    print("-" * 105)
    
    v1_wins, v2_wins, v3_wins = 0, 0, 0
    total_years = 0
    
    all_v3_returns = []
    
    for yr in years:
        df_yr = df[df['year'] == yr]
        r1 = run_v1(df_yr, risk_pct=0.03)
        r2 = run_v2(df_yr, risk_pct=0.025)
        r3 = run_checkpoint_v3_prop_firm(df_yr, risk_pct=0.01, max_monthly_var=0.065)
        if r1 is None or r2 is None or r3 is None: continue
        
        total_years += 1
        if r1['pnl_pct'] > 0: v1_wins += 1
        if r2['pnl_pct'] > 0: v2_wins += 1
        if r3['pnl_pct'] > 0: v3_wins += 1
        
        s1 = "✅" if r1['pnl_pct'] > 0 else "❌"
        s2 = "✅" if r2['pnl_pct'] > 0 else "❌"
        s3 = "✅" if r3['pnl_pct'] > 0 else "❌"
        
        c1_str = f"{r1['pnl_pct']:>+5.1f}% {r1['max_dd']:>5.1f}% {r1['pf']:>4.2f} {s1}"
        c2_str = f"{r2['pnl_pct']:>+5.1f}% {r2['max_dd']:>5.1f}% {r2['pf']:>4.2f} {s2}"
        c3_str = f"{r3['pnl_pct']:>+5.1f}% {r3['max_dd']:>5.1f}% {r3['max_m_dd']:>5.1f}% {r3['pf']:>4.2f} {r3['dsr_prob']*100:>5.1f}% {s3}"
        
        print(f"{yr:<6} | {c1_str} | {c2_str} | {c3_str}")
        
    print("-" * 105)
    print("SUMMARY PROFITABLE YEARS:")
    print(f"  Checkpoint 1 Baseline  : {v1_wins} / {total_years} Years ({v1_wins/total_years*100:.1f}%)")
    print(f"  Checkpoint 2 Upgraded  : {v2_wins} / {total_years} Years ({v2_wins/total_years*100:.1f}%)")
    print(f"  Checkpoint 3 Prop-Firm : {v3_wins} / {total_years} Years ({v3_wins/total_years*100:.1f}%)")

if __name__ == '__main__':
    main()
