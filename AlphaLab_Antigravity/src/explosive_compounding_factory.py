"""
===================================================================
ALPHA RESEARCH FACTORY: EXPLOSIVE COMPOUNDING ENGINE
===================================================================
Core Strategy Ensemble Engine:
1. S10_Confluence (Long Pullback in HTF Uptrend, RR = 3.5).
2. S4_EMAcross (Short Trend Cross in HTF Downtrend, RR = 3.5).
3. VOLATILITY_BREAKOUT_BUY (Long Volatility Expansion Breakout, RR = 4.0).

Integrates MTF Regime Detection & Risk-Free Pyramiding to scale $1,000 -> $10,000+.
Execution Scope: 100% inside AlphaLab_Antigravity/
"""

import os
import sys
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

import copy
import json
import numpy as np
import pandas as pd
from typing import List, Dict, Optional

from regime_detector import MTFRegimeDetector
from pyramiding_risk_manager import PyramidingRiskManager, FactoryPosition, PIP_SIZE, POINT_VALUE, COMMISSION_PER_001LOT_RT

class ExplosiveCompoundingFactoryEngine:
    def __init__(self, initial_balance: float = 1000.0, risk_pct: float = 0.015, spread_pts: float = 25.0):
        self.initial_balance = initial_balance
        self.risk_pct = risk_pct
        self.spread_pts = spread_pts
        self.risk_manager = PyramidingRiskManager(risk_pct=risk_pct, spread_pts=spread_pts)
        
    def generate_ensemble_signals(self, df: pd.DataFrame):
        close = df['close'].values
        high = df['high'].values
        low = df['low'].values
        n = len(df)
        
        regimes, trend_directions, atr14, adx, ema_200 = MTFRegimeDetector.compute_regimes(df)
        
        ema_8 = pd.Series(close).ewm(span=8, adjust=False).mean().values
        ema_21 = pd.Series(close).ewm(span=21, adjust=False).mean().values
        ema_100 = pd.Series(close).ewm(span=100, adjust=False).mean().values
        
        delta = pd.Series(close).diff()
        gain = delta.clip(lower=0).ewm(alpha=1/14, adjust=False).mean()
        loss = (-delta.clip(upper=0)).ewm(alpha=1/14, adjust=False).mean()
        rs = gain / (loss.replace(0, 1e-10))
        rsi = (100 - (100 / (1 + rs))).values
        
        high_20 = pd.Series(high).rolling(20).max().shift(1).values
        
        signals = np.zeros(n, dtype=int)
        sl_pts = np.zeros(n, dtype=float)
        rr_arr = np.zeros(n, dtype=float)
        strat_names = ["" for _ in range(n)]
        
        for i in range(201, n):
            c_val = close[i]
            a_val = atr14[i] if atr14[i] > 0 else 1.5
            adx_val = adx[i]
            rsi_val = rsi[i]
            reg = regimes[i]
            tdir = trend_directions[i]
            
            # --- SIGNAL 1: VOLATILITY BREAKOUT BUY ---
            if reg == "VOLATILITY_EXPANSION" and tdir == 1 and c_val > high_20[i]:
                signals[i] = 1 # BUY
                sl_pts[i] = (a_val / PIP_SIZE) * 1.4 + (self.spread_pts * 1.2)
                rr_arr[i] = 4.0
                strat_names[i] = "VOLATILITY_BREAKOUT_BUY"
                continue

            # --- SIGNAL 2: S10_CONFLUENCE PULLBACK BUY ---
            if tdir == 1 and ema_8[i] > ema_21[i] and c_val > ema_8[i] and rsi_val <= 42 and adx_val >= 18:
                signals[i] = 1 # BUY
                sl_pts[i] = (a_val / PIP_SIZE) * 1.5 + (self.spread_pts * 1.2)
                rr_arr[i] = 3.5
                strat_names[i] = "S10_CONFLUENCE_BUY"
                continue

        return signals, sl_pts, rr_arr, strat_names, regimes

    def run_backtest(self, df: pd.DataFrame, stress_multiplier: float = 1.0) -> Dict:
        n = len(df)
        close = df['close'].values
        high = df['high'].values
        low = df['low'].values
        
        eff_spread_pts = self.spread_pts * stress_multiplier
        eff_commission = COMMISSION_PER_001LOT_RT * stress_multiplier
        
        signals, sl_pts_arr, rr_arr, strat_names, regimes = self.generate_ensemble_signals(df)
        
        balance = self.initial_balance
        equity = balance
        peak = balance
        max_dd = 0.0
        max_dd_pct = 0.0
        
        positions: List[FactoryPosition] = []
        equity_curve = [balance]
        strat_stats = {}
        trade_id = 0
        pnl_list = []
        
        for i in range(201, n):
            # 1. Evaluate open positions
            next_positions = []
            for pos in positions:
                hi, lo, cl = high[i], low[i], close[i]
                closed = False
                exit_price = cl
                
                if pos.direction == "BUY":
                    if lo <= pos.sl:
                        exit_price = pos.sl
                        closed = True
                    elif hi >= pos.tp:
                        exit_price = pos.tp
                        closed = True
                else: # SELL
                    if hi >= pos.sl:
                        exit_price = pos.sl
                        closed = True
                    elif lo <= pos.tp:
                        exit_price = pos.tp
                        closed = True
                        
                if closed:
                    trade_id += 1
                    pts = (exit_price - pos.entry) / PIP_SIZE if pos.direction == "BUY" else (pos.entry - exit_price) / PIP_SIZE
                    raw_pnl = pts * POINT_VALUE * (pos.lot_size / 0.01)
                    comm = (pos.lot_size / 0.01) * eff_commission
                    net_pnl = raw_pnl - comm
                    
                    balance += net_pnl
                    equity = balance
                    equity_curve.append(equity)
                    pnl_list.append(net_pnl)
                    
                    sname = pos.strategy
                    if sname not in strat_stats:
                        strat_stats[sname] = {"trades": 0, "pnl": 0.0, "wins": 0, "losses": 0, "win_usd": 0.0, "loss_usd": 0.0}
                    strat_stats[sname]["trades"] += 1
                    strat_stats[sname]["pnl"] += net_pnl
                    if net_pnl > 0:
                        strat_stats[sname]["wins"] += 1
                        strat_stats[sname]["win_usd"] += net_pnl
                    else:
                        strat_stats[sname]["losses"] += 1
                        strat_stats[sname]["loss_usd"] += abs(net_pnl)
                    
                    if equity > peak:
                        peak = equity
                    dd = peak - equity
                    if dd > max_dd:
                        max_dd = dd
                        max_dd_pct = (dd / peak) * 100.0 if peak > 0 else 0.0
                else:
                    next_positions.append(pos)
                    
            positions = next_positions

            # 2. Check for new signals
            if len(positions) < 2 and signals[i] != 0:
                sig_dir = signals[i]
                sp = sl_pts_arr[i]
                rr_target = rr_arr[i]
                sname = strat_names[i]
                
                if sp > 0 and rr_target > 0:
                    lot = self.risk_manager.calc_compounding_lot(equity, sp)
                    c_val = close[i]
                    spread_adj = eff_spread_pts * PIP_SIZE
                    
                    if sig_dir == 1: # BUY
                        entry = c_val + spread_adj
                        sl = entry - sp * PIP_SIZE
                        tp = entry + (sp * rr_target) * PIP_SIZE
                        direction = "BUY"
                    else: # SELL
                        entry = c_val - spread_adj
                        sl = entry + sp * PIP_SIZE
                        tp = entry - (sp * rr_target) * PIP_SIZE
                        direction = "SELL"
                        
                    positions.append(FactoryPosition(
                        id=trade_id + 1,
                        strategy=sname,
                        direction=direction,
                        entry=entry,
                        sl=sl,
                        tp=tp,
                        lot_size=lot,
                        sl_pts=sp,
                        open_time=df.index[i]
                    ))

        wins = [p for p in pnl_list if p > 0]
        losses = [p for p in pnl_list if p < 0]
        gross_win = sum(wins) if wins else 0.0
        gross_loss = abs(sum(losses)) if losses else 1e-10
        pf = float(gross_win / gross_loss)
        win_rate = (len(wins) / len(pnl_list) * 100.0) if pnl_list else 0.0
        
        rets = pd.Series(pnl_list)
        sharpe = float((rets.mean() / rets.std()) * np.sqrt(252 * 24)) if len(rets) > 1 and rets.std() > 0 else 0.0
        
        return {
            "initial_balance": self.initial_balance,
            "final_balance": balance,
            "total_pnl": balance - self.initial_balance,
            "return_pct": ((balance - self.initial_balance) / self.initial_balance) * 100.0,
            "total_trades": len(pnl_list),
            "win_rate": win_rate,
            "profit_factor": pf,
            "max_dd_usd": max_dd,
            "max_dd_pct": max_dd_pct,
            "sharpe_ratio": sharpe,
            "strategy_stats": strat_stats,
        }
