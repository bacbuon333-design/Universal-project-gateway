from __future__ import annotations

"""Controlled append-only fresh-OOS Gold M30 acquisition for V3.12.

No strategy/outcome logic is present. Requests use UTC Unix epoch seconds and
only bars strictly after the frozen canonical cutoff are eligible for storage.
"""

import argparse
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd

import export_v3_7_1_mt5_canonical_gold_m30 as v371
from fresh_oos_v312_contract import (
    CANONICAL_FREEZE_CUTOFF,
    CANONICAL_SHA256,
    EXPECTED_BROKER_COMPANY,
    EXPECTED_BROKER_SERVER,
    EXPECTED_BROKER_SYMBOL,
    EXPECTED_REQUEST_BOUNDARY,
    EXPECTED_TIMEFRAME,
    OOS_CSV,
    OOS_SOURCE,
    sha256_file,
    verify_oos_provenance,
)

UTC = timezone.utc
REQUEST_START = CANONICAL_FREEZE_CUTOFF.to_pydatetime() + timedelta(minutes=30)


def _fetch_epoch(symbol: str, start_utc: datetime, end_utc: datetime) -> Any:
    if start_utc.tzinfo is None or end_utc.tzinfo is None:
        raise RuntimeError("V3.12 MT5 boundaries must be timezone-aware UTC")
    start_epoch = int(start_utc.astimezone(UTC).timestamp())
    end_epoch = int(end_utc.astimezone(UTC).timestamp())
    if start_epoch > end_epoch:
        return np.array([], dtype=[])
    v371.mt5.symbol_select(symbol, True)
    rates = v371.mt5.copy_rates_range(symbol, v371.mt5.TIMEFRAME_M30, start_epoch, end_epoch)
    if rates is None:
        raise RuntimeError(f"copy_rates_range failed: {v371.mt5.last_error()}")
    return rates


def _verify_identity(symbol: str) -> Dict[str, Any]:
    identity = v371.source_identity(symbol)
    if identity["broker_company"] != EXPECTED_BROKER_COMPANY:
        raise RuntimeError(f"Broker company drift: {identity['broker_company']}")
    if identity["broker_server"] != EXPECTED_BROKER_SERVER:
        raise RuntimeError(f"Broker server drift: {identity['broker_server']}")
    if identity["symbol"] != EXPECTED_BROKER_SYMBOL:
        raise RuntimeError(f"Broker symbol drift: {identity['symbol']}")
    return identity


def _merge_append_only(existing: pd.DataFrame, new: pd.DataFrame) -> pd.DataFrame:
    if existing.empty:
        return new.sort_values("time", kind="mergesort").reset_index(drop=True)
    both = pd.concat([existing, new], ignore_index=True)
    # Duplicate timestamps are allowed only when every serialized data field agrees.
    dup = both[both["time"].duplicated(keep=False)]
    if len(dup):
        compare_cols = [c for c in v371.CANONICAL_COLUMNS if c != "timestamp_utc"]
        for _, g in dup.groupby("time"):
            if len(g[compare_cols].drop_duplicates()) != 1:
                raise RuntimeError(f"Fresh-OOS revision conflict at epoch {int(g['time'].iloc[0])}")
    out = both.drop_duplicates("time", keep="first").sort_values("time", kind="mergesort").reset_index(drop=True)
    return out[v371.CANONICAL_COLUMNS]


def run_accrual(symbol: str, terminal_path: Optional[str] = None, now_utc: Optional[datetime] = None) -> Dict[str, Any]:
    if symbol != EXPECTED_BROKER_SYMBOL:
        raise RuntimeError(f"V3.12 requires exact symbol {EXPECTED_BROKER_SYMBOL}")
    now = (now_utc or datetime.now(UTC)).astimezone(UTC)
    requested_end = v371.last_completed_m30_open(now)
    if requested_end <= CANONICAL_FREEZE_CUTOFF.to_pydatetime():
        return {"status": "NO_FRESH_BARS_AVAILABLE", "requested_end_utc": requested_end.isoformat(), "rows_added": 0}

    previous_sha = None
    existing = pd.DataFrame(columns=v371.CANONICAL_COLUMNS)
    if OOS_CSV.exists() or OOS_SOURCE.exists():
        if not OOS_CSV.exists() or not OOS_SOURCE.exists():
            raise RuntimeError("Existing fresh-OOS data/provenance pair is incomplete")
        previous_sha = verify_oos_provenance()["dataset_sha256"]
        existing = pd.read_csv(OOS_CSV)

    fetch_start = REQUEST_START
    if len(existing):
        last_epoch = int(pd.to_numeric(existing["time"], errors="raise").max())
        fetch_start = datetime.fromtimestamp(last_epoch + 1800, tz=UTC)
    if fetch_start > requested_end:
        return {"status": "NO_FRESH_BARS_AVAILABLE", "requested_end_utc": requested_end.isoformat(), "rows_added": 0}

    v371._initialize_mt5(terminal_path)
    try:
        identity = _verify_identity(symbol)
        rates = _fetch_epoch(symbol, fetch_start, requested_end)
    finally:
        v371.mt5.shutdown()

    if rates is None or len(rates) == 0:
        return {"status": "NO_FRESH_BARS_AVAILABLE", "requested_end_utc": requested_end.isoformat(), "rows_added": 0}

    new = v371.normalize_rates(rates)
    cutoff_epoch = int(CANONICAL_FREEZE_CUTOFF.timestamp())
    new = new[pd.to_numeric(new["time"]) > cutoff_epoch].copy()
    if new.empty:
        return {"status": "NO_FRESH_BARS_AVAILABLE", "requested_end_utc": requested_end.isoformat(), "rows_added": 0}

    merged = _merge_append_only(existing, new)
    before = len(existing)
    added = len(merged) - before
    if added <= 0:
        return {"status": "NO_FRESH_BARS_AVAILABLE", "requested_end_utc": requested_end.isoformat(), "rows_added": 0}

    OOS_CSV.parent.mkdir(parents=True, exist_ok=True)
    v371.deterministic_csv_write(merged, OOS_CSV)
    dataset_sha = sha256_file(OOS_CSV)

    source = {
        "dataset_id": "GOLD_M30_FRESH_OOS",
        "dataset_sha256": dataset_sha,
        "canonical_parent_sha256": CANONICAL_SHA256,
        "canonical_freeze_cutoff_utc": CANONICAL_FREEZE_CUTOFF.isoformat(),
        "source_type": "METATRADER5_TERMINAL_BROKER_FEED",
        "broker_company": identity["broker_company"],
        "broker_server": identity["broker_server"],
        "broker_symbol": identity["symbol"],
        "timeframe": EXPECTED_TIMEFRAME,
        "extraction_method": "MetaTrader5.copy_rates_range",
        "request_boundary_representation": EXPECTED_REQUEST_BOUNDARY,
        "timestamp_semantic": "BAR_OPEN_TIME",
        "timestamp_timezone_status": "EXPLICIT_UTC",
        "timestamp_timezone": "UTC",
        "transform_chain": [
            "Request only bars strictly after frozen canonical cutoff using UTC Unix epoch seconds",
            "Preserve raw MT5 M30 fields without resampling/interpolation/gap filling",
            "Normalize epoch time to explicit timestamp_utc",
            "Append-only merge; duplicate epochs must be byte/value consistent",
            "Deterministic CSV serialization and SHA-256 hash",
        ],
        "previous_dataset_sha256": previous_sha,
        "accrual_generated_at_utc": now.isoformat(),
        "first_bar_open_utc": pd.to_datetime(merged["time"].iloc[0], unit="s", utc=True).isoformat(),
        "last_bar_open_utc": pd.to_datetime(merged["time"].iloc[-1], unit="s", utc=True).isoformat(),
        "row_count": int(len(merged)),
        "rows_added_this_accrual": int(added),
        "sensitive_account_fields_committed": False,
    }
    OOS_SOURCE.write_text(json.dumps(source, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    return {
        "status": "FRESH_OOS_ACCRUAL_WRITTEN",
        "dataset_sha256": dataset_sha,
        "row_count": int(len(merged)),
        "rows_added": int(added),
        "first_bar_open_utc": source["first_bar_open_utc"],
        "last_bar_open_utc": source["last_bar_open_utc"],
    }


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="V3.12 controlled fresh-OOS Gold M30 accrual")
    p.add_argument("--symbol", required=True)
    p.add_argument("--terminal-path", default=None)
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    print(json.dumps(run_accrual(args.symbol, args.terminal_path), indent=2, ensure_ascii=False))
