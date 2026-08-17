from __future__ import annotations

"""Data audit, validation, and quarantine loader for ALAB-M1-FUSION-001R."""

import hashlib
from pathlib import Path
from typing import Any, Dict, Tuple
import numpy as np
import pandas as pd

MIN_REPLICATION_ROWS = 1_000_000
MIN_VALID_CALENDAR_YEARS = 3
DISCOVERY_CUTOFF_UTC = pd.Timestamp("2026-01-01T00:00:00Z")
DISCOVERY_KNOWN_SHA256 = "b980ac086f5de4ab60621d0ddcb3bac59d37ebd0bec236d24971f81918b1f3ec"


def compute_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def audit_and_load_m1_data(
    file_path: Path | str,
    symbol: str = "GOLD",
    quarantine_2026_discovery: bool = True,
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """Load, audit, and quarantine M1 data for replication inference."""
    path = Path(file_path).resolve()
    if not path.exists():
        raise FileNotFoundError(f"Data file not found: {path}")

    file_size = path.stat().st_size
    file_sha256 = compute_sha256(path)

    df_raw = pd.read_csv(path)
    required_cols = {"open", "high", "low", "close"}
    cols_present = set(df_raw.columns)

    if not required_cols.issubset(cols_present):
        missing = required_cols - cols_present
        raise ValueError(f"Missing required columns in {path}: {missing}")

    # Standardize datetime to UTC
    if "datetime" in df_raw.columns:
        dt_series = pd.to_datetime(df_raw["datetime"], utc=True)
    elif "datetime_str" in df_raw.columns:
        dt_series = pd.to_datetime(df_raw["datetime_str"], utc=True)
    elif "time" in df_raw.columns:
        dt_series = pd.to_datetime(df_raw["time"], unit="s", utc=True)
    else:
        raise ValueError("No datetime, datetime_str, or time column found.")

    df_all = pd.DataFrame()
    df_all["datetime"] = dt_series
    df_all["open"] = df_raw["open"].astype(float)
    df_all["high"] = df_raw["high"].astype(float)
    df_all["low"] = df_raw["low"].astype(float)
    df_all["close"] = df_raw["close"].astype(float)

    has_spread = "spread" in df_raw.columns
    if has_spread:
        df_all["spread"] = df_raw["spread"].astype(float)

    if "tick_volume" in df_raw.columns:
        df_all["tick_volume"] = df_raw["tick_volume"].astype(float)
    if "real_volume" in df_raw.columns:
        df_all["real_volume"] = df_raw["real_volume"].astype(float)

    # Sort if needed
    is_monotonic = df_all["datetime"].is_monotonic_increasing
    if not is_monotonic:
        df_all = df_all.sort_values("datetime").reset_index(drop=True)

    # Duplicates check
    dup_count = int(df_all["datetime"].duplicated().sum())
    if dup_count > 0:
        df_all = df_all.drop_duplicates(subset=["datetime"], keep="first").reset_index(drop=True)

    # Discovery sample quarantine
    total_raw_rows = len(df_all)
    if quarantine_2026_discovery:
        mask_pre_2026 = df_all["datetime"] < DISCOVERY_CUTOFF_UTC
        df_replication = df_all[mask_pre_2026].copy().reset_index(drop=True)
        quarantined_2026_rows = int((~mask_pre_2026).sum())
    else:
        df_replication = df_all.copy()
        quarantined_2026_rows = 0

    replication_rows = len(df_replication)
    start_dt = str(df_replication["datetime"].iloc[0]) if replication_rows > 0 else "NA"
    end_dt = str(df_replication["datetime"].iloc[-1]) if replication_rows > 0 else "NA"

    # Distinct calendar years in replication set
    if replication_rows > 0:
        unique_years = sorted(list(df_replication["datetime"].dt.year.unique()))
        unique_days = int(df_replication["datetime"].dt.date.nunique())
    else:
        unique_years = []
        unique_days = 0

    valid_calendar_years = len(unique_years)

    # Validity checks
    missing_ohlc = int(df_replication[["open", "high", "low", "close"]].isna().sum().sum()) if replication_rows > 0 else 0
    invalid_hl = int((df_replication["high"] < df_replication["low"]).sum()) if replication_rows > 0 else 0
    invalid_oc_high = int((df_replication["high"] < np.maximum(df_replication["open"], df_replication["close"])).sum()) if replication_rows > 0 else 0
    invalid_oc_low = int((df_replication["low"] > np.minimum(df_replication["open"], df_replication["close"])).sum()) if replication_rows > 0 else 0
    total_invalid = invalid_hl + invalid_oc_high + invalid_oc_low

    is_sufficient_history = replication_rows >= MIN_REPLICATION_ROWS
    is_sufficient_temporal = valid_calendar_years >= MIN_VALID_CALENDAR_YEARS

    audit_meta = {
        "source_path": str(path),
        "symbol": symbol,
        "timeframe": "M1",
        "total_source_rows": total_raw_rows,
        "replication_rows": replication_rows,
        "quarantined_2026_rows": quarantined_2026_rows,
        "start_datetime": start_dt,
        "end_datetime": end_dt,
        "unique_calendar_years": unique_years,
        "valid_calendar_years": valid_calendar_years,
        "unique_days": unique_days,
        "timezone": "UTC",
        "duplicate_timestamp_count": dup_count,
        "non_monotonic_timestamp_count": 0 if is_monotonic else 1,
        "missing_ohlc_count": missing_ohlc,
        "invalid_high_low_count": total_invalid,
        "data_hash_sha256": file_sha256,
        "file_size": file_size,
        "has_spread": has_spread,
        "is_sufficient_history": is_sufficient_history,
        "is_sufficient_temporal_coverage": is_sufficient_temporal,
        "discovery_cutoff_applied": str(DISCOVERY_CUTOFF_UTC),
        "discovery_overlap_count": 0 if quarantine_2026_discovery else quarantined_2026_rows,
    }

    return df_replication, audit_meta
