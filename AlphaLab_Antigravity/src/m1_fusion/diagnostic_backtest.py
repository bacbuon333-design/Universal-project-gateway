from __future__ import annotations

"""Single frozen diagnostic backtest for ALAB-M1-FUSION-001.

DIAGNOSTIC ONLY. Never overrides event-study verdict.
Rules:
- Signal: Failed Auction with Reaction Score >= 7.
- Entry: Open of bar t+1.
- SL: 1.00 * ATR14[t].
- TP: NONE.
- Max holding: 5 M1 bars (exit at Close of bar t+5 or stop touched first).
- One position at a time.
"""

from typing import Any, Dict, List
import numpy as np
import pandas as pd

from .failed_auction import FailedAuctionEvent

LOT_SIZE = 0.10
CONTRACT_SIZE = 100.0  # 1 lot Gold = 100 oz


def run_diagnostic_backtest(
    df: pd.DataFrame,
    events: List[FailedAuctionEvent],
    min_reaction_score: int = 7,
    sl_atr_mult: float = 1.0,
    max_holding_bars: int = 5,
) -> Dict[str, Any]:
    """Execute single diagnostic backtest simulation."""
    # Filter qualifying events (Score >= 7)
    qualifying_events = [ev for ev in events if ev.reaction_score >= min_reaction_score]
    
    n = len(df)
    opens = df["open"].to_numpy(dtype=float)
    highs = df["high"].to_numpy(dtype=float)
    lows = df["low"].to_numpy(dtype=float)
    closes = df["close"].to_numpy(dtype=float)
    dts = df["datetime"]
    has_spread = "spread" in df.columns
    spreads = df["spread"].to_numpy(dtype=float) if has_spread else np.zeros(n, dtype=float)

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
        
        # Calculate spread cost if available
        # In Gold, 1 point spread = 0.01 USD on 1 oz (XM: 25 points = 0.25 USD)
        spread_cost_per_oz = spreads[t_entry] * 0.01 if has_spread else 0.0
        commission_per_oz = 0.07  # Standard 7 USD / lot = 0.07 USD / oz

        if side == "LONG":
            sl_price = entry_price - sl_dist
        else:
            sl_price = entry_price + sl_dist

        exit_bar = -1
        exit_price = 0.0
        exit_reason = "TIME_EXIT"

        # Simulate holding up to max_holding_bars
        max_bar = min(t_entry + max_holding_bars - 1, n - 1)
        for b in range(t_entry, max_bar + 1):
            if side == "LONG":
                # Check adverse gap through stop
                if opens[b] <= sl_price:
                    exit_bar = b
                    exit_price = opens[b]  # pessimistic open fill
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
                    exit_price = opens[b]  # pessimistic open fill
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

        # Calculate PnL (in USD for 0.10 lot = 10 oz)
        oz = LOT_SIZE * CONTRACT_SIZE  # 10 oz
        if side == "LONG":
            gross_pnl_usd = (exit_price - entry_price) * oz
        else:
            gross_pnl_usd = (entry_price - exit_price) * oz

        total_costs_usd = (spread_cost_per_oz + commission_per_oz) * oz
        net_pnl_usd = gross_pnl_usd - total_costs_usd

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
            "gross_pnl_usd": gross_pnl_usd,
            "net_pnl_usd": net_pnl_usd,
            "pnl_bps": (net_pnl_usd / (entry_price * oz)) * 10000.0 if entry_price > 0 else 0.0,
            "is_win": net_pnl_usd > 0,
        })

    # Summary Performance Metrics
    total_trades = len(trades)
    if total_trades == 0:
        return {
            "status": "INSUFFICIENT_DIAGNOSTIC",
            "total_trades": 0,
            "message": "No qualifying trades taken.",
            "cost_verification_status": "VERIFIED" if has_spread else "UNVERIFIED",
        }

    df_t = pd.DataFrame(trades)
    wins = df_t[df_t["net_pnl_usd"] > 0]
    losses = df_t[df_t["net_pnl_usd"] <= 0]

    gross_profit = float(wins["net_pnl_usd"].sum()) if len(wins) > 0 else 0.0
    gross_loss = abs(float(losses["net_pnl_usd"].sum())) if len(losses) > 0 else 0.0

    profit_factor = gross_profit / gross_loss if gross_loss > 1e-9 else (999.0 if gross_profit > 0 else 0.0)
    net_pnl_total = float(df_t["net_pnl_usd"].sum())
    win_rate_pct = (len(wins) / total_trades) * 100.0
    expectancy_usd = net_pnl_total / total_trades

    # Max Drawdown
    equity_curve = df_t["net_pnl_usd"].cumsum()
    peak = equity_curve.cummax()
    drawdown = peak - equity_curve
    max_dd_usd = float(drawdown.max()) if len(drawdown) > 0 else 0.0

    # Sub-breakdowns
    longs = df_t[df_t["side"] == "LONG"]
    shorts = df_t[df_t["side"] == "SHORT"]

    long_wins = int((longs["net_pnl_usd"] > 0).sum())
    short_wins = int((shorts["net_pnl_usd"] > 0).sum())

    stop_exits = int((df_t["exit_reason"] == "STOP_LOSS").sum())
    time_exits = int((df_t["exit_reason"] == "TIME_EXIT").sum())

    cost_status = "VERIFIED" if has_spread else "UNVERIFIED"

    if total_trades < 30:
        diag_status = "INSUFFICIENT_DIAGNOSTIC"
    elif profit_factor >= 1.05 and net_pnl_total > 0:
        diag_status = "POSITIVE_DIAGNOSTIC"
    else:
        diag_status = "NEGATIVE_DIAGNOSTIC"

    return {
        "status": diag_status,
        "total_trades": total_trades,
        "long_trades": len(longs),
        "long_wins": long_wins,
        "long_win_rate_pct": (long_wins / len(longs) * 100.0) if len(longs) > 0 else 0.0,
        "short_trades": len(shorts),
        "short_wins": short_wins,
        "short_win_rate_pct": (short_wins / len(shorts) * 100.0) if len(shorts) > 0 else 0.0,
        "win_rate_pct": win_rate_pct,
        "profit_factor": profit_factor,
        "expectancy_usd": expectancy_usd,
        "net_pnl_usd": net_pnl_total,
        "gross_profit_usd": gross_profit,
        "gross_loss_usd": gross_loss,
        "max_drawdown_usd": max_dd_usd,
        "stop_loss_exits": stop_exits,
        "time_exits": time_exits,
        "cost_verification_status": cost_status,
        "trades": trades,
    }
