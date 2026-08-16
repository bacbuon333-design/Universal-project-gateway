"""V3.7 canonical-data auditor for GOLD_M30.csv.

Reads data and optional explicit provenance sidecar, computes structural facts,
and fails closed when lineage/time semantics are unresolved. No strategy logic.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional
import json
import subprocess
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DATA_CANDIDATES = [
    ROOT / "AlphaLab_Antigravity" / "data" / "GOLD_M30.csv",
    ROOT / "AlphaLab_Antigravity" / "GOLD_M30.csv",
    ROOT / "GOLD_M30.csv",
]
PROVENANCE_PATH = ROOT / "AlphaLab_Antigravity" / "data" / "provenance" / "GOLD_M30.source.json"
OUT_DIR = ROOT / "AlphaLab_Antigravity" / "reports" / "v3_7"

sys.path.insert(0, str(Path(__file__).resolve().parent))
from canonical_data_contract import (  # noqa: E402
    CanonicalManifest,
    LineageStatus,
    TimestampSemantic,
    TimezoneStatus,
    decide_research_eligibility,
    load_json,
    sha256_file,
    validate_provenance_sidecar,
)


def git_head() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, stderr=subprocess.DEVNULL
        ).strip()
    except Exception:
        return "UNKNOWN_GIT_SHA"


def locate_dataset() -> Path:
    for p in DATA_CANDIDATES:
        if p.exists():
            return p
    raise FileNotFoundError("GOLD_M30.csv not found in canonical candidate paths")


def timestamp_column(df: pd.DataFrame) -> Optional[str]:
    for c in ("datetime_str", "datetime", "timestamp", "time"):
        if c in df.columns:
            return c
    return None


def analyze_structure(path: Path, expected_minutes: float = 30.0) -> Dict[str, Any]:
    df = pd.read_csv(path)
    cols = [str(c) for c in df.columns]
    tcol = timestamp_column(df)

    structural_problems: List[str] = []
    first_ts: Optional[str] = None
    last_ts: Optional[str] = None
    median_delta: Optional[float] = None
    pct_expected: Optional[float] = None
    duplicate_count = 0
    non_monotonic_count = 0
    parse_status = "NO_TIMESTAMP_COLUMN"
    data_timezone_status = TimezoneStatus.NAIVE_UNRESOLVED.value
    data_timezone = "UNRESOLVED"

    if tcol is None:
        structural_problems.append("TIMESTAMP_COLUMN_MISSING")
    else:
        parsed = pd.to_datetime(df[tcol], errors="coerce")
        bad = int(parsed.isna().sum())
        if bad:
            parse_status = f"FAIL:{bad}_UNPARSEABLE"
            structural_problems.append("TIMESTAMP_PARSE_FAILURE")
        else:
            parse_status = "PASS"
            first_ts = str(parsed.iloc[0])
            last_ts = str(parsed.iloc[-1])
            duplicate_count = int(parsed.duplicated().sum())
            delta_seconds = parsed.diff().dt.total_seconds()
            non_monotonic_count = int((delta_seconds.dropna() <= 0).sum())
            positive_minutes = delta_seconds.dropna()
            positive_minutes = positive_minutes[positive_minutes > 0] / 60.0
            if len(positive_minutes):
                median_delta = float(positive_minutes.median())
                pct_expected = float(
                    np.mean(np.isclose(positive_minutes.to_numpy(), expected_minutes)) * 100.0
                )
            if duplicate_count:
                structural_problems.append("DUPLICATE_TIMESTAMPS")
            if non_monotonic_count:
                structural_problems.append("NON_MONOTONIC_TIMESTAMPS")

            try:
                tz = parsed.dt.tz
            except Exception:
                tz = None
            if tz is not None:
                tz_name = str(tz)
                data_timezone = tz_name
                if tz_name.upper() in {"UTC", "UTC+00:00", "+00:00"}:
                    data_timezone_status = TimezoneStatus.EXPLICIT_UTC.value
                else:
                    data_timezone_status = TimezoneStatus.EXPLICIT_OFFSET.value

    required_ohlc = ["open", "high", "low", "close"]
    lower_map = {str(c).lower(): c for c in df.columns}
    ohlc_violation_count = 0
    ohlc_details: Dict[str, int] = {}
    if not all(k in lower_map for k in required_ohlc):
        structural_problems.append("OHLC_COLUMNS_MISSING")
        ohlc_violation_count = -1
    else:
        o = pd.to_numeric(df[lower_map["open"]], errors="coerce")
        h = pd.to_numeric(df[lower_map["high"]], errors="coerce")
        l = pd.to_numeric(df[lower_map["low"]], errors="coerce")
        c = pd.to_numeric(df[lower_map["close"]], errors="coerce")
        null_ohlc = int(pd.concat([o, h, l, c], axis=1).isna().any(axis=1).sum())
        high_low = int((h < l).fillna(False).sum())
        high_body = int((h < pd.concat([o, c], axis=1).max(axis=1)).fillna(False).sum())
        low_body = int((l > pd.concat([o, c], axis=1).min(axis=1)).fillna(False).sum())
        ohlc_details = {
            "null_ohlc_rows": null_ohlc,
            "high_below_low_rows": high_low,
            "high_below_open_or_close_rows": high_body,
            "low_above_open_or_close_rows": low_body,
        }
        ohlc_violation_count = null_ohlc + high_low + high_body + low_body
        if ohlc_violation_count:
            structural_problems.append("OHLC_CONSISTENCY_FAILURE")

    structural_status = "PASS" if not structural_problems else "FAIL"
    return {
        "row_count": int(len(df)),
        "columns": cols,
        "timestamp_column": tcol,
        "timestamp_parse_status": parse_status,
        "first_timestamp": first_ts,
        "last_timestamp": last_ts,
        "timestamp_timezone_status_from_csv": data_timezone_status,
        "timestamp_timezone_from_csv": data_timezone,
        "median_delta_minutes": median_delta,
        "pct_expected_cadence": pct_expected,
        "duplicate_timestamp_count": duplicate_count,
        "non_monotonic_timestamp_count": non_monotonic_count,
        "ohlc_violation_count": ohlc_violation_count,
        "ohlc_details": ohlc_details,
        "structural_validation_status": structural_status,
        "structural_problems": structural_problems,
    }


def unresolved_provenance() -> Dict[str, Any]:
    return {
        "lineage_status": LineageStatus.UNRESOLVED.value,
        "hash_match": False,
        "timestamp_semantic": TimestampSemantic.UNRESOLVED.value,
        "timestamp_timezone_status": TimezoneStatus.NAIVE_UNRESOLVED.value,
        "timestamp_timezone": "UNRESOLVED",
        "source_type": "UNRESOLVED",
        "source_identifier": "UNRESOLVED",
        "exporter_or_extraction_method": "UNRESOLVED",
        "exporter_path": "UNRESOLVED",
        "transform_chain": [],
        "problems": ["PROVENANCE_SIDECAR_NOT_FOUND"],
    }


def run_audit() -> Dict[str, Any]:
    path = locate_dataset()
    actual_hash = sha256_file(path)
    structural = analyze_structure(path)

    if PROVENANCE_PATH.exists():
        sidecar = load_json(PROVENANCE_PATH)
        provenance = validate_provenance_sidecar(sidecar, actual_hash)
        provenance_source = str(PROVENANCE_PATH.relative_to(ROOT))
    else:
        provenance = unresolved_provenance()
        provenance_source = "NONE"

    if provenance["lineage_status"] == LineageStatus.VERIFIED.value:
        tz_status = provenance["timestamp_timezone_status"]
        tz_name = provenance["timestamp_timezone"]
        semantic = provenance["timestamp_semantic"]
    else:
        tz_status = structural["timestamp_timezone_status_from_csv"]
        tz_name = structural["timestamp_timezone_from_csv"]
        semantic = TimestampSemantic.UNRESOLVED.value

    eligibility = decide_research_eligibility(
        structural_validation_status=structural["structural_validation_status"],
        timestamp_semantic=semantic,
        timestamp_timezone_status=tz_status,
        lineage_status=provenance["lineage_status"],
        source_type=provenance["source_type"],
        source_identifier=provenance["source_identifier"],
        exporter_or_extraction_method=provenance["exporter_or_extraction_method"],
        transform_chain=provenance["transform_chain"],
    )

    all_blockers = list(eligibility["blocking_reasons"])
    for p in provenance.get("problems", []):
        marker = f"PROVENANCE:{p}"
        if marker not in all_blockers:
            all_blockers.append(marker)

    manifest = CanonicalManifest(
        dataset_id="GOLD_M30",
        relative_path=str(path.relative_to(ROOT)).replace("\\", "/"),
        sha256=actual_hash,
        size_bytes=int(path.stat().st_size),
        row_count=structural["row_count"],
        columns=structural["columns"],
        first_timestamp=structural["first_timestamp"],
        last_timestamp=structural["last_timestamp"],
        timestamp_column=structural["timestamp_column"],
        timestamp_parse_status=structural["timestamp_parse_status"],
        timestamp_timezone_status=tz_status,
        timestamp_timezone=tz_name,
        timestamp_semantic=semantic,
        timeframe="M30",
        median_delta_minutes=structural["median_delta_minutes"],
        pct_expected_cadence=structural["pct_expected_cadence"],
        duplicate_timestamp_count=structural["duplicate_timestamp_count"],
        non_monotonic_timestamp_count=structural["non_monotonic_timestamp_count"],
        ohlc_violation_count=structural["ohlc_violation_count"],
        source_type=provenance["source_type"],
        source_identifier=provenance["source_identifier"],
        exporter_or_extraction_method=provenance["exporter_or_extraction_method"],
        exporter_path=provenance["exporter_path"],
        transform_chain=provenance["transform_chain"],
        lineage_status=provenance["lineage_status"],
        structural_validation_status=structural["structural_validation_status"],
        research_eligibility=eligibility["research_eligibility"],
        blocking_reasons=all_blockers,
    )

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest_path = OUT_DIR / "GOLD_M30.canonical_manifest.json"
    structural_path = OUT_DIR / "GOLD_M30.structural_audit.json"
    decision_path = OUT_DIR / "V3_7_DATA_ELIGIBILITY_DECISION.json"
    report_path = ROOT / "V3_7_CANONICAL_DATA_AUDIT_REPORT.md"

    manifest_obj = manifest.to_dict()
    manifest_obj["provenance_sidecar"] = provenance_source
    manifest_obj["git_head_at_execution"] = git_head()

    structural_obj = {
        "dataset_id": "GOLD_M30",
        "actual_sha256": actual_hash,
        **structural,
    }
    decision_obj = {
        "dataset_id": "GOLD_M30",
        "research_eligibility": manifest.research_eligibility,
        "blocking_reasons": manifest.blocking_reasons,
        "lineage_status": manifest.lineage_status,
        "timestamp_semantic": manifest.timestamp_semantic,
        "timestamp_timezone_status": manifest.timestamp_timezone_status,
        "structural_validation_status": manifest.structural_validation_status,
        "fail_closed": True,
        "git_head_at_execution": git_head(),
    }

    for out_path, obj in (
        (manifest_path, manifest_obj),
        (structural_path, structural_obj),
        (decision_path, decision_obj),
    ):
        out_path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    blockers_md = "\n".join(f"- `{x}`" for x in manifest.blocking_reasons) or "- None"
    report = "# V3.7 CANONICAL DATA AUDIT REPORT\n\n"
    report += f"- Dataset: `GOLD_M30`\n- SHA-256: `{actual_hash}`\n"
    report += f"- Rows: `{manifest.row_count}`\n- Structural validation: `{manifest.structural_validation_status}`\n"
    report += f"- Lineage: `{manifest.lineage_status}`\n- Timestamp semantic: `{manifest.timestamp_semantic}`\n"
    report += f"- Timezone status: `{manifest.timestamp_timezone_status}`\n- Research eligibility: **`{manifest.research_eligibility}`**\n\n"
    report += "## Blocking reasons\n\n" + blockers_md + "\n\n"
    report += "## Governance interpretation\n\n"
    report += (
        "Structural integrity is not provenance. M30 cadence does not prove "
        "bar-open/bar-close semantics, and naive timestamps are not promoted "
        "to UTC without exact-hash source evidence.\n"
    )
    report_path.write_text(report, encoding="utf-8")

    return {
        "manifest": manifest_obj,
        "structural": structural_obj,
        "decision": decision_obj,
        "outputs": [str(manifest_path), str(structural_path), str(decision_path), str(report_path)],
    }


if __name__ == "__main__":
    result = run_audit()
    print(json.dumps(result["decision"], indent=2, ensure_ascii=False))
