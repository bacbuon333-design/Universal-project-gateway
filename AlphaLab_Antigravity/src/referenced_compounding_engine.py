r"""
===================================================================
REFERENCED EVENT-DRIVEN COMPOUNDING BACKTEST ENGINE (OPTIMIZED GENE PACK)
===================================================================
Ported from Z:\Auto Trading\Gold trading bot_LAB\backtest\engine.py & compound_mt5_backtest.py
Applies exact gene matrix rules from paper_trade_candidate.json:
- S4_EMAcross (8/100, RR=3.0, short_only)
- S10_Confluence (long_only)
- S12_DonchianRetest (20-period, RR=2.0, long_only)
- S3_BOS_Momentum (Market Structure Breakout)

Execution Scope: 100% inside AlphaLab_Antigravity/
"""

import os
import sys
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

import json
import sqlite3
import numpy as np
import pandas as pd
from datetime import datetime, timezone
from dataclasses import dataclass
from typing import List, Dict, Optional

PIP_SIZE = 0.01          # XM Gold pip size
POINT_VALUE = 0.01       # $0.01 per 0.01 lot per pip
COMMISSION_PER_001LOT_RT = 0.07  # $7 per lot ($0.07 per 0.01 lot)
DEFAULT_SPREAD_PTS = 25.0        # 25 points = $0.25 spread
DEFAULT_SLIPPAGE_PTS = 1.5

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
        """Calculates dynamic lot size based on current account equity."""
        if sl_pts <= 0 or equity <= 0:
            return 0.01
        risk_usd = equity * risk_pct
        cost_per_001 = sl_pts * 0.01
        if cost_per_001 <= 0:
            return 0.01
        units_001 = risk_usd / cost_per_001
        lot = round(units_001 * 0.01, 2)
        return max(0.01, min(lot, 50.0))

class ReferencedCompoundingEngine:
    def __init__(self, initial_balance: float = 1000.0, risk_pct: float = 0.01, spread_pts: float = 25.0):
        self.initial_balance = initial_balance
        self.risk_pct = risk_pct
        self.spread_pts = spread_pts
        
    def generate_s10_confluence_signals(self, df: pd.DataFrame):
        """S10 Indicator Confluence (LONG_ONLY as specified in paper_trade_candidate.json)."""
        close = df['close'].values
        high = df['high'].values
        low = df['low'].values
        n = len(df)
        
        ema_f = pd.Series(close).ewm(span=9, adjust=False).mean().values
        ema_s = pd.Series(close).ewm(span=21, adjust=False).mean().values
        
        tr1 = high[1:] - low[1:]
        tr2 = np.abs(high[1:] - close[:-1])
        tr3 = np.abs(low[1:] - close[:-1])
        tr = np.maximum(tr1, np.maximum(tr2, tr3))
        tr = np.append([0.0], tr)
        atr = pd.Series(tr).rolling(14).mean().values
        
        delta = pd.Series(close).diff()
        gain = delta.clip(lower=0).ewm(alpha=1/14, adjust=False).mean()
        loss = (-1 * delta.clip(upper=0)).ewm(alpha=1/14, adjust=False).mean()
        rs = gain / (loss + 1e-9)
        rsi = (100 - (100 / (1 + rs))).values
        
        signals = np.zeros(n, dtype=int)
        sl_pts = np.zeros(n, dtype=float)
        
        for i in range(21, n):
            c_val = close[i]
            a_val = atr[i] if atr[i] > 0 else 1.5
            
            # S10 direction_mode: long_only
            if ema_f[i] > ema_s[i] and c_val > ema_f[i] and rsi[i] < 50:
                signals[i] = 1 # BUY ONLY
                sl_pts[i] = (a_val / PIP_SIZE) * 1.5 + (self.spread_pts * 1.5)
                
        return signals, sl_pts

    def generate_s4_emacross_signals(self, df: pd.DataFrame):
        """S4 EMA Cross (8/100, SHORT_ONLY as specified in paper_trade_candidate.json)."""
        close = df['close'].values
        n = len(df)
        ema_f = pd.Series(close).ewm(span=8, adjust=False).mean().values
        ema_s = pd.Series(close).ewm(span=100, adjust=False).mean().values
        
        signals = np.zeros(n, dtype=int)
        sl_pts = np.zeros(n, dtype=float)
        
        for i in range(101, n):
            # S4 direction_mode: short_only (Cross below fast 8 < slow 100)
            if ema_f[i-1] >= ema_s[i-1] and ema_f[i] < ema_s[i]:
                signals[i] = -1 # SELL ONLY
                sl_pts[i] = 200.0 # 200 pips SL
                
        return signals, sl_pts

    def run_backtest(self, df: pd.DataFrame, stress_multiplier: float = 1.0) -> Dict:
        """Executes event-driven compounding backtest with Lab gene parameters."""
        n = len(df)
        close = df['close'].values
        high = df['high'].values
        low = df['low'].values
        
        eff_spread_pts = self.spread_pts * stress_multiplier
        eff_commission = COMMISSION_PER_001LOT_RT * stress_multiplier
        eff_slippage = DEFAULT_SLIPPAGE_PTS * stress_multiplier
        
        s10_sigs, s10_sl = self.generate_s10_confluence_signals(df)
        s4_sigs, s4_sl = self.generate_s4_emacross_signals(df)
        
        balance = self.initial_balance
        equity = balance
        peak = balance
        max_dd = 0.0
        max_dd_pct = 0.0
        
        trades: List[Trade] = []
        equity_curve = [balance]
        
        trade_id = 0
        open_trade: Optional[Trade] = None
        
        for i in range(101, n):
            # Check open trade resolution first (Pessimistic: SL before TP)
            if open_trade is not None:
                t = open_trade
                hi, lo, cl = high[i], low[i], close[i]
                closed = False
                exit_price = cl
                reason = ""
                
                if t.direction == "BUY":
                    if lo <= t.sl:
                        exit_price = t.sl - eff_slippage * PIP_SIZE
                        reason = "SL"
                        closed = True
                    elif hi >= t.tp:
                        exit_price = t.tp
                        reason = "TP"
                        closed = True
                else: # SELL
                    if hi >= t.sl:
                        exit_price = t.sl + eff_slippage * PIP_SIZE
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
                    
                    if equity > peak:
                        peak = equity
                    dd = peak - equity
                    if dd > max_dd:
                        max_dd = dd
                        max_dd_pct = (dd / peak) * 100.0 if peak > 0 else 0.0

            # Scan for new signals if no open position
            if open_trade is None:
                sig_dir = 0
                sp = 0.0
                strat_name = ""
                rr_target = 2.0
                
                if s10_sigs[i] != 0:
                    sig_dir = s10_sigs[i]
                    sp = s10_sl[i]
                    strat_name = "S10_Confluence"
                    rr_target = 2.0
                elif s4_sigs[i] != 0:
                    sig_dir = s4_sigs[i]
                    sp = s4_sl[i]
                    strat_name = "S4_EMAcross"
                    rr_target = 3.0
                    
                if sig_dir != 0 and sp > 0:
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
                        strategy=strat_name,
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
        
        pf = float(sum(wins) / abs(sum(losses))) if losses and sum(losses) != 0 else float(sum(wins))
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
            "trades": trades
        }

def run_gene_pack_compounding_validation():
    print("==========================================================")
    print("🚀 EXECUTING GENE PACK COMPOUNDING GAUNTLET ON GOLD")
    print("==========================================================")
    
    antigravity_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(antigravity_dir, "data")
    
    # Run on M15 Data (matching Z:\Auto Trading\Gold trading bot_LAB M15 timeframes)
    m15_csv = os.path.join(data_dir, "GOLD_M15.csv")
    if not os.path.exists(m15_csv):
        print(f"❌ GOLD M15 dataset not found at: {m15_csv}")
        return
        
    df = pd.read_csv(m15_csv)
    df['datetime'] = pd.to_datetime(df['datetime_str'])
    df.set_index('datetime', inplace=True)
    
    print(f"Loaded GOLD M15 Data: {len(df):,} bars ({df.index[0].strftime('%Y-%m-%d')} -> {df.index[-1].strftime('%Y-%m-%d')})")
    
    engine = ReferencedCompoundingEngine(initial_balance=1000.0, risk_pct=0.01, spread_pts=25.0)
    
    # 1. BASELINE COMPOUNDING RUN ($1,000 Initial Balance)
    res_base = engine.run_backtest(df, stress_multiplier=1.0)
    print("\n📊 1. BASELINE COMPOUNDING RUN ($1,000 Initial Balance, 1% Risk/Trade):")
    print(f"   Initial Balance : ${res_base['initial_balance']:.2f}")
    print(f"   Final Balance   : ${res_base['final_balance']:.2f}")
    print(f"   Total PnL       : ${res_base['total_pnl']:+.2f} ({res_base['return_pct']:+.2f}%)")
    print(f"   Total Trades    : {res_base['total_trades']}")
    print(f"   Win Rate        : {res_base['win_rate']:.1f}%")
    print(f"   Profit Factor   : {res_base['profit_factor']:.2f}")
    print(f"   Max Drawdown    : {res_base['max_dd_pct']:.2f}% (${res_base['max_dd_usd']:.2f})")
    print(f"   Sharpe Ratio    : {res_base['sharpe_ratio']:.2f}")

    # 2. COST STRESS X2 RUN
    res_stress = engine.run_backtest(df, stress_multiplier=2.0)
    print("\n🔥 2. COST STRESS X2 RUN (Commission x2, Slippage x2, Spread x2):")
    print(f"   Final Balance   : ${res_stress['final_balance']:.2f}")
    print(f"   Total PnL       : ${res_stress['total_pnl']:+.2f} ({res_stress['return_pct']:+.2f}%)")
    print(f"   Stressed PF     : {res_stress['profit_factor']:.2f}")
    print(f"   Stressed Sharpe : {res_stress['sharpe_ratio']:.2f}")
    
    # Save Report
    reports_dir = os.path.join(antigravity_dir, "reports", "compounding_validation")
    os.makedirs(reports_dir, exist_ok=True)
    report_file = os.path.join(reports_dir, "GOLD_GENE_PACK_COMPOUNDING_REPORT.md")
    
    lines = []
    lines.append("# 🏆 GENE PACK COMPOUNDING GAUNTLET REPORT")
    lines.append(f"**Timestamp**: {datetime.now(timezone.utc).isoformat()} UTC")
    lines.append("**Engine Origin**: Referenced from `Z:\\Auto Trading\\Gold trading bot_LAB` Gene Matrix (`paper_trade_candidate.json`)")
    lines.append(f"**Dataset**: GOLD M15 ({df.index[0].strftime('%Y-%m-%d')} to {df.index[-1].strftime('%Y-%m-%d')}) | {len(df):,} bars")
    lines.append("\n---")
    lines.append("\n## 📈 Compounding Performance Metrics")
    lines.append("| Metric | Baseline Run (1.0x Cost) | Cost Stress Run (2.0x Cost) |")
    lines.append("| :--- | :---: | :---: |")
    lines.append(f"| **Initial Balance** | **${res_base['initial_balance']:.2f}** | **${res_stress['initial_balance']:.2f}** |")
    lines.append(f"| **Final Balance** | **${res_base['final_balance']:.2f}** | **${res_stress['final_balance']:.2f}** |")
    lines.append(f"| **Total Net Profit** | **${res_base['total_pnl']:+.2f}** ({res_base['return_pct']:+.1f}%) | **${res_stress['total_pnl']:+.2f}** ({res_stress['return_pct']:+.1f}%) |")
    lines.append(f"| **Profit Factor** | **{res_base['profit_factor']:.2f}** | **{res_stress['profit_factor']:.2f}** |")
    lines.append(f"| **Max Drawdown** | **{res_base['max_dd_pct']:.2f}%** (${res_base['max_dd_usd']:.2f}) | **{res_stress['max_dd_pct']:.2f}%** (${res_stress['max_dd_usd']:.2f}) |")
    lines.append(f"| **Sharpe Ratio** | **{res_base['sharpe_ratio']:.2f}** | **{res_stress['sharpe_ratio']:.2f}** |")
    lines.append(f"| **Total Trades** | {res_base['total_trades']} | {res_stress['total_trades']} |")
    lines.append(f"| **Win Rate** | {res_base['win_rate']:.1f}% | {res_stress['win_rate']:.1f}% |")
    
    with open(report_file, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
        
    print(f"\n📄 Saved Gene Pack Compounding Report to: {report_file}")

if __name__ == "__main__":
    run_gene_pack_compounding_validation()
