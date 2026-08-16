"""V3.7.1.1 exact canonical reproduction with UTC epoch request boundaries.

This module deliberately reuses V3.7.1 normalization, structural validation,
coverage validation, source identity, serialization, and provenance machinery.
The only acquisition-semantic repair is the representation of copy_rates_range
boundaries: timezone-aware UTC datetimes are converted to Unix epoch seconds.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np

import export_v3_7_1_mt5_canonical_gold_m30 as v371

ROOT = v371.ROOT
UTC = v371.UTC

DATA_DIR = ROOT / "AlphaLab_Antigravity" / "data" / "canonical"
PROV_DIR = ROOT / "AlphaLab_Antigravity" / "data" / "provenance"
REPORT_DIR = ROOT / "AlphaLab_Antigravity" / "reports" / "v3_7_1_1"

CSV_PATH = DATA_DIR / "GOLD_M30_CANONICAL_V2.csv"
SIDECAR_PATH = PROV_DIR / "GOLD_M30_CANONICAL_V2.source.json"
MANIFEST_PATH = PROV_DIR / "GOLD_M30_CANONICAL_V2.manifest.json"
STRUCTURAL_PATH = REPORT_DIR / "GOLD_M30_CANONICAL_V2.structural_audit.json"
DECISION_PATH = REPORT_DIR / "V3_7_1_1_REPRODUCTION_DECISION.json"
EXPORTER_REPO_PATH = "AlphaLab_Antigravity/src/export_v3_7_1_1_mt5_canonical_gold_m30_v2.py"

V371_CSV = DATA_DIR / "GOLD_M30_CANONICAL.csv"
V371_FROZEN_SHA = "c48ca44dcecae9eb1c2590c586e27c4bc5f246215c549d0d0bc1201d95d5ea1d"


def _fetch_rates_range_epoch(symbol: str, start_utc: datetime, end_utc: datetime) -> Any:
    """Fetch M30 bars using unambiguous UTC Unix-second boundaries."""
    if start_utc.tzinfo is None or end_utc.tzinfo is None:
        raise ValueError("V3.7.1.1 requires timezone-aware UTC boundary inputs")
    start = start_utc.astimezone(UTC)
    end = end_utc.astimezone(UTC)
    if not start < end:
        raise ValueError("start_utc must be before end_utc")

    v371.mt5.symbol_select(symbol, True)
    chunks = []
    cur = start
    step_years = 2
    while cur < end:
        next_year_boundary = datetime(cur.year + step_years, 1, 1, tzinfo=UTC)
        nxt = min(next_year_boundary, end)
        date_from_epoch = int(cur.timestamp())
        date_to_epoch = int(nxt.timestamp())
        rates = v371.mt5.copy_rates_range(
            symbol,
            v371.mt5.TIMEFRAME_M30,
            date_from_epoch,
            date_to_epoch,
        )
        if rates is not None and len(rates):
            chunks.append(rates)
        cur = nxt

    if not chunks:
        raise RuntimeError(f"copy_rates_range returned no rates: {v371.mt5.last_error()}")

    all_rates = np.concatenate(chunks)
    _, unique_indices = np.unique(all_rates["time"], return_index=True)
    return all_rates[np.sort(unique_indices)]


def _patch_v371_output_contract() -> None:
    """Redirect reused V3.7.1 machinery to immutable V2 output paths."""
    v371.DATA_DIR = DATA_DIR
    v371.PROV_DIR = PROV_DIR
    v371.REPORT_DIR = REPORT_DIR
    v371.CSV_PATH = CSV_PATH
    v371.SIDECAR_PATH = SIDECAR_PATH
    v371.MANIFEST_PATH = MANIFEST_PATH
    v371.STRUCTURAL_PATH = STRUCTURAL_PATH
    v371.DECISION_PATH = DECISION_PATH
    v371.EXPORTER_REPO_PATH = EXPORTER_REPO_PATH
    v371._fetch_rates_range = _fetch_rates_range_epoch


def _postprocess_v2_metadata(result: Dict[str, Any]) -> Dict[str, Any]:
    sidecar = json.loads(SIDECAR_PATH.read_text(encoding="utf-8"))
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    decision = json.loads(DECISION_PATH.read_text(encoding="utf-8"))

    sidecar["dataset_id"] = "GOLD_M30_CANONICAL_V2"
    sidecar["request_boundary_representation"] = "UNIX_EPOCH_SECONDS_UTC"
    sidecar["request_boundary_semantic_repair"] = (
        "date_from/date_to passed to MetaTrader5.copy_rates_range as integer Unix epoch seconds "
        "derived from timezone-aware UTC datetimes; no timezone-naive datetime is used."
    )
    sidecar["prior_v3_7_1_dataset_sha256"] = V371_FROZEN_SHA
    sidecar["terminal_history_cap_explicit"] = sidecar.get("terminal_metadata_non_sensitive", {}).get("maxbars")
    chain = list(sidecar.get("transform_chain", []))
    if len(chain) >= 2:
        chain[1] = (
            f"MetaTrader5.copy_rates_range(symbol={sidecar.get('broker_symbol')}, timeframe=TIMEFRAME_M30, "
            "date_from/date_to=UTC Unix epoch seconds in two-year chunks)"
        )
    sidecar["transform_chain"] = chain

    manifest["dataset_id"] = "GOLD_M30_CANONICAL_V2"
    manifest["relative_path"] = str(CSV_PATH.relative_to(ROOT)).replace("\\", "/")
    manifest["request_boundary_representation"] = "UNIX_EPOCH_SECONDS_UTC"

    current_hash = manifest["sha256"]
    prior_file_hash = v371.sha256_file(V371_CSV) if V371_CSV.exists() else None
    byte_comparison = (
        "BYTE_IDENTICAL_TO_V3_7_1"
        if current_hash == V371_FROZEN_SHA and prior_file_hash == V371_FROZEN_SHA
        else "BYTE_DIFFERENT_FROM_V3_7_1"
    )

    decision["dataset_id"] = "GOLD_M30_CANONICAL_V2"
    decision["request_boundary_representation"] = "UNIX_EPOCH_SECONDS_UTC"
    decision["v3_7_1_frozen_sha256"] = V371_FROZEN_SHA
    decision["v3_7_1_file_sha256_at_reproduction"] = prior_file_hash
    decision["byte_concordance_with_v3_7_1"] = byte_comparison
    decision["canonical_v2_status"] = (
        "CANONICAL_V2_REPRODUCTION_ELIGIBLE"
        if decision.get("research_eligibility") == "ELIGIBLE"
        else "CANONICAL_V2_REPRODUCTION_BLOCKED"
    )

    SIDECAR_PATH.write_text(json.dumps(sidecar, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    DECISION_PATH.write_text(json.dumps(decision, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    result["decision"] = decision
    result["csv"] = str(CSV_PATH)
    result["sidecar"] = str(SIDECAR_PATH)
    result["manifest"] = str(MANIFEST_PATH)
    result["structural"] = str(STRUCTURAL_PATH)
    return result


def run_reproduction(symbol: str, terminal_path: Optional[str] = None) -> Dict[str, Any]:
    _patch_v371_output_contract()
    result = v371.run_export(symbol=symbol, terminal_path=terminal_path)
    return _postprocess_v2_metadata(result)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="V3.7.1.1 UTC-epoch canonical Gold M30 reproduction")
    p.add_argument("--symbol", required=True, help="Exact broker Gold symbol")
    p.add_argument("--terminal-path", default=None)
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    output = run_reproduction(args.symbol, args.terminal_path)
    print(json.dumps(output["decision"], indent=2, ensure_ascii=False))
