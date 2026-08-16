"""V3.7.2 V2 engine-interface and legacy/canonical concordance audit.

No strategy or trading rule is executed here.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict
import json
import subprocess

import numpy as np
import pandas as pd

from canonical_v2_research_engine import (
    ROOT,
    FROZEN_SHA256,
    canonical_v2_engine_compatibility_snapshot,
    load_authorized_canonical_v2_dataframe,
)

LEGACY_CSV = ROOT / "AlphaLab_Antigravity" / "data" / "GOLD_M30.csv"
OUT_DIR = ROOT / "AlphaLab_Antigravity" / "reports" / "v3_7_2_v2"


def git_head() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        return "UNAVAILABLE"


def _match_view(canonical: pd.DataFrame, legacy: pd.DataFrame, shift_minutes: int) -> Dict[str, Any]:
    c = canonical.copy()
    c["match_label"] = c["canonical_label"] + pd.Timedelta(minutes=shift_minutes)
    merged = c.merge(legacy, left_on="match_label", right_on="legacy_label", how="inner", suffixes=("_can", "_leg"))
    out: Dict[str, Any] = {
        "shift_minutes_applied_to_canonical_label": shift_minutes,
        "overlap_rows": int(len(merged)),
    }
    if merged.empty:
        out["all_ohlc_exact_match_rate"] = None
        out["per_field"] = {}
        return out

    all_exact = np.ones(len(merged), dtype=bool)
    fields: Dict[str, Any] = {}
    for col in ("open", "high", "low", "close"):
        a = merged[f"{col}_can"].astype(float).to_numpy()
        b = merged[f"{col}_leg"].astype(float).to_numpy()
        exact = a == b
        all_exact &= exact
        fields[col] = {
            "exact_match_rate": float(exact.mean()),
            "max_abs_difference": float(np.max(np.abs(a - b))),
            "mean_abs_difference": float(np.mean(np.abs(a - b))),
        }
    out["all_ohlc_exact_match_rate"] = float(all_exact.mean())
    out["per_field"] = fields

    for col in ("tick_volume", "spread"):
        can = f"{col}_can"
        leg = f"{col}_leg"
        if can in merged.columns and leg in merged.columns:
            a = merged[can].to_numpy()
            b = merged[leg].to_numpy()
            out[f"{col}_exact_match_rate"] = float((a == b).mean())
    return out


def run_audit() -> Dict[str, Any]:
    canonical, auth = load_authorized_canonical_v2_dataframe()
    snapshot = canonical_v2_engine_compatibility_snapshot()

    canonical = canonical.copy()
    canonical["canonical_label"] = pd.to_datetime(canonical["timestamp_utc"], utc=True).dt.tz_convert("UTC").dt.tz_localize(None)

    if not LEGACY_CSV.exists():
        raise RuntimeError(f"Legacy comparison file missing: {LEGACY_CSV}")
    legacy = pd.read_csv(LEGACY_CSV)
    if "datetime_str" not in legacy.columns:
        raise RuntimeError("Legacy datetime_str column missing")
    legacy = legacy.copy()
    legacy["legacy_label"] = pd.to_datetime(legacy["datetime_str"], errors="raise")

    same = _match_view(canonical, legacy, 0)
    plus30 = _match_view(canonical, legacy, 30)
    minus30 = _match_view(canonical, legacy, -30)

    can_first = canonical["canonical_label"].min()
    can_last = canonical["canonical_label"].max()
    leg_first = legacy["legacy_label"].min()
    leg_last = legacy["legacy_label"].max()
    overlap_start = max(can_first, leg_first)
    overlap_end = min(can_last, leg_last)

    can_labels = set(canonical.loc[(canonical["canonical_label"] >= overlap_start) & (canonical["canonical_label"] <= overlap_end), "canonical_label"])
    leg_labels = set(legacy.loc[(legacy["legacy_label"] >= overlap_start) & (legacy["legacy_label"] <= overlap_end), "legacy_label"])

    concordance = {
        "purpose": "EMPIRICAL_CONCORDANCE_ONLY_NOT_LEGACY_PROVENANCE",
        "legacy_research_eligibility_remains": "BLOCKED",
        "canonical_v2_sha256": auth["dataset_sha256"],
        "canonical_v2_rows": int(len(canonical)),
        "legacy_rows": int(len(legacy)),
        "canonical_label_range": [str(can_first), str(can_last)],
        "legacy_label_range": [str(leg_first), str(leg_last)],
        "common_label_range": [str(overlap_start), str(overlap_end)],
        "canonical_labels_missing_in_legacy_within_common_range": int(len(can_labels - leg_labels)),
        "legacy_labels_missing_in_canonical_within_common_range": int(len(leg_labels - can_labels)),
        "same_label": same,
        "canonical_plus_30m_to_legacy": plus30,
        "canonical_minus_30m_to_legacy": minus30,
        "interpretation_guard": "Highest match view is descriptive only. It cannot establish or change legacy source lineage, timezone, or timestamp semantics.",
    }

    compatibility_checks = {
        "frozen_sha_match": snapshot["dataset_sha256"] == FROZEN_SHA256,
        "dataset_id_v2": snapshot["dataset_id"] == "GOLD_M30_CANONICAL_V2",
        "calendar_not_1970": snapshot["min_year"] == 2018 and snapshot["max_year"] == 2026,
        "first_timestamp_correct": snapshot["first_datetime"] == "2018-02-22T18:30:00+00:00",
        "last_timestamp_correct": snapshot["last_datetime"] == "2026-08-14T23:30:00+00:00",
        "timezone_utc": snapshot["timezone"] == "UTC",
        "has_2018Q2": snapshot["contains_2018Q2"],
        "has_2026Q2": snapshot["contains_2026Q2"],
        "gold_spec": snapshot["instrument_symbol"] == "GOLD" and snapshot["instrument_asset_class"] == "COMMODITY",
        "row_count_100000": snapshot["row_count"] == 100000,
        "request_boundary_epoch_utc": snapshot["request_boundary_representation"] == "UNIX_EPOCH_SECONDS_UTC",
        "data_authorized": snapshot["research_eligibility"] == "ELIGIBLE",
    }
    status = "CANONICAL_V2_ENGINE_COMPATIBILITY_PASS" if all(compatibility_checks.values()) else "CANONICAL_V2_ENGINE_COMPATIBILITY_BLOCKED"

    decision = {
        "status": status,
        "canonical_dataset_id": snapshot["dataset_id"],
        "canonical_dataset_sha256": snapshot["dataset_sha256"],
        "compatibility_checks": compatibility_checks,
        "strategy_executed": False,
        "legacy_status_changed": False,
        "git_head_at_execution": git_head(),
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "canonical_v2_engine_snapshot.json").write_text(json.dumps(snapshot, indent=2) + "\n", encoding="utf-8")
    (OUT_DIR / "legacy_canonical_v2_concordance.json").write_text(json.dumps(concordance, indent=2) + "\n", encoding="utf-8")
    (OUT_DIR / "V3_7_2_V2_ENGINE_COMPATIBILITY_DECISION.json").write_text(json.dumps(decision, indent=2) + "\n", encoding="utf-8")
    return {"snapshot": snapshot, "concordance": concordance, "decision": decision}


if __name__ == "__main__":
    result = run_audit()
    print(json.dumps(result["decision"], indent=2))
