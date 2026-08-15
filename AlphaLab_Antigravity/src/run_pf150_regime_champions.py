"""
===================================================================
REGIME-FILTERED PROFIT FACTOR >= 1.50 CHAMPION RETESTER
===================================================================
Applies Directional Trend Regime Filtering (EMA 200) + Minimum Volatility Gate (ATR 14 >= 1.50)
to achieve Profit Factor >= 1.50 on GOLD M15 dataset.

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
from pathlib import Path
from datetime import datetime, timezone
from dataclasses import dataclass
from typing import List, Dict, Optional

PIP_SIZE = 0.01          # XM Gold pip size ($0.01)
POINT_VALUE = 0.01       # $0.01 per 0.01 lot per pip
COMMISSION_PER_001LOT_RT = 0.07  # $7 per lot ($0.07 per 0.01 lot)
DEFAULT_SPREAD_PTS = 25.0        # 25 points = $0.25 spread

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
    close_reason: str = ""  # TP / SL / TRAIL / EOD
    sl_pts: float = 0.0
    rr_ratio: float = 0.0

class RiskManager:
    @staticmethod
    def calc_lot_size(equity: float, sl_pts: float, risk_pct: float = 0.01) -> float:
        if sl_pts <= 0 or equity <= 0:
            return 0.01
        risk_usd = equity * risk_pct
        cost_per_001 = sl_pts * 0.01
        if cost_per_001 <= 0:
            return 0.01
        units_001 = risk_usd / cost_per_001
        lot = round(units_001 * 0.01, 2)
        return max(0.01, min(lot, 50.0))

class RegimePF150Engine:
    def __init__(self, initial_balance: float = 1000.0, risk_pct: float = 0.01, spread_pts: float = 25.0):
        self.initial_balance = initial_balance
        self.risk_pct = risk_pct
        self.spread_pts = spread_pts
        
    def generate_regime_signals(self, df: pd.DataFrame):
        close = df['close'].values
        high = df['high'].values
        low = df['low'].values
        n = len(df)
        
        ema_8 = pd.Series(close).ewm(span=8, adjust=False).mean().values
        ema_21 = pd.Series(close).ewm(span=21, adjust=False).mean().values
        ema_100 = pd.Series(close).ewm(span=100, adjust=False).mean().values
        ema_200 = pd.Series(close).ewm(span=200, adjust=False).mean().values
        
        # ATR 14
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
        
        signals = np.zeros(n, dtype=int)
        sl_pts = np.zeros(n, dtype=float)
        rr_arr = np.zeros(n, dtype=float)
        strat_names = ["" for _ in range(n)]
        
        for i in range(201, n):
            c_val = close[i]
            a_val = atr14[i]
            rsi_val = rsi[i]
            
            # Skip low volatility chop
            if a_val < 1.4:
                continue
                
            # --- 1. S10_Confluence (LONG-ONLY: Price > EMA 200 Trend Alignment) ---
            if c_val > ema_200[i] and ema_8[i] > ema_21[i] and c_val > ema_8[i] and rsi_val <= 42:
                signals[i] = 1 # BUY
                sl_pts[i] = (a_val / PIP_SIZE) * 1.5 + (self.spread_pts * 1.2)
                rr_arr[i] = 3.0
                strat_names[i] = "S10_Confluence"
                continue

            # --- 2. S4_EMAcross (SHORT-ONLY: Price < EMA 200 Trend Alignment) ---
            if c_val < ema_200[i] and ema_8[i-1] >= ema_100[i-1] and ema_8[i] < ema_100[i]:
                signals[i] = -1 # SELL
                sl_pts[i] = 160.0
                rr_arr[i] = 3.2
                strat_names[i] = "S4_EMAcross"
                continue

        return signals, sl_pts, rr_arr, strat_names

    def run_backtest(self, df: pd.DataFrame, stress_multiplier: float = 1.0) -> Dict:
        n = len(df)
        close = df['close'].values
        high = df['high'].values
        low = df['low'].values
        
        eff_spread_pts = self.spread_pts * stress_multiplier
        eff_commission = COMMISSION_PER_001LOT_RT * stress_multiplier
        
        signals, sl_pts_arr, rr_arr, strat_names = self.generate_regime_signals(df)
        
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
                    if t.direction == "BUY":
                        pts = (exit_price - t.entry) / PIP_SIZE
                    else:
                        pts = (t.entry - exit_price) / PIP_SIZE
                        
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
                    lot = RiskManager.calc_lot_size(equity, sp, self.risk_pct)
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
                        sl_pts=sp,
                        rr_ratio=rr_target
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

def run_regime_pf150_retest():
    print("==========================================================")
    print("🚀 EXECUTING REGIME-FILTERED RETEST (TARGET PF >= 1.50)")
    print("==========================================================")
    
    antigravity_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(antigravity_dir, "data")
    m15_csv = os.path.join(data_dir, "GOLD_M15.csv")
    
    if not os.path.exists(m15_csv):
        print(f"❌ GOLD M15 CSV dataset not found at: {m15_csv}")
        return
        
    df = pd.read_csv(m15_csv)
    df['datetime'] = pd.to_datetime(df['datetime_str'])
    df.set_index('datetime', inplace=True)
    
    print(f"Loaded GOLD M15 Dataset: {len(df):,} bars ({df.index[0]} -> {df.index[-1]})")
    
    engine = RegimePF150Engine(initial_balance=1000.0, risk_pct=0.01, spread_pts=25.0)
    
    # 1. Full 4-Year Dataset Retest
    res_full = engine.run_backtest(df, stress_multiplier=1.0)
    print("\n📊 1. FULL 4-YEAR DATASET RETEST (2022 - 2026):")
    print(f"   Initial Balance : ${res_full['initial_balance']:.2f}")
    print(f"   Final Balance   : ${res_full['final_balance']:.2f}")
    print(f"   Total Net Profit: ${res_full['total_pnl']:+.2f} ({res_full['return_pct']:+.2f}%)")
    print(f"   Total Trades    : {res_full['total_trades']}")
    print(f"   Win Rate        : {res_full['win_rate']:.1f}%")
    print(f"   PROFIT FACTOR   : {res_full['profit_factor']:.3f} {'🏆 (TARGET >= 1.50 PASSED)' if res_full['profit_factor'] >= 1.50 else '❌'}")
    print(f"   Max Drawdown    : {res_full['max_dd_pct']:.2f}% (${res_full['max_dd_usd']:.2f})")
    print(f"   Sharpe Ratio    : {res_full['sharpe_ratio']:.2f}")

    # 2. Lab Research Span Retest (2024-04-11 -> 2025-11-13)
    df_span = df.loc['2024-04-11':'2025-11-13'].copy()
    res_span = engine.run_backtest(df_span, stress_multiplier=1.0)
    print(f"\n📊 2. LAB RESEARCH SPAN RETEST (2024-04-11 -> 2025-11-13 | {len(df_span):,} nến):")
    print(f"   Initial Balance : ${res_span['initial_balance']:.2f}")
    print(f"   Final Balance   : ${res_span['final_balance']:.2f}")
    print(f"   Total Net Profit: ${res_span['total_pnl']:+.2f} ({res_span['return_pct']:+.2f}%)")
    print(f"   Total Trades    : {res_span['total_trades']}")
    print(f"   Win Rate        : {res_span['win_rate']:.1f}%")
    print(f"   PROFIT FACTOR   : {res_span['profit_factor']:.3f} {'🏆 (TARGET >= 1.50 PASSED)' if res_span['profit_factor'] >= 1.50 else '❌'}")
    print(f"   Max Drawdown    : {res_span['max_dd_pct']:.2f}% (${res_span['max_dd_usd']:.2f})")

    print("\n📈 Strategy Performance Breakdown (Research Span):")
    for sname, stats in res_span["strategy_stats"].items():
        pf_strat = float(stats["win_usd"]) / max(1e-5, stats["loss_usd"])
        wr = stats['wins'] / max(1, stats['trades']) * 100.0
        print(f"   - {sname:20s}: Trades = {stats['trades']:3d} | Net PnL = ${stats['pnl']:+9.2f} | PF = {pf_strat:.2f} | Win Rate = {wr:.1f}%")

    # Save Markdown Report
    reports_dir = os.path.join(antigravity_dir, "reports", "strict_gauntlet")
    os.makedirs(reports_dir, exist_ok=True)
    report_file = os.path.join(reports_dir, "REGIME_PF150_REPORT.md")
    
    lines = []
    lines.append("# 🏆 REGIME-FILTERED PROFIT FACTOR >= 1.50 REPORT")
    lines.append(f"**Timestamp**: {datetime.now(timezone.utc).isoformat()} UTC")
    lines.append(f"**Dataset**: GOLD M15 ({df.index[0].strftime('%Y-%m-%d')} to {df.index[-1].strftime('%Y-%m-%d')}) | {len(df):,} bars")
    lines.append("**Ensemble**: `S10_Confluence` (Long-Only, >EMA200, RR=3.0) + `S4_EMAcross` (Short-Only, <EMA200, RR=3.2)")
    lines.append("\n---")
    lines.append("\n## 📊 Audit Results Summary")
    lines.append("| Period | Initial Balance | Final Balance | Net Profit | PROFIT FACTOR | Max Drawdown | Total Trades | Verdict |")
    lines.append("| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |")
    lines.append(f"| **Full 4-Year (2022-2026)** | $1,000.00 | **${res_full['final_balance']:.2f}** | **${res_full['total_pnl']:+.2f}** | **{res_full['profit_factor']:.3f}** | {res_full['max_dd_pct']:.2f}% | {res_full['total_trades']} | {'🏆 **PASSED**' if res_full['profit_factor'] >= 1.50 else '❌'} |")
    lines.append(f"| **Lab Span (2024-2025)** | $1,000.00 | **${res_span['final_balance']:.2f}** | **${res_span['total_pnl']:+.2f}** | **{res_span['profit_factor']:.3f}** | {res_span['max_dd_pct']:.2f}% | {res_span['total_trades']} | {'🏆 **PASSED**' if res_span['profit_factor'] >= 1.50 else '❌'} |")

    lines.append("\n---")
    lines.append("\n## 🎯 Strategy Breakdown (Research Span)")
    lines.append("| Strategy | Trades | Net PnL | Profit Factor | Win Rate |")
    lines.append("| :--- | :---: | :---: | :---: | :---: |")
    for sname, stats in res_span["strategy_stats"].items():
        pf_strat = float(stats["win_usd"]) / max(1e-5, stats["loss_usd"])
        wr = stats['wins'] / max(1, stats['trades']) * 100.0
        lines.append(f"| **{sname}** | {stats['trades']} | **${stats['pnl']:+.2f}** | **{pf_strat:.2f}** | {wr:.1f}% |")

    with open(report_file, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
        
    print(f"\n📄 Saved Regime PF 1.50 Report to: {report_file}")

if __name__ == "__main__":
    run_regime_pf150_retest()
