"""V3.7.3 gap-safe execution engine for canonical V2 research.

Infrastructure only. The legacy DeepQuantEngine is intentionally not modified.
"""
from __future__ import annotations

from typing import Callable, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from canonical_v2_research_engine import CanonicalV2DeepQuantEngine
from deep_quant_engine import Trade, QuarterResult, calculate_trade_pnl, validate_strategy_output


class CanonicalV2ExecutionEngine(CanonicalV2DeepQuantEngine):
    """Canonical V2 engine with pessimistic adverse-gap stop handling."""

    def run_strategy(
        self,
        signal_fn: Callable[[pd.DataFrame], Tuple[np.ndarray, np.ndarray, np.ndarray]],
        spread_pips: Optional[float] = None,
        slippage_pips: float = 0.0,
        commission_per_lot: Optional[float] = None,
        fixed_lot: float = 0.10,
        pessimistic_ambiguous_bars: bool = True,
        max_holding_bars: int = 120,
    ) -> Tuple[pd.DataFrame, pd.DataFrame, Dict]:
        df = self.df
        n = len(df)
        spr = spread_pips if spread_pips is not None else self.spec.default_spread_pips
        comm_rate = commission_per_lot if commission_per_lot is not None else self.spec.commission_per_lot_usd
        spread_price = spr * self.pip_size
        slippage_price = slippage_pips * self.pip_size

        signals, sl_dists, tp_dists = signal_fn(df)
        validate_strategy_output(df, signals, sl_dists, tp_dists)

        trades: List[Trade] = []
        active_trade = None
        trade_id = 1

        o = df["open"].values
        h = df["high"].values
        l = df["low"].values
        c = df["close"].values
        dt = df["datetime"]
        q_series = df["quarter"].values
        y_series = df["year"].values

        for i in range(n - 1):
            if active_trade is not None:
                d = active_trade["direction"]
                entry_p = active_trade["entry_price"]
                sl_p = active_trade["sl"]
                tp_p = active_trade["tp"]
                closed = False
                exit_price = 0.0
                exit_reason = ""
                dir_int = 1 if d == "BUY" else -1

                if d == "BUY":
                    gap_stop = o[i] < sl_p
                    hit_sl = l[i] <= sl_p
                    hit_tp = h[i] >= tp_p
                    if gap_stop:
                        exit_price = o[i] - slippage_price
                        exit_reason = "SL_GAP_OPEN_PESSIMISTIC"
                        closed = True
                    elif hit_sl and hit_tp:
                        if pessimistic_ambiguous_bars:
                            exit_price = sl_p - slippage_price
                            exit_reason = "SL_AMBIGUOUS_PESSIMISTIC"
                        else:
                            exit_price = tp_p - slippage_price
                            exit_reason = "TP_AMBIGUOUS_OPTIMISTIC"
                        closed = True
                    elif hit_sl:
                        exit_price = sl_p - slippage_price
                        exit_reason = "SL"
                        closed = True
                    elif hit_tp:
                        exit_price = tp_p - slippage_price
                        exit_reason = "TP"
                        closed = True
                    elif i - active_trade["entry_bar"] >= max_holding_bars:
                        exit_price = c[i] - slippage_price
                        exit_reason = "TIME_EXIT"
                        closed = True
                else:
                    ask_open = o[i] + spread_price
                    gap_stop = ask_open > sl_p
                    hit_sl = h[i] + spread_price >= sl_p
                    hit_tp = l[i] + spread_price <= tp_p
                    if gap_stop:
                        exit_price = ask_open + slippage_price
                        exit_reason = "SL_GAP_OPEN_PESSIMISTIC"
                        closed = True
                    elif hit_sl and hit_tp:
                        if pessimistic_ambiguous_bars:
                            exit_price = sl_p + slippage_price
                            exit_reason = "SL_AMBIGUOUS_PESSIMISTIC"
                        else:
                            exit_price = tp_p + slippage_price
                            exit_reason = "TP_AMBIGUOUS_OPTIMISTIC"
                        closed = True
                    elif hit_sl:
                        exit_price = sl_p + slippage_price
                        exit_reason = "SL"
                        closed = True
                    elif hit_tp:
                        exit_price = tp_p + slippage_price
                        exit_reason = "TP"
                        closed = True
                    elif i - active_trade["entry_bar"] >= max_holding_bars:
                        exit_price = c[i] + spread_price + slippage_price
                        exit_reason = "TIME_EXIT"
                        closed = True

                if closed:
                    pnl_dict = calculate_trade_pnl(
                        self.spec, dir_int, entry_p, exit_price,
                        lots=fixed_lot, commission_per_lot=comm_rate,
                    )
                    pnl_usd = pnl_dict["net_pnl_usd"]
                    pnl_pts = pnl_dict["pnl_pips"]
                    sl_risk_dict = calculate_trade_pnl(
                        self.spec, dir_int, entry_p, sl_p,
                        lots=fixed_lot, commission_per_lot=comm_rate,
                    )
                    sl_risk_usd = abs(sl_risk_dict["net_pnl_usd"])
                    pnl_r = pnl_usd / sl_risk_usd if sl_risk_usd > 0 else 0.0
                    trades.append(Trade(
                        id=trade_id,
                        entry_bar=active_trade["entry_bar"],
                        entry_time=active_trade["entry_time"],
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
                        quarter=active_trade["quarter"],
                        year=active_trade["year"],
                        holding_bars=i - active_trade["entry_bar"],
                    ))
                    trade_id += 1
                    active_trade = None

            # Signal at close i; execution at open i+1. The new position is
            # managed on the following loop iteration, which is the entry bar.
            if active_trade is None and i < n - 1:
                sig = signals[i]
                if sig != 0 and sl_dists[i] > 0 and tp_dists[i] > 0:
                    sl_dist = sl_dists[i]
                    tp_dist = tp_dists[i]
                    if sig == 1:
                        entry_price = o[i + 1] + spread_price + slippage_price
                        active_trade = {
                            "direction": "BUY",
                            "entry_bar": i + 1,
                            "entry_time": dt.iloc[i + 1],
                            "entry_price": entry_price,
                            "sl": entry_price - sl_dist,
                            "tp": entry_price + tp_dist,
                            "quarter": q_series[i + 1],
                            "year": y_series[i + 1],
                        }
                    elif sig == -1:
                        entry_price = o[i + 1] - slippage_price
                        active_trade = {
                            "direction": "SELL",
                            "entry_bar": i + 1,
                            "entry_time": dt.iloc[i + 1],
                            "entry_price": entry_price,
                            "sl": entry_price + sl_dist,
                            "tp": entry_price - tp_dist,
                            "quarter": q_series[i + 1],
                            "year": y_series[i + 1],
                        }

        trades_df = pd.DataFrame([t.__dict__ for t in trades])
        quarter_results = []
        for q in sorted(df["quarter"].unique()):
            y = int(str(q)[:4])
            q_trades = trades_df[trades_df["quarter"] == q] if len(trades_df) else pd.DataFrame()
            n_t = len(q_trades)
            if n_t == 0:
                qr = QuarterResult(
                    quarter=q, year=y, trades=0, wins=0, losses=0, win_rate_pct=0.0,
                    net_pnl_usd=0.0, gross_profit_usd=0.0, gross_loss_usd=0.0,
                    profit_factor=0.0, max_drawdown_pct=0.0, expectancy_usd=0.0,
                    expectancy_r=0.0, payoff_ratio=0.0, tail_loss_usd=0.0, verdict="NO_TRADE",
                )
            else:
                wins = q_trades[q_trades["pnl_usd"] > 0]
                losses = q_trades[q_trades["pnl_usd"] <= 0]
                gp = float(wins["pnl_usd"].sum()) if len(wins) else 0.0
                gl = abs(float(losses["pnl_usd"].sum())) if len(losses) else 0.0
                net = float(q_trades["pnl_usd"].sum())
                pf = gp / gl if gl > 0 else (999.0 if gp > 0 else 0.0)
                avg_win = float(wins["pnl_usd"].mean()) if len(wins) else 0.0
                avg_loss = abs(float(losses["pnl_usd"].mean())) if len(losses) else 0.0
                cum = q_trades["pnl_usd"].cumsum()
                peak = np.maximum.accumulate(cum)
                max_dd = float((peak - cum).max()) if len(cum) else 0.0
                verdict = "INCONCLUSIVE" if n_t < 3 else ("PASS" if pf >= 1.25 and net > 0 else ("FAIL" if pf < 0.90 or net < 0 else "INCONCLUSIVE"))
                qr = QuarterResult(
                    quarter=q, year=y, trades=n_t, wins=len(wins), losses=len(losses),
                    win_rate_pct=len(wins) / n_t * 100.0, net_pnl_usd=net,
                    gross_profit_usd=gp, gross_loss_usd=gl, profit_factor=pf,
                    max_drawdown_pct=max_dd, expectancy_usd=net / n_t,
                    expectancy_r=float(q_trades["pnl_r"].mean()),
                    payoff_ratio=avg_win / avg_loss if avg_loss > 0 else 0.0,
                    tail_loss_usd=abs(float(losses["pnl_usd"].min())) if len(losses) else 0.0,
                    verdict=verdict,
                )
            quarter_results.append(qr)

        quarters_df = pd.DataFrame([x.__dict__ for x in quarter_results])
        tot = len(trades_df)
        tot_pnl = float(trades_df["pnl_usd"].sum()) if tot else 0.0
        gp = float(trades_df.loc[trades_df["pnl_usd"] > 0, "pnl_usd"].sum()) if tot else 0.0
        gl = abs(float(trades_df.loc[trades_df["pnl_usd"] <= 0, "pnl_usd"].sum())) if tot else 0.0
        active_q = quarters_df[quarters_df["trades"] >= 3]
        n_active = len(active_q)
        n_active_pass = len(active_q[active_q["verdict"] == "PASS"])
        n_total_pass = len(quarters_df[quarters_df["verdict"] == "PASS"])

        summary = {
            "symbol": self.spec.symbol,
            "asset_class": self.spec.asset_class,
            "total_trades": tot,
            "total_pnl_usd": tot_pnl,
            "gross_profit_usd": gp,
            "gross_loss_usd": gl,
            "overall_pf": gp / gl if gl > 0 else (999.0 if gp > 0 else 0.0),
            "overall_wr_pct": float((trades_df["pnl_usd"] > 0).mean() * 100.0) if tot else 0.0,
            "avg_expectancy_usd": tot_pnl / tot if tot else 0.0,
            "avg_expectancy_r": float(trades_df["pnl_r"].mean()) if tot else 0.0,
            "total_quarters": len(quarters_df),
            "active_quarters": n_active,
            "active_quarter_pass_pct": (n_active_pass / n_active * 100.0) if n_active else 0.0,
            "full_calendar_pass_pct": (n_total_pass / len(quarters_df) * 100.0) if len(quarters_df) else 0.0,
            "execution_contract": "CANONICAL_V2_GAP_SAFE_V3_7_3",
        }
        return trades_df, quarters_df, summary


def assert_post_evaluation_buffer(
    df: pd.DataFrame,
    evaluation_end: pd.Timestamp,
    max_holding_bars: int,
    timeframe_minutes: int = 30,
) -> Dict[str, object]:
    end = pd.Timestamp(evaluation_end)
    if end.tzinfo is None:
        end = end.tz_localize("UTC")
    else:
        end = end.tz_convert("UTC")
    last = pd.Timestamp(df["datetime"].iloc[-1])
    if last.tzinfo is None:
        last = last.tz_localize("UTC")
    required_minutes = max_holding_bars * timeframe_minutes
    available_minutes = (last - end).total_seconds() / 60.0
    return {
        "evaluation_end": end.isoformat(),
        "dataset_last_datetime": last.isoformat(),
        "required_buffer_minutes": required_minutes,
        "available_buffer_minutes": available_minutes,
        "pass": available_minutes >= required_minutes,
    }
