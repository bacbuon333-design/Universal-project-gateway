"""
V3.4 BATCH-1 — H-215 TO H-217 DIRECTIONAL FOLLOW-UP
====================================================

IMPORTANT:
- This file implements the already-committed V3_4_BATCH1_PRECOMMIT.md.
- It must not be used to expand the parameter grid after results are seen.
- The underlying H-209/H-213/H-214 signal generators are imported from the
  audited V3.3.1 runner and are not reimplemented here.
- The only structural transformation is deterministic Long-only masking.

Research status:
Directional asymmetry was observed historically in V3.3/V3.3.1. Therefore
this is an explicitly post-hoc exploratory follow-up, not validation.
"""

from __future__ import annotations

import json
import os
from typing import Callable, Dict, List, Tuple

import numpy as np
import pandas as pd

from deep_quant_engine import DeepQuantEngine
from experiment_v3_3_1_batch1_repaired import (
    gini,
    make_h209_signals,
    make_h213_signals,
    make_h214_signals,
)

EVAL_START = "2018Q2"
EVAL_END = "2026Q2"
EXPECTED_QUARTERS = 33
EXPECTED_ROLLING4 = 30
SPREAD_PIPS = 25.0
SLIPPAGE_PIPS = 0.0
COMMISSION_PER_LOT = 7.0
FIXED_LOT = 0.10


# ---------------------------------------------------------------------------
# 1. DIRECTIONAL TRANSFORMATION
# ---------------------------------------------------------------------------
def long_only(base_signal_fn: Callable) -> Callable:
    """Return a strategy wrapper that preserves only the base function's Long signals.

    Invariants:
    - Every base +1 signal remains +1.
    - Every base -1/0 signal becomes 0.
    - SL/TP distances on preserved Long signals are unchanged byte-for-byte
      at the NumPy value level.
    - SL/TP outputs are zeroed wherever the resulting signal is inactive.
    """

    def wrapped(df: pd.DataFrame):
        base_sig, base_sl, base_tp = base_signal_fn(df)

        base_sig = np.asarray(base_sig).copy()
        base_sl = np.asarray(base_sl, dtype=float).copy()
        base_tp = np.asarray(base_tp, dtype=float).copy()

        sig = np.zeros_like(base_sig, dtype=int)
        sl = np.zeros_like(base_sl, dtype=float)
        tp = np.zeros_like(base_tp, dtype=float)

        keep = base_sig == 1
        sig[keep] = 1
        sl[keep] = base_sl[keep]
        tp[keep] = base_tp[keep]

        # Contract / anti-drift assertions.
        assert np.array_equal(sig == 1, base_sig == 1), "Long signal locations drifted"
        assert not np.any(sig == -1), "Long-only wrapper emitted a Short signal"
        assert np.array_equal(sl[keep], base_sl[keep]), "Long SL distances drifted"
        assert np.array_equal(tp[keep], base_tp[keep]), "Long TP distances drifted"
        assert np.all(sl[~keep] == 0.0), "Inactive SL outputs must be zero"
        assert np.all(tp[~keep] == 0.0), "Inactive TP outputs must be zero"

        return sig, sl, tp

    return wrapped


# ---------------------------------------------------------------------------
# 2. FROZEN CONFIGURATION MATRIX — EXACTLY 12 CONFIGURATIONS
# ---------------------------------------------------------------------------
def build_configs() -> List[Tuple[str, str, str, str, Callable]]:
    configs = [
        # H-215: Long-only H-213 / MRLM
        (
            "H-215-C1", "MRLM-L", "H-213-C1",
            "Long-only MRLM: Channel50 0.75/0.25 SL1.5 TP3.0",
            long_only(lambda df: make_h213_signals(
                df, channel_len=50, th_upper=0.75, th_lower=0.25,
                sl_mult=1.5, tp_rr=2.0,
            )),
        ),
        (
            "H-215-C2", "MRLM-L", "H-213-C2",
            "Long-only MRLM: Channel50 0.75/0.25 SL1.5 TP3.75",
            long_only(lambda df: make_h213_signals(
                df, channel_len=50, th_upper=0.75, th_lower=0.25,
                sl_mult=1.5, tp_rr=2.5,
            )),
        ),
        (
            "H-215-C3", "MRLM-L", "H-213-C3",
            "Long-only MRLM: Channel100 0.80/0.20 SL1.5 TP3.0",
            long_only(lambda df: make_h213_signals(
                df, channel_len=100, th_upper=0.80, th_lower=0.20,
                sl_mult=1.5, tp_rr=2.0,
            )),
        ),
        (
            "H-215-C4", "MRLM-L", "H-213-C4",
            "Long-only MRLM: Channel100 0.80/0.20 SL1.5 TP3.75",
            long_only(lambda df: make_h213_signals(
                df, channel_len=100, th_upper=0.80, th_lower=0.20,
                sl_mult=1.5, tp_rr=2.5,
            )),
        ),

        # H-216: Long-only H-214 / VRA
        (
            "H-216-C1", "VRA-L", "H-214-C1",
            "Long-only VRA: ATR7/28>1.20 3b breakout EMA50 SL1.5 TP3.0",
            long_only(lambda df: make_h214_signals(
                df, ratio_th=1.20, sl_mult=1.5, tp_rr=2.0,
            )),
        ),
        (
            "H-216-C2", "VRA-L", "H-214-C2",
            "Long-only VRA: ATR7/28>1.20 3b breakout EMA50 SL1.5 TP3.75",
            long_only(lambda df: make_h214_signals(
                df, ratio_th=1.20, sl_mult=1.5, tp_rr=2.5,
            )),
        ),
        (
            "H-216-C3", "VRA-L", "H-214-C3",
            "Long-only VRA: ATR7/28>1.30 3b breakout EMA50 SL1.5 TP3.0",
            long_only(lambda df: make_h214_signals(
                df, ratio_th=1.30, sl_mult=1.5, tp_rr=2.0,
            )),
        ),
        (
            "H-216-C4", "VRA-L", "H-214-C4",
            "Long-only VRA: ATR7/28>1.30 3b breakout EMA50 SL1.5 TP3.75",
            long_only(lambda df: make_h214_signals(
                df, ratio_th=1.30, sl_mult=1.5, tp_rr=2.5,
            )),
        ),

        # H-217: Long-only H-209 / MHTP directional control family
        (
            "H-217-C1", "MHTP-L", "H-209-C1",
            "Long-only MHTP control: EMA50/100 EMA20 pullback SL1.5 TP3.0",
            long_only(lambda df: make_h209_signals(
                df, sl_mult=1.5, tp_rr=2.0,
            )),
        ),
        (
            "H-217-C2", "MHTP-L", "H-209-C2",
            "Long-only MHTP control: EMA50/100 EMA20 pullback SL1.5 TP3.75",
            long_only(lambda df: make_h209_signals(
                df, sl_mult=1.5, tp_rr=2.5,
            )),
        ),
        (
            "H-217-C3", "MHTP-L", "H-209-C3",
            "Long-only MHTP control: EMA50/100 EMA20 pullback SL2.0 TP4.0",
            long_only(lambda df: make_h209_signals(
                df, sl_mult=2.0, tp_rr=2.0,
            )),
        ),
        (
            "H-217-C4", "MHTP-L", "H-209-C4",
            "Long-only MHTP control: EMA50/100 EMA20 pullback SL2.0 TP5.0",
            long_only(lambda df: make_h209_signals(
                df, sl_mult=2.0, tp_rr=2.5,
            )),
        ),
    ]

    ids = [x[0] for x in configs]
    assert len(configs) == 12, f"Frozen research budget is 12 configs, got {len(configs)}"
    assert len(set(ids)) == 12, "Duplicate config IDs detected"
    assert ids == [
        "H-215-C1", "H-215-C2", "H-215-C3", "H-215-C4",
        "H-216-C1", "H-216-C2", "H-216-C3", "H-216-C4",
        "H-217-C1", "H-217-C2", "H-217-C3", "H-217-C4",
    ], "Frozen config matrix changed"
    return configs


# ---------------------------------------------------------------------------
# 3. EVALUATION HELPERS
# ---------------------------------------------------------------------------
def all_complete_quarters() -> List[str]:
    quarters = []
    for year in range(2018, 2027):
        for q in range(1, 5):
            label = f"{year}Q{q}"
            if EVAL_START <= label <= EVAL_END:
                quarters.append(label)
    assert len(quarters) == EXPECTED_QUARTERS
    return quarters


def safe_pf(pnls: pd.Series) -> float:
    if len(pnls) == 0:
        return 0.0
    gp = float(pnls[pnls > 0].sum())
    gl = float(abs(pnls[pnls < 0].sum()))
    return gp / gl if gl > 0 else (999.0 if gp > 0 else 0.0)


def positive_pool_shares(values: np.ndarray, ks=(1, 3, 5, 10)) -> Tuple[Dict[int, float], bool]:
    positive = np.asarray(values, dtype=float)
    positive = positive[positive > 0]
    denom = float(positive.sum())
    if denom <= 0 or len(positive) == 0:
        return {k: np.nan for k in ks}, False
    positive = np.sort(positive)[::-1]
    return {
        k: float(positive[: min(k, len(positive))].sum() / denom * 100.0)
        for k in ks
    }, True


def build_quarter_table(eval_trades: pd.DataFrame) -> pd.DataFrame:
    records = []
    for quarter in all_complete_quarters():
        sub = eval_trades[eval_trades["entry_quarter"] == quarter]
        pnls = sub["pnl_usd"] if len(sub) else pd.Series(dtype=float)
        gp = float(pnls[pnls > 0].sum()) if len(sub) else 0.0
        gl = float(abs(pnls[pnls < 0].sum())) if len(sub) else 0.0
        records.append({
            "quarter": quarter,
            "year": int(quarter[:4]),
            "trades": int(len(sub)),
            "wins": int((pnls > 0).sum()) if len(sub) else 0,
            "losses": int((pnls < 0).sum()) if len(sub) else 0,
            "net_pnl_usd": float(pnls.sum()) if len(sub) else 0.0,
            "gross_profit_usd": gp,
            "gross_loss_usd": gl,
            "pf": gp / gl if gl > 0 else (999.0 if gp > 0 else 0.0),
            "expectancy_usd": float(pnls.mean()) if len(sub) else 0.0,
        })
    qdf = pd.DataFrame(records)
    assert len(qdf) == EXPECTED_QUARTERS
    assert int(qdf["trades"].sum()) == len(eval_trades)
    return qdf


def build_rolling4(qdf: pd.DataFrame) -> pd.DataFrame:
    records = []
    for i in range(len(qdf) - 3):
        sub = qdf.iloc[i : i + 4]
        gp = float(sub["gross_profit_usd"].sum())
        gl = float(sub["gross_loss_usd"].sum())
        pf = gp / gl if gl > 0 else (999.0 if gp > 0 else 0.0)
        pnl = float(sub["net_pnl_usd"].sum())
        records.append({
            "window": f"{sub.iloc[0]['quarter']}->{sub.iloc[-1]['quarter']}",
            "net_pnl_usd": pnl,
            "gross_profit_usd": gp,
            "gross_loss_usd": gl,
            "pf": pf,
            "is_positive": bool(pnl > 0),
            "is_pf_ge_120": bool(pf >= 1.20),
        })
    rdf = pd.DataFrame(records)
    assert len(rdf) == EXPECTED_ROLLING4, f"Expected 30 rolling-4Q windows, got {len(rdf)}"
    return rdf


def build_year_table(eval_trades: pd.DataFrame) -> pd.DataFrame:
    records = []
    for year in range(2018, 2027):
        sub = eval_trades[eval_trades["entry_year"] == year]
        pnls = sub["pnl_usd"] if len(sub) else pd.Series(dtype=float)
        records.append({
            "year": year,
            "trades": int(len(sub)),
            "net_pnl_usd": float(pnls.sum()) if len(sub) else 0.0,
            "pf": safe_pf(pnls),
            "expectancy_usd": float(pnls.mean()) if len(sub) else 0.0,
            "is_complete_calendar_year": bool(2019 <= year <= 2025),
        })
    return pd.DataFrame(records)


def compute_summary(
    config_id: str,
    family: str,
    source_config: str,
    description: str,
    eval_trades: pd.DataFrame,
    qdf: pd.DataFrame,
    r4df: pd.DataFrame,
    ydf: pd.DataFrame,
    symmetric_row: pd.Series,
) -> Dict:
    total = len(eval_trades)
    assert total > 0, f"{config_id}: zero realized evaluation trades"
    assert set(eval_trades["direction"].unique()) <= {"BUY"}, f"{config_id}: non-BUY trade survived Long-only mask"

    pnls = eval_trades["pnl_usd"]
    gp = float(pnls[pnls > 0].sum())
    gl = float(abs(pnls[pnls < 0].sum()))
    net_pnl = float(pnls.sum())
    pf = gp / gl if gl > 0 else (999.0 if gp > 0 else 0.0)
    expectancy = float(pnls.mean())
    win_rate = float((pnls > 0).mean() * 100.0)

    trade_counts = qdf["trades"].to_numpy(dtype=float)
    min_q = int(trade_counts.min())
    median_q = float(np.median(trade_counts))
    max_q = int(trade_counts.max())
    max_share = float(max_q / total * 100.0)
    max_median = float(max_q / median_q) if median_q > 0 else 999.0
    trade_gini = float(gini(trade_counts))
    mean_q = float(trade_counts.mean())
    std_q = float(trade_counts.std(ddof=0))
    cv_q = float(std_q / mean_q) if mean_q > 0 else np.nan

    q_shares, profit_pool_applicable = positive_pool_shares(qdf["net_pnl_usd"].to_numpy())
    trade_shares, positive_trade_pool_applicable = positive_pool_shares(pnls.to_numpy(), ks=(1, 3, 5))

    year_shares, positive_year_pool_applicable = positive_pool_shares(ydf["net_pnl_usd"].to_numpy(), ks=(1, 3))
    full_years = ydf[ydf["is_complete_calendar_year"]]
    profitable_full_years = int((full_years["net_pnl_usd"] > 0).sum())

    r4_pos_pct = float(r4df["is_positive"].mean() * 100.0)
    r4_pf120_pct = float(r4df["is_pf_ge_120"].mean() * 100.0)

    gate_A1 = bool(min_q >= 5)
    gate_A2 = bool(max_share <= 5.0)
    gate_A3 = bool(max_median <= 3.0)
    gate_A4 = bool(trade_gini < 0.30)
    gate_B1 = bool(q_shares[3] <= 40.0) if profit_pool_applicable else False
    gate_B2 = bool(q_shares[5] <= 60.0) if profit_pool_applicable else False
    gate_D1 = bool(r4_pos_pct >= 70.0)
    gate_D2 = bool(r4_pf120_pct >= 65.0)
    gate_E1 = bool(pf >= 1.25)
    gate_E2 = bool(expectancy > 0.0)

    all_pass = bool(
        gate_A1 and gate_A2 and gate_A3 and gate_A4 and
        gate_B1 and gate_B2 and gate_D1 and gate_D2 and
        gate_E1 and gate_E2
    )

    ordered_gates = [
        ("A1", gate_A1, f"Min Trades/Q = {min_q} < 5"),
        ("A2", gate_A2, f"Max Q Share = {max_share:.2f}% > 5.0%"),
        ("A3", gate_A3, f"Max/Median = {max_median:.2f} > 3.0"),
        ("A4", gate_A4, f"Gini = {trade_gini:.3f} >= 0.30"),
        ("E1", gate_E1, f"PF = {pf:.3f} < 1.25"),
        ("E2", gate_E2, f"Expectancy = ${expectancy:+.2f} <= $0"),
        ("D1", gate_D1, f"R4 Positive = {r4_pos_pct:.1f}% < 70.0%"),
        ("D2", gate_D2, f"R4 PF>=1.20 = {r4_pf120_pct:.1f}% < 65.0%"),
        ("B1", gate_B1, f"Top3 positive-quarter share = {q_shares[3]:.1f}% > 40.0%" if profit_pool_applicable else "No positive quarter profit pool"),
        ("B2", gate_B2, f"Top5 positive-quarter share = {q_shares[5]:.1f}% > 60.0%" if profit_pool_applicable else "No positive quarter profit pool"),
    ]
    primary_failure = "NONE — ALL HARD GATES PASSED"
    for gate_name, passed, reason in ordered_gates:
        if not passed:
            primary_failure = f"Gate {gate_name}: {reason}"
            break

    status = (
        "HISTORICAL DIRECTIONAL SURVIVOR — REQUIRES STABILITY BATCH"
        if all_pass
        else "REJECTED"
    )

    return {
        "config_id": config_id,
        "family": family,
        "source_symmetric_config": source_config,
        "description": description,
        "evaluation_start": EVAL_START,
        "evaluation_end": EVAL_END,
        "baseline_spread_pips": SPREAD_PIPS,
        "baseline_slippage_pips": SLIPPAGE_PIPS,
        "commission_per_lot": COMMISSION_PER_LOT,
        "fixed_lot": FIXED_LOT,
        "total_trades": int(total),
        "min_trades_q": min_q,
        "p10_trades_q": float(np.percentile(trade_counts, 10)),
        "p25_trades_q": float(np.percentile(trade_counts, 25)),
        "median_trades_q": median_q,
        "mean_trades_q": mean_q,
        "p75_trades_q": float(np.percentile(trade_counts, 75)),
        "p90_trades_q": float(np.percentile(trade_counts, 90)),
        "max_trades_q": max_q,
        "max_q_share_pct": max_share,
        "max_median": max_median,
        "trade_count_cv": cv_q,
        "trade_count_gini": trade_gini,
        "net_pnl_usd": net_pnl,
        "gross_profit_usd": gp,
        "gross_loss_usd": gl,
        "pf": pf,
        "expectancy_usd": expectancy,
        "win_rate_pct": win_rate,
        "top1_positive_q_share_pct": q_shares[1],
        "top3_positive_q_share_pct": q_shares[3],
        "top5_positive_q_share_pct": q_shares[5],
        "top10_positive_q_share_pct": q_shares[10],
        "positive_quarter_profit_pool_applicable": profit_pool_applicable,
        "rolling4_positive_pct": r4_pos_pct,
        "rolling4_pf120_pct": r4_pf120_pct,
        "full_calendar_years": int(len(full_years)),
        "profitable_full_calendar_years": profitable_full_years,
        "profitable_full_calendar_year_pct": float(profitable_full_years / len(full_years) * 100.0),
        "best_positive_year_share_pct": year_shares[1],
        "top3_positive_year_share_pct": year_shares[3],
        "positive_year_profit_pool_applicable": positive_year_pool_applicable,
        "best_positive_trade_share_pct": trade_shares[1],
        "top3_positive_trade_share_pct": trade_shares[3],
        "top5_positive_trade_share_pct": trade_shares[5],
        "positive_trade_profit_pool_applicable": positive_trade_pool_applicable,
        "gate_A1": gate_A1,
        "gate_A2": gate_A2,
        "gate_A3": gate_A3,
        "gate_A4": gate_A4,
        "gate_B1": gate_B1,
        "gate_B2": gate_B2,
        "gate_D1": gate_D1,
        "gate_D2": gate_D2,
        "gate_E1": gate_E1,
        "gate_E2": gate_E2,
        "all_gates_pass": all_pass,
        "primary_failure_reason": primary_failure,
        "final_status": status,
        # Historical symmetric comparison is diagnostic context only.
        "symmetric_v3_3_1_total_trades": int(symmetric_row["total_trades"]),
        "symmetric_v3_3_1_pf": float(symmetric_row["pf"]),
        "symmetric_v3_3_1_expectancy": float(symmetric_row["expectancy"]),
        "symmetric_v3_3_1_r4_positive_pct": float(symmetric_row["rolling4_positive_pct"]),
        "symmetric_v3_3_1_r4_pf120_pct": float(symmetric_row["rolling4_pf120_pct"]),
    }


# ---------------------------------------------------------------------------
# 4. MAIN EXECUTION
# ---------------------------------------------------------------------------
def run_v3_4_batch1() -> pd.DataFrame:
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    out_dir = os.path.join(root, "AlphaLab_Antigravity", "reports", "v3_4")
    os.makedirs(out_dir, exist_ok=True)

    baseline_path = os.path.join(
        root, "AlphaLab_Antigravity", "reports", "v3_3_1", "batch1_repaired_summary.csv"
    )
    if not os.path.exists(baseline_path):
        raise FileNotFoundError(
            "Authoritative V3.3.1 repaired summary is required for diagnostic baseline comparison: "
            + baseline_path
        )
    baseline = pd.read_csv(baseline_path)

    configs = build_configs()
    engine = DeepQuantEngine("GOLD_M30.csv")
    summaries = []

    print("=" * 100)
    print("V3.4 BATCH-1 — H-215 TO H-217 LONG-ONLY DIRECTIONAL FOLLOW-UP")
    print("Frozen configurations: 12 | Evaluation: 2018Q2..2026Q2")
    print("=" * 100)

    for config_id, family, source_config, description, signal_fn in configs:
        print(f"Running {config_id} ({source_config}) ...")

        tdf_raw, _, _ = engine.run_strategy(
            signal_fn,
            spread_pips=SPREAD_PIPS,
            slippage_pips=SLIPPAGE_PIPS,
            commission_per_lot=COMMISSION_PER_LOT,
            fixed_lot=FIXED_LOT,
            pessimistic_ambiguous_bars=True,
        )

        if len(tdf_raw) == 0:
            raise RuntimeError(f"{config_id}: engine produced zero raw trades; stop for audit")

        tdf_raw = tdf_raw.copy()
        tdf_raw["entry_dt"] = pd.to_datetime(tdf_raw["entry_time"])
        tdf_raw["entry_quarter"] = tdf_raw["entry_dt"].dt.to_period("Q").astype(str)
        tdf_raw["entry_year"] = tdf_raw["entry_dt"].dt.year.astype(int)

        eval_trades = tdf_raw[
            (tdf_raw["entry_quarter"] >= EVAL_START)
            & (tdf_raw["entry_quarter"] <= EVAL_END)
        ].copy().reset_index(drop=True)

        # Boundary and directional invariants.
        assert len(eval_trades) > 0, f"{config_id}: no evaluation trades"
        assert eval_trades["entry_quarter"].min() >= EVAL_START
        assert eval_trades["entry_quarter"].max() <= EVAL_END
        assert not (eval_trades["entry_quarter"] == "2018Q1").any()
        assert not (eval_trades["entry_quarter"] == "2026Q3").any()
        assert set(eval_trades["direction"].unique()) == {"BUY"}, (
            f"{config_id}: expected BUY-only realized trades, got "
            f"{eval_trades['direction'].unique().tolist()}"
        )

        qdf = build_quarter_table(eval_trades)
        r4df = build_rolling4(qdf)
        ydf = build_year_table(eval_trades)

        symmetric_match = baseline[baseline["config_id"] == source_config]
        if len(symmetric_match) != 1:
            raise RuntimeError(
                f"{config_id}: expected exactly one V3.3.1 baseline row for {source_config}, got {len(symmetric_match)}"
            )
        symmetric_row = symmetric_match.iloc[0]

        summary = compute_summary(
            config_id=config_id,
            family=family,
            source_config=source_config,
            description=description,
            eval_trades=eval_trades,
            qdf=qdf,
            r4df=r4df,
            ydf=ydf,
            symmetric_row=symmetric_row,
        )
        summaries.append(summary)

        tag = config_id.lower().replace("-", "_")
        eval_trades.to_csv(os.path.join(out_dir, f"{tag}_evaluation_trades.csv"), index=False)
        qdf.to_csv(os.path.join(out_dir, f"{tag}_quarters.csv"), index=False)
        r4df.to_csv(os.path.join(out_dir, f"{tag}_rolling4q.csv"), index=False)
        ydf.to_csv(os.path.join(out_dir, f"{tag}_years.csv"), index=False)

        diagnostics = {
            "config_id": config_id,
            "source_symmetric_config": source_config,
            "post_hoc_directional_followup": True,
            "interpretation_warning": (
                "Long-only direction was motivated by historical V3.3/V3.3.1 observations. "
                "Any survivor is exploratory and requires a separate stability precommit and true future OOS."
            ),
            "summary": summary,
        }
        with open(os.path.join(out_dir, f"{tag}_diagnostics.json"), "w", encoding="utf-8") as f:
            json.dump(diagnostics, f, indent=2, allow_nan=True)

        print(
            f"  trades={summary['total_trades']} min/Q={summary['min_trades_q']} "
            f"PF={summary['pf']:.3f} exp=${summary['expectancy_usd']:+.2f} "
            f"R4+={summary['rolling4_positive_pct']:.1f}% "
            f"R4PF={summary['rolling4_pf120_pct']:.1f}% "
            f"status={summary['final_status']}"
        )

    summary_df = pd.DataFrame(summaries)
    assert len(summary_df) == 12
    assert summary_df["config_id"].is_unique

    summary_path = os.path.join(out_dir, "batch1_directional_summary.csv")
    summary_df.to_csv(summary_path, index=False)

    # Compact machine-readable batch metadata. No guessed Git SHA is embedded.
    batch_meta = {
        "batch": "V3.4 Batch 1",
        "hypotheses": ["H-215", "H-216", "H-217"],
        "configuration_count": 12,
        "evaluation_start": EVAL_START,
        "evaluation_end": EVAL_END,
        "complete_quarters": EXPECTED_QUARTERS,
        "rolling4_windows": EXPECTED_ROLLING4,
        "spread_pips": SPREAD_PIPS,
        "slippage_pips": SLIPPAGE_PIPS,
        "commission_per_lot": COMMISSION_PER_LOT,
        "fixed_lot": FIXED_LOT,
        "post_hoc_directional_followup": True,
        "survivor_count": int(summary_df["all_gates_pass"].sum()),
    }
    with open(os.path.join(out_dir, "batch1_metadata.json"), "w", encoding="utf-8") as f:
        json.dump(batch_meta, f, indent=2)

    print("-" * 100)
    print(f"Saved authoritative summary: {summary_path}")
    print(f"Survivors: {int(summary_df['all_gates_pass'].sum())} / 12")
    print("STOP after Batch 1. Do not expand H-218+ or tune configs before independent audit.")
    return summary_df


if __name__ == "__main__":
    run_v3_4_batch1()
