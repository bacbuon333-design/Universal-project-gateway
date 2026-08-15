"""
GLM-5.3 DEEP QUANT RESEARCH ENGINE (ASSET-AWARE V3.2.2)
========================================================
A high-throughput, vectorized, quarter-aware quantitative backtesting engine.
Features:
1. Strict Temporal Causality (No lookahead leakage)
2. Platform-Independent Data Path Resolution (No hardcoded paths)
3. Truly Asset-Aware Instrument Economics (InstrumentSpec architecture):
   - Supports XAUUSD, EURUSD, GBPUSD, USDJPY (dynamic contemporaneous JPY/USD conversion), BTCUSD
   - Trade-level exact account currency (USD) PnL calculation during execution
   - Net-cost adjusted R calculation (including spread & commission in 1R denominator)
4. Runtime Strategy Output Contract Validation (validate_strategy_output)
5. Symmetrically Sound Execution Model:
   - OHLC represents Bid
   - BUY Entry: Ask = Open + spread + slippage
   - BUY Exit: Bid - slippage
   - SELL Entry: Bid = Open - slippage
   - SELL Exit: Ask = Target + spread + slippage
   - Symmetrical 1 round-trip spread paid by both BUY and SELL
6. Symmetrical Pessimistic Intra-Bar Execution (SL preferred on ambiguous bars for both BUY and SELL)
7. Full 100-Quarter Distribution Accounting (Total, Active, Inactive, Inconclusive quarters)
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
class InstrumentSpec:
    symbol: str
    asset_class: str            # "COMMODITY", "FOREX_USD_QUOTE", "FOREX_USD_BASE", "CRYPTO"
    price_digits: int           # Digits of price precision (e.g. 2 for Gold/Crypto, 5 for EURUSD, 3 for USDJPY)
    point_size: float           # Minimum price increment (e.g. 0.01, 0.00001, 0.001)
    pip_size: float             # Standard pip price increment (e.g. 0.01 for Gold/USDJPY, 0.0001 for EURUSD)
    contract_size: float        # Contract units per 1.0 standard lot (e.g. 100 oz Gold, 100,000 base FX, 1.0 BTC)
    default_lot: float = 0.10   # Default trading volume (e.g. 0.10 standard lot)
    quote_currency: str = "USD" # "USD", "JPY", etc.
    account_currency: str = "USD"
    default_spread_pips: float = 25.0
    commission_per_lot_usd: float = 7.0 # $7.00/lot round-trip -> $0.70 on 0.10 lot

STANDARD_SPECS: Dict[str, InstrumentSpec] = {
    "XAUUSD": InstrumentSpec(
        symbol="XAUUSD", asset_class="COMMODITY", price_digits=2, point_size=0.01, pip_size=0.01,
        contract_size=100.0, default_lot=0.10, quote_currency="USD", account_currency="USD",
        default_spread_pips=25.0, commission_per_lot_usd=7.0
    ),
    "GOLD": InstrumentSpec(
        symbol="GOLD", asset_class="COMMODITY", price_digits=2, point_size=0.01, pip_size=0.01,
        contract_size=100.0, default_lot=0.10, quote_currency="USD", account_currency="USD",
        default_spread_pips=25.0, commission_per_lot_usd=7.0
    ),
    "EURUSD": InstrumentSpec(
        symbol="EURUSD", asset_class="FOREX_USD_QUOTE", price_digits=5, point_size=0.00001, pip_size=0.0001,
        contract_size=100000.0, default_lot=0.10, quote_currency="USD", account_currency="USD",
        default_spread_pips=1.5, commission_per_lot_usd=7.0
    ),
    "GBPUSD": InstrumentSpec(
        symbol="GBPUSD", asset_class="FOREX_USD_QUOTE", price_digits=5, point_size=0.00001, pip_size=0.0001,
        contract_size=100000.0, default_lot=0.10, quote_currency="USD", account_currency="USD",
        default_spread_pips=1.8, commission_per_lot_usd=7.0
    ),
    "USDJPY": InstrumentSpec(
        symbol="USDJPY", asset_class="FOREX_USD_BASE", price_digits=3, point_size=0.001, pip_size=0.01,
        contract_size=100000.0, default_lot=0.10, quote_currency="JPY", account_currency="USD",
        default_spread_pips=1.8, commission_per_lot_usd=7.0
    ),
    "BTCUSD": InstrumentSpec(
        symbol="BTCUSD", asset_class="CRYPTO", price_digits=2, point_size=0.01, pip_size=1.00,
        contract_size=1.0, default_lot=0.10, quote_currency="USD", account_currency="USD",
        default_spread_pips=50.0, commission_per_lot_usd=7.0
    )
}

def get_instrument_spec(identifier: str) -> InstrumentSpec:
    """Resolves an InstrumentSpec from a symbol or filename cleanly."""
    id_upper = os.path.basename(identifier).upper()
    for key, spec in STANDARD_SPECS.items():
        if key in id_upper:
            return spec
    # Default fallback to Gold / Commodity
    return STANDARD_SPECS["XAUUSD"]

def calculate_trade_pnl(spec: InstrumentSpec, direction: int, entry_price: float, exit_price: float,
                        lots: float = 0.10, commission_per_lot: float = None) -> Dict[str, float]:
    """
    Authoritative trade-level PnL computation function in account currency (USD).
    direction: +1 for BUY, -1 for SELL
    """
    comm_rate = commission_per_lot if commission_per_lot is not None else spec.commission_per_lot_usd
    vol = lots * spec.contract_size
    price_diff = (exit_price - entry_price) * direction
    pnl_pips = price_diff / spec.pip_size
    
    if spec.asset_class in ["COMMODITY", "FOREX_USD_QUOTE", "CRYPTO"]:
        gross_pnl_usd = price_diff * vol
    elif spec.asset_class == "FOREX_USD_BASE": # e.g. USDJPY
        gross_pnl_jpy = price_diff * vol
        eff_exit = exit_price if exit_price > 0 else entry_price
        gross_pnl_usd = gross_pnl_jpy / eff_exit
    else:
        gross_pnl_usd = price_diff * vol
        
    comm_cost_usd = comm_rate * lots
    net_pnl_usd = gross_pnl_usd - comm_cost_usd
    
    return {
        'pnl_pips': pnl_pips,
        'gross_pnl_usd': gross_pnl_usd,
        'commission_usd': comm_cost_usd,
        'net_pnl_usd': net_pnl_usd,
        'is_win': net_pnl_usd > 0
    }

def validate_strategy_output(df: pd.DataFrame, signals: np.ndarray, sl_dists: np.ndarray, tp_dists: np.ndarray) -> None:
    """
    Authoritative runtime contract validator asserting strategy output conformity.
    Raises ValueError immediately if any interface invariant is breached.
    """
    n = len(df)
    if len(signals) != n or len(sl_dists) != n or len(tp_dists) != n:
        raise ValueError(f"Array length mismatch: df={n}, signals={len(signals)}, sl_dists={len(sl_dists)}, tp_dists={len(tp_dists)}")
        
    valid_sigs = {-1, 0, 1}
    unique_sigs = set(np.unique(signals))
    if not unique_sigs.issubset(valid_sigs):
        raise ValueError(f"Invalid signal values: {unique_sigs - valid_sigs}. Allowed: {-1, 0, 1}")
        
    active_idx = np.where(signals != 0)[0]
    if len(active_idx) > 0:
        if np.isnan(sl_dists[active_idx]).any() or np.isnan(tp_dists[active_idx]).any():
            raise ValueError("NaN detected in active sl_dists or tp_dists")
            
        if (sl_dists[active_idx] <= 0).any() or (tp_dists[active_idx] <= 0).any():
            raise ValueError("Non-positive distance detected in active sl_dists or tp_dists")
            
        close_vals = df['close'].values[active_idx]
        if (sl_dists[active_idx] > 0.50 * close_vals).any():
            raise ValueError("Unreasonably large sl_dist detected (>50% of market price). Possible absolute price passed instead of distance!")

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
    def __init__(self, data_file: Optional[str] = "GOLD_H1_2001_2026.csv", 
                 df: Optional[pd.DataFrame] = None,
                 spec: Optional[InstrumentSpec] = None,
                 pip_size: Optional[float] = None, 
                 point_val: Optional[float] = None):
        self.data_file = data_file
        if df is not None:
            self.resolved_path = "SYNTHETIC_DATAFRAME"
            self.spec = spec if spec is not None else STANDARD_SPECS["XAUUSD"]
            self.df = self._prepare_dataframe(df.copy())
        else:
            self.resolved_path = resolve_data_path(data_file)
            self.spec = spec if spec is not None else get_instrument_spec(data_file)
            self.df = self._load_and_prepare_data(self.resolved_path)
            
        self.pip_size = pip_size if pip_size is not None else self.spec.pip_size
        
    def _prepare_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        dt_col = None
        for c in ['datetime_str', 'dt', 'time', 'timestamp', 'date', 'datetime']:
            if c in df.columns:
                dt_col = c
                break
        if dt_col is None:
            dt_col = df.columns[0]
            
        df['datetime'] = pd.to_datetime(df[dt_col])
        df = df.sort_values('datetime').reset_index(drop=True)
        df['year'] = df['datetime'].dt.year
        df['quarter'] = df['datetime'].dt.to_period('Q').astype(str)
        for col in ['open', 'high', 'low', 'close']:
            if col in df.columns:
                df[col] = df[col].astype(float)
        return df

    def _load_and_prepare_data(self, path: str) -> pd.DataFrame:
        df = pd.read_csv(path)
        return self._prepare_dataframe(df)

    def run_strategy(self, 
                     signal_fn: Callable[[pd.DataFrame], Tuple[np.ndarray, np.ndarray, np.ndarray]], 
                     spread_pips: Optional[float] = None,
                     slippage_pips: float = 0.0,
                     commission_per_lot: Optional[float] = None,
                     fixed_lot: float = 0.10,
                     pessimistic_ambiguous_bars: bool = True,
                     max_holding_bars: int = 120) -> Tuple[pd.DataFrame, pd.DataFrame, Dict]:
        """
        Executes a causal vector backtest with native asset-aware execution.
        signal_fn must return: (signals, sl_dists, tp_dists)
        """
        df = self.df
        n = len(df)
        
        spr = spread_pips if spread_pips is not None else self.spec.default_spread_pips
        comm_rate = commission_per_lot if commission_per_lot is not None else self.spec.commission_per_lot_usd
        
        spread_price = spr * self.pip_size
        slippage_price = slippage_pips * self.pip_size
        
        signals, sl_dists, tp_dists = signal_fn(df)
        
        # Authoritative strategy contract validation
        validate_strategy_output(df, signals, sl_dists, tp_dists)
        
        trades: List[Trade] = []
        active_trade = None
        balance = 10000.0 # Standard nominal base
        trade_id = 1
        
        o = df['open'].values
        h = df['high'].values
        l = df['low'].values
        c = df['close'].values
        dt = df['datetime']
        q_series = df['quarter'].values
        y_series = df['year'].values
        
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
                dir_int = 1 if d == 'BUY' else -1
                
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
                    # Exact asset-aware trade-level PnL computation
                    pnl_dict = calculate_trade_pnl(
                        self.spec, dir_int, entry_p, exit_price,
                        lots=fixed_lot, commission_per_lot=comm_rate
                    )
                    pnl_usd = pnl_dict['net_pnl_usd']
                    pnl_pts = pnl_dict['pnl_pips']
                    
                    balance += pnl_usd
                    # Exact 1R risk in USD (loss when hitting initial SL, net of costs)
                    sl_risk_dict = calculate_trade_pnl(self.spec, dir_int, entry_p, sl_p, lots=fixed_lot, commission_per_lot=comm_rate)
                    sl_risk_usd = abs(sl_risk_dict['net_pnl_usd'])
                    pnl_r = (pnl_usd / sl_risk_usd) if sl_risk_usd > 0 else 0.0
                    
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
                        entry_price = o[i+1] + spread_price + slippage_price
                        sl_price = entry_price - sl_dist
                        tp_price = entry_price + tp_dist
                        active_trade = {
                            'direction': 'BUY',
                            'entry_bar': i+1,
                            'entry_time': dt.iloc[i+1],
                            'entry_price': entry_price,
                            'sl': sl_price,
                            'tp': tp_price,
                            'quarter': q_series[i+1],
                            'year': y_series[i+1]
                        }
                    elif sig == -1: # SELL
                        # Enter at Bid = Open - slippage (Spread will be paid upon buying back at exit)
                        entry_price = o[i+1] - slippage_price
                        sl_price = entry_price + sl_dist
                        tp_price = entry_price - tp_dist
                        active_trade = {
                            'direction': 'SELL',
                            'entry_bar': i+1,
                            'entry_time': dt.iloc[i+1],
                            'entry_price': entry_price,
                            'sl': sl_price,
                            'tp': tp_price,
                            'quarter': q_series[i+1],
                            'year': y_series[i+1]
                        }

        # Convert trades to DataFrame
        trades_df = pd.DataFrame([t.__dict__ for t in trades])
        
        # Quarter-by-quarter metrics
        quarter_results = []
        unique_quarters = sorted(df['quarter'].unique())
        
        for q in unique_quarters:
            y = int(q[:4])
            if len(trades_df) > 0:
                q_trades = trades_df[trades_df['quarter'] == q]
            else:
                q_trades = pd.DataFrame()
                
            n_t = len(q_trades)
            if n_t == 0:
                qr = QuarterResult(
                    quarter=q, year=y, trades=0, wins=0, losses=0, win_rate_pct=0.0,
                    net_pnl_usd=0.0, gross_profit_usd=0.0, gross_loss_usd=0.0,
                    profit_factor=0.0, max_drawdown_pct=0.0, expectancy_usd=0.0,
                    expectancy_r=0.0, payoff_ratio=0.0, tail_loss_usd=0.0, verdict='NO_TRADE'
                )
            else:
                wins = q_trades[q_trades['pnl_usd'] > 0]
                losses = q_trades[q_trades['pnl_usd'] <= 0]
                n_w = len(wins)
                n_l = len(losses)
                wr = (n_w / n_t) * 100.0
                
                gp = wins['pnl_usd'].sum() if n_w > 0 else 0.0
                gl = abs(losses['pnl_usd'].sum()) if n_l > 0 else 0.0
                net_pnl = q_trades['pnl_usd'].sum()
                
                pf = (gp / gl) if gl > 0 else (999.0 if gp > 0 else 0.0)
                exp_usd = net_pnl / n_t
                exp_r = q_trades['pnl_r'].mean()
                
                avg_win = wins['pnl_usd'].mean() if n_w > 0 else 0.0
                avg_loss = abs(losses['pnl_usd'].mean()) if n_l > 0 else 0.0
                payoff = (avg_win / avg_loss) if avg_loss > 0 else 0.0
                tail_loss = abs(losses['pnl_usd'].min()) if n_l > 0 else 0.0
                
                # Quarter Drawdown
                cum_pnl = q_trades['pnl_usd'].cumsum()
                peak = np.maximum.accumulate(cum_pnl)
                dd = peak - cum_pnl
                max_dd = dd.max() if len(dd) > 0 else 0.0
                
                # Scientific Verdict per Quarter
                if n_t < 3:
                    verdict = 'INCONCLUSIVE'
                elif pf >= 1.25 and net_pnl > 0:
                    verdict = 'PASS'
                elif pf < 0.90 or net_pnl < 0:
                    verdict = 'FAIL'
                else:
                    verdict = 'INCONCLUSIVE'
                    
                qr = QuarterResult(
                    quarter=q, year=y, trades=n_t, wins=n_w, losses=n_l, win_rate_pct=wr,
                    net_pnl_usd=net_pnl, gross_profit_usd=gp, gross_loss_usd=gl,
                    profit_factor=pf, max_drawdown_pct=max_dd, expectancy_usd=exp_usd,
                    expectancy_r=exp_r, payoff_ratio=payoff, tail_loss_usd=tail_loss, verdict=verdict
                )
            quarter_results.append(qr)
            
        quarters_df = pd.DataFrame([qr.__dict__ for qr in quarter_results])
        
        # Summary statistics
        tot_trades = len(trades_df)
        tot_pnl = trades_df['pnl_usd'].sum() if tot_trades > 0 else 0.0
        tot_gp = trades_df[trades_df['pnl_usd'] > 0]['pnl_usd'].sum() if tot_trades > 0 else 0.0
        tot_gl = abs(trades_df[trades_df['pnl_usd'] <= 0]['pnl_usd'].sum()) if tot_trades > 0 else 0.0
        overall_pf = (tot_gp / tot_gl) if tot_gl > 0 else (999.0 if tot_gp > 0 else 0.0)
        overall_wr = (len(trades_df[trades_df['pnl_usd'] > 0]) / tot_trades * 100.0) if tot_trades > 0 else 0.0
        
        # Quarter Pass Rates
        active_q = quarters_df[quarters_df['trades'] >= 3]
        n_active = len(active_q)
        n_active_pass = len(active_q[active_q['verdict'] == 'PASS'])
        active_pass_rate = (n_active_pass / n_active * 100.0) if n_active > 0 else 0.0
        
        total_q = len(quarters_df)
        n_total_pass = len(quarters_df[quarters_df['verdict'] == 'PASS'])
        full_pass_rate = (n_total_pass / total_q * 100.0) if total_q > 0 else 0.0
        
        summary = {
            'symbol': self.spec.symbol,
            'asset_class': self.spec.asset_class,
            'total_trades': tot_trades,
            'total_pnl_usd': tot_pnl,
            'gross_profit_usd': tot_gp,
            'gross_loss_usd': tot_gl,
            'overall_pf': overall_pf,
            'overall_wr_pct': overall_wr,
            'avg_expectancy_usd': (tot_pnl / tot_trades) if tot_trades > 0 else 0.0,
            'avg_expectancy_r': trades_df['pnl_r'].mean() if tot_trades > 0 else 0.0,
            'total_quarters': total_q,
            'active_quarters': n_active,
            'active_quarter_pass_pct': active_pass_rate,
            'full_calendar_pass_pct': full_pass_rate
        }
        
        return trades_df, quarters_df, summary

def print_backtest_report(summary: Dict, quarters_df: pd.DataFrame):
    print("=" * 80)
    print(f"📊 BACKTEST AUDIT REPORT: {summary['symbol']} ({summary['asset_class']})")
    print("=" * 80)
    print(f"Total Trades           : {summary['total_trades']}")
    print(f"Total Net PnL (USD)    : ${summary['total_pnl_usd']:+,.2f}")
    print(f"Gross Profit / Loss    : ${summary['gross_profit_usd']:+,.2f} / ${summary['gross_loss_usd']:,.2f}")
    print(f"Overall Profit Factor  : {summary['overall_pf']:.3f}")
    print(f"Win Rate               : {summary['overall_wr_pct']:.2f}%")
    print(f"Avg Expectancy         : ${summary['avg_expectancy_usd']:+.2f} USD ({summary['avg_expectancy_r']:+.3f} R)")
    print(f"Total Calendar Quarters: {summary['total_quarters']}")
    print(f"Active Quarters (>=3 tr): {summary['active_quarters']}")
    print(f"Active Quarter Pass Rate: {summary['active_quarter_pass_pct']:.1f}%")
    print(f"Full Calendar Pass Rate : {summary['full_calendar_pass_pct']:.1f}%")
    print("=" * 80)
