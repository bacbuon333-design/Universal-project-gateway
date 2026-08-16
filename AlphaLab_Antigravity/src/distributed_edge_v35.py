from __future__ import annotations

from typing import Dict, Iterable, Tuple
import numpy as np
import pandas as pd

EVAL_START = "2018Q2"
EVAL_END = "2026Q2"
EXPECTED_QUARTERS = 33
EXPECTED_R4 = 30
EXPECTED_R8 = 26
FULL_YEARS = list(range(2019, 2026))


def gini(values: Iterable[float]) -> float:
    x = np.asarray(list(values), dtype=float)
    if len(x) == 0 or float(np.mean(x)) == 0.0:
        return 0.0
    mad = np.abs(np.subtract.outer(x, x)).mean()
    return float(0.5 * mad / np.mean(x))


def safe_pf(pnls: pd.Series) -> float:
    if len(pnls) == 0:
        return 0.0
    gp = float(pnls[pnls > 0].sum())
    gl = float(abs(pnls[pnls < 0].sum()))
    return gp / gl if gl > 0 else (999.0 if gp > 0 else 0.0)


def positive_pool_shares(values: Iterable[float], ks=(1, 3, 5, 10)) -> Tuple[Dict[int, float], bool]:
    x = np.asarray(list(values), dtype=float)
    x = x[x > 0]
    denom = float(x.sum())
    if len(x) == 0 or denom <= 0:
        return {k: np.nan for k in ks}, False
    x = np.sort(x)[::-1]
    return {k: float(x[: min(k, len(x))].sum() / denom * 100.0) for k in ks}, True


def complete_quarters():
    out = []
    for year in range(2018, 2027):
        for q in range(1, 5):
            label = f"{year}Q{q}"
            if EVAL_START <= label <= EVAL_END:
                out.append(label)
    assert len(out) == EXPECTED_QUARTERS
    return out


def prepare_evaluation_trades(trades: pd.DataFrame) -> pd.DataFrame:
    t = trades.copy()
    t["entry_dt"] = pd.to_datetime(t["entry_time"])
    t["entry_quarter"] = t["entry_dt"].dt.to_period("Q").astype(str)
    t["entry_year"] = t["entry_dt"].dt.year.astype(int)
    t = t[(t["entry_quarter"] >= EVAL_START) & (t["entry_quarter"] <= EVAL_END)].copy().reset_index(drop=True)
    if len(t):
        assert t["entry_quarter"].min() >= EVAL_START
        assert t["entry_quarter"].max() <= EVAL_END
    return t


def build_quarter_table(eval_trades: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for q in complete_quarters():
        sub = eval_trades[eval_trades["entry_quarter"] == q]
        pnls = sub["pnl_usd"] if len(sub) else pd.Series(dtype=float)
        gp = float(pnls[pnls > 0].sum()) if len(sub) else 0.0
        gl = float(abs(pnls[pnls < 0].sum())) if len(sub) else 0.0
        rows.append({
            "quarter": q,
            "year": int(q[:4]),
            "trades": int(len(sub)),
            "net_pnl_usd": float(pnls.sum()) if len(sub) else 0.0,
            "gross_profit_usd": gp,
            "gross_loss_usd": gl,
            "pf": gp / gl if gl > 0 else (999.0 if gp > 0 else 0.0),
            "expectancy_usd": float(pnls.mean()) if len(sub) else 0.0,
        })
    qdf = pd.DataFrame(rows)
    assert len(qdf) == EXPECTED_QUARTERS
    assert int(qdf["trades"].sum()) == len(eval_trades)
    return qdf


def build_rolling(qdf: pd.DataFrame, width: int) -> pd.DataFrame:
    rows = []
    for i in range(len(qdf) - width + 1):
        sub = qdf.iloc[i : i + width]
        gp = float(sub["gross_profit_usd"].sum())
        gl = float(sub["gross_loss_usd"].sum())
        pnl = float(sub["net_pnl_usd"].sum())
        pf = gp / gl if gl > 0 else (999.0 if gp > 0 else 0.0)
        rows.append({
            "window": f"{sub.iloc[0]['quarter']}->{sub.iloc[-1]['quarter']}",
            "width_quarters": width,
            "net_pnl_usd": pnl,
            "pf": pf,
            "is_positive": bool(pnl > 0),
            "is_pf_ge_120": bool(pf >= 1.20),
        })
    out = pd.DataFrame(rows)
    expected = EXPECTED_R4 if width == 4 else EXPECTED_R8 if width == 8 else len(qdf) - width + 1
    assert len(out) == expected
    return out


def build_year_table(eval_trades: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for year in range(2018, 2027):
        sub = eval_trades[eval_trades["entry_year"] == year]
        pnls = sub["pnl_usd"] if len(sub) else pd.Series(dtype=float)
        rows.append({
            "year": year,
            "trades": int(len(sub)),
            "net_pnl_usd": float(pnls.sum()) if len(sub) else 0.0,
            "pf": safe_pf(pnls),
            "expectancy_usd": float(pnls.mean()) if len(sub) else 0.0,
            "is_complete_calendar_year": bool(year in FULL_YEARS),
        })
    return pd.DataFrame(rows)


def evaluate_distribution(config_id: str, raw_trades: pd.DataFrame) -> Tuple[Dict, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    eval_trades = prepare_evaluation_trades(raw_trades)
    if len(eval_trades) == 0:
        raise RuntimeError(f"{config_id}: no evaluation trades")

    qdf = build_quarter_table(eval_trades)
    r4 = build_rolling(qdf, 4)
    r8 = build_rolling(qdf, 8)
    ydf = build_year_table(eval_trades)

    pnls = eval_trades["pnl_usd"]
    gp = float(pnls[pnls > 0].sum())
    gl = float(abs(pnls[pnls < 0].sum()))
    net = float(pnls.sum())
    pf = gp / gl if gl > 0 else (999.0 if gp > 0 else 0.0)
    expectancy = float(pnls.mean())

    counts = qdf["trades"].to_numpy(dtype=float)
    min_q = int(counts.min())
    median_q = float(np.median(counts))
    max_q = int(counts.max())
    max_share = float(max_q / len(eval_trades) * 100.0)
    max_median = float(max_q / median_q) if median_q > 0 else 999.0
    trade_gini = gini(counts)

    qshares, qpool = positive_pool_shares(qdf["net_pnl_usd"], ks=(1, 3, 5, 10))

    r4_pos = float(r4["is_positive"].mean() * 100.0)
    r4_pf = float(r4["is_pf_ge_120"].mean() * 100.0)
    r8_pos = float(r8["is_positive"].mean() * 100.0)
    r8_pf = float(r8["is_pf_ge_120"].mean() * 100.0)

    full = ydf[ydf["is_complete_calendar_year"]].copy()
    assert full["year"].tolist() == FULL_YEARS
    min_full_year_trades = int(full["trades"].min())
    profitable_year_pct = float((full["net_pnl_usd"] > 0).mean() * 100.0)

    gates = {
        "gate_A1": bool(min_q >= 5),
        "gate_A2": bool(max_share <= 5.0),
        "gate_A3": bool(max_median <= 3.0),
        "gate_A4": bool(trade_gini < 0.30),
        "gate_B1": bool(qshares[3] <= 40.0) if qpool else False,
        "gate_B2": bool(qshares[5] <= 60.0) if qpool else False,
        "gate_D4_1": bool(r4_pos >= 70.0),
        "gate_D4_2": bool(r4_pf >= 65.0),
        "gate_D8_1": bool(r8_pos >= 75.0),
        "gate_D8_2": bool(r8_pf >= 70.0),
        "gate_Y1": bool(min_full_year_trades >= 20),
        "gate_Y2": bool(profitable_year_pct >= 70.0),
        "gate_E1": bool(pf >= 1.25),
        "gate_E2": bool(expectancy > 0.0),
    }
    all_pass = bool(all(gates.values()))

    ordered = [
        ("A1", gates["gate_A1"], f"min trades/Q {min_q} < 5"),
        ("A2", gates["gate_A2"], f"max quarter share {max_share:.2f}% > 5%"),
        ("A3", gates["gate_A3"], f"max/median {max_median:.2f} > 3"),
        ("A4", gates["gate_A4"], f"Gini {trade_gini:.3f} >= 0.30"),
        ("E1", gates["gate_E1"], f"PF {pf:.3f} < 1.25"),
        ("E2", gates["gate_E2"], f"expectancy {expectancy:+.2f} <= 0"),
        ("D4_1", gates["gate_D4_1"], f"R4 positive {r4_pos:.1f}% < 70%"),
        ("D4_2", gates["gate_D4_2"], f"R4 PF>=1.20 {r4_pf:.1f}% < 65%"),
        ("D8_1", gates["gate_D8_1"], f"R8 positive {r8_pos:.1f}% < 75%"),
        ("D8_2", gates["gate_D8_2"], f"R8 PF>=1.20 {r8_pf:.1f}% < 70%"),
        ("Y1", gates["gate_Y1"], f"min full-year trades {min_full_year_trades} < 20"),
        ("Y2", gates["gate_Y2"], f"profitable full years {profitable_year_pct:.1f}% < 70%"),
        ("B1", gates["gate_B1"], f"Top3 +Q share {qshares[3]:.1f}% > 40%" if qpool else "no positive quarter pool"),
        ("B2", gates["gate_B2"], f"Top5 +Q share {qshares[5]:.1f}% > 60%" if qpool else "no positive quarter pool"),
    ]
    primary_failure = "NONE — ALL GATES PASSED"
    for name, passed, reason in ordered:
        if not passed:
            primary_failure = f"Gate {name}: {reason}"
            break

    summary = {
        "config_id": config_id,
        "evaluation_start": EVAL_START,
        "evaluation_end": EVAL_END,
        "total_trades": int(len(eval_trades)),
        "min_trades_q": min_q,
        "median_trades_q": median_q,
        "max_trades_q": max_q,
        "max_q_share_pct": max_share,
        "max_median": max_median,
        "trade_count_gini": trade_gini,
        "net_pnl_usd": net,
        "gross_profit_usd": gp,
        "gross_loss_usd": gl,
        "pf": pf,
        "expectancy_usd": expectancy,
        "win_rate_pct": float((pnls > 0).mean() * 100.0),
        "top1_positive_q_share_pct": qshares[1],
        "top3_positive_q_share_pct": qshares[3],
        "top5_positive_q_share_pct": qshares[5],
        "top10_positive_q_share_pct": qshares[10],
        "positive_quarter_pool_applicable": qpool,
        "rolling4_positive_pct": r4_pos,
        "rolling4_pf120_pct": r4_pf,
        "rolling8_positive_pct": r8_pos,
        "rolling8_pf120_pct": r8_pf,
        "min_full_year_trades": min_full_year_trades,
        "profitable_full_year_pct": profitable_year_pct,
        **gates,
        "all_gates_pass": all_pass,
        "primary_failure_reason": primary_failure,
        "final_status": "HISTORICAL DISTRIBUTED SURVIVOR — REQUIRES PRECOMMITTED STABILITY BATCH" if all_pass else "REJECTED",
    }
    return summary, eval_trades, qdf, r4, r8, ydf
