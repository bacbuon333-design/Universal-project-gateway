from __future__ import annotations

"""V3.12 fresh-OOS forward-lock contract.

This module contains no trading strategy and no forward-return evaluation.
It validates the temporal partition/provenance of future Gold M30 OOS data and
counts only frozen H226 C1/C4 *eligibility* events using information available
at the close of the first UTC-day bar.
"""

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, Iterable, List, Tuple
import hashlib
import json

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
CANONICAL_V2 = ROOT / "AlphaLab_Antigravity" / "data" / "canonical" / "GOLD_M30_CANONICAL_V2.csv"
OOS_CSV = ROOT / "AlphaLab_Antigravity" / "data" / "oos" / "GOLD_M30_FRESH_OOS.csv"
OOS_SOURCE = ROOT / "AlphaLab_Antigravity" / "data" / "oos" / "GOLD_M30_FRESH_OOS.source.json"

CANONICAL_SHA256 = "c48ca44dcecae9eb1c2590c586e27c4bc5f246215c549d0d0bc1201d95d5ea1d"
CANONICAL_FREEZE_CUTOFF = pd.Timestamp("2026-08-14T23:30:00Z")
FIRST_DECISION_QUARTER = "2026Q4"
BRIDGE_QUARTER = "2026Q3"

EXPECTED_BROKER_COMPANY = "XM Global Limited"
EXPECTED_BROKER_SERVER = "XMGlobal-MT5 9"
EXPECTED_BROKER_SYMBOL = "GOLD"
EXPECTED_TIMEFRAME = "M30"
EXPECTED_TIMESTAMP_SEMANTIC = "BAR_OPEN_TIME"
EXPECTED_TIMEZONE_STATUS = "EXPLICIT_UTC"
EXPECTED_TIMEZONE = "UTC"
EXPECTED_REQUEST_BOUNDARY = "UNIX_EPOCH_SECONDS_UTC"

MIN_COMPLETE_QUARTERS = 8
MIN_C1_EVENTS = 160
MIN_C4_EVENTS = 100
MIN_C1_PER_QUARTER = 10
MIN_C4_PER_QUARTER = 5

C1_GAP_Z = 0.05
C1_RESIDUAL = 0.25
C4_GAP_Z = 0.10
C4_RESIDUAL = 0.50

WAITING = "WAITING_FOR_FIRST_FRESH_OOS_BAR"
ACCRUING = "FRESH_OOS_ACCRUING_NOT_MATURE"
MATURE = "FRESH_OOS_MATURE_FOR_SEPARATELY_PRECOMMITTED_EVALUATION"


@dataclass(frozen=True)
class MaturityAssessment:
    status: str
    complete_decision_quarters: List[str]
    c1_total: int
    c4_total: int
    c1_min_per_complete_quarter: int
    c4_min_per_complete_quarter: int
    checks: Dict[str, bool]

    def to_dict(self) -> Dict:
        return asdict(self)


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


def normalize_bar_timestamps(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if "timestamp_utc" in out.columns:
        ts = pd.to_datetime(out["timestamp_utc"], utc=True, errors="raise")
    elif "time" in out.columns and pd.api.types.is_numeric_dtype(out["time"]):
        ts = pd.to_datetime(out["time"], unit="s", utc=True, errors="raise")
    else:
        raise RuntimeError("No canonical UTC timestamp column")
    out["datetime"] = ts
    out = out.sort_values("datetime").reset_index(drop=True)
    return out


def verify_frozen_canonical_cutoff(path: Path = CANONICAL_V2) -> Dict:
    if not path.exists():
        raise RuntimeError(f"Canonical V2 missing: {path}")
    actual_sha = sha256_file(path)
    if actual_sha != CANONICAL_SHA256:
        raise RuntimeError(f"Canonical V2 SHA drift: {actual_sha}")
    df = normalize_bar_timestamps(pd.read_csv(path))
    if df.empty:
        raise RuntimeError("Canonical V2 is empty")
    last_ts = df["datetime"].iloc[-1]
    if last_ts != CANONICAL_FREEZE_CUTOFF:
        raise RuntimeError(f"Canonical cutoff drift: {last_ts.isoformat()}")
    return {
        "dataset_sha256": actual_sha,
        "row_count": int(len(df)),
        "last_bar_open_utc": last_ts.isoformat(),
    }


def verify_oos_provenance(csv_path: Path = OOS_CSV, source_path: Path = OOS_SOURCE) -> Dict:
    if not csv_path.exists() or not source_path.exists():
        raise RuntimeError("Fresh-OOS data/provenance pair is incomplete")
    source = load_json(source_path)
    actual_sha = sha256_file(csv_path)
    required = {
        "dataset_id": source.get("dataset_id") == "GOLD_M30_FRESH_OOS",
        "sha": source.get("dataset_sha256") == actual_sha,
        "broker_company": source.get("broker_company") == EXPECTED_BROKER_COMPANY,
        "broker_server": source.get("broker_server") == EXPECTED_BROKER_SERVER,
        "broker_symbol": source.get("broker_symbol") == EXPECTED_BROKER_SYMBOL,
        "timeframe": source.get("timeframe") == EXPECTED_TIMEFRAME,
        "timestamp_semantic": source.get("timestamp_semantic") == EXPECTED_TIMESTAMP_SEMANTIC,
        "timezone_status": source.get("timestamp_timezone_status") == EXPECTED_TIMEZONE_STATUS,
        "timezone": source.get("timestamp_timezone") == EXPECTED_TIMEZONE,
        "request_boundary": source.get("request_boundary_representation") == EXPECTED_REQUEST_BOUNDARY,
        "freeze_cutoff": source.get("canonical_freeze_cutoff_utc") == CANONICAL_FREEZE_CUTOFF.isoformat(),
        "parent_sha": source.get("canonical_parent_sha256") == CANONICAL_SHA256,
    }
    failed = [k for k, ok in required.items() if not ok]
    if failed:
        raise RuntimeError("Fresh-OOS provenance blocked: " + ", ".join(failed))
    return {"dataset_sha256": actual_sha, "source": source}


def validate_oos_temporal_partition(df: pd.DataFrame) -> Dict:
    out = normalize_bar_timestamps(df)
    if out.empty:
        raise RuntimeError("Fresh-OOS CSV is empty")
    if out["datetime"].duplicated().any():
        raise RuntimeError("Fresh-OOS duplicate timestamps")
    if not out["datetime"].is_monotonic_increasing:
        raise RuntimeError("Fresh-OOS timestamps are not monotonic")
    first_ts = out["datetime"].iloc[0]
    if first_ts <= CANONICAL_FREEZE_CUTOFF:
        raise RuntimeError(
            f"Fresh-OOS overlap/backfill detected: first={first_ts.isoformat()} cutoff={CANONICAL_FREEZE_CUTOFF.isoformat()}"
        )
    bridge_rows = int((out["datetime"].dt.to_period("Q").astype(str) == BRIDGE_QUARTER).sum())
    return {
        "row_count": int(len(out)),
        "first_bar_open_utc": first_ts.isoformat(),
        "last_bar_open_utc": out["datetime"].iloc[-1].isoformat(),
        "bridge_quarantine_rows": bridge_rows,
    }


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


def _quarter_labels(ts: pd.Series) -> pd.Series:
    naive = ts.dt.tz_convert("UTC").dt.tz_localize(None)
    return naive.dt.to_period("Q").astype(str)


def count_readiness_events(canonical_df: pd.DataFrame, oos_df: pd.DataFrame) -> pd.DataFrame:
    """Count C1/C4 eligibility using no post-signal outcome information."""
    hist = normalize_bar_timestamps(canonical_df).tail(200).copy()
    fresh = normalize_bar_timestamps(oos_df).copy()
    if fresh.empty:
        return pd.DataFrame(columns=["quarter", "c1_events", "c4_events"])
    if fresh["datetime"].iloc[0] <= CANONICAL_FREEZE_CUTOFF:
        raise RuntimeError("OOS overlap/backfill detected before event counting")

    df = pd.concat([hist, fresh], ignore_index=True, sort=False)
    df = df.sort_values("datetime").drop_duplicates("datetime", keep="last").reset_index(drop=True)
    df["quarter"] = _quarter_labels(df["datetime"])
    a = atr14(df).to_numpy(dtype=float)
    dates = df["datetime"].dt.date.to_numpy()
    op = df["open"].astype(float).to_numpy()
    cl = df["close"].astype(float).to_numpy()

    counts: Dict[str, List[int]] = {}
    for i in range(1, len(df)):
        ts = df.loc[i, "datetime"]
        if ts <= CANONICAL_FREEZE_CUTOFF:
            continue
        if dates[i] == dates[i - 1]:
            continue
        q = str(df.loc[i, "quarter"])
        if q < FIRST_DECISION_QUARTER:
            continue  # bridge/quarantine only
        atr_prev = a[i - 1]
        if not np.isfinite(atr_prev) or atr_prev <= 0:
            continue
        prev_close = cl[i - 1]
        gap = op[i] - prev_close
        if not np.isfinite(gap) or abs(gap) <= 1e-12:
            continue
        crossed = bool((gap > 0 and cl[i] <= prev_close) or (gap < 0 and cl[i] >= prev_close))
        if crossed:
            continue
        gap_z = abs(gap) / atr_prev
        residual = abs(cl[i] - prev_close) / abs(gap)
        c1 = int(gap_z >= C1_GAP_Z and residual >= C1_RESIDUAL)
        c4 = int(gap_z >= C4_GAP_Z and residual >= C4_RESIDUAL)
        if q not in counts:
            counts[q] = [0, 0]
        counts[q][0] += c1
        counts[q][1] += c4

    rows = [
        {"quarter": q, "c1_events": v[0], "c4_events": v[1]}
        for q, v in sorted(counts.items())
    ]
    return pd.DataFrame(rows, columns=["quarter", "c1_events", "c4_events"])


def complete_decision_quarters(as_of_utc: pd.Timestamp) -> List[str]:
    ts = pd.Timestamp(as_of_utc)
    if ts.tzinfo is None:
        raise RuntimeError("as_of_utc must be timezone-aware")
    ts = ts.tz_convert("UTC")
    first = pd.Period(FIRST_DECISION_QUARTER, freq="Q")
    current = ts.tz_localize(None).to_period("Q")
    last_complete = current - 1
    if last_complete < first:
        return []
    return [str(p) for p in pd.period_range(first, last_complete, freq="Q")]


def assess_maturity(counts: pd.DataFrame, as_of_utc: pd.Timestamp, has_fresh_bars: bool) -> MaturityAssessment:
    if not has_fresh_bars:
        return MaturityAssessment(
            status=WAITING,
            complete_decision_quarters=[],
            c1_total=0,
            c4_total=0,
            c1_min_per_complete_quarter=0,
            c4_min_per_complete_quarter=0,
            checks={
                "eight_complete_quarters": False,
                "c1_total_min": False,
                "c4_total_min": False,
                "c1_each_quarter_min": False,
                "c4_each_quarter_min": False,
            },
        )

    complete = complete_decision_quarters(as_of_utc)
    idx = counts.set_index("quarter") if len(counts) else pd.DataFrame(columns=["c1_events", "c4_events"])
    c1_by_q = [int(idx.loc[q, "c1_events"]) if q in idx.index else 0 for q in complete]
    c4_by_q = [int(idx.loc[q, "c4_events"]) if q in idx.index else 0 for q in complete]
    c1_total = int(sum(c1_by_q))
    c4_total = int(sum(c4_by_q))
    c1_min = min(c1_by_q) if c1_by_q else 0
    c4_min = min(c4_by_q) if c4_by_q else 0
    checks = {
        "eight_complete_quarters": len(complete) >= MIN_COMPLETE_QUARTERS,
        "c1_total_min": c1_total >= MIN_C1_EVENTS,
        "c4_total_min": c4_total >= MIN_C4_EVENTS,
        "c1_each_quarter_min": bool(complete) and c1_min >= MIN_C1_PER_QUARTER,
        "c4_each_quarter_min": bool(complete) and c4_min >= MIN_C4_PER_QUARTER,
    }
    status = MATURE if all(checks.values()) else ACCRUING
    return MaturityAssessment(
        status=status,
        complete_decision_quarters=complete,
        c1_total=c1_total,
        c4_total=c4_total,
        c1_min_per_complete_quarter=c1_min,
        c4_min_per_complete_quarter=c4_min,
        checks=checks,
    )


def forbidden_outcome_tokens() -> Tuple[str, ...]:
    return (
        "signed_reversion_return_atr",
        "excess_reversion_atr",
        "mfe_atr",
        "mae_atr",
        "gap_closed_by_horizon",
        "profit_factor",
        "expectancy",
    )
