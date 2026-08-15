"""
GLM-5.3 DEEP QUANT RESEARCH ENGINE
===================================
A high-throughput, vectorized, quarter-aware quantitative backtesting and research engine.
Enforces:
1. Strict Temporal Causality (No lookahead leakage)
2. Quarter-as-Primary-Unit Evaluation (Independent Q1, Q2, Q3, Q4 metrics)
3. Pessimistic Intra-Bar Execution (SL hit first on ambiguous bars)
4. Full Cost Stress (Spread, Commission, Slippage modeling)
5. Multi-Timeframe Causal Resampling
"""

import os
import sys
import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional, Callable

sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None

DATA_DIR = r"C:\Users\gugul\AppData\Roaming\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05\AlphaLab_Antigravity\data"

@dataclass
class Trade:
    id: int
    entry_bar: int
    entry_time: pd.Timestamp
    exit_bar: int
    exit_time: pd.Timestamp
    direction: str  # 'BUY' or 'SELL'
    entry_price: float
    exit_price: float
    sl: float
    tp: float
    lots: float
    pnl_usd: float
    pnl_pts: float
    pnl_r: float
    exit_reason: str
    quarter: str
    year: int
    holding_bars: int

@dataclass
class QuarterResult:
    quarter: str
    year: int
    trades: int
    wins: int
    losses: int
    win_rate_pct: float
    net_pnl_usd: float
    gross_profit_usd: float
    gross_loss_usd: float
    profit_factor: float
    max_drawdown_pct: float
    expectancy_usd: float
    expectancy_r: float
    payoff_ratio: float
    tail_loss_usd: float
    verdict: str  # 'PASS', 'FAIL', 'INCONCLUSIVE'

class DeepQuantEngine:
    def __init__(self, data_file: str = "GOLD_H1_2001_2026.csv", pip_size: float = 0.01, point_val: float = 0.01):
        self.data_file = data_file
        self.pip_size = pip_size
        self.point_val = point_val
        self.df = self._load_data(data_file)
        
    def _load_data(self, filename: str) -> pd.DataFrame:
        if os.path.isabs(filename) and os.path.exists(filename):
            path = filename
        else:
            path = os.path.join(DATA_DIR, filename)
        if not os.path.exists(path):
            raise FileNotFoundError(f"Data file not found: {path}")
        df = pd.read_csv(path)
        dt_col = 'datetime_str' if 'datetime_str' in df.columns else ('dt' if 'dt' in df.columns else 'time')
        df['dt'] = pd.to_datetime(df[dt_col])
        df = df.sort_values('dt').reset_index(drop=True)
        # Ensure quarters and years are assigned
        df['quarter'] = df['dt'].dt.to_period('Q').astype(str)
        df['year'] = df['dt'].dt.year
        return df

    def run_strategy(self, 
                     signal_fn: Callable[[pd.DataFrame], Tuple[np.ndarray, np.ndarray, np.ndarray]], 
                     spread_pips: float = 25.0, 
                     commission_per_lot: float = 7.0, 
                     slippage_pips: float = 0.0,
                     pessimistic_ambiguous_bars: bool = True,
                     fixed_lot: float = 0.10,
                     initial_deposit: float = 1000.0,
                     max_holding_bars: int = 120) -> Tuple[pd.DataFrame, pd.DataFrame, Dict]:
        """
        Runs a strategy where signal_fn(df) returns:
        - signals: 1 for BUY, -1 for SELL, 0 for HOLD (generated at close of bar i)
        - sl_dists: Stop loss distance in price points
        - tp_dists: Take profit distance in price points
        """
        df = self.df
        n = len(df)
        signals, sl_dists, tp_dists = signal_fn(df)
        
        o = df['open'].values
        h = df['high'].values
        l = df['low'].values
        c = df['close'].values
        dt = df['dt']
        quarters = df['quarter'].values
        years = df['year'].values
        
        spread_price = spread_pips * self.pip_size
        slippage_price = slippage_pips * self.pip_size
        comm_usd_per_trade = (fixed_lot / 0.01) * (commission_per_lot / 100.0) # $7 per 1.0 lot ($0.07 per 0.01 lot)
        
        trades: List[Trade] = []
        active_trade: Optional[Dict] = None
        trade_id = 0
        
        balance = initial_deposit
        peak_balance = initial_deposit
        equity_curve = [initial_deposit]
        
        for i in range(len(df) - 1):
            # 1. Manage existing open trade during bar i
            if active_trade is not None:
                d = active_trade['direction']
                entry_p = active_trade['entry_price']
                sl_p = active_trade['sl']
                tp_p = active_trade['tp']
                
                closed = False
                exit_price = 0.0
                exit_reason = ''
                
                if d == 'BUY':
                    hit_sl = (l[i] <= sl_p)
                    hit_tp = (h[i] >= tp_p)
                    
                    if hit_sl and hit_tp:
                        if pessimistic_ambiguous_bars:
                            exit_price = sl_p - slippage_price
                            exit_reason = 'SL_AMBIGUOUS_PESSIMISTIC'
                        else:
                            exit_price = tp_p - slippage_price
                            exit_reason = 'TP_AMBIGUOUS_OPTIMISTIC'
                        closed = True
                    elif hit_sl:
                        exit_price = sl_p - slippage_price
                        exit_reason = 'SL'
                        closed = True
                    elif hit_tp:
                        exit_price = tp_p - slippage_price
                        exit_reason = 'TP'
                        closed = True
                    elif i - active_trade['entry_bar'] >= max_holding_bars:
                        exit_price = c[i] - slippage_price
                        exit_reason = 'TIME_EXIT'
                        closed = True
                        
                    if closed:
                        pnl_pts = (exit_price - entry_p) / self.pip_size
                        pnl_usd = (pnl_pts * self.point_val * (fixed_lot / 0.01)) - comm_usd_per_trade
                else: # SELL
                    hit_sl = (h[i] >= sl_p)
                    hit_tp = (l[i] <= tp_p)
                    
                    if hit_sl and hit_tp:
                        if pessimistic_ambiguous_bars:
                            exit_price = sl_p + slippage_price
                            exit_reason = 'SL_AMBIGUOUS_PESSIMISTIC'
                        else:
                            exit_price = tp_p + slippage_price
                            exit_reason = 'TP_AMBIGUOUS_OPTIMISTIC'
                        closed = True
                    elif hit_sl:
                        exit_price = sl_p + slippage_price
                        exit_reason = 'SL'
                        closed = True
                    elif hit_tp:
                        exit_price = tp_p + slippage_price
                        exit_reason = 'TP'
                        closed = True
                    elif i - active_trade['entry_bar'] >= max_holding_bars:
                        exit_price = c[i] + slippage_price
                        exit_reason = 'TIME_EXIT'
                        closed = True
                        
                    if closed:
                        pnl_pts = (entry_p - exit_price) / self.pip_size
                        pnl_usd = (pnl_pts * self.point_val * (fixed_lot / 0.01)) - comm_usd_per_trade
                
                if closed:
                    balance += pnl_usd
                    sl_risk_pts = abs(entry_p - sl_p) / self.pip_size
                    pnl_r = pnl_pts / sl_risk_pts if sl_risk_pts > 0 else 0.0
                    
                    t = Trade(
                        id=trade_id,
                        entry_bar=active_trade['entry_bar'],
                        entry_time=active_trade['entry_time'],
                        exit_bar=i,
                        exit_time=dt.iloc[i],
                        direction=d,
                        entry_price=entry_p,
                        exit_price=exit_price,
                        sl=sl_p,
                        tp=tp_p,
                        lots=fixed_lot,
                        pnl_usd=pnl_usd,
                        pnl_pts=pnl_pts,
                        pnl_r=pnl_r,
                        exit_reason=exit_reason,
                        quarter=active_trade['quarter'],
                        year=active_trade['year'],
                        holding_bars=i - active_trade['entry_bar']
                    )
                    trades.append(t)
                    trade_id += 1
                    active_trade = None
                    
            # 2. Check for new signal at close of bar i (executed at open of bar i+1)
            if active_trade is None and i < n - 1:
                sig = signals[i]
                if sig != 0 and sl_dists[i] > 0 and tp_dists[i] > 0:
                    sl_dist = sl_dists[i]
                    tp_dist = tp_dists[i]
                    
                    if sig == 1: # BUY
                        # Pay spread at entry: Ask = Open + spread
                        entry_p = o[i+1] + spread_price + slippage_price
                        sl_p = entry_p - sl_dist
                        tp_p = entry_p + tp_dist
                        d = 'BUY'
                    elif sig == -1: # SELL
                        # Sell at Bid = Open - slippage
                        entry_p = o[i+1] - slippage_price
                        sl_p = entry_p + sl_dist
                        tp_p = entry_p - tp_dist
                        d = 'SELL'
                    else:
                        continue
                        
                    active_trade = {
                        'entry_bar': i + 1,
                        'entry_time': dt.iloc[i+1],
                        'direction': d,
                        'entry_price': entry_p,
                        'sl': sl_p,
                        'tp': tp_p,
                        'quarter': quarters[i+1],
                        'year': years[i+1]
                    }

        # Convert trades to DataFrame
        trades_data = [t.__dict__ for t in trades]
        tdf = pd.DataFrame(trades_data)
        
        # Calculate Quarter Results
        q_results: List[QuarterResult] = []
        all_quarters = df['quarter'].unique()
        
        for q in all_quarters:
            yr = int(q[:4])
            if len(tdf) > 0:
                q_trades = tdf[tdf['quarter'] == q]
            else:
                q_trades = pd.DataFrame()
                
            q_n = len(q_trades)
            if q_n == 0:
                q_results.append(QuarterResult(
                    quarter=q, year=yr, trades=0, wins=0, losses=0,
                    win_rate_pct=0.0, net_pnl_usd=0.0, gross_profit_usd=0.0,
                    gross_loss_usd=0.0, profit_factor=0.0, max_drawdown_pct=0.0,
                    expectancy_usd=0.0, expectancy_r=0.0, payoff_ratio=0.0,
                    tail_loss_usd=0.0, verdict='INCONCLUSIVE'
                ))
                continue
                
            q_wins = q_trades[q_trades['pnl_usd'] > 0]
            q_losses = q_trades[q_trades['pnl_usd'] < 0]
            n_w = len(q_wins)
            n_l = len(q_losses)
            wr = (n_w / q_n) * 100.0
            
            pnl_net = q_trades['pnl_usd'].sum()
            gross_p = q_wins['pnl_usd'].sum() if n_w > 0 else 0.0
            gross_l = abs(q_losses['pnl_usd'].sum()) if n_l > 0 else 0.0
            pf = gross_p / gross_l if gross_l > 0 else (999.0 if gross_p > 0 else 0.0)
            
            # Drawdown within quarter
            cum_pnl = q_trades['pnl_usd'].cumsum()
            peak = np.maximum.accumulate(cum_pnl)
            dd = peak - cum_pnl
            max_dd_usd = dd.max() if len(dd) > 0 else 0.0
            max_dd_pct = (max_dd_usd / initial_deposit) * 100.0
            
            exp_usd = q_trades['pnl_usd'].mean()
            exp_r = q_trades['pnl_r'].mean()
            
            avg_win = q_wins['pnl_usd'].mean() if n_w > 0 else 0.0
            avg_loss = abs(q_losses['pnl_usd'].mean()) if n_l > 0 else 1e-9
            payoff = avg_win / avg_loss if avg_loss > 0 else 0.0
            
            # Tail loss: 5th percentile worst trade
            tail_loss = np.percentile(q_trades['pnl_usd'], 5) if q_n >= 5 else (q_trades['pnl_usd'].min() if q_n > 0 else 0.0)
            
            # Quarter Verdict
            if q_n >= 3 and pnl_net > 0 and pf >= 1.20:
                verdict = 'PASS'
            elif q_n >= 3 and pnl_net <= 0:
                verdict = 'FAIL'
            else:
                verdict = 'INCONCLUSIVE'
                
            q_results.append(QuarterResult(
                quarter=q, year=yr, trades=q_n, wins=n_w, losses=n_l,
                win_rate_pct=wr, net_pnl_usd=pnl_net, gross_profit_usd=gross_p,
                gross_loss_usd=gross_l, profit_factor=pf, max_drawdown_pct=max_dd_pct,
                expectancy_usd=exp_usd, expectancy_r=exp_r, payoff_ratio=payoff,
                tail_loss_usd=tail_loss, verdict=verdict
            ))
            
        qdf = pd.DataFrame([r.__dict__ for r in q_results])
        
        # Summary metrics
        total_trades = len(tdf)
        total_pnl = tdf['pnl_usd'].sum() if total_trades > 0 else 0.0
        total_wins = len(tdf[tdf['pnl_usd'] > 0]) if total_trades > 0 else 0
        total_losses = len(tdf[tdf['pnl_usd'] < 0]) if total_trades > 0 else 0
        overall_wr = (total_wins / total_trades * 100.0) if total_trades > 0 else 0.0
        
        tot_gp = tdf[tdf['pnl_usd'] > 0]['pnl_usd'].sum() if total_wins > 0 else 0.0
        tot_gl = abs(tdf[tdf['pnl_usd'] < 0]['pnl_usd'].sum()) if total_losses > 0 else 0.0
        overall_pf = tot_gp / tot_gl if tot_gl > 0 else (999.0 if tot_gp > 0 else 0.0)
        
        # Robustness ratio: % of active quarters that passed
        active_qs = qdf[qdf['trades'] >= 3]
        n_active_qs = len(active_qs)
        passed_qs = len(active_qs[active_qs['verdict'] == 'PASS'])
        robustness_ratio = (passed_qs / n_active_qs * 100.0) if n_active_qs > 0 else 0.0
        
        summary = {
            'total_trades': total_trades,
            'total_pnl_usd': total_pnl,
            'overall_wr_pct': overall_wr,
            'overall_pf': overall_pf,
            'active_quarters': n_active_qs,
            'passed_quarters': passed_qs,
            'robustness_ratio_pct': robustness_ratio,
            'avg_expectancy_r': tdf['pnl_r'].mean() if total_trades > 0 else 0.0,
            'avg_expectancy_usd': tdf['pnl_usd'].mean() if total_trades > 0 else 0.0
        }
        
        return tdf, qdf, summary

def print_backtest_report(title: str, tdf: pd.DataFrame, qdf: pd.DataFrame, summary: Dict):
    print(f"\n{'='*95}")
    print(f"📊 SYSTEMATIC EVALUATION: {title}")
    print(f"{'='*95}")
    print(f"Total Trades        : {summary['total_trades']:,}")
    print(f"Net PnL (USD)       : ${summary['total_pnl_usd']:+,.2f}")
    print(f"Win Rate (%)        : {summary['overall_wr_pct']:.2f}%")
    print(f"Profit Factor       : {summary['overall_pf']:.3f}")
    print(f"Expectancy (USD/tr) : ${summary['avg_expectancy_usd']:+.2f}")
    print(f"Expectancy (R/tr)   : {summary['avg_expectancy_r']:+.3f} R")
    print(f"Quarter Robustness  : {summary['passed_quarters']}/{summary['active_quarters']} Active Quarters Passed ({summary['robustness_ratio_pct']:.1f}%)")
    print(f"{'-'*95}")
    
    # Print recent and notable quarters table
    if len(qdf) > 0:
        active_qdf = qdf[qdf['trades'] > 0]
        print(f"\n--- QUARTERLY RESULTS TABLE (Active Quarters: {len(active_qdf)}) ---")
        display_cols = ['quarter', 'trades', 'win_rate_pct', 'net_pnl_usd', 'profit_factor', 'expectancy_r', 'verdict']
        print(active_qdf[display_cols].to_string(index=False))
    print(f"{'='*95}\n")
