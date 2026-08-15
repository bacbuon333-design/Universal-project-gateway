"""
===================================================================
ALL-YEARS 15-20% WAVE AMPLITUDE CAPTURE QUANT ENGINE
===================================================================
Engine specifically designed to hit 15% - 20% of Oracle Perfect Wave Trajectory
across EVERY single historical year (2022 - 2026):

Targets per Year ($1,000 Initial Balance):
- 2024-2025: Target 20% Wave = +$2,808.21 USD (Final Balance $3,808.21)
- 2023-2024: Target 20% Wave = +$1,340.85 USD (Final Balance $2,340.85)
- 2022-2023: Target 20% Wave = +$1,526.19 USD (Final Balance $2,526.19)
- 2025-2026: Target 20% Wave = +$14,980.94 USD (Final Balance $15,980.94)

Hard Risk Constraint: Max Drawdown <= 20.0% across ALL years.

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
from datetime import datetime, timezone
from dataclasses import dataclass
from typing import List, Dict, Optional

PIP_SIZE = 0.01          # XM Gold pip size ($0.01)
POINT_VALUE = 0.01       # USD per point per 0.01 lot
COMMISSION_PER_001LOT_RT = 0.07  # $7/lot ($0.07 / 0.01 lot)

@dataclass
class Trade:
    id: int = 0
    strategy: str = ""
    direction: str = ""      # BUY / SELL
    entry: float = 0.0
    sl: float = 0.0
    tp: float = 0.0
    lot_size: float = 0.01
    close_price: float = 0.0
    profit_usd: float = 0.0
    open_time: object = None
    close_time: object = None
    close_reason: str = ""
    sl_pts: float = 0.0

class MultiYearRiskManager:
    @staticmethod
    def calc_lot(equity: float, peak_equity: float, sl_pts: float, base_risk_pct: float = 0.055) -> float:
        if sl_pts <= 0 or equity <= 0:
            return 0.01
            
        current_dd_pct = (peak_equity - equity) / max(1.0, peak_equity) * 100.0 if peak_equity > 0 else 0.0
        if current_dd_pct >= 14.0:
            effective_risk = base_risk_pct * 0.25
        elif current_dd_pct >= 9.0:
            effective_risk = base_risk_pct * 0.50
        else:
            effective_risk = base_risk_pct
            
        risk_usd = equity * effective_risk
        cost_per_001 = sl_pts * 0.01
        if cost_per_001 <= 0:
            return 0.01
        units_001 = risk_usd / cost_per_001
        lot = round(units_001 * 0.01, 2)
        return max(0.01, min(lot, 30.0))

class AllYearsWaveCaptureEngine:
    def __init__(self, initial_balance: float = 1000.0, base_risk_pct: float = 0.055, spread_pts: float = 25.0):
        self.initial_balance = initial_balance
        self.base_risk_pct = base_risk_pct
        self.spread_pts = spread_pts
        
    def generate_signals(self, df: pd.DataFrame):
        close = df['close'].values
        high = df['high'].values
        low = df['low'].values
        n = len(df)
        
        # Moving Averages
        ema_8 = pd.Series(close).ewm(span=8, adjust=False).mean().values
        ema_21 = pd.Series(close).ewm(span=21, adjust=False).mean().values
        ema_50 = pd.Series(close).ewm(span=50, adjust=False).mean().values
        ema_200 = pd.Series(close).ewm(span=200, adjust=False).mean().values
        
        # ATR & Volatility Ratio
        tr1 = high[1:] - low[1:]
        tr2 = np.abs(high[1:] - close[:-1])
        tr3 = np.abs(low[1:] - close[:-1])
        tr = np.maximum(tr1, np.maximum(tr2, tr3))
        tr = np.append([0.0], tr)
        atr14 = pd.Series(tr).rolling(14).mean().values
        
        # RSI 14
        delta = pd.Series(close).diff()
        gain = delta.clip(lower=0).ewm(alpha=1/14, adjust=False).mean()
        loss = (-delta.clip(upper=0)).ewm(alpha=1/14, adjust=False).mean()
        rs = gain / (loss.replace(0, 1e-10))
        rsi = (100 - (100 / (1 + rs))).values
        
        # ADX 14
        up = pd.Series(high).diff()
        dn = -pd.Series(low).diff()
        pdm = up.where((up > dn) & (up > 0), 0.0)
        ndm = dn.where((dn > up) & (dn > 0), 0.0)
        atr_adx = pd.Series(tr).ewm(alpha=1/14, min_periods=14, adjust=False).mean()
        pdi = 100 * pdm.ewm(alpha=1/14, min_periods=14, adjust=False).mean() / atr_adx.replace(0, 1e-10)
        ndi = 100 * ndm.ewm(alpha=1/14, min_periods=14, adjust=False).mean() / atr_adx.replace(0, 1e-10)
        dx = 100 * (pdi - ndi).abs() / (pdi + ndi).replace(0, 1e-10)
        adx = dx.ewm(alpha=1/14, min_periods=14, adjust=False).mean().values
        
        signals = np.zeros(n, dtype=int)
        sl_pts = np.zeros(n, dtype=float)
        rr_arr = np.zeros(n, dtype=float)
        strat_names = ["" for _ in range(n)]
        
        for i in range(201, n):
            c_val = close[i]
            a_val = atr14[i] if atr14[i] > 0 else 1.5
            adx_val = adx[i]
            rsi_val = rsi[i]
            
            # --- SIGNAL 1: BULLISH VALUE PULLBACK BUY (3.8x R:R) ---
            if c_val > ema_200[i] and ema_8[i] > ema_21[i] and low[i] <= ema_8[i] and rsi_val <= 46 and adx_val >= 18:
                signals[i] = 1 # BUY
                sl_pts[i] = (a_val / PIP_SIZE) * 1.4 + (self.spread_pts * 1.2)
                rr_arr[i] = 3.8
                strat_names[i] = "ALL_YEARS_BULL_PULLBACK_BUY"
                continue

            # --- SIGNAL 2: BEARISH VALUE REBOUND SELL (3.8x R:R) ---
            if c_val < ema_200[i] and ema_50[i] < ema_200[i] and ema_8[i] < ema_21[i] and high[i] >= ema_8[i] and rsi_val >= 58 and adx_val >= 25:
                signals[i] = -1 # SELL
                sl_pts[i] = (a_val / PIP_SIZE) * 1.4 + (self.spread_pts * 1.2)
                rr_arr[i] = 3.8
                strat_names[i] = "ALL_YEARS_BEAR_REBOUND_SELL"
                continue

        return signals, sl_pts, rr_arr, strat_names

    def run_backtest(self, df: pd.DataFrame, stress_multiplier: float = 1.0) -> Dict:
        n = len(df)
        close = df['close'].values
        high = df['high'].values
        low = df['low'].values
        
        eff_spread_pts = self.spread_pts * stress_multiplier
        eff_commission = COMMISSION_PER_001LOT_RT * stress_multiplier
        
        signals, sl_pts_arr, rr_arr, strat_names = self.generate_signals(df)
        
        balance = self.initial_balance
        equity = balance
        peak = balance
        max_dd = 0.0
        max_dd_pct = 0.0
        
        trades: List[Trade] = []
        equity_curve = [balance]
        strat_stats = {}
        
        trade_id = 0
        open_trade: Optional[Trade] = None
        
        for i in range(201, n):
            if open_trade is not None:
                t = open_trade
                hi, lo, cl = high[i], low[i], close[i]
                closed = False
                exit_price = cl
                reason = ""
                
                if t.direction == "BUY":
                    if lo <= t.sl:
                        exit_price = t.sl
                        reason = "SL"
                        closed = True
                    elif hi >= t.tp:
                        exit_price = t.tp
                        reason = "TP"
                        closed = True
                else: # SELL
                    if hi >= t.sl:
                        exit_price = t.sl
                        reason = "SL"
                        closed = True
                    elif lo <= t.tp:
                        exit_price = t.tp
                        reason = "TP"
                        closed = True
                        
                if closed:
                    pts = (exit_price - t.entry) / PIP_SIZE if t.direction == "BUY" else (t.entry - exit_price) / PIP_SIZE
                    raw_pnl = pts * POINT_VALUE * (t.lot_size / 0.01)
                    comm = (t.lot_size / 0.01) * eff_commission
                    net_pnl = raw_pnl - comm
                    
                    balance += net_pnl
                    equity = balance
                    equity_curve.append(equity)
                    
                    t.close_price = exit_price
                    t.close_reason = reason
                    t.close_time = df.index[i]
                    t.profit_usd = net_pnl
                    trades.append(t)
                    open_trade = None
                    
                    sname = t.strategy
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

            if open_trade is None and signals[i] != 0:
                sig_dir = signals[i]
                sp = sl_pts_arr[i]
                rr_target = rr_arr[i]
                sname = strat_names[i]
                
                if sp > 0 and rr_target > 0:
                    lot = MultiYearRiskManager.calc_lot(equity, peak, sp, self.base_risk_pct)
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
                        
                    trade_id += 1
                    open_trade = Trade(
                        id=trade_id,
                        strategy=sname,
                        direction=direction,
                        entry=entry,
                        sl=sl,
                        tp=tp,
                        lot_size=lot,
                        open_time=df.index[i],
                        sl_pts=sp
                    )

        pnl_series = [t.profit_usd for t in trades]
        wins = [p for p in pnl_series if p > 0]
        losses = [p for p in pnl_series if p < 0]
        
        gross_win = sum(wins) if wins else 0.0
        gross_loss = abs(sum(losses)) if losses else 1e-10
        pf = float(gross_win / gross_loss)
        win_rate = (len(wins) / len(trades) * 100.0) if trades else 0.0
        
        rets = pd.Series(pnl_series)
        sharpe = float((rets.mean() / rets.std()) * np.sqrt(252 * 24)) if len(rets) > 1 and rets.std() > 0 else 0.0
        
        return {
            "initial_balance": self.initial_balance,
            "final_balance": balance,
            "total_pnl": balance - self.initial_balance,
            "return_pct": ((balance - self.initial_balance) / self.initial_balance) * 100.0,
            "total_trades": len(trades),
            "win_rate": win_rate,
            "profit_factor": pf,
            "max_dd_usd": max_dd,
            "max_dd_pct": max_dd_pct,
            "sharpe_ratio": sharpe,
            "strategy_stats": strat_stats,
            "trades": trades
        }

def run_all_years_wave_capture_validation():
    print("==========================================================")
    print("🎯 EXECUTING ALL-YEARS 15-20% WAVE CAPTURE GAUNTLET ($1,000 INITIAL)")
    print("==========================================================")
    
    antigravity_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(antigravity_dir, "data")
    m15_csv = os.path.join(data_dir, "GOLD_M15.csv")
    
    if not os.path.exists(m15_csv):
        print(f"❌ GOLD M15 CSV not found at: {m15_csv}")
        return
        
    df_m15 = pd.read_csv(m15_csv)
    df_m15['datetime'] = pd.to_datetime(df_m15['datetime_str'])
    df_m15.set_index('datetime', inplace=True)
    
    engine = AllYearsWaveCaptureEngine(initial_balance=1000.0, base_risk_pct=0.055, spread_pts=25.0)
    
    # 1. Year 2024-2025
    df_2024 = df_m15.loc['2024-05-01 00:00:00':'2025-05-01 00:00:00'].copy()
    res_2024 = engine.run_backtest(df_2024)
    
    # 2. Year 2023-2024
    df_2023 = df_m15.loc['2023-05-01 00:00:00':'2024-05-01 00:00:00'].copy()
    res_2023 = engine.run_backtest(df_2023)
    
    # 3. Year 2022-2023
    df_2022 = df_m15.loc['2022-05-02 00:00:00':'2023-05-01 00:00:00'].copy()
    res_2022 = engine.run_backtest(df_2022)
    
    # 4. Year 2025-2026
    df_2025 = df_m15.loc['2025-05-01 00:00:00':'2026-07-24 23:45:00'].copy()
    res_2025 = engine.run_backtest(df_2025)

    print("\n📊 MULTI-YEAR WAVE CAPTURE PERFORMANCE MATRIX:")
    print(f"1. Năm 2024-2025: Final=${res_2024['final_balance']:,.2f} | Net=${res_2024['total_pnl']:+,.2f} | PF={res_2024['profit_factor']:.3f} | MaxDD={res_2024['max_dd_pct']:.2f}% | Trades={res_2024['total_trades']}")
    print(f"2. Năm 2023-2024: Final=${res_2023['final_balance']:,.2f} | Net=${res_2023['total_pnl']:+,.2f} | PF={res_2023['profit_factor']:.3f} | MaxDD={res_2023['max_dd_pct']:.2f}% | Trades={res_2023['total_trades']}")
    print(f"3. Năm 2022-2023: Final=${res_2022['final_balance']:,.2f} | Net=${res_2022['total_pnl']:+,.2f} | PF={res_2022['profit_factor']:.3f} | MaxDD={res_2022['max_dd_pct']:.2f}% | Trades={res_2022['total_trades']}")
    print(f"4. Năm 2025-2026: Final=${res_2025['final_balance']:,.2f} | Net=${res_2025['total_pnl']:+,.2f} | PF={res_2025['profit_factor']:.3f} | MaxDD={res_2025['max_dd_pct']:.2f}% | Trades={res_2025['total_trades']}")

if __name__ == "__main__":
    run_all_years_wave_capture_validation()
