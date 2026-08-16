from __future__ import annotations

"""V3.9 read-only loss-tail diagnostics and H226 event study.

No trading engine is executed. V3.8 verdicts remain immutable.
"""

from pathlib import Path
from typing import Dict, Iterable, List
import json
import math
import subprocess

import numpy as np
import pandas as pd

from canonical_v2_research_engine import (
    FROZEN_SHA256,
    load_authorized_canonical_v2_dataframe,
)

ROOT = Path(__file__).resolve().parents[2]
V38_DIR = ROOT / "AlphaLab_Antigravity" / "reports" / "v3_8"
OUT_DIR = ROOT / "AlphaLab_Antigravity" / "reports" / "v3_9"
EVAL_START = "2018Q2"
EVAL_END = "2026Q2"
FULL_YEARS = list(range(2019, 2026))
BOOTSTRAP_REPS = 2000
BOOTSTRAP_SEED = 390226
HORIZONS = {"30m": 1, "1h": 2, "2h": 4, "4h": 8, "8h": 16}
KEY_BOOT_HORIZONS = ("1h", "2h", "4h", "8h")
STABILITY_HORIZONS = ("2h", "4h")
COHORTS = {
    "H226-C1": (0.05, 0.25),
    "H226-C2": (0.10, 0.25),
    "H226-C3": (0.05, 0.50),
    "H226-C4": (0.10, 0.50),
}


def git_head() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        return "UNAVAILABLE"


def complete_quarters() -> List[str]:
    out: List[str] = []
    for y in range(2018, 2027):
        for q in range(1, 5):
            label = f"{y}Q{q}"
            if EVAL_START <= label <= EVAL_END:
                out.append(label)
    if len(out) != 33:
        raise RuntimeError("V3.9 quarter contract drift")
    return out


def atr14(df: pd.DataFrame) -> pd.Series:
    prev_close = df["close"].shift(1)
    tr = pd.concat(
        [
            df["high"] - df["low"],
            (df["high"] - prev_close).abs(),
            (df["low"] - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.ewm(alpha=1.0 / 14.0, adjust=False, min_periods=14).mean()


def _pool_share(values: Iterable[float], k: int) -> float:
    x = np.asarray(list(values), dtype=float)
    x = x[np.isfinite(x) & (x > 0)]
    if len(x) == 0 or float(x.sum()) <= 0:
        return float("nan")
    x = np.sort(x)[::-1]
    return float(x[: min(k, len(x))].sum() / x.sum() * 100.0)


def _tail_share(values: np.ndarray, pct: float) -> float:
    x = np.asarray(values, dtype=float)
    x = x[np.isfinite(x) & (x > 0)]
    if len(x) == 0 or float(x.sum()) <= 0:
        return float("nan")
    k = max(1, int(math.ceil(len(x) * pct)))
    x = np.sort(x)[::-1]
    return float(x[:k].sum() / x.sum() * 100.0)


def audit_loss_concentration() -> pd.DataFrame:
    all_cfg = pd.read_csv(V38_DIR / "v3_8_all_configs.csv")
    if len(all_cfg) != 24:
        raise RuntimeError("Expected exactly 24 frozen V3.8 configs")
    rows: List[Dict] = []
    for _, meta in all_cfg.sort_values("config_id").iterrows():
        cid = str(meta["config_id"])
        stem = cid.lower().replace("-", "_")
        trades = pd.read_csv(V38_DIR / f"{stem}_trades.csv")
        qdf = pd.read_csv(V38_DIR / f"{stem}_quarters.csv")
        ydf = pd.read_csv(V38_DIR / f"{stem}_years.csv")

        neg_q = (-qdf.loc[qdf["net_pnl_usd"] < 0, "net_pnl_usd"].astype(float)).to_numpy()
        full_y = ydf[ydf["year"].astype(int).isin(FULL_YEARS)].copy()
        neg_y = (-full_y.loc[full_y["net_pnl_usd"] < 0, "net_pnl_usd"].astype(float)).to_numpy()

        losses = (-trades.loc[trades["pnl_usd"] < 0, "pnl_usd"].astype(float)).to_numpy()
        if len(losses):
            s = np.sort(losses)
            k5 = max(1, int(math.ceil(len(s) * 0.05)))
            cvar95 = float(s[-k5:].mean())
            med = float(np.median(s))
            mean_loss = float(np.mean(s))
            p95 = float(np.quantile(s, 0.95))
            p99 = float(np.quantile(s, 0.99))
            max_loss = float(np.max(s))
            max_med = max_loss / med if med > 0 else float("nan")
        else:
            cvar95 = med = mean_loss = p95 = p99 = max_loss = max_med = float("nan")

        rows.append({
            "config_id": cid,
            "family": meta["family"],
            "v38_pf": float(meta["pf"]),
            "v38_expectancy_usd": float(meta["expectancy_usd"]),
            "v38_rolling8_positive_pct": float(meta["rolling8_positive_pct"]),
            "v38_profitable_full_year_pct": float(meta["profitable_full_year_pct"]),
            "negative_quarter_count": int(len(neg_q)),
            "negative_quarter_loss_pool_abs_usd": float(neg_q.sum()) if len(neg_q) else 0.0,
            "worst1_negative_q_loss_share_pct": _pool_share(neg_q, 1),
            "worst3_negative_q_loss_share_pct": _pool_share(neg_q, 3),
            "worst5_negative_q_loss_share_pct": _pool_share(neg_q, 5),
            "negative_complete_year_count": int(len(neg_y)),
            "negative_complete_year_loss_pool_abs_usd": float(neg_y.sum()) if len(neg_y) else 0.0,
            "worst1_negative_year_loss_share_pct": _pool_share(neg_y, 1),
            "worst3_negative_year_loss_share_pct": _pool_share(neg_y, 3),
            "losing_trade_count": int(len(losses)),
            "median_losing_trade_abs_usd": med,
            "mean_losing_trade_abs_usd": mean_loss,
            "p95_losing_trade_abs_usd": p95,
            "p99_losing_trade_abs_usd": p99,
            "loss_cvar95_abs_usd": cvar95,
            "worst1pct_losing_trade_loss_share_pct": _tail_share(losses, 0.01),
            "worst5pct_losing_trade_loss_share_pct": _tail_share(losses, 0.05),
            "largest_single_trade_loss_abs_usd": max_loss,
            "largest_loss_to_median_loss_ratio": max_med,
            "v38_final_status_frozen": str(meta["final_status"]),
        })
    return pd.DataFrame(rows)


def _quarter_labels(ts: pd.Series) -> pd.Series:
    naive = ts.dt.tz_convert("UTC").dt.tz_localize(None)
    return naive.dt.to_period("Q").astype(str)


def build_h226_events() -> pd.DataFrame:
    df, auth = load_authorized_canonical_v2_dataframe()
    if auth["dataset_sha256"] != FROZEN_SHA256:
        raise RuntimeError("Canonical V2 SHA drift")
    df = df.copy().sort_values("timestamp_utc").reset_index(drop=True)
    df["datetime"] = pd.to_datetime(df["timestamp_utc"], utc=True, errors="raise")
    df["quarter"] = _quarter_labels(df["datetime"])
    a = atr14(df).to_numpy(dtype=float)
    ts = df["datetime"]
    dates = ts.dt.date.to_numpy()
    op = df["open"].astype(float).to_numpy()
    hi = df["high"].astype(float).to_numpy()
    lo = df["low"].astype(float).to_numpy()
    cl = df["close"].astype(float).to_numpy()

    rows: List[Dict] = []
    event_id = 0
    for i in range(1, len(df) - 1):
        if dates[i] == dates[i - 1]:
            continue
        q = str(df.loc[i, "quarter"])
        if not (EVAL_START <= q <= EVAL_END):
            continue
        atr_prev = a[i - 1]
        if not np.isfinite(atr_prev) or atr_prev <= 0:
            continue
        prev_close = cl[i - 1]
        gap = op[i] - prev_close
        if not np.isfinite(gap) or abs(gap) <= 1e-12:
            continue
        gap_z = abs(gap) / atr_prev
        crossed = bool((gap > 0 and cl[i] <= prev_close) or (gap < 0 and cl[i] >= prev_close))
        residual = abs(cl[i] - prev_close) / abs(gap)
        rev_sign = -1 if gap > 0 else 1
        entry_idx = i + 1
        entry_proxy = op[entry_idx]
        event_id += 1

        cohorts = ["ALL_DAILY_GAPS"]
        if not crossed:
            for name, (gmin, rmin) in COHORTS.items():
                if gap_z >= gmin and residual >= rmin:
                    cohorts.append(name)

        for cohort in cohorts:
            for hname, bars in HORIZONS.items():
                end_idx = entry_idx + bars - 1
                if end_idx >= len(df):
                    continue
                path_hi = hi[entry_idx : end_idx + 1]
                path_lo = lo[entry_idx : end_idx + 1]
                signed_ret = rev_sign * (cl[end_idx] - entry_proxy) / atr_prev
                if rev_sign == 1:
                    mfe = (float(np.max(path_hi)) - entry_proxy) / atr_prev
                    mae = (entry_proxy - float(np.min(path_lo))) / atr_prev
                else:
                    mfe = (entry_proxy - float(np.min(path_lo))) / atr_prev
                    mae = (float(np.max(path_hi)) - entry_proxy) / atr_prev
                if gap > 0:
                    gap_closed = bool(np.min(path_lo) <= prev_close)
                else:
                    gap_closed = bool(np.max(path_hi) >= prev_close)
                rows.append({
                    "event_id": event_id,
                    "signal_bar_open_time_utc": ts.iloc[i].isoformat(),
                    "entry_proxy_bar_open_time_utc": ts.iloc[entry_idx].isoformat(),
                    "year": int(ts.iloc[i].year),
                    "quarter": q,
                    "cohort": cohort,
                    "gap_direction": "UP" if gap > 0 else "DOWN",
                    "gap_price": float(gap),
                    "gap_z_atr": float(gap_z),
                    "first_bar_crossed_prior_close": crossed,
                    "residual_after_first_bar": float(residual),
                    "atr_prev": float(atr_prev),
                    "prev_close": float(prev_close),
                    "entry_proxy": float(entry_proxy),
                    "horizon": hname,
                    "horizon_bars": bars,
                    "signed_reversion_return_atr": float(signed_ret),
                    "mfe_atr": float(max(mfe, 0.0)),
                    "mae_atr": float(max(mae, 0.0)),
                    "gap_closed_by_horizon": gap_closed,
                })
    out = pd.DataFrame(rows)
    if out.empty:
        raise RuntimeError("V3.9 produced no H226 events")
    return out


def summarize_events(events: pd.DataFrame) -> pd.DataFrame:
    rows: List[Dict] = []
    order = ["ALL_DAILY_GAPS", *COHORTS.keys()]
    for cohort in order:
        for hname in HORIZONS:
            sub = events[(events["cohort"] == cohort) & (events["horizon"] == hname)]
            x = sub["signed_reversion_return_atr"].to_numpy(dtype=float)
            if len(x) == 0:
                continue
            k = max(1, int(math.ceil(len(x) * 0.05)))
            left = float(np.sort(x)[:k].mean())
            rows.append({
                "cohort": cohort,
                "horizon": hname,
                "event_count": int(len(sub)),
                "mean_signed_reversion_atr": float(np.mean(x)),
                "median_signed_reversion_atr": float(np.median(x)),
                "positive_return_pct": float(np.mean(x > 0) * 100.0),
                "p10_signed_reversion_atr": float(np.quantile(x, 0.10)),
                "p25_signed_reversion_atr": float(np.quantile(x, 0.25)),
                "p75_signed_reversion_atr": float(np.quantile(x, 0.75)),
                "p90_signed_reversion_atr": float(np.quantile(x, 0.90)),
                "mean_mfe_atr": float(sub["mfe_atr"].mean()),
                "mean_mae_atr": float(sub["mae_atr"].mean()),
                "median_mfe_atr": float(sub["mfe_atr"].median()),
                "median_mae_atr": float(sub["mae_atr"].median()),
                "gap_closure_pct": float(sub["gap_closed_by_horizon"].mean() * 100.0),
                "worst5pct_mean_signed_reversion_atr": left,
            })
    return pd.DataFrame(rows)


def temporal_stability(events: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    yrows: List[Dict] = []
    qrows: List[Dict] = []
    for cohort in COHORTS:
        for hname in STABILITY_HORIZONS:
            base = events[(events["cohort"] == cohort) & (events["horizon"] == hname)]
            year_means: List[float] = []
            for year in FULL_YEARS:
                sub = base[base["year"] == year]
                mean = float(sub["signed_reversion_return_atr"].mean()) if len(sub) else float("nan")
                year_means.append(mean)
                yrows.append({
                    "cohort": cohort,
                    "horizon": hname,
                    "year": year,
                    "event_count": int(len(sub)),
                    "mean_signed_reversion_atr": mean,
                    "positive_mean": bool(np.isfinite(mean) and mean > 0),
                })
            for q in complete_quarters():
                sub = base[base["quarter"] == q]
                mean = float(sub["signed_reversion_return_atr"].mean()) if len(sub) else float("nan")
                qrows.append({
                    "cohort": cohort,
                    "horizon": hname,
                    "quarter": q,
                    "event_count": int(len(sub)),
                    "mean_signed_reversion_atr": mean,
                    "positive_mean": bool(np.isfinite(mean) and mean > 0),
                })
    return pd.DataFrame(yrows), pd.DataFrame(qrows)


def quarter_block_bootstrap(events: pd.DataFrame) -> pd.DataFrame:
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    quarters = complete_quarters()
    rows: List[Dict] = []
    for cohort in COHORTS:
        for hname in KEY_BOOT_HORIZONS:
            sub = events[(events["cohort"] == cohort) & (events["horizon"] == hname)]
            blocks = {q: sub.loc[sub["quarter"] == q, "signed_reversion_return_atr"].to_numpy(dtype=float) for q in quarters}
            reps: List[float] = []
            for _ in range(BOOTSTRAP_REPS):
                sampled = rng.choice(quarters, size=len(quarters), replace=True)
                pieces = [blocks[q] for q in sampled if len(blocks[q])]
                if not pieces:
                    continue
                reps.append(float(np.mean(np.concatenate(pieces))))
            if not reps:
                lo = hi = ppos = float("nan")
            else:
                arr = np.asarray(reps, dtype=float)
                lo = float(np.quantile(arr, 0.025))
                hi = float(np.quantile(arr, 0.975))
                ppos = float(np.mean(arr > 0) * 100.0)
            rows.append({
                "cohort": cohort,
                "horizon": hname,
                "bootstrap_reps_requested": BOOTSTRAP_REPS,
                "bootstrap_reps_valid": int(len(reps)),
                "seed": BOOTSTRAP_SEED,
                "ci_2_5": lo,
                "ci_97_5": hi,
                "p_mean_gt_zero_pct": ppos,
            })
    return pd.DataFrame(rows)


def mechanism_decision(summary: pd.DataFrame, years: pd.DataFrame, boot: pd.DataFrame) -> Dict:
    detail: Dict[str, Dict] = {}
    for cohort in COHORTS:
        d: Dict[str, object] = {}
        for h in ("2h", "4h"):
            s = summary[(summary["cohort"] == cohort) & (summary["horizon"] == h)].iloc[0]
            b = boot[(boot["cohort"] == cohort) & (boot["horizon"] == h)].iloc[0]
            d[h] = {
                "mean": float(s["mean_signed_reversion_atr"]),
                "median": float(s["median_signed_reversion_atr"]),
                "block_ci_lower": float(b["ci_2_5"]),
                "block_ci_upper": float(b["ci_97_5"]),
            }
        y4 = years[(years["cohort"] == cohort) & (years["horizon"] == "4h")]
        pos_years = int(y4["positive_mean"].sum())
        s4 = summary[(summary["cohort"] == cohort) & (summary["horizon"] == "4h")].iloc[0]
        b4 = boot[(boot["cohort"] == cohort) & (boot["horizon"] == "4h")].iloc[0]
        d["positive_years_4h"] = pos_years
        d["positive_year_pct_4h"] = float(pos_years / 7.0 * 100.0)
        d["diagnostics_4h"] = {
            "mean_reversion_positive": bool(s4["mean_signed_reversion_atr"] > 0),
            "median_reversion_positive": bool(s4["median_signed_reversion_atr"] > 0),
            "block_ci_excludes_zero_positive": bool(b4["ci_2_5"] > 0),
            "positive_years_at_least_4_of_7": bool(pos_years >= 4),
            "gap_closure_probability_gt_50pct": bool(s4["gap_closure_pct"] > 50.0),
            "left_tail_abs_exceeds_mean_magnitude": bool(abs(s4["worst5pct_mean_signed_reversion_atr"]) > abs(s4["mean_signed_reversion_atr"])),
        }
        detail[cohort] = d

    def full_support(cohort: str) -> bool:
        d = detail[cohort]
        for h in ("2h", "4h"):
            if not (d[h]["mean"] > 0 and d[h]["median"] > 0 and d[h]["block_ci_lower"] > 0):
                return False
        return bool(d["positive_years_4h"] >= 4)

    support = full_support("H226-C1") and full_support("H226-C4")
    weak = all(any(detail[c][h]["mean"] > 0 for h in ("2h", "4h")) for c in ("H226-C1", "H226-C4"))
    if support:
        label = "H226 GAP-REVERSION MECHANISM DESCRIPTIVELY SUPPORTED — STRATEGY STILL REJECTED"
    elif weak:
        label = "H226 GAP-REVERSION MECHANISM WEAK / TAIL-UNSTABLE — STRATEGY STILL REJECTED"
    else:
        label = "H226 GAP-REVERSION MECHANISM NOT SUPPORTED — STRATEGY REJECTED"
    return {
        "mechanism_label": label,
        "decision_cohorts_frozen_pre_result": ["H226-C1", "H226-C4"],
        "strategy_status_remains": "REJECTED",
        "strategy_redesign_authorized": False,
        "detail": detail,
    }


def run_audit() -> Dict:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    frozen_head = git_head()
    loss = audit_loss_concentration()
    events = build_h226_events()
    summary = summarize_events(events)
    years, quarters = temporal_stability(events)
    boot = quarter_block_bootstrap(events)
    decision = mechanism_decision(summary, years, boot)

    loss.to_csv(OUT_DIR / "v3_9_loss_concentration_all_configs.csv", index=False)
    summary.to_csv(OUT_DIR / "v3_9_h226_event_summary.csv", index=False)
    events.to_csv(OUT_DIR / "v3_9_h226_events.csv", index=False)
    years.to_csv(OUT_DIR / "v3_9_h226_year_stability.csv", index=False)
    quarters.to_csv(OUT_DIR / "v3_9_h226_quarter_stability.csv", index=False)
    boot.to_csv(OUT_DIR / "v3_9_h226_block_bootstrap.csv", index=False)
    (OUT_DIR / "v3_9_h226_mechanism_decision.json").write_text(json.dumps(decision, indent=2) + "\n", encoding="utf-8")

    metadata = {
        "chapter": "V3.9 LOSS-CONCENTRATION & H226 TAIL-MECHANISM AUDIT",
        "artifact_generation_parent_sha": frozen_head,
        "scientific_parent_v38_final": "635258edb87da39cb3bd1a599bec2f6c94a0b477",
        "canonical_dataset_id": "GOLD_M30_CANONICAL_V2",
        "canonical_dataset_sha256": FROZEN_SHA256,
        "v38_strategy_conclusion_frozen": "NO V3.8 CONFIGURATION PASSED ALL FROZEN DISTRIBUTED-EDGE GATES",
        "strategy_executed": False,
        "trading_engine_called": False,
        "v38_config_count_audited": int(len(loss)),
        "h226_cohorts": {k: {"gap_z_min": v[0], "residual_min": v[1]} for k, v in COHORTS.items()},
        "horizons": HORIZONS,
        "bootstrap_reps": BOOTSTRAP_REPS,
        "bootstrap_seed": BOOTSTRAP_SEED,
        "mechanism_label": decision["mechanism_label"],
        "strategy_redesign_authorized": False,
    }
    (OUT_DIR / "v3_9_metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    return {"loss": loss, "events": events, "summary": summary, "years": years, "quarters": quarters, "bootstrap": boot, "decision": decision, "metadata": metadata}


if __name__ == "__main__":
    result = run_audit()
    print(json.dumps({
        "artifact_generation_parent_sha": result["metadata"]["artifact_generation_parent_sha"],
        "loss_configs": len(result["loss"]),
        "event_rows": len(result["events"]),
        "mechanism_label": result["decision"]["mechanism_label"],
        "strategy_executed": False,
    }, indent=2))
