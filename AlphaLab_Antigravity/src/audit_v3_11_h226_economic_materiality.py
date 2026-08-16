from __future__ import annotations

"""V3.11 read-only economic-materiality closure for frozen H226 8h events.

No strategy execution. No raw-market reconstruction. H226 trading strategies remain
rejected regardless of this diagnostic result.
"""

from pathlib import Path
from typing import Dict, List
import hashlib
import json
import math
import subprocess

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SRC_EVENTS = ROOT / "AlphaLab_Antigravity" / "reports" / "v3_9" / "v3_9_h226_events.csv"
SRC_V310_DECISION = ROOT / "AlphaLab_Antigravity" / "reports" / "v3_10" / "v3_10_8h_decision.json"
OUT_DIR = ROOT / "AlphaLab_Antigravity" / "reports" / "v3_11"

V39_EVENTS_SHA256 = "aecdb78d22598a962c29adbd7448755eaf31399d351d5efcbeeddc0c823d920f"
CANONICAL_SHA256 = "c48ca44dcecae9eb1c2590c586e27c4bc5f246215c549d0d0bc1201d95d5ea1d"
V310_FINAL_SHA = "b387e25bdf6fd814c3034f3688af50e976f5cc59"
HORIZON = "8h"
COHORTS = ("H226-C1", "H226-C2", "H226-C3", "H226-C4")
DECISION_COHORTS = ("H226-C1", "H226-C4")
FULL_YEARS = tuple(range(2019, 2026))
ROUNDTRIP_PRICE_EQUIV_USD_PER_OZ = 0.32
QUARTER_BOOT_REPS = 5000
QUARTER_BOOT_SEED = 311226
YEAR_BOOT_REPS = 5000
YEAR_BOOT_SEED = 311227
EXPECTED_8H_COUNTS = {"H226-C1": 913, "H226-C2": 696, "H226-C3": 851, "H226-C4": 639}


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


def complete_quarters() -> List[str]:
    out: List[str] = []
    for y in range(2018, 2027):
        for q in range(1, 5):
            s = f"{y}Q{q}"
            if "2018Q2" <= s <= "2026Q2":
                out.append(s)
    if len(out) != 33:
        raise RuntimeError("V3.11 quarter contract drift")
    return out


def _load_json(path: Path) -> Dict:
    with path.open("r", encoding="utf-8") as f:
        x = json.load(f)
    if not isinstance(x, dict):
        raise RuntimeError(f"Expected JSON object: {path}")
    return x


def load_frozen_events() -> tuple[pd.DataFrame, Dict]:
    if sha256_file(SRC_EVENTS) != V39_EVENTS_SHA256:
        raise RuntimeError("Frozen V3.9 event source SHA drift")
    prior = _load_json(SRC_V310_DECISION)
    if prior.get("mechanism_label") != "H226 DELAYED 8H REVERSION REGIME / DIRECTION DEPENDENT — STRATEGY DESIGN NOT AUTHORIZED":
        raise RuntimeError("V3.10 frozen conclusion drift")
    df = pd.read_csv(SRC_EVENTS)
    df = df[(df["horizon"].astype(str) == HORIZON) & (df["cohort"].isin(COHORTS))].copy()
    counts = df.groupby("cohort").size().to_dict()
    if counts != EXPECTED_8H_COUNTS:
        raise RuntimeError(f"Frozen 8h cohort counts drift: {counts}")
    required = {"cohort", "year", "quarter", "gap_direction", "atr_prev", "signed_reversion_return_atr"}
    missing = required - set(df.columns)
    if missing:
        raise RuntimeError(f"Frozen event columns missing: {sorted(missing)}")
    df["cost_hurdle_atr"] = ROUNDTRIP_PRICE_EQUIV_USD_PER_OZ / df["atr_prev"].astype(float)
    df["excess_reversion_atr"] = df["signed_reversion_return_atr"].astype(float) - df["cost_hurdle_atr"]
    return df, prior


def _summarize(sub: pd.DataFrame) -> Dict:
    x = sub["excess_reversion_atr"].astype(float).to_numpy()
    raw = sub["signed_reversion_return_atr"].astype(float).to_numpy()
    cost = sub["cost_hurdle_atr"].astype(float).to_numpy()
    if len(x) == 0:
        return {
            "event_count": 0,
            "mean_raw_reversion_atr": float("nan"),
            "mean_excess_reversion_atr": float("nan"),
            "median_excess_reversion_atr": float("nan"),
            "positive_excess_pct": float("nan"),
            "median_cost_hurdle_atr": float("nan"),
            "worst5pct_mean_excess_atr": float("nan"),
        }
    k = max(1, int(math.ceil(len(x) * 0.05)))
    return {
        "event_count": int(len(x)),
        "mean_raw_reversion_atr": float(np.mean(raw)),
        "mean_excess_reversion_atr": float(np.mean(x)),
        "median_excess_reversion_atr": float(np.median(x)),
        "positive_excess_pct": float(np.mean(x > 0) * 100.0),
        "median_cost_hurdle_atr": float(np.median(cost)),
        "worst5pct_mean_excess_atr": float(np.sort(x)[:k].mean()),
    }


def build_view_summary(df: pd.DataFrame) -> pd.DataFrame:
    rows: List[Dict] = []
    for cohort in COHORTS:
        base = df[df["cohort"] == cohort]
        views = {
            "FULL": base,
            "PRE_2025": base[base["quarter"].astype(str) <= "2024Q4"],
            "RECENT": base[base["quarter"].astype(str) >= "2025Q1"],
            "UP_GAP": base[base["gap_direction"] == "UP"],
            "DOWN_GAP": base[base["gap_direction"] == "DOWN"],
        }
        for name, sub in views.items():
            rows.append({"cohort": cohort, "view": name, **_summarize(sub)})
    return pd.DataFrame(rows)


def build_year_stability(df: pd.DataFrame) -> pd.DataFrame:
    rows: List[Dict] = []
    for cohort in COHORTS:
        base = df[df["cohort"] == cohort]
        for year in FULL_YEARS:
            sub = base[base["year"].astype(int) == year]
            s = _summarize(sub)
            rows.append({
                "cohort": cohort,
                "year": year,
                **s,
                "positive_mean_excess": bool(np.isfinite(s["mean_excess_reversion_atr"]) and s["mean_excess_reversion_atr"] > 0),
            })
    return pd.DataFrame(rows)


def build_quarter_stability(df: pd.DataFrame) -> pd.DataFrame:
    rows: List[Dict] = []
    for cohort in COHORTS:
        base = df[df["cohort"] == cohort]
        for quarter in complete_quarters():
            sub = base[base["quarter"].astype(str) == quarter]
            s = _summarize(sub)
            rows.append({
                "cohort": cohort,
                "quarter": quarter,
                **s,
                "positive_mean_excess": bool(np.isfinite(s["mean_excess_reversion_atr"]) and s["mean_excess_reversion_atr"] > 0),
            })
    return pd.DataFrame(rows)


def build_leave_one_year_out(df: pd.DataFrame) -> pd.DataFrame:
    rows: List[Dict] = []
    for cohort in COHORTS:
        base = df[df["cohort"] == cohort]
        for year in FULL_YEARS:
            sub = base[base["year"].astype(int) != year]
            s = _summarize(sub)
            rows.append({
                "cohort": cohort,
                "excluded_year": year,
                **s,
                "positive_mean_excess": bool(np.isfinite(s["mean_excess_reversion_atr"]) and s["mean_excess_reversion_atr"] > 0),
            })
    return pd.DataFrame(rows)


def _cluster_bootstrap(df: pd.DataFrame, unit_col: str, units: List, reps: int, seed: int, label: str) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows: List[Dict] = []
    for cohort in COHORTS:
        sub = df[df["cohort"] == cohort]
        blocks = {u: sub.loc[sub[unit_col] == u, "excess_reversion_atr"].astype(float).to_numpy() for u in units}
        draws: List[float] = []
        for _ in range(reps):
            sampled = rng.choice(units, size=len(units), replace=True)
            pieces = [blocks[u] for u in sampled if len(blocks[u])]
            if pieces:
                draws.append(float(np.mean(np.concatenate(pieces))))
        if not draws:
            lo = hi = ppos = float("nan")
        else:
            a = np.asarray(draws, dtype=float)
            lo = float(np.quantile(a, 0.025))
            hi = float(np.quantile(a, 0.975))
            ppos = float(np.mean(a > 0) * 100.0)
        rows.append({
            "cohort": cohort,
            "block_type": label,
            "bootstrap_reps_requested": reps,
            "bootstrap_reps_valid": len(draws),
            "seed": seed,
            "ci_2_5": lo,
            "ci_97_5": hi,
            "p_mean_excess_gt_zero_pct": ppos,
        })
    return pd.DataFrame(rows)


def build_bootstrap(df: pd.DataFrame) -> pd.DataFrame:
    q = _cluster_bootstrap(df, "quarter", complete_quarters(), QUARTER_BOOT_REPS, QUARTER_BOOT_SEED, "QUARTER")
    years = list(FULL_YEARS)
    ydf = df[df["year"].astype(int).isin(years)].copy()
    y = _cluster_bootstrap(ydf, "year", years, YEAR_BOOT_REPS, YEAR_BOOT_SEED, "YEAR")
    return pd.concat([q, y], ignore_index=True)


def make_decision(views: pd.DataFrame, years: pd.DataFrame, loo: pd.DataFrame, boot: pd.DataFrame) -> Dict:
    detail: Dict[str, Dict] = {}
    for cohort in COHORTS:
        v = views[views["cohort"] == cohort].set_index("view")
        y = years[years["cohort"] == cohort]
        l = loo[loo["cohort"] == cohort]
        b = boot[boot["cohort"] == cohort].set_index("block_type")
        checks = {
            "full_mean_excess_positive": bool(v.loc["FULL", "mean_excess_reversion_atr"] > 0),
            "full_median_excess_positive": bool(v.loc["FULL", "median_excess_reversion_atr"] > 0),
            "quarter_block_ci_lower_positive": bool(b.loc["QUARTER", "ci_2_5"] > 0),
            "year_block_ci_lower_positive": bool(b.loc["YEAR", "ci_2_5"] > 0),
            "pre2025_mean_excess_positive": bool(v.loc["PRE_2025", "mean_excess_reversion_atr"] > 0),
            "recent_mean_excess_positive": bool(v.loc["RECENT", "mean_excess_reversion_atr"] > 0),
            "up_gap_mean_excess_positive": bool(v.loc["UP_GAP", "mean_excess_reversion_atr"] > 0),
            "down_gap_mean_excess_positive": bool(v.loc["DOWN_GAP", "mean_excess_reversion_atr"] > 0),
            "at_least_5_of_7_positive_years": bool(int(y["positive_mean_excess"].sum()) >= 5),
            "all_leave_one_year_out_means_positive": bool(l["positive_mean_excess"].all()),
        }
        detail[cohort] = {
            "checks": checks,
            "all_broad_economic_checks_pass": bool(all(checks.values())),
            "positive_complete_years": int(y["positive_mean_excess"].sum()),
            "full": {
                "n": int(v.loc["FULL", "event_count"]),
                "mean_raw": float(v.loc["FULL", "mean_raw_reversion_atr"]),
                "mean_excess": float(v.loc["FULL", "mean_excess_reversion_atr"]),
                "median_excess": float(v.loc["FULL", "median_excess_reversion_atr"]),
            },
            "quarter_block_ci": [float(b.loc["QUARTER", "ci_2_5"]), float(b.loc["QUARTER", "ci_97_5"])],
            "year_block_ci": [float(b.loc["YEAR", "ci_2_5"]), float(b.loc["YEAR", "ci_97_5"])],
        }
    broad = all(detail[c]["all_broad_economic_checks_pass"] for c in DECISION_COHORTS)
    pooled_positive = all(detail[c]["full"]["mean_excess"] > 0 for c in DECISION_COHORTS)
    if broad:
        label = "H226 DELAYED 8H REVERSION BROADLY ECONOMICALLY MATERIAL — H226 STRATEGY CHAPTER CLOSED; FRESH OOS REQUIRED"
    elif pooled_positive:
        label = "H226 DELAYED 8H REVERSION ECONOMICALLY ASYMMETRIC / REGIME-CONCENTRATED — H226 STRATEGY CHAPTER CLOSED; FRESH OOS REQUIRED"
    else:
        label = "H226 DELAYED 8H REVERSION ECONOMICALLY IMMATERIAL — H226 CHAPTER CLOSED"
    return {
        "mechanism_label": label,
        "decision_cohorts_frozen": list(DECISION_COHORTS),
        "h226_strategy_status_remains": "REJECTED",
        "same_sample_h226_research_closed": True,
        "strategy_design_authorized": False,
        "fresh_oos_required_for_future_h226_inspired_strategy": True,
        "detail": detail,
    }


def run_audit() -> Dict:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    frozen_head = git_head()
    events, prior = load_frozen_events()
    views = build_view_summary(events)
    years = build_year_stability(events)
    quarters = build_quarter_stability(events)
    loo = build_leave_one_year_out(events)
    boot = build_bootstrap(events)
    decision = make_decision(views, years, loo, boot)

    views.to_csv(OUT_DIR / "v3_11_8h_economic_views.csv", index=False)
    years.to_csv(OUT_DIR / "v3_11_8h_economic_years.csv", index=False)
    quarters.to_csv(OUT_DIR / "v3_11_8h_economic_quarters.csv", index=False)
    loo.to_csv(OUT_DIR / "v3_11_8h_economic_leave_one_year_out.csv", index=False)
    boot.to_csv(OUT_DIR / "v3_11_8h_economic_cluster_bootstrap.csv", index=False)
    (OUT_DIR / "v3_11_8h_economic_decision.json").write_text(json.dumps(decision, indent=2) + "\n", encoding="utf-8")

    metadata = {
        "chapter": "V3.11 H226 ECONOMIC-MATERIALITY & ASYMMETRY CLOSURE",
        "artifact_generation_parent_sha": frozen_head,
        "scientific_parent_v310_final": V310_FINAL_SHA,
        "source_v39_events_sha256": V39_EVENTS_SHA256,
        "canonical_dataset_id": "GOLD_M30_CANONICAL_V2",
        "canonical_dataset_sha256": CANONICAL_SHA256,
        "horizon": HORIZON,
        "source_8h_counts": EXPECTED_8H_COUNTS,
        "roundtrip_price_equiv_usd_per_oz": ROUNDTRIP_PRICE_EQUIV_USD_PER_OZ,
        "quarter_bootstrap_reps": QUARTER_BOOT_REPS,
        "quarter_bootstrap_seed": QUARTER_BOOT_SEED,
        "year_bootstrap_reps": YEAR_BOOT_REPS,
        "year_bootstrap_seed": YEAR_BOOT_SEED,
        "raw_market_data_read": False,
        "events_reconstructed": False,
        "trading_engine_called": False,
        "strategy_executed": False,
        "strategy_design_authorized": False,
        "same_sample_h226_research_closed": True,
        "mechanism_label": decision["mechanism_label"],
    }
    (OUT_DIR / "v3_11_metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    return {"events": events, "views": views, "years": years, "quarters": quarters, "loo": loo, "bootstrap": boot, "decision": decision, "metadata": metadata}


if __name__ == "__main__":
    r = run_audit()
    print(json.dumps({
        "artifact_generation_parent_sha": r["metadata"]["artifact_generation_parent_sha"],
        "event_rows": int(len(r["events"])),
        "mechanism_label": r["decision"]["mechanism_label"],
        "strategy_executed": False,
    }, indent=2))
