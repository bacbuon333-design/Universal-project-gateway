from __future__ import annotations

"""V3.10 read-only stability audit of the already-frozen V3.9 H226 8h events.

This module never rebuilds events from market data and never calls a trading engine.
"""

from pathlib import Path
from typing import Dict, Iterable, List
import hashlib
import json
import subprocess

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
V39_DIR = ROOT / "AlphaLab_Antigravity" / "reports" / "v3_9"
OUT_DIR = ROOT / "AlphaLab_Antigravity" / "reports" / "v3_10"
EVENTS_PATH = V39_DIR / "v3_9_h226_events.csv"
V39_META_PATH = V39_DIR / "v3_9_metadata.json"
V39_DECISION_PATH = V39_DIR / "v3_9_h226_mechanism_decision.json"

SCIENTIFIC_PARENT = "ae3e4a0d0116b07867ead4e09a6466e54faef8d5"
V39_FROZEN_CODE_HEAD = "505e217fba0d27bc250d14890093215c1cea8f69"
CANONICAL_ID = "GOLD_M30_CANONICAL_V2"
CANONICAL_SHA = "c48ca44dcecae9eb1c2590c586e27c4bc5f246215c549d0d0bc1201d95d5ea1d"
COHORTS = ("H226-C1", "H226-C2", "H226-C3", "H226-C4")
DECISION_COHORTS = ("H226-C1", "H226-C4")
FULL_YEARS = tuple(range(2019, 2026))
EVAL_START = "2018Q2"
EVAL_END = "2026Q2"
HORIZON = "8h"
QUARTER_BOOT_REPS = 5000
QUARTER_BOOT_SEED = 310226
YEAR_BOOT_REPS = 5000
YEAR_BOOT_SEED = 310227
ROUNDTRIP_PRICE_EQUIV_USD_PER_OZ = 0.32


def git_head() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        return "UNAVAILABLE"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path: Path) -> Dict:
    with path.open("r", encoding="utf-8") as f:
        obj = json.load(f)
    if not isinstance(obj, dict):
        raise RuntimeError(f"Expected JSON object: {path}")
    return obj


def complete_quarters() -> List[str]:
    out: List[str] = []
    for year in range(2018, 2027):
        for quarter in range(1, 5):
            label = f"{year}Q{quarter}"
            if EVAL_START <= label <= EVAL_END:
                out.append(label)
    if len(out) != 33:
        raise RuntimeError("V3.10 quarter contract drift")
    return out


def verify_v39_source() -> Dict:
    for p in (EVENTS_PATH, V39_META_PATH, V39_DECISION_PATH):
        if not p.exists():
            raise RuntimeError(f"Missing frozen V3.9 source artifact: {p}")
    meta = load_json(V39_META_PATH)
    decision = load_json(V39_DECISION_PATH)
    checks = {
        "artifact_parent": meta.get("artifact_generation_parent_sha") == V39_FROZEN_CODE_HEAD,
        "canonical_id": meta.get("canonical_dataset_id") == CANONICAL_ID,
        "canonical_sha": meta.get("canonical_dataset_sha256") == CANONICAL_SHA,
        "strategy_not_executed": meta.get("strategy_executed") is False,
        "engine_not_called": meta.get("trading_engine_called") is False,
        "v39_label": meta.get("mechanism_label") == "H226 GAP-REVERSION MECHANISM WEAK / TAIL-UNSTABLE — STRATEGY STILL REJECTED",
        "redesign_not_authorized": meta.get("strategy_redesign_authorized") is False,
        "decision_cohorts": decision.get("decision_cohorts_frozen_pre_result") == ["H226-C1", "H226-C4"],
        "strategy_rejected": decision.get("strategy_status_remains") == "REJECTED",
    }
    failed = [k for k, ok in checks.items() if not ok]
    if failed:
        raise RuntimeError("Frozen V3.9 source verification failed: " + ", ".join(failed))
    return {
        "events_sha256": sha256_file(EVENTS_PATH),
        "metadata": meta,
        "decision": decision,
        "checks": checks,
    }


def load_frozen_8h_events() -> tuple[pd.DataFrame, Dict]:
    source = verify_v39_source()
    df = pd.read_csv(EVENTS_PATH)
    required = {
        "event_id", "year", "quarter", "cohort", "gap_direction", "horizon",
        "signed_reversion_return_atr", "gap_closed_by_horizon", "atr_prev",
    }
    missing = required.difference(df.columns)
    if missing:
        raise RuntimeError(f"V3.9 events missing columns: {sorted(missing)}")
    df = df[(df["horizon"].astype(str) == HORIZON) & (df["cohort"].isin(COHORTS))].copy()
    if df.empty:
        raise RuntimeError("No frozen H226 8h events")
    if set(df["cohort"].unique()) != set(COHORTS):
        raise RuntimeError("One or more frozen H226 cohorts missing at 8h")
    if not set(df["quarter"].astype(str)).issubset(set(complete_quarters())):
        raise RuntimeError("8h event outside frozen evaluation quarters")
    df["year"] = df["year"].astype(int)
    df["signed_reversion_return_atr"] = df["signed_reversion_return_atr"].astype(float)
    df["atr_prev"] = df["atr_prev"].astype(float)
    df["gap_closed_by_horizon"] = df["gap_closed_by_horizon"].astype(str).str.lower().map({"true": True, "false": False}).fillna(df["gap_closed_by_horizon"]).astype(bool)
    return df.reset_index(drop=True), source


def summarize_slice(cohort: str, view: str, sub: pd.DataFrame) -> Dict:
    x = sub["signed_reversion_return_atr"].to_numpy(dtype=float)
    if len(x) == 0:
        return {
            "cohort": cohort, "view": view, "event_count": 0,
            "mean_signed_reversion_atr": np.nan, "median_signed_reversion_atr": np.nan,
            "positive_return_pct": np.nan, "p10_signed_reversion_atr": np.nan,
            "p90_signed_reversion_atr": np.nan, "worst5pct_mean_signed_reversion_atr": np.nan,
            "gap_closure_pct": np.nan, "median_cost_hurdle_atr": np.nan,
            "mean_to_median_cost_hurdle_ratio": np.nan,
        }
    k = max(1, int(np.ceil(len(x) * 0.05)))
    worst5 = float(np.sort(x)[:k].mean())
    costs = ROUNDTRIP_PRICE_EQUIV_USD_PER_OZ / sub["atr_prev"].to_numpy(dtype=float)
    costs = costs[np.isfinite(costs) & (costs > 0)]
    med_cost = float(np.median(costs)) if len(costs) else np.nan
    mean = float(np.mean(x))
    return {
        "cohort": cohort,
        "view": view,
        "event_count": int(len(sub)),
        "mean_signed_reversion_atr": mean,
        "median_signed_reversion_atr": float(np.median(x)),
        "positive_return_pct": float(np.mean(x > 0) * 100.0),
        "p10_signed_reversion_atr": float(np.quantile(x, 0.10)),
        "p90_signed_reversion_atr": float(np.quantile(x, 0.90)),
        "worst5pct_mean_signed_reversion_atr": worst5,
        "gap_closure_pct": float(sub["gap_closed_by_horizon"].mean() * 100.0),
        "median_cost_hurdle_atr": med_cost,
        "mean_to_median_cost_hurdle_ratio": float(mean / med_cost) if np.isfinite(med_cost) and med_cost > 0 else np.nan,
    }


def build_view_summary(events: pd.DataFrame) -> pd.DataFrame:
    rows: List[Dict] = []
    for cohort in COHORTS:
        base = events[events["cohort"] == cohort]
        views = {
            "FULL": base,
            "PRE_2025": base[base["quarter"] <= "2024Q4"],
            "RECENT": base[(base["quarter"] >= "2025Q1") & (base["quarter"] <= "2026Q2")],
            "UP_GAP": base[base["gap_direction"] == "UP"],
            "DOWN_GAP": base[base["gap_direction"] == "DOWN"],
            "LEAVE_2025_2026_OUT": base[base["quarter"] <= "2024Q4"],
        }
        for view, sub in views.items():
            rows.append(summarize_slice(cohort, view, sub))
    return pd.DataFrame(rows)


def build_year_stability(events: pd.DataFrame) -> pd.DataFrame:
    rows: List[Dict] = []
    for cohort in COHORTS:
        base = events[events["cohort"] == cohort]
        for year in FULL_YEARS:
            row = summarize_slice(cohort, f"YEAR_{year}", base[base["year"] == year])
            row["year"] = year
            row["positive_mean"] = bool(np.isfinite(row["mean_signed_reversion_atr"]) and row["mean_signed_reversion_atr"] > 0)
            rows.append(row)
    return pd.DataFrame(rows)


def build_quarter_stability(events: pd.DataFrame) -> pd.DataFrame:
    rows: List[Dict] = []
    for cohort in COHORTS:
        base = events[events["cohort"] == cohort]
        for quarter in complete_quarters():
            row = summarize_slice(cohort, f"QUARTER_{quarter}", base[base["quarter"] == quarter])
            row["quarter"] = quarter
            row["positive_mean"] = bool(np.isfinite(row["mean_signed_reversion_atr"]) and row["mean_signed_reversion_atr"] > 0)
            rows.append(row)
    return pd.DataFrame(rows)


def build_leave_one_year_out(events: pd.DataFrame) -> pd.DataFrame:
    rows: List[Dict] = []
    for cohort in COHORTS:
        base = events[events["cohort"] == cohort]
        for year in FULL_YEARS:
            sub = base[base["year"] != year]
            row = summarize_slice(cohort, f"LEAVE_{year}_OUT", sub)
            row["excluded_year"] = year
            row["positive_mean"] = bool(np.isfinite(row["mean_signed_reversion_atr"]) and row["mean_signed_reversion_atr"] > 0)
            rows.append(row)
    return pd.DataFrame(rows)


def clustered_bootstrap(events: pd.DataFrame, block_type: str, reps: int, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows: List[Dict] = []
    if block_type == "QUARTER":
        labels: Iterable[str | int] = complete_quarters()
        column = "quarter"
    elif block_type == "YEAR":
        labels = FULL_YEARS
        column = "year"
    else:
        raise ValueError(block_type)
    labels = list(labels)
    for cohort in COHORTS:
        base = events[events["cohort"] == cohort]
        if block_type == "YEAR":
            base = base[base["year"].isin(FULL_YEARS)]
        blocks = {
            label: base.loc[base[column] == label, "signed_reversion_return_atr"].to_numpy(dtype=float)
            for label in labels
        }
        draws: List[float] = []
        for _ in range(reps):
            sampled = rng.choice(labels, size=len(labels), replace=True)
            pieces = [blocks[label] for label in sampled if len(blocks[label])]
            if pieces:
                draws.append(float(np.mean(np.concatenate(pieces))))
        arr = np.asarray(draws, dtype=float)
        if len(arr) == 0:
            lo = hi = ppos = np.nan
        else:
            lo = float(np.quantile(arr, 0.025))
            hi = float(np.quantile(arr, 0.975))
            ppos = float(np.mean(arr > 0) * 100.0)
        rows.append({
            "cohort": cohort,
            "horizon": HORIZON,
            "block_type": block_type,
            "bootstrap_reps_requested": reps,
            "bootstrap_reps_valid": int(len(arr)),
            "seed": seed,
            "ci_2_5": lo,
            "ci_97_5": hi,
            "p_mean_gt_zero_pct": ppos,
        })
    return pd.DataFrame(rows)


def make_decision(views: pd.DataFrame, years: pd.DataFrame, loo: pd.DataFrame, boots: pd.DataFrame) -> Dict:
    detail: Dict[str, Dict] = {}
    for cohort in COHORTS:
        v = views[views["cohort"] == cohort].set_index("view")
        y = years[years["cohort"] == cohort]
        l = loo[loo["cohort"] == cohort]
        b = boots[boots["cohort"] == cohort].set_index("block_type")
        positive_years = int(y["positive_mean"].sum())
        checks = {
            "full_mean_positive": bool(v.loc["FULL", "mean_signed_reversion_atr"] > 0),
            "full_median_positive": bool(v.loc["FULL", "median_signed_reversion_atr"] > 0),
            "quarter_block_ci_lower_positive": bool(b.loc["QUARTER", "ci_2_5"] > 0),
            "year_block_ci_lower_positive": bool(b.loc["YEAR", "ci_2_5"] > 0),
            "pre2025_mean_positive": bool(v.loc["PRE_2025", "mean_signed_reversion_atr"] > 0),
            "recent_mean_positive": bool(v.loc["RECENT", "mean_signed_reversion_atr"] > 0),
            "up_gap_mean_positive": bool(v.loc["UP_GAP", "mean_signed_reversion_atr"] > 0),
            "down_gap_mean_positive": bool(v.loc["DOWN_GAP", "mean_signed_reversion_atr"] > 0),
            "at_least_5_of_7_positive_years": bool(positive_years >= 5),
            "all_leave_one_year_out_means_positive": bool(len(l) == 7 and l["positive_mean"].all()),
            "leave_2025_2026_out_mean_positive": bool(v.loc["LEAVE_2025_2026_OUT", "mean_signed_reversion_atr"] > 0),
        }
        detail[cohort] = {
            "checks": checks,
            "all_robustness_checks_pass": bool(all(checks.values())),
            "positive_complete_years": positive_years,
            "full": {
                "n": int(v.loc["FULL", "event_count"]),
                "mean": float(v.loc["FULL", "mean_signed_reversion_atr"]),
                "median": float(v.loc["FULL", "median_signed_reversion_atr"]),
            },
            "quarter_block_ci": [float(b.loc["QUARTER", "ci_2_5"]), float(b.loc["QUARTER", "ci_97_5"])],
            "year_block_ci": [float(b.loc["YEAR", "ci_2_5"]), float(b.loc["YEAR", "ci_97_5"])],
        }
    robust = all(detail[c]["all_robustness_checks_pass"] for c in DECISION_COHORTS)
    pooled_positive = all(detail[c]["checks"]["full_mean_positive"] for c in DECISION_COHORTS)
    if robust:
        label = "H226 DELAYED 8H REVERSION ROBUSTLY SUPPORTED — STRATEGY DESIGN NOT AUTHORIZED"
    elif pooled_positive:
        label = "H226 DELAYED 8H REVERSION REGIME / DIRECTION DEPENDENT — STRATEGY DESIGN NOT AUTHORIZED"
    else:
        label = "H226 DELAYED 8H REVERSION NOT SUPPORTED — H226 CHAPTER CLOSED"
    return {
        "mechanism_label": label,
        "horizon_frozen": HORIZON,
        "decision_cohorts_frozen": list(DECISION_COHORTS),
        "h226_strategy_status_remains": "REJECTED",
        "strategy_design_authorized": False,
        "detail": detail,
    }


def run_audit() -> Dict:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    frozen_head = git_head()
    events, source = load_frozen_8h_events()
    views = build_view_summary(events)
    years = build_year_stability(events)
    quarters = build_quarter_stability(events)
    loo = build_leave_one_year_out(events)
    qb = clustered_bootstrap(events, "QUARTER", QUARTER_BOOT_REPS, QUARTER_BOOT_SEED)
    yb = clustered_bootstrap(events, "YEAR", YEAR_BOOT_REPS, YEAR_BOOT_SEED)
    boots = pd.concat([qb, yb], ignore_index=True)
    decision = make_decision(views, years, loo, boots)

    views.to_csv(OUT_DIR / "v3_10_8h_view_summary.csv", index=False)
    years.to_csv(OUT_DIR / "v3_10_8h_year_stability.csv", index=False)
    quarters.to_csv(OUT_DIR / "v3_10_8h_quarter_stability.csv", index=False)
    loo.to_csv(OUT_DIR / "v3_10_8h_leave_one_year_out.csv", index=False)
    boots.to_csv(OUT_DIR / "v3_10_8h_cluster_bootstrap.csv", index=False)
    (OUT_DIR / "v3_10_8h_decision.json").write_text(json.dumps(decision, indent=2) + "\n", encoding="utf-8")

    metadata = {
        "chapter": "V3.10 H226 DELAYED 8H REVERSION STABILITY AUDIT",
        "artifact_generation_parent_sha": frozen_head,
        "scientific_parent_v39_final": SCIENTIFIC_PARENT,
        "source_v39_event_sha256": source["events_sha256"],
        "source_v39_artifact_parent_sha": V39_FROZEN_CODE_HEAD,
        "canonical_dataset_id": CANONICAL_ID,
        "canonical_dataset_sha256": CANONICAL_SHA,
        "horizon": HORIZON,
        "cohorts": list(COHORTS),
        "decision_cohorts": list(DECISION_COHORTS),
        "quarter_bootstrap_reps": QUARTER_BOOT_REPS,
        "quarter_bootstrap_seed": QUARTER_BOOT_SEED,
        "year_bootstrap_reps": YEAR_BOOT_REPS,
        "year_bootstrap_seed": YEAR_BOOT_SEED,
        "strategy_executed": False,
        "trading_engine_called": False,
        "raw_market_data_read": False,
        "events_reconstructed": False,
        "h226_strategy_status_remains": "REJECTED",
        "strategy_design_authorized": False,
        "mechanism_label": decision["mechanism_label"],
    }
    (OUT_DIR / "v3_10_metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    return {
        "events": events, "views": views, "years": years, "quarters": quarters,
        "loo": loo, "boots": boots, "decision": decision, "metadata": metadata,
    }


if __name__ == "__main__":
    result = run_audit()
    print(json.dumps({
        "artifact_generation_parent_sha": result["metadata"]["artifact_generation_parent_sha"],
        "source_8h_event_rows": len(result["events"]),
        "mechanism_label": result["decision"]["mechanism_label"],
        "strategy_executed": False,
        "raw_market_data_read": False,
    }, indent=2))
