from __future__ import annotations

"""V3.12 blind fresh-OOS readiness audit.

This script never calculates post-signal returns. It only verifies the frozen
canonical cutoff, optional future OOS provenance/temporal partition, and C1/C4
eligibility-event counts needed to determine whether a later independent OOS
evaluation is mature enough to be designed/executed.
"""

from pathlib import Path
import json
import subprocess

import pandas as pd

from fresh_oos_v312_contract import (
    ACCRUING,
    BRIDGE_QUARTER,
    CANONICAL_FREEZE_CUTOFF,
    CANONICAL_SHA256,
    CANONICAL_V2,
    FIRST_DECISION_QUARTER,
    MIN_C1_EVENTS,
    MIN_C1_PER_QUARTER,
    MIN_C4_EVENTS,
    MIN_C4_PER_QUARTER,
    MIN_COMPLETE_QUARTERS,
    MATURE,
    OOS_CSV,
    OOS_SOURCE,
    WAITING,
    assess_maturity,
    count_readiness_events,
    normalize_bar_timestamps,
    validate_oos_temporal_partition,
    verify_frozen_canonical_cutoff,
    verify_oos_provenance,
)

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "AlphaLab_Antigravity" / "reports" / "v3_12"
READINESS_JSON = OUT_DIR / "V3_12_FRESH_OOS_READINESS.json"
COUNTS_CSV = OUT_DIR / "v3_12_fresh_oos_event_counts.csv"


def git_head() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        return "UNAVAILABLE"


def run_readiness_audit(as_of_utc: pd.Timestamp | None = None) -> dict:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    as_of = pd.Timestamp.now(tz="UTC") if as_of_utc is None else pd.Timestamp(as_of_utc)
    if as_of.tzinfo is None:
        raise RuntimeError("V3.12 as_of_utc must be timezone-aware")
    as_of = as_of.tz_convert("UTC")

    frozen_head = git_head()
    canonical = verify_frozen_canonical_cutoff()

    base = {
        "chapter": "V3.12 FRESH-OOS FORWARD LOCK",
        "artifact_generation_parent_sha": frozen_head,
        "scientific_parent_v311_final": "b821248667badea5e763173101c52ef95dbcf5d4",
        "canonical_dataset_id": "GOLD_M30_CANONICAL_V2",
        "canonical_dataset_sha256": CANONICAL_SHA256,
        "canonical_last_bar_open_utc": canonical["last_bar_open_utc"],
        "canonical_freeze_cutoff_utc": CANONICAL_FREEZE_CUTOFF.isoformat(),
        "bridge_quarter_quarantined": BRIDGE_QUARTER,
        "first_complete_fresh_oos_decision_quarter": FIRST_DECISION_QUARTER,
        "as_of_utc": as_of.isoformat(),
        "maturity_contract": {
            "minimum_complete_quarters": MIN_COMPLETE_QUARTERS,
            "minimum_c1_events": MIN_C1_EVENTS,
            "minimum_c4_events": MIN_C4_EVENTS,
            "minimum_c1_events_each_complete_quarter": MIN_C1_PER_QUARTER,
            "minimum_c4_events_each_complete_quarter": MIN_C4_PER_QUARTER,
        },
        "outcome_metrics_computed": False,
        "trading_engine_called": False,
        "strategy_executed": False,
        "strategy_design_authorized": False,
        "same_sample_h226_research_closed": True,
    }

    if not OOS_CSV.exists() and not OOS_SOURCE.exists():
        counts = pd.DataFrame(columns=["quarter", "c1_events", "c4_events"])
        maturity = assess_maturity(counts, as_of, has_fresh_bars=False)
        counts.to_csv(COUNTS_CSV, index=False)
        result = {
            **base,
            "fresh_oos_file_present": False,
            "fresh_oos_provenance_present": False,
            "fresh_oos_dataset_sha256": None,
            "fresh_oos_temporal_partition": None,
            "readiness": maturity.to_dict(),
            "final_status": WAITING,
        }
        READINESS_JSON.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        return result

    if not OOS_CSV.exists() or not OOS_SOURCE.exists():
        raise RuntimeError("Fresh-OOS data/provenance pair is incomplete; fail closed")

    provenance = verify_oos_provenance()
    oos_raw = pd.read_csv(OOS_CSV)
    temporal = validate_oos_temporal_partition(oos_raw)
    canonical_raw = pd.read_csv(CANONICAL_V2)
    counts = count_readiness_events(canonical_raw, oos_raw)
    counts.to_csv(COUNTS_CSV, index=False)
    maturity = assess_maturity(counts, as_of, has_fresh_bars=len(oos_raw) > 0)

    result = {
        **base,
        "fresh_oos_file_present": True,
        "fresh_oos_provenance_present": True,
        "fresh_oos_dataset_sha256": provenance["dataset_sha256"],
        "fresh_oos_temporal_partition": temporal,
        "readiness": maturity.to_dict(),
        "final_status": maturity.status,
    }
    READINESS_JSON.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    r = run_readiness_audit()
    print(json.dumps({
        "artifact_generation_parent_sha": r["artifact_generation_parent_sha"],
        "final_status": r["final_status"],
        "outcome_metrics_computed": r["outcome_metrics_computed"],
        "strategy_executed": r["strategy_executed"],
        "strategy_design_authorized": r["strategy_design_authorized"],
    }, indent=2))
