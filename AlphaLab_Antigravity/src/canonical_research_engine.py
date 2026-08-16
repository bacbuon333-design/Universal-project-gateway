"""V3.7.2 canonical research-data authorization and engine adapter.

This module contains no strategy logic. It exists to make the V3.7.1 canonical
Gold M30 dataset safe to consume without reintroducing timestamp ambiguity.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Tuple
import hashlib
import json

import pandas as pd

from deep_quant_engine import DeepQuantEngine, STANDARD_SPECS

ROOT = Path(__file__).resolve().parents[2]
CANONICAL_CSV = ROOT / "AlphaLab_Antigravity" / "data" / "canonical" / "GOLD_M30_CANONICAL.csv"
SOURCE_JSON = ROOT / "AlphaLab_Antigravity" / "data" / "provenance" / "GOLD_M30_CANONICAL.source.json"
MANIFEST_JSON = ROOT / "AlphaLab_Antigravity" / "data" / "provenance" / "GOLD_M30_CANONICAL.manifest.json"
DECISION_JSON = ROOT / "AlphaLab_Antigravity" / "reports" / "v3_7_1" / "V3_7_1_REEXPORT_DECISION.json"
FROZEN_SHA256 = "c48ca44dcecae9eb1c2590c586e27c4bc5f246215c549d0d0bc1201d95d5ea1d"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        obj = json.load(f)
    if not isinstance(obj, dict):
        raise RuntimeError(f"Expected JSON object: {path}")
    return obj


def verify_canonical_authorization(
    csv_path: Path = CANONICAL_CSV,
    source_path: Path = SOURCE_JSON,
    manifest_path: Path = MANIFEST_JSON,
    decision_path: Path = DECISION_JSON,
    expected_sha256: str = FROZEN_SHA256,
) -> Dict[str, Any]:
    for p in (csv_path, source_path, manifest_path, decision_path):
        if not p.exists():
            raise RuntimeError(f"Canonical authorization artifact missing: {p}")

    actual_sha = sha256_file(csv_path)
    source = load_json(source_path)
    manifest = load_json(manifest_path)
    decision = load_json(decision_path)

    hashes = {
        "expected": expected_sha256,
        "actual": actual_sha,
        "source": source.get("dataset_sha256"),
        "manifest": manifest.get("sha256"),
        "decision": decision.get("dataset_sha256"),
    }
    if len(set(hashes.values())) != 1:
        raise RuntimeError(f"Canonical SHA mismatch: {hashes}")

    required = {
        "source.timestamp_semantic": source.get("timestamp_semantic") == "BAR_OPEN_TIME",
        "source.timezone_status": source.get("timestamp_timezone_status") == "EXPLICIT_UTC",
        "source.timezone": source.get("timestamp_timezone") == "UTC",
        "manifest.timestamp_semantic": manifest.get("timestamp_semantic") == "BAR_OPEN_TIME",
        "manifest.timezone_status": manifest.get("timestamp_timezone_status") == "EXPLICIT_UTC",
        "manifest.lineage": manifest.get("lineage_status") == "VERIFIED",
        "manifest.structural": manifest.get("structural_validation_status") == "PASS",
        "manifest.coverage": manifest.get("coverage_status") == "PASS",
        "manifest.eligibility": manifest.get("research_eligibility") == "ELIGIBLE",
        "decision.lineage": decision.get("lineage_status") == "VERIFIED",
        "decision.structural": decision.get("structural_validation_status") == "PASS",
        "decision.coverage": decision.get("coverage_status") == "PASS",
        "decision.eligibility": decision.get("research_eligibility") == "ELIGIBLE",
        "decision.no_blockers": not decision.get("blocking_reasons"),
    }
    failed = [k for k, ok in required.items() if not ok]
    if failed:
        raise RuntimeError("Canonical authorization blocked: " + ", ".join(failed))

    return {
        "dataset_sha256": actual_sha,
        "timestamp_semantic": "BAR_OPEN_TIME",
        "timestamp_timezone_status": "EXPLICIT_UTC",
        "timestamp_timezone": "UTC",
        "lineage_status": "VERIFIED",
        "research_eligibility": "ELIGIBLE",
        "broker_symbol": source.get("broker_symbol"),
        "broker_company": source.get("broker_company"),
        "broker_server": source.get("broker_server"),
    }


def load_authorized_canonical_dataframe() -> Tuple[pd.DataFrame, Dict[str, Any]]:
    auth = verify_canonical_authorization()
    df = pd.read_csv(CANONICAL_CSV)
    if "timestamp_utc" not in df.columns:
        raise RuntimeError("Canonical timestamp_utc column missing")
    ts = pd.to_datetime(df["timestamp_utc"], utc=True, errors="raise")
    if ts.isna().any():
        raise RuntimeError("Canonical timestamp parse produced NaT")
    df["timestamp_utc"] = ts
    return df, auth


class CanonicalDeepQuantEngine(DeepQuantEngine):
    """DeepQuantEngine adapter restricted to authorized canonical data.

    It overrides only DataFrame timestamp preparation. Execution behavior is
    inherited unchanged from the audited DeepQuantEngine.
    """

    def __init__(self):
        df, auth = load_authorized_canonical_dataframe()
        self.canonical_authorization = auth
        super().__init__(data_file="GOLD_M30_CANONICAL.csv", df=df, spec=STANDARD_SPECS["GOLD"])
        self.resolved_path = str(CANONICAL_CSV)

    def _prepare_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        if "timestamp_utc" in df.columns:
            dt = pd.to_datetime(df["timestamp_utc"], utc=True, errors="raise")
        elif "datetime_str" in df.columns:
            # Legacy-style DataFrames retain their textual interpretation when
            # explicitly supplied to this method in tests; canonical research
            # itself requires timestamp_utc via the authorization loader.
            dt = pd.to_datetime(df["datetime_str"], errors="raise")
        elif "time" in df.columns and pd.api.types.is_numeric_dtype(df["time"]):
            dt = pd.to_datetime(df["time"], unit="s", utc=True, errors="raise")
        else:
            raise RuntimeError("No supported timestamp column for canonical engine adapter")

        df = df.copy()
        df["datetime"] = dt
        df = df.sort_values("datetime").reset_index(drop=True)
        df["year"] = df["datetime"].dt.year
        # Convert through timezone-naive UTC only for pandas Period labels; the
        # authoritative datetime column remains timezone-aware UTC.
        period_source = df["datetime"].dt.tz_convert("UTC").dt.tz_localize(None) if getattr(df["datetime"].dt, "tz", None) is not None else df["datetime"]
        df["quarter"] = period_source.dt.to_period("Q").astype(str)
        for col in ("open", "high", "low", "close"):
            if col in df.columns:
                df[col] = df[col].astype(float)
        return df


def canonical_engine_compatibility_snapshot() -> Dict[str, Any]:
    eng = CanonicalDeepQuantEngine()
    dt = eng.df["datetime"]
    quarters = set(eng.df["quarter"].astype(str))
    return {
        "dataset_sha256": eng.canonical_authorization["dataset_sha256"],
        "row_count": int(len(eng.df)),
        "first_datetime": dt.iloc[0].isoformat(),
        "last_datetime": dt.iloc[-1].isoformat(),
        "timezone": str(dt.dt.tz),
        "min_year": int(dt.dt.year.min()),
        "max_year": int(dt.dt.year.max()),
        "contains_2018Q2": "2018Q2" in quarters,
        "contains_2026Q2": "2026Q2" in quarters,
        "instrument_symbol": eng.spec.symbol,
        "instrument_asset_class": eng.spec.asset_class,
        "timestamp_semantic": eng.canonical_authorization["timestamp_semantic"],
        "research_eligibility": eng.canonical_authorization["research_eligibility"],
    }


if __name__ == "__main__":
    print(json.dumps(canonical_engine_compatibility_snapshot(), indent=2))
