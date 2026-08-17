from __future__ import annotations

"""Data audit and loader for ALAB-M1-FUSION-001."""

import hashlib
from pathlib import Path
from typing import Any, Dict, Tuple
import numpy as np
import pandas as pd


def compute_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def audit_and_load_m1_data(
    file_path: Path | str,
    symbol: str = "GOLD",
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
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

    # Standardize datetime
    if "datetime" in df_raw.columns:
        dt_series = pd.to_datetime(df_raw["datetime"], utc=True)
    elif "datetime_str" in df_raw.columns:
        dt_series = pd.to_datetime(df_raw["datetime_str"], utc=True)
    elif "time" in df_raw.columns:
        dt_series = pd.to_datetime(df_raw["time"], unit="s", utc=True)
    else:
        raise ValueError("No datetime, datetime_str, or time column found.")

    df = pd.DataFrame()
    df["datetime"] = dt_series
    df["open"] = df_raw["open"].astype(float)
    df["high"] = df_raw["high"].astype(float)
    df["low"] = df_raw["low"].astype(float)
    df["close"] = df_raw["close"].astype(float)

    has_spread = "spread" in df_raw.columns
    if has_spread:
        df["spread"] = df_raw["spread"].astype(float)

    if "tick_volume" in df_raw.columns:
        df["tick_volume"] = df_raw["tick_volume"].astype(float)
    if "real_volume" in df_raw.columns:
        df["real_volume"] = df_raw["real_volume"].astype(float)

    # Sort if needed
    is_monotonic = df["datetime"].is_monotonic_increasing
    if not is_monotonic:
        df = df.sort_values("datetime").reset_index(drop=True)

    # Duplicates check
    dup_count = int(df["datetime"].duplicated().sum())
    if dup_count > 0:
        df = df.drop_duplicates(subset=["datetime"], keep="first").reset_index(drop=True)

    # Validity checks
    missing_ohlc = int(df[["open", "high", "low", "close"]].isna().sum().sum())
    invalid_hl = int((df["high"] < df["low"]).sum())
    invalid_oc_high = int((df["high"] < np.maximum(df["open"], df["close"])).sum())
    invalid_oc_low = int((df["low"] > np.minimum(df["open"], df["close"])).sum())
    total_invalid = invalid_hl + invalid_oc_high + invalid_oc_low

    row_count = len(df)
    start_dt = str(df["datetime"].iloc[0]) if row_count > 0 else "NA"
    end_dt = str(df["datetime"].iloc[-1]) if row_count > 0 else "NA"

    audit_meta = {
        "source_path": str(path),
        "symbol": symbol,
        "timeframe": "M1",
        "row_count": row_count,
        "start_datetime": start_dt,
        "end_datetime": end_dt,
        "timezone": "UTC",
        "duplicate_timestamp_count": dup_count,
        "non_monotonic_timestamp_count": 0 if is_monotonic else 1,
        "missing_ohlc_count": missing_ohlc,
        "invalid_high_low_count": total_invalid,
        "data_hash_sha256": file_sha256,
        "file_size": file_size,
        "has_spread": has_spread,
        "is_sufficient_history": row_count >= 250000,
    }

    return df, audit_meta
