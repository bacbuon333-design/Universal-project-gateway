from __future__ import annotations

"""Single frozen diagnostic backtest with dual gross/net metrics for ALAB-M1-FUSION-001R.

DIAGNOSTIC ONLY. Never overrides event-study verdict.
Rules:
- Signal: Failed Auction with Reaction Score >= 7.
- Entry: Open of bar t+1.
- SL: 1.00 * ATR14[t].
- TP: NONE.
- Max holding: 5 M1 bars (exit at Close of bar t+5 or stop touched first).
- One position at a time per symbol.
"""

from typing import Any, Dict, List
import numpy as np
import pandas as pd

from .failed_auction import FailedAuctionEvent
from .cost_contract import CostContract, get_verified_cost_contract

LOT_SIZE = 0.10


def run_diagnostic_backtest(
    df: pd.DataFrame,
    events: List[FailedAuctionEvent],
    min_reaction_score: int = 7,
    sl_atr_mult: float = 1.0,
    max_holding_bars: int = 5,
    cost_contract: CostContract | None = None,
) -> Dict[str, Any]:
    """Execute single diagnostic backtest simulation."""
    if cost_contract is None:
        cost_contract = get_verified_cost_contract("GOLD")

    qualifying_events = [ev for ev in events if ev.reaction_score >= min_reaction_score]
    n = len(df)
    opens = df["open"].to_numpy(dtype=float)
    highs = df["high"].to_numpy(dtype=float)
    lows = df["low"].to_numpy(dtype=float)
    closes = df["close"].to_numpy(dtype=float)
    dts = df["datetime"]
    has_spread = "spread" in df.columns
    spreads = df["spread"].to_numpy(dtype=float) if has_spread else np.zeros(n, dtype=float)

    point = cost_contract.point
    contract_size = cost_contract.trade_contract_size
    oz = LOT_SIZE * contract_size  # 10 oz for 0.10 lot
    comm_per_oz = (cost_contract.commission_per_lot_usd / 100.0)  # USD / oz

    trades = []
    current_position_exit_bar = -1

    for ev in qualifying_events:
        t_sig = ev.bar_index
        t_entry = t_sig + 1
        if t_entry >= n:
            continue

        # One position at a time constraint
        if t_entry <= current_position_exit_bar:
            continue

        side = ev.side
        entry_price = opens[t_entry]
        atr_sig = ev.atr14
        sl_dist = sl_atr_mult * atr_sig
        
        # Dynamic spread price conversion
        spread_pts = spreads[t_entry] if has_spread else 0.0
        spread_price_dist = spread_pts * point
        spread_cost_usd = spread_price_dist * oz
        comm_cost_usd = comm_per_oz * oz
        total_costs_trade = spread_cost_usd + comm_cost_usd

        if side == "LONG":
            sl_price = entry_price - sl_dist
        else:
            sl_price = entry_price + sl_dist

        exit_bar = -1
        exit_price = 0.0
        exit_reason = "TIME_EXIT"

        # Simulate holding
        max_bar = min(t_entry + max_holding_bars - 1, n - 1)
        for b in range(t_entry, max_bar + 1):
            if side == "LONG":
                if opens[b] <= sl_price:
                    exit_bar = b
                    exit_price = opens[b]  # pessimistic fill
                    exit_reason = "STOP_LOSS"
                    break
                elif lows[b] <= sl_price:
                    exit_bar = b
                    exit_price = sl_price
                    exit_reason = "STOP_LOSS"
                    break
            else:  # SHORT
                if opens[b] >= sl_price:
                    exit_bar = b
                    exit_price = opens[b]  # pessimistic fill
                    exit_reason = "STOP_LOSS"
                    break
                elif highs[b] >= sl_price:
                    exit_bar = b
                    exit_price = sl_price
                    exit_reason = "STOP_LOSS"
                    break

        if exit_bar == -1:
            exit_bar = max_bar
            exit_price = closes[max_bar]
            exit_reason = "TIME_EXIT"

        current_position_exit_bar = exit_bar

        if side == "LONG":
            gross_pnl_usd = (exit_price - entry_price) * oz
        else:
            gross_pnl_usd = (entry_price - exit_price) * oz

        net_pnl_usd = gross_pnl_usd - total_costs_trade

        trades.append({
            "event_id": ev.event_id,
            "signal_bar": t_sig,
            "entry_bar": t_entry,
            "entry_time": str(dts.iloc[t_entry]),
            "exit_bar": exit_bar,
            "exit_time": str(dts.iloc[exit_bar]),
            "side": side,
            "reaction_score": ev.reaction_score,
            "entry_price": entry_price,
            "sl_price": sl_price,
            "exit_price": exit_price,
            "exit_reason": exit_reason,
            "holding_bars": exit_bar - t_entry + 1,
            "cost_usd": total_costs_trade,
            "gross_pnl_usd": gross_pnl_usd,
            "net_pnl_usd": net_pnl_usd,
            "is_gross_win": gross_pnl_usd > 0,
            "is_net_win": net_pnl_usd > 0,
        })

    total_trades = len(trades)
    if total_trades == 0:
        return {
            "status": "INSUFFICIENT_DIAGNOSTIC",
            "total_trades": 0,
            "message": "No qualifying trades taken.",
            "cost_verification_status": cost_contract.cost_verification_status,
        }

    df_t = pd.DataFrame(trades)
    gross_wins = df_t[df_t["gross_pnl_usd"] > 0]
    gross_losses = df_t[df_t["gross_pnl_usd"] <= 0]
    net_wins = df_t[df_t["net_pnl_usd"] > 0]
    net_losses = df_t[df_t["net_pnl_usd"] <= 0]

    gross_profit = float(gross_wins["gross_pnl_usd"].sum()) if len(gross_wins) > 0 else 0.0
    gross_loss = abs(float(gross_losses["gross_pnl_usd"].sum())) if len(gross_losses) > 0 else 0.0
    gross_pf = gross_profit / gross_loss if gross_loss > 1e-9 else (999.0 if gross_profit > 0 else 0.0)

    net_profit = float(net_wins["net_pnl_usd"].sum()) if len(net_wins) > 0 else 0.0
    net_loss = abs(float(net_losses["net_pnl_usd"].sum())) if len(net_losses) > 0 else 0.0
    net_pf = net_profit / net_loss if net_loss > 1e-9 else (999.0 if net_profit > 0 else 0.0)

    gross_pnl_total = float(df_t["gross_pnl_usd"].sum())
    net_pnl_total = float(df_t["net_pnl_usd"].sum())
    total_costs_all = float(df_t["cost_usd"].sum())

    gross_expectancy = gross_pnl_total / total_trades
    net_expectancy = net_pnl_total / total_trades
    win_rate_pct = (len(net_wins) / total_trades) * 100.0
    gross_win_rate_pct = (len(gross_wins) / total_trades) * 100.0

    # Max Drawdown
    equity_curve = df_t["net_pnl_usd"].cumsum()
    peak = equity_curve.cummax()
    drawdown = peak - equity_curve
    max_dd_usd = float(drawdown.max()) if len(drawdown) > 0 else 0.0

    # Sub-breakdowns
    longs = df_t[df_t["side"] == "LONG"]
    shorts = df_t[df_t["side"] == "SHORT"]

    long_net_wins = int((longs["net_pnl_usd"] > 0).sum())
    short_net_wins = int((shorts["net_pnl_usd"] > 0).sum())

    stop_exits = int((df_t["exit_reason"] == "STOP_LOSS").sum())
    time_exits = int((df_t["exit_reason"] == "TIME_EXIT").sum())

    cost_to_edge = (total_costs_all / gross_pnl_total) if gross_pnl_total > 1e-9 else 999.0

    if total_trades < 30:
        diag_status = "INSUFFICIENT_DIAGNOSTIC"
    elif net_pf >= 1.05 and net_pnl_total > 0:
        diag_status = "POSITIVE_DIAGNOSTIC"
    else:
        diag_status = "NEGATIVE_DIAGNOSTIC"

    return {
        "status": diag_status,
        "total_trades": total_trades,
        "long_trades": len(longs),
        "long_wins": long_net_wins,
        "long_win_rate_pct": (long_net_wins / len(longs) * 100.0) if len(longs) > 0 else 0.0,
        "short_trades": len(shorts),
        "short_wins": short_net_wins,
        "short_win_rate_pct": (short_net_wins / len(shorts) * 100.0) if len(shorts) > 0 else 0.0,
        "win_rate_pct": win_rate_pct,
        "gross_win_rate_pct": gross_win_rate_pct,
        "gross_profit_factor": gross_pf,
        "net_profit_factor": net_pf,
        "gross_expectancy_usd": gross_expectancy,
        "net_expectancy_usd": net_expectancy,
        "gross_pnl_usd": gross_pnl_total,
        "net_pnl_usd": net_pnl_total,
        "total_costs_usd": total_costs_all,
        "mean_cost_per_trade_usd": float(df_t["cost_usd"].mean()),
        "median_cost_per_trade_usd": float(df_t["cost_usd"].median()),
        "cost_to_gross_edge_ratio": cost_to_edge,
        "max_drawdown_usd": max_dd_usd,
        "stop_loss_exits": stop_exits,
        "time_exits": time_exits,
        "cost_verification_status": cost_contract.cost_verification_status,
        "trades": trades,
    }
