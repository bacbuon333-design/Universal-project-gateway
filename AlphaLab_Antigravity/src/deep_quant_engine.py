"""
GLM-5.3 DEEP QUANT RESEARCH ENGINE (CORRECTED AUDIT V2)
========================================================
A high-throughput, vectorized, quarter-aware quantitative backtesting engine.
Features:
1. Strict Temporal Causality (No lookahead leakage)
2. Platform-Independent Data Path Resolution (No hardcoded paths)
3. Symmetrically Sound Execution Model:
   - OHLC represents Bid
   - BUY Entry: Ask = Open + spread + slippage
   - BUY Exit: Bid - slippage
   - SELL Entry: Bid = Open - slippage
   - SELL Exit: Ask = Target + spread + slippage
   - Symmetrical 1 round-trip spread paid by both BUY and SELL
4. Symmetrical Pessimistic Intra-Bar Execution (SL preferred on ambiguous bars for both BUY and SELL)
5. Exact Institutional Cost Accounting ($7/lot round-turn commission, pip & point scaling)
6. Full 100-Quarter Distribution Accounting (Total, Active, Inactive, Inconclusive quarters)
"""

import os
import sys
import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional, Callable

sys.stdout.reconfigure(encoding='utf-8') if sys.platform == 'win32' else None

def resolve_data_path(filename: str) -> str:
    """Resolves data file location cleanly across any machine, OS, or environment."""
    if os.path.isabs(filename) and os.path.exists(filename):
        return filename
    
    # Check environment variable if specified
    if "ALPHALAB_DATA_DIR" in os.environ:
        env_path = os.path.join(os.environ["ALPHALAB_DATA_DIR"], filename)
        if os.path.exists(env_path):
            return env_path
            
    # Check relative to script directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.abspath(os.path.join(script_dir, "..", "data", filename)),
        os.path.abspath(os.path.join(script_dir, "data", filename)),
        os.path.abspath(os.path.join(os.getcwd(), "AlphaLab_Antigravity", "data", filename)),
        os.path.abspath(os.path.join(os.getcwd(), "data", filename)),
        os.path.abspath(os.path.join(os.getcwd(), filename))
    ]
    
    for c in candidates:
        if os.path.exists(c):
            return c
            
    raise FileNotFoundError(f"Market dataset '{filename}' not found. Searched paths:\n" + "\n".join(candidates))

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
    verdict: str  # 'PASS', 'FAIL', 'INCONCLUSIVE', 'NO_TRADE'

class DeepQuantEngine:
    def __init__(self, data_file: str = "GOLD_H1_2001_2026.csv", pip_size: float = 0.01, point_val: float = 0.01):
        self.data_file = data_file
        self.pip_size = pip_size
        self.point_val = point_val
        self.resolved_path = resolve_data_path(data_file)
        self.df = self._load_data(self.resolved_path)
        
    def _load_data(self, path: str) -> pd.DataFrame:
        df = pd.read_csv(path)
        dt_col = 'datetime_str' if 'datetime_str' in df.columns else ('dt' if 'dt' in df.columns else 'time')
        df['dt'] = pd.to_datetime(df[dt_col])
        df = df.sort_values('dt').reset_index(drop=True)
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
        # Commission: $7.00 per 1.0 standard lot round-turn ($0.70 per 0.10 lot)
        comm_usd_per_trade = (fixed_lot / 0.01) * (commission_per_lot / 100.0)
        
        trades: List[Trade] = []
        active_trade: Optional[Dict] = None
        trade_id = 0
        
        balance = initial_deposit
        
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
                    # For SELL, buying back to exit is done at Ask = Bid + spread
                    # Stop loss is triggered if Ask >= sl_p (i.e. High + spread >= sl_p)
                    # Take profit is triggered if Ask <= tp_p (i.e. Low + spread <= tp_p)
                    hit_sl = (h[i] + spread_price >= sl_p)
                    hit_tp = (l[i] + spread_price <= tp_p)
                    
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
                        exit_price = c[i] + spread_price + slippage_price
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
                        # Pay spread at entry: Ask = Open + spread + slippage
                        entry_p = o[i+1] + spread_price + slippage_price
                        sl_p = entry_p - sl_dist
                        tp_p = entry_p + tp_dist
                        d = 'BUY'
                    elif sig == -1: # SELL
                        # Sell at Bid = Open - slippage
                        # sl_p and tp_p are the target Ask prices where trade will buy back
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
        
        # Quarter-by-quarter full calendar accounting (including zero-trade quarters)
        unique_quarters = df['quarter'].unique()
        q_results: List[QuarterResult] = []
        
        for q in unique_quarters:
            yr = int(q[:4])
            if len(tdf) > 0 and q in tdf['quarter'].values:
                qtdf = tdf[tdf['quarter'] == q]
                n_t = len(qtdf)
                wins = len(qtdf[qtdf['pnl_usd'] > 0])
                losses = len(qtdf[qtdf['pnl_usd'] <= 0])
                wr = (wins / n_t) * 100.0 if n_t > 0 else 0.0
                net_pnl = qtdf['pnl_usd'].sum()
                gp = qtdf[qtdf['pnl_usd'] > 0]['pnl_usd'].sum() if wins > 0 else 0.0
                gl = abs(qtdf[qtdf['pnl_usd'] < 0]['pnl_usd'].sum()) if losses > 0 else 0.0
                pf = (gp / gl) if gl > 0 else (999.0 if gp > 0 else 0.0)
                
                cum_pnl = qtdf['pnl_usd'].cumsum()
                peak = np.maximum.accumulate(cum_pnl)
                dd = peak - cum_pnl
                max_dd_usd = np.max(dd) if len(dd) > 0 else 0.0
                max_dd_pct = (max_dd_usd / initial_deposit) * 100.0
                
                exp_usd = qtdf['pnl_usd'].mean() if n_t > 0 else 0.0
                exp_r = qtdf['pnl_r'].mean() if n_t > 0 else 0.0
                
                avg_win = qtdf[qtdf['pnl_usd'] > 0]['pnl_usd'].mean() if wins > 0 else 0.0
                avg_loss = abs(qtdf[qtdf['pnl_usd'] < 0]['pnl_usd'].mean()) if losses > 0 else 0.0
                payoff = (avg_win / avg_loss) if avg_loss > 0 else 0.0
                tail_loss = qtdf['pnl_usd'].min() if n_t > 0 else 0.0
                
                # Minimum sample criteria for PASS: trades >= 3, PF >= 1.25, net PnL > 0
                if n_t >= 3:
                    if pf >= 1.25 and net_pnl > 0:
                        verdict = 'PASS'
                    elif pf < 0.90 or net_pnl < 0:
                        verdict = 'FAIL'
                    else:
                        verdict = 'INCONCLUSIVE'
                else:
                    verdict = 'INCONCLUSIVE'
            else:
                n_t = 0
                wins = 0
                losses = 0
                wr = 0.0
                net_pnl = 0.0
                gp = 0.0
                gl = 0.0
                pf = 0.0
                max_dd_pct = 0.0
                exp_usd = 0.0
                exp_r = 0.0
                payoff = 0.0
                tail_loss = 0.0
                verdict = 'NO_TRADE'
                
            q_results.append(QuarterResult(
                quarter=q,
                year=yr,
                trades=n_t,
                wins=wins,
                losses=losses,
                win_rate_pct=wr,
                net_pnl_usd=net_pnl,
                gross_profit_usd=gp,
                gross_loss_usd=gl,
                profit_factor=pf,
                max_drawdown_pct=max_dd_pct,
                expectancy_usd=exp_usd,
                expectancy_r=exp_r,
                payoff_ratio=payoff,
                tail_loss_usd=tail_loss,
                verdict=verdict
            ))
            
        qdf = pd.DataFrame([qr.__dict__ for qr in q_results])
        
        # Overall Summary
        tot_trades = len(tdf)
        tot_pnl = tdf['pnl_usd'].sum() if tot_trades > 0 else 0.0
        tot_wins = len(tdf[tdf['pnl_usd'] > 0]) if tot_trades > 0 else 0
        tot_wr = (tot_wins / tot_trades) * 100.0 if tot_trades > 0 else 0.0
        tot_gp = tdf[tdf['pnl_usd'] > 0]['pnl_usd'].sum() if tot_wins > 0 else 0.0
        tot_gl = abs(tdf[tdf['pnl_usd'] < 0]['pnl_usd'].sum()) if (tot_trades - tot_wins) > 0 else 0.0
        overall_pf = (tot_gp / tot_gl) if tot_gl > 0 else (999.0 if tot_gp > 0 else 0.0)
        
        total_qs = len(qdf)
        no_trade_qs = len(qdf[qdf['verdict'] == 'NO_TRADE'])
        low_trade_qs = len(qdf[(qdf['trades'] > 0) & (qdf['trades'] < 3)])
        active_qs = len(qdf[qdf['trades'] >= 3])
        pass_qs = len(qdf[qdf['verdict'] == 'PASS'])
        fail_qs = len(qdf[qdf['verdict'] == 'FAIL'])
        inconcl_qs = len(qdf[qdf['verdict'] == 'INCONCLUSIVE'])
        
        active_pass_ratio = (pass_qs / active_qs * 100.0) if active_qs > 0 else 0.0
        full_pass_ratio = (pass_qs / total_qs * 100.0) if total_qs > 0 else 0.0
        
        summary = {
            'total_trades': tot_trades,
            'total_pnl_usd': tot_pnl,
            'overall_pf': overall_pf,
            'overall_wr_pct': tot_wr,
            'total_calendar_quarters': total_qs,
            'no_trade_quarters': no_trade_qs,
            'low_trade_quarters': low_trade_qs,
            'active_quarters': active_qs,
            'pass_quarters': pass_qs,
            'fail_quarters': fail_qs,
            'inconclusive_quarters': inconcl_qs,
            'active_quarter_pass_pct': active_pass_ratio,
            'full_calendar_pass_pct': full_pass_ratio,
            'avg_expectancy_usd': tdf['pnl_usd'].mean() if tot_trades > 0 else 0.0,
            'avg_expectancy_r': tdf['pnl_r'].mean() if tot_trades > 0 else 0.0
        }
        
        return tdf, qdf, summary

def print_backtest_report(title: str, tdf: pd.DataFrame, qdf: pd.DataFrame, summary: Dict):
    print("=" * 95)
    print(f"📊 {title.upper()}")
    print("=" * 95)
    print(f"  Total Trades        : {summary['total_trades']}")
    print(f"  Net PnL (USD)       : ${summary['total_pnl_usd']:+,.2f}")
    print(f"  Win Rate (%)        : {summary['overall_wr_pct']:.2f}%")
    print(f"  Profit Factor       : {summary['overall_pf']:.3f}")
    print(f"  Expectancy (USD)    : ${summary['avg_expectancy_usd']:+.2f} / trade")
    print(f"  Expectancy (R)      : {summary['avg_expectancy_r']:+.3f} R / trade")
    print(f"  Calendar Quarters   : {summary['total_calendar_quarters']} total ({summary['no_trade_quarters']} no-trade, {summary['low_trade_quarters']} low-trade [1-2], {summary['active_quarters']} active [>=3])")
    print(f"  Quarter Verdicts    : {summary['pass_quarters']} PASS | {summary['fail_quarters']} FAIL | {summary['inconclusive_quarters']} INCONCLUSIVE")
    print(f"  Active Q-Pass Rate  : {summary['active_quarter_pass_pct']:.1f}% ({summary['pass_quarters']}/{summary['active_quarters']})")
    print(f"  Full Q-Pass Rate    : {summary['full_calendar_pass_pct']:.1f}% ({summary['pass_quarters']}/{summary['total_calendar_quarters']})")
    print("=" * 95)
