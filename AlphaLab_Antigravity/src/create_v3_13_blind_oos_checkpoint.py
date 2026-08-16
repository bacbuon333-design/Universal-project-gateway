from __future__ import annotations

"""V3.13 blind fresh-OOS checkpoint ledger.

Operational governance only. This module never evaluates post-signal outcomes.
It records immutable hash-chained snapshots of fresh-OOS provenance and V3.12
readiness counts.
"""

from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

import fresh_oos_v312_contract as v312

UTC = timezone.utc
ROOT = v312.ROOT
CHECKPOINT_DIR = ROOT / "AlphaLab_Antigravity" / "reports" / "v3_13" / "checkpoints"
V312_FINAL_SHA = "c1d7ba04aeb3b5bbc275a1a223c9d2bb5624a315"
CHECKPOINT_RE = re.compile(r"^(\d{6})_(\d{8}T\d{6}Z)\.json$")


def _json_load(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        obj = json.load(f)
    if not isinstance(obj, dict):
        raise RuntimeError(f"Checkpoint must be JSON object: {path}")
    return obj


def _checkpoint_files() -> List[Path]:
    if not CHECKPOINT_DIR.exists():
        return []
    out = []
    for p in CHECKPOINT_DIR.iterdir():
        if p.is_file() and p.suffix == ".json" and CHECKPOINT_RE.match(p.name):
            out.append(p)
    return sorted(out, key=lambda p: int(CHECKPOINT_RE.match(p.name).group(1)))


def _parse_created_at(obj: Dict[str, Any]) -> pd.Timestamp:
    ts = pd.Timestamp(obj.get("created_at_utc"))
    if ts.tzinfo is None:
        raise RuntimeError("Checkpoint created_at_utc must be timezone-aware")
    return ts.tz_convert("UTC")


def validate_checkpoint_chain(now_utc: Optional[datetime] = None) -> Dict[str, Any]:
    now = pd.Timestamp(now_utc or datetime.now(UTC)).tz_convert("UTC")
    files = _checkpoint_files()
    previous_path: Optional[Path] = None
    previous_sha: Optional[str] = None
    previous_created: Optional[pd.Timestamp] = None

    for expected_sequence, path in enumerate(files, start=1):
        m = CHECKPOINT_RE.match(path.name)
        if not m:
            raise RuntimeError(f"Invalid checkpoint filename: {path.name}")
        filename_sequence = int(m.group(1))
        if filename_sequence != expected_sequence:
            raise RuntimeError(
                f"Checkpoint sequence gap/duplicate: expected {expected_sequence}, got {filename_sequence}"
            )
        obj = _json_load(path)
        if int(obj.get("sequence", -1)) != expected_sequence:
            raise RuntimeError(f"Checkpoint payload sequence mismatch: {path.name}")
        created = _parse_created_at(obj)
        if created > now:
            raise RuntimeError(f"Checkpoint timestamp is in the future: {path.name}")
        if previous_created is not None and created <= previous_created:
            raise RuntimeError("Checkpoint created_at_utc must be strictly increasing")

        parent_name = obj.get("previous_checkpoint_filename")
        parent_sha = obj.get("previous_checkpoint_sha256")
        if expected_sequence == 1:
            if parent_name is not None or parent_sha is not None:
                raise RuntimeError("Genesis checkpoint must have null previous checkpoint pointer")
        else:
            if parent_name != previous_path.name:
                raise RuntimeError(f"Checkpoint parent filename mismatch: {path.name}")
            if parent_sha != previous_sha:
                raise RuntimeError(f"Checkpoint parent SHA mismatch: {path.name}")

        previous_path = path
        previous_sha = v312.sha256_file(path)
        previous_created = created

    return {
        "checkpoint_count": len(files),
        "latest_checkpoint_filename": previous_path.name if previous_path else None,
        "latest_checkpoint_sha256": previous_sha,
        "latest_checkpoint_created_at_utc": previous_created.isoformat() if previous_created is not None else None,
    }


def _load_current_oos_state() -> Tuple[Optional[pd.DataFrame], Dict[str, Any]]:
    csv_exists = v312.OOS_CSV.exists()
    source_exists = v312.OOS_SOURCE.exists()
    if csv_exists != source_exists:
        raise RuntimeError("Fresh-OOS data/provenance pair is incomplete")
    if not csv_exists:
        return None, {
            "fresh_oos_file_present": False,
            "fresh_oos_provenance_present": False,
            "fresh_oos_dataset_sha256": None,
            "fresh_oos_provenance_sha256": None,
            "fresh_oos_previous_dataset_sha256": None,
            "fresh_oos_row_count": 0,
            "fresh_oos_first_bar_open_utc": None,
            "fresh_oos_last_bar_open_utc": None,
            "bridge_quarantine_rows": 0,
        }

    verified = v312.verify_oos_provenance()
    df = pd.read_csv(v312.OOS_CSV)
    temporal = v312.validate_oos_temporal_partition(df)
    source = verified["source"]
    return df, {
        "fresh_oos_file_present": True,
        "fresh_oos_provenance_present": True,
        "fresh_oos_dataset_sha256": verified["dataset_sha256"],
        "fresh_oos_provenance_sha256": v312.sha256_file(v312.OOS_SOURCE),
        "fresh_oos_previous_dataset_sha256": source.get("previous_dataset_sha256"),
        "fresh_oos_row_count": int(temporal["row_count"]),
        "fresh_oos_first_bar_open_utc": temporal["first_bar_open_utc"],
        "fresh_oos_last_bar_open_utc": temporal["last_bar_open_utc"],
        "bridge_quarantine_rows": int(temporal["bridge_quarantine_rows"]),
    }


def _readiness_snapshot(oos_df: Optional[pd.DataFrame], as_of: pd.Timestamp) -> Tuple[pd.DataFrame, v312.MaturityAssessment]:
    if oos_df is None or oos_df.empty:
        counts = pd.DataFrame(columns=["quarter", "c1_events", "c4_events"])
        maturity = v312.assess_maturity(counts, as_of, has_fresh_bars=False)
        return counts, maturity

    canonical = pd.read_csv(v312.CANONICAL_V2)
    counts = v312.count_readiness_events(canonical, oos_df)
    maturity = v312.assess_maturity(counts, as_of, has_fresh_bars=True)
    return counts, maturity


def _checkpoint_filename(sequence: int, created: pd.Timestamp) -> str:
    stamp = created.strftime("%Y%m%dT%H%M%SZ")
    return f"{sequence:06d}_{stamp}.json"


def create_checkpoint(now_utc: Optional[datetime] = None) -> Dict[str, Any]:
    created = pd.Timestamp(now_utc or datetime.now(UTC))
    if created.tzinfo is None:
        raise RuntimeError("Checkpoint time must be timezone-aware")
    created = created.tz_convert("UTC")

    v312.verify_frozen_canonical_cutoff()
    chain = validate_checkpoint_chain(created.to_pydatetime())
    previous_count = int(chain["checkpoint_count"])
    sequence = previous_count + 1

    if chain["latest_checkpoint_created_at_utc"] is not None:
        prior_created = pd.Timestamp(chain["latest_checkpoint_created_at_utc"])
        if created <= prior_created:
            raise RuntimeError("New checkpoint time must be later than latest checkpoint")

    oos_df, oos_state = _load_current_oos_state()
    counts, maturity = _readiness_snapshot(oos_df, created)

    payload: Dict[str, Any] = {
        "chapter": "V3.13 BLIND OOS ACCRUAL LEDGER",
        "sequence": sequence,
        "created_at_utc": created.isoformat(),
        "scientific_parent_v312_final": V312_FINAL_SHA,
        "canonical_dataset_id": "GOLD_M30_CANONICAL_V2",
        "canonical_dataset_sha256": v312.CANONICAL_SHA256,
        "canonical_freeze_cutoff_utc": v312.CANONICAL_FREEZE_CUTOFF.isoformat(),
        "bridge_quarter_quarantined": v312.BRIDGE_QUARTER,
        "first_complete_fresh_oos_decision_quarter": v312.FIRST_DECISION_QUARTER,
        "previous_checkpoint_filename": chain["latest_checkpoint_filename"],
        "previous_checkpoint_sha256": chain["latest_checkpoint_sha256"],
        **oos_state,
        "readiness": maturity.to_dict(),
        "readiness_event_counts": counts.to_dict(orient="records"),
        "outcome_metrics_computed": False,
        "trading_engine_called": False,
        "strategy_executed": False,
        "strategy_design_authorized": False,
        "same_sample_h226_research_closed": True,
        "historical_h226_strategy_status": "REJECTED",
        "future_oos_outcome_evaluator_authorized": False,
    }

    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
    path = CHECKPOINT_DIR / _checkpoint_filename(sequence, created)
    if path.exists():
        raise FileExistsError(f"Checkpoint already exists: {path}")
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    checkpoint_sha = v312.sha256_file(path)

    # Revalidate the entire chain including the just-written checkpoint.
    post = validate_checkpoint_chain(created.to_pydatetime())
    if post["latest_checkpoint_filename"] != path.name or post["latest_checkpoint_sha256"] != checkpoint_sha:
        raise RuntimeError("Post-write checkpoint chain validation failed")

    return {
        "checkpoint_path": str(path.relative_to(ROOT)).replace("\\", "/"),
        "checkpoint_filename": path.name,
        "checkpoint_sha256": checkpoint_sha,
        "sequence": sequence,
        "readiness_status": maturity.status,
        "fresh_oos_file_present": bool(oos_state["fresh_oos_file_present"]),
        "fresh_oos_dataset_sha256": oos_state["fresh_oos_dataset_sha256"],
        "fresh_oos_row_count": int(oos_state["fresh_oos_row_count"]),
        "complete_decision_quarters": maturity.complete_decision_quarters,
        "c1_total": maturity.c1_total,
        "c4_total": maturity.c4_total,
    }


if __name__ == "__main__":
    print(json.dumps(create_checkpoint(), indent=2, ensure_ascii=False))
