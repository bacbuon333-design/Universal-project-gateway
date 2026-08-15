import pandas as pd
import numpy as np
from hmmlearn.hmm import GaussianHMM
import warnings
warnings.filterwarnings('ignore')
import os

# Set file paths
DATA_FILE = r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05\AlphaLab_Antigravity\data\GOLD_M15.csv"
REPORT_FILE = r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05\AlphaLab_Antigravity\reports\nexus_reset\v32_results.md"

def load_and_resample(file_path):
    print(f"Loading data from {file_path}...")
    df = pd.read_csv(file_path)
    # Parse datetime
    df['datetime'] = pd.to_datetime(df['datetime_str'] if 'datetime_str' in df.columns else df.iloc[:,0])
    df.set_index('datetime', inplace=True)
    df.sort_index(inplace=True)
    
    # Resample to H1
    df_h1 = df.resample('1h').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'tick_volume': 'sum'
    }).dropna()
    
    return df, df_h1

def calc_atr(df, period=14):
    high_low = df['high'] - df['low']
    high_close = np.abs(df['high'] - df['close'].shift())
    low_close = np.abs(df['low'] - df['close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = np.max(ranges, axis=1)
    return true_range.rolling(period).mean()

def compute_features(df_h1):
    print("Computing features...")
    df = df_h1.copy()
    
    df['atr14'] = calc_atr(df, 14)
    df['atr14_mean120'] = df['atr14'].rolling(120).mean()
    df['atr14_std120'] = df['atr14'].rolling(120).std()
    
    df['log_ret_1h'] = np.log(df['close'] / df['close'].shift(1))
    df['log_ret_4h'] = np.log(df['close'] / df['close'].shift(4))
    df['log_ret_24h'] = np.log(df['close'] / df['close'].shift(24))
    df['log_ret_96h'] = np.log(df['close'] / df['close'].shift(96))
    
    df['hl_range_norm'] = (df['high'] - df['low']) / df['atr14']
    
    denom = df['high'] - df['low'] + 1e-5
    df['body_ratio'] = np.abs(df['close'] - df['open']) / denom
    df['upper_wick'] = (df['high'] - df[['open', 'close']].max(axis=1)) / denom
    df['lower_wick'] = (df[['open', 'close']].min(axis=1) - df['low']) / denom
    
    df['vol_zscore'] = (df['atr14'] - df['atr14_mean120']) / df['atr14_std120']
    
    df['displacement_24h'] = (df['close'] - df['close'].shift(24)) / df['atr14']
    
    # 48-period highs and lows (causal: up to i, shifted later if needed)
    df['max_h_48'] = df['high'].rolling(49).max()
    df['min_l_48'] = df['low'].rolling(49).min()
    
    df['dist_to_high48'] = (df['max_h_48'] - df['close']) / df['atr14']
    df['dist_to_low48'] = (df['close'] - df['min_l_48']) / df['atr14']
    
    denom48 = df['max_h_48'] - df['min_l_48'] + 1e-5
    df['retracement'] = (df['close'] - df['min_l_48']) / denom48
    
    df['approach_velocity'] = (df['close'] - df['close'].shift(3)) / (3 * df['atr14'])
    
    # Donchian 20 for breakouts
    df['max_h_20_prev'] = df['high'].shift(1).rolling(20).max()
    df['min_l_20_prev'] = df['low'].shift(1).rolling(20).min()
    
    return df.dropna()

def fit_hmm(df_train, n_states=4):
    print("Fitting HMM on training period...")
    model = GaussianHMM(n_components=n_states, covariance_type="diag", n_iter=100, random_state=42)
    # Fit on H1 log returns
    X_train = df_train[['log_ret_1h']].values
    model.fit(X_train)
    
    # Map states to 0, 1, 2, 3 based on mu and vol
    means = model.means_.flatten()
    covars = model.covars_.flatten()
    
    # We expect:
    # State 0 (Low-vol flat): mu approx 0, low var
    # State 1 (Med-vol bull): mu > 0, med var
    # State 2 (High-vol bear): mu < 0, high var
    # State 3 (High-vol bull): mu > 0, high var
    
    # We will heuristically map states by ordering variance and means
    # To strictly match the scientific facts:
    state_metrics = []
    for i in range(n_states):
        state_metrics.append({'state': i, 'mu': means[i], 'var': covars[i]})
        
    state_metrics.sort(key=lambda x: x['var'])
    # Lowest var -> State 0
    mapping = {state_metrics[0]['state']: 0}
    
    # Highest var are 2 and 3. Bearish is 2, Bullish is 3
    remaining = state_metrics[1:]
    # Sort remaining 3 by variance
    # The two highest variances
    high_var = sorted(remaining[1:], key=lambda x: x['mu'])
    # high_var[0] is bear (mu smaller), high_var[1] is bull
    mapping[high_var[0]['state']] = 2
    mapping[high_var[1]['state']] = 3
    
    # the medium variance one
    mapping[remaining[0]['state']] = 1
    
    return model, mapping

def infer_hmm(df, model, mapping):
    # Rolling viterbi? No, just predict state causally using historical rolling window or just predict forward
    # For simplicity, predict whole series and apply mapping, but strictly, predict should only use past data.
    # However, hmmlearn predict on single point is just emission probability. We can run predict on cumulative history.
    # To speed up, we predict on the whole series. This doesn't leak future data for the CURRENT state estimate because Viterbi on history[0:i] ending state is equivalent to forward algorithm, but standard predict uses full sequence.
    # We should use only forward probabilities to be strictly causal, or just rely on the fact that states are persistent.
    
    # strictly causal HMM forward pass
    X = df[['log_ret_1h']].values
    
    # To be fast and reasonably causal, we could use forward algorithm to get P(S_t | O_{1..t})
    states = []
    logprob, posteriors = model.score_samples(X) # this is smoothed (future leak).
    # To do causal, we can use model._compute_log_likelihood(X) and do forward algorithm.
    framelogprob = model._compute_log_likelihood(X)
    
    log_alpha = np.zeros((X.shape[0], model.n_components))
    log_alpha[0] = np.log(model.startprob_) + framelogprob[0]
    
    for t in range(1, X.shape[0]):
        # log_alpha[t-1] is (n_components,)
        # transmat is (n_components, n_components)
        # we need log( sum_i alpha_{t-1, i} * P(j | i) ) + log P(O_t | j)
        for j in range(model.n_components):
            m = np.max(log_alpha[t-1])
            sum_prob = np.sum(np.exp(log_alpha[t-1] - m) * model.transmat_[:, j])
            log_alpha[t, j] = m + np.log(sum_prob) + framelogprob[t, j]
            
    # Normalize and get argmax
    causal_states = np.argmax(log_alpha, axis=1)
    
    # map states
    df['hmm_state'] = [mapping[s] for s in causal_states]
    return df

def generate_signals(df, vol_zscore_thresh=1.5):
    # Signal Type 1 — IMPULSE_LONG
    sig1 = (df['hmm_state'] == 3) & \
           (df['close'] > df['max_h_20_prev'])
           
    # Signal Type 2 — STRUCTURE_LONG
    sig2 = (df['hmm_state'].isin([1, 3])) & \
           (df['retracement'] > 0.1) & (df['retracement'] < 0.6) & \
           (df['lower_wick'] > 0.2)
           
    # Signal Type 3 — IMPULSE_SHORT
    sig3 = (df['hmm_state'] == 2) & \
           (df['close'] < df['min_l_20_prev'])
           
    # Signal Type 4 — STRUCTURE_SHORT
    sig4 = (df['hmm_state'] == 2) & \
           (df['retracement'] > 0.4) & (df['retracement'] < 0.9) & \
           (df['upper_wick'] > 0.2)
           
    df['signal'] = 0
    df['signal_type'] = ''
    df['sl_dist'] = 0.0
    df['tp_dist'] = 0.0
    
    # Priority: IMPULSE > STRUCTURE
    
    # Apply sig2
    df.loc[sig2, 'signal'] = 1
    df.loc[sig2, 'signal_type'] = 'STRUCTURE_LONG'
    df.loc[sig2, 'sl_dist'] = 1.5 * df['atr14']
    df.loc[sig2, 'tp_dist'] = 3.0 * df['atr14'] * 1.5
    
    # Apply sig4
    df.loc[sig4, 'signal'] = -1
    df.loc[sig4, 'signal_type'] = 'STRUCTURE_SHORT'
    df.loc[sig4, 'sl_dist'] = 1.5 * df['atr14']
    df.loc[sig4, 'tp_dist'] = 3.0 * df['atr14'] * 1.5

    # Apply sig1 (overrides)
    df.loc[sig1, 'signal'] = 1
    df.loc[sig1, 'signal_type'] = 'IMPULSE_LONG'
    df.loc[sig1, 'sl_dist'] = 1.2 * df['atr14']
    df.loc[sig1, 'tp_dist'] = 4.5 * df['atr14'] * 1.2

    # Apply sig3 (overrides)
    df.loc[sig3, 'signal'] = -1
    df.loc[sig3, 'signal_type'] = 'IMPULSE_SHORT'
    df.loc[sig3, 'sl_dist'] = 1.2 * df['atr14']
    df.loc[sig3, 'tp_dist'] = 4.5 * df['atr14'] * 1.2

    return df

def simulate(df, initial_equity=1000.0):
    equity = initial_equity
    peak_equity = equity
    max_dd = 0.0
    
    trades = []
    
    pos = 0 # 1 long, -1 short, 0 none
    entry_price = 0
    sl = 0
    tp = 0
    pos_size = 0
    cooldown_until = df.index[0]
    
    # Fix 4: Variable spread logic
    # Spread = base 25 pips + 10 if ATR > 1.5*ATR_slow
    # Note: 1 pip = 0.1 for Gold? Wait, XAUUSD standard is 0.01 per pip or 0.1 depending on broker.
    # Usually XAUUSD pip is 0.1 or 0.01. Let's assume 1 pip = 0.1 for now, so 25 pips = 2.5
    # Let's parameterize pip_size = 0.1
    pip_size = 0.1
    
    for i in range(1, len(df)):
        current_time = df.index[i]
        bar = df.iloc[i]
        prev_bar = df.iloc[i-1]
        
        # Check if we have an open position
        if pos != 0:
            # Check trailing SL
            if pos == 1:
                # Trailing stop activates at 1.5*SL gained, trails at 2.5*ATR
                profit_gained = bar['high'] - entry_price
                if profit_gained > 1.5 * (entry_price - sl) and bar['high'] > sl + 2.5 * bar['atr14']:
                    new_sl = bar['high'] - 2.5 * bar['atr14']
                    if new_sl > sl: sl = new_sl
                    
                # Check SL / TP
                if bar['low'] <= sl:
                    # FIX-3: SL fill = SL price +/- 5 pip slippage (worse for user)
                    exit_price = sl - 5 * pip_size
                    pnl = (exit_price - entry_price) * pos_size
                    equity = max(0, equity + pnl) # FIX-5
                    trades.append({'time': current_time, 'type': 'EXIT_LONG_SL', 'pnl': pnl, 'equity': equity, 'sig': pos_type})
                    pos = 0
                elif bar['high'] >= tp:
                    exit_price = tp
                    pnl = (exit_price - entry_price) * pos_size
                    equity = max(0, equity + pnl)
                    trades.append({'time': current_time, 'type': 'EXIT_LONG_TP', 'pnl': pnl, 'equity': equity, 'sig': pos_type})
                    pos = 0
            
            elif pos == -1:
                profit_gained = entry_price - bar['low']
                if profit_gained > 1.5 * (sl - entry_price) and bar['low'] < sl - 2.5 * bar['atr14']:
                    new_sl = bar['low'] + 2.5 * bar['atr14']
                    if new_sl < sl: sl = new_sl
                    
                if bar['high'] >= sl:
                    exit_price = sl + 5 * pip_size
                    pnl = (entry_price - exit_price) * pos_size
                    equity = max(0, equity + pnl)
                    trades.append({'time': current_time, 'type': 'EXIT_SHORT_SL', 'pnl': pnl, 'equity': equity, 'sig': pos_type})
                    pos = 0
                elif bar['low'] <= tp:
                    exit_price = tp
                    pnl = (entry_price - exit_price) * pos_size
                    equity = max(0, equity + pnl)
                    trades.append({'time': current_time, 'type': 'EXIT_SHORT_TP', 'pnl': pnl, 'equity': equity, 'sig': pos_type})
                    pos = 0
                    
            if equity > peak_equity: peak_equity = equity
            dd = (peak_equity - equity) / peak_equity
            if dd > max_dd: max_dd = dd
            continue
            
        # Entry logic (Fix 1: Entry at NEXT bar OPEN, so we use prev_bar's signal)
        if current_time >= cooldown_until and prev_bar['signal'] != 0:
            sig = prev_bar['signal']
            pos_type = prev_bar['signal_type']
            sl_dist = prev_bar['sl_dist']
            tp_dist = prev_bar['tp_dist']
            
            # Spread calc
            spread = 25 * pip_size
            if prev_bar['atr14'] > 1.5 * prev_bar['atr14_mean120']:
                spread += 10 * pip_size
                
            entry_price = bar['open'] + (spread if sig == 1 else -spread)
            
            # Risk per trade 5.5% base equity
            risk_amount = equity * 0.055
            # Scale down if in DD
            curr_dd = (peak_equity - equity) / peak_equity if peak_equity > 0 else 0
            if curr_dd > 0.1: risk_amount *= 0.5
            if curr_dd > 0.15: risk_amount *= 0.5
            
            if sl_dist > 0:
                pos_size = risk_amount / sl_dist
            else:
                pos_size = 0.01 # Fallback
                
            pos = sig
            if pos == 1:
                sl = entry_price - sl_dist
                tp = entry_price + tp_dist
            else:
                sl = entry_price + sl_dist
                tp = entry_price - tp_dist
                
            trades.append({'time': current_time, 'type': f'ENTRY_{pos_type}', 'price': entry_price})
            # Cooldown 72 bars (3 days)
            cooldown_until = current_time + pd.Timedelta(hours=72)

    return equity, max_dd, trades

def evaluate_period(df, start, end):
    mask = (df.index >= start) & (df.index <= end)
    sub_df = df[mask]
    if len(sub_df) == 0:
        return {}
    
    eq, max_dd, trades = simulate(sub_df)
    
    # Compile stats
    closed_trades = [t for t in trades if 'EXIT' in t['type']]
    wins = [t for t in closed_trades if t['pnl'] > 0]
    
    if len(closed_trades) > 0:
        win_rate = len(wins) / len(closed_trades)
        gross_profit = sum(t['pnl'] for t in wins)
        gross_loss = abs(sum(t['pnl'] for t in closed_trades if t['pnl'] < 0))
        pf = gross_profit / gross_loss if gross_loss > 0 else float('inf')
    else:
        win_rate = 0
        pf = 0
        
    # Breakdown by signal type
    sig_breakdown = {}
    for t in closed_trades:
        sig = t['sig']
        sig_breakdown[sig] = sig_breakdown.get(sig, 0) + 1
        
    pnl_pct = (eq - 1000.0) / 1000.0 * 100
    
    return {
        'pnl_pct': pnl_pct,
        'max_dd_pct': max_dd * 100,
        'num_trades': len(closed_trades),
        'win_rate': win_rate * 100,
        'pf': pf,
        'breakdown': sig_breakdown
    }

def main():
    df_raw, df_h1 = load_and_resample(DATA_FILE)
    df = compute_features(df_h1)
    
    # Train HMM on 2022-05-02 to 2024-04-30
    train_mask = (df.index >= '2022-05-02') & (df.index <= '2024-04-30')
    df_train = df[train_mask]
    
    model, mapping = fit_hmm(df_train)
    print("HMM State mapping:", mapping)
    
    df = infer_hmm(df, model, mapping)
    
    results_text = []
    
    # Baseline run
    df_sigs = generate_signals(df, vol_zscore_thresh=1.5)
    
    periods = [
        ('TRAIN', '2022-05-02', '2024-04-30'),
        ('OOS', '2024-05-01', '2025-04-30'),
        ('SEALED', '2025-05-01', '2026-07-24'),
        ('2022-2023', '2022-01-01', '2023-12-31'),
        ('2023-2024', '2023-01-01', '2024-12-31'),
        ('2024-2025', '2024-01-01', '2025-12-31'),
        ('2025-2026', '2025-01-01', '2026-12-31')
    ]
    
    results_text.append("# ALAB NEXUS v32 - Backtest Results\n")
    results_text.append("## Baseline Configuration\n")
    
    for name, start, end in periods:
        res = evaluate_period(df_sigs, start, end)
        if res:
            res_str = f"**{name} ({start} to {end})**\n"
            res_str += f"- PnL: {res['pnl_pct']:.2f}%\n"
            res_str += f"- Max DD: {res['max_dd_pct']:.2f}%\n"
            res_str += f"- Trades: {res['num_trades']}\n"
            res_str += f"- Win Rate: {res['win_rate']:.2f}%\n"
            res_str += f"- Profit Factor: {res['pf']:.2f}\n"
            res_str += f"- Breakdown: {res['breakdown']}\n"
            results_text.append(res_str)
            print(res_str)
            
    # Sensitivity analysis on vol_zscore_thresh
    results_text.append("## Sensitivity Analysis (OOS Period 2024-05-01 to 2025-04-30)\n")
    for thresh in [0.5, 1.0, 1.5, 2.0]:
        df_sens = generate_signals(df, vol_zscore_thresh=thresh)
        res = evaluate_period(df_sens, '2024-05-01', '2025-04-30')
        if res:
            res_str = f"**Threshold {thresh}** -> PnL: {res['pnl_pct']:.2f}%, MaxDD: {res['max_dd_pct']:.2f}%, Trades: {res['num_trades']}, WR: {res['win_rate']:.2f}%, PF: {res['pf']:.2f}\n"
            results_text.append(res_str)
            print(res_str)
            
    with open(REPORT_FILE, 'w') as f:
        f.write('\n'.join(results_text))
        
    print(f"Report saved to {REPORT_FILE}")

if __name__ == '__main__':
    main()
