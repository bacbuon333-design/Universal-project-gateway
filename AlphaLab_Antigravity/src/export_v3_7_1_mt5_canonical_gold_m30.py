"""V3.7.1 controlled canonical GOLD M30 re-export.

Data-governance infrastructure only. No strategies, signals, backtests, or
performance evaluation live in this module.

The exporter creates a new lineage from the official MetaTrader5 Python rates
API. It does not modify or overwrite the legacy GOLD_M30.csv.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
from typing import Any, Dict, Iterable, Optional, Tuple

import pandas as pd

from canonical_data_contract import (
    Eligibility,
    LineageStatus,
    TimestampSemantic,
    TimezoneStatus,
    decide_research_eligibility,
    validate_provenance_sidecar,
)

try:
    import MetaTrader5 as mt5
except ImportError:  # pragma: no cover - exercised only on machines without MT5
    mt5 = None


UTC = timezone.utc
M30_SECONDS = 30 * 60
REQUEST_START_UTC = datetime(2018, 1, 1, 0, 0, tzinfo=UTC)
REQUIRED_RESEARCH_START_UTC = datetime(2018, 4, 1, 0, 0, tzinfo=UTC)
MAX_RECENCY_LAG_DAYS = 5

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "AlphaLab_Antigravity" / "data" / "canonical"
PROV_DIR = ROOT / "AlphaLab_Antigravity" / "data" / "provenance"
REPORT_DIR = ROOT / "AlphaLab_Antigravity" / "reports" / "v3_7_1"

CSV_PATH = DATA_DIR / "GOLD_M30_CANONICAL.csv"
SIDECAR_PATH = PROV_DIR / "GOLD_M30_CANONICAL.source.json"
MANIFEST_PATH = PROV_DIR / "GOLD_M30_CANONICAL.manifest.json"
STRUCTURAL_PATH = REPORT_DIR / "GOLD_M30_CANONICAL.structural_audit.json"
DECISION_PATH = REPORT_DIR / "V3_7_1_REEXPORT_DECISION.json"

EXPORTER_REPO_PATH = "AlphaLab_Antigravity/src/export_v3_7_1_mt5_canonical_gold_m30.py"
OFFICIAL_DOC_REFERENCES = [
    {
        "title": "MetaTrader5 Python copy_rates_range",
        "url": "https://www.mql5.com/en/docs/python_metatrader5/mt5copyratesrange_py",
        "contract": "Bars are selected by bar open time; MT5 bar open times are stored/returned in UTC.",
    },
    {
        "title": "MetaTrader5 Python copy_rates_from",
        "url": "https://www.mql5.com/en/docs/python_metatrader5/mt5copyratesfrom_py",
        "contract": "date_from is an initial bar open date; received bar time is UTC.",
    },
]

REQUIRED_RATE_COLUMNS = [
    "time",
    "open",
    "high",
    "low",
    "close",
    "tick_volume",
    "spread",
    "real_volume",
]
CANONICAL_COLUMNS = [
    "time",
    "timestamp_utc",
    "open",
    "high",
    "low",
    "close",
    "tick_volume",
    "spread",
    "real_volume",
]


def git_sha(ref: str = "HEAD") -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", ref], cwd=ROOT, text=True, stderr=subprocess.DEVNULL
        ).strip()
    except Exception:
        return "UNKNOWN_GIT_SHA"


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def floor_m30_open(dt: datetime) -> datetime:
    """Return the M30 bar-open boundary containing dt, in UTC."""
    if dt.tzinfo is None:
        raise ValueError("datetime must be timezone-aware")
    dt = dt.astimezone(UTC)
    epoch = int(dt.timestamp())
    floored = epoch - (epoch % M30_SECONDS)
    return datetime.fromtimestamp(floored, tz=UTC)


def last_completed_m30_open(dt: Optional[datetime] = None) -> datetime:
    """Open time of the latest M30 bar guaranteed complete at dt."""
    now = (dt or datetime.now(UTC)).astimezone(UTC)
    return floor_m30_open(now) - timedelta(seconds=M30_SECONDS)


def _namedtuple_to_safe_dict(obj: Any, allowed: Iterable[str]) -> Dict[str, Any]:
    if obj is None:
        return {}
    result: Dict[str, Any] = {}
    for key in allowed:
        value = getattr(obj, key, None)
        if isinstance(value, (str, int, float, bool)) or value is None:
            result[key] = value
        else:
            result[key] = str(value)
    return result


def normalize_rates(rates: Any) -> pd.DataFrame:
    """Normalize MT5 structured rates without resampling or price changes."""
    df = pd.DataFrame(rates)
    missing = [c for c in REQUIRED_RATE_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"MT5 response missing columns: {missing}")
    if df.empty:
        raise ValueError("MT5 returned zero bars")

    df = df[REQUIRED_RATE_COLUMNS].copy()
    df = df.sort_values("time", kind="mergesort").reset_index(drop=True)

    if df["time"].isna().any():
        raise ValueError("Null raw epoch timestamp")
    if df["time"].duplicated().any():
        raise ValueError("Duplicate raw epoch timestamp")

    df["time"] = df["time"].astype("int64")
    ts = pd.to_datetime(df["time"], unit="s", utc=True)
    # Explicit ISO-8601 UTC string. No local-time conversion is permitted.
    df.insert(1, "timestamp_utc", ts.dt.strftime("%Y-%m-%dT%H:%M:%SZ"))

    return df[CANONICAL_COLUMNS]


def structural_audit(df: pd.DataFrame, requested_end_open_utc: datetime) -> Dict[str, Any]:
    problems = []

    if df.empty:
        problems.append("EMPTY_DATASET")

    duplicate_count = int(df["time"].duplicated().sum()) if not df.empty else 0
    if duplicate_count:
        problems.append("DUPLICATE_TIMESTAMPS")

    non_monotonic = 0
    if len(df) > 1:
        d = df["time"].diff().iloc[1:]
        non_monotonic = int((d <= 0).sum())
        if non_monotonic:
            problems.append("NON_MONOTONIC_TIMESTAMPS")
        median_delta_minutes = float(d.median() / 60.0)
        pct_30m = float((d == M30_SECONDS).mean() * 100.0)
    else:
        median_delta_minutes = None
        pct_30m = None

    if median_delta_minutes != 30.0:
        problems.append("MEDIAN_CADENCE_NOT_30_MINUTES")

    ohlc = df[["open", "high", "low", "close"]].apply(pd.to_numeric, errors="coerce")
    null_ohlc = int(ohlc.isna().any(axis=1).sum())
    high_below_low = int((ohlc["high"] < ohlc["low"]).sum())
    high_below_oc = int((ohlc["high"] < ohlc[["open", "close"]].max(axis=1)).sum())
    low_above_oc = int((ohlc["low"] > ohlc[["open", "close"]].min(axis=1)).sum())
    ohlc_violations = null_ohlc + high_below_low + high_below_oc + low_above_oc
    if ohlc_violations:
        problems.append("OHLC_VALIDATION_FAILED")

    max_allowed_epoch = int(requested_end_open_utc.timestamp())
    bars_after_requested_end = int((df["time"] > max_allowed_epoch).sum())
    if bars_after_requested_end:
        problems.append("BAR_AFTER_REQUESTED_LAST_COMPLETED_OPEN")

    first_ts = pd.to_datetime(int(df["time"].iloc[0]), unit="s", utc=True) if not df.empty else None
    last_ts = pd.to_datetime(int(df["time"].iloc[-1]), unit="s", utc=True) if not df.empty else None

    return {
        "status": "PASS" if not problems else "FAIL",
        "problems": problems,
        "row_count": int(len(df)),
        "first_bar_open_utc": first_ts.isoformat() if first_ts is not None else None,
        "last_bar_open_utc": last_ts.isoformat() if last_ts is not None else None,
        "duplicate_timestamp_count": duplicate_count,
        "non_monotonic_timestamp_count": non_monotonic,
        "median_delta_minutes": median_delta_minutes,
        "pct_exact_30m_deltas": pct_30m,
        "bars_after_requested_end": bars_after_requested_end,
        "ohlc": {
            "null_ohlc_rows": null_ohlc,
            "high_below_low_rows": high_below_low,
            "high_below_open_or_close_rows": high_below_oc,
            "low_above_open_or_close_rows": low_above_oc,
            "total_violation_count": ohlc_violations,
        },
    }


def coverage_audit(df: pd.DataFrame, requested_end_open_utc: datetime) -> Dict[str, Any]:
    if df.empty:
        return {"status": "FAIL", "reasons": ["EMPTY_DATASET"]}

    first_open = datetime.fromtimestamp(int(df["time"].iloc[0]), tz=UTC)
    last_open = datetime.fromtimestamp(int(df["time"].iloc[-1]), tz=UTC)
    reasons = []

    if first_open > REQUIRED_RESEARCH_START_UTC:
        reasons.append("HISTORY_DOES_NOT_COVER_2018Q2_START")

    lag = requested_end_open_utc - last_open
    if lag < timedelta(0):
        reasons.append("LAST_BAR_AFTER_REQUESTED_END")
    elif lag > timedelta(days=MAX_RECENCY_LAG_DAYS):
        reasons.append("LATEST_HISTORY_MORE_THAN_5_DAYS_STALE")

    return {
        "status": "PASS" if not reasons else "FAIL",
        "reasons": reasons,
        "required_first_bar_no_later_than": REQUIRED_RESEARCH_START_UTC.isoformat(),
        "actual_first_bar_open_utc": first_open.isoformat(),
        "requested_last_completed_bar_open_utc": requested_end_open_utc.isoformat(),
        "actual_last_bar_open_utc": last_open.isoformat(),
        "latest_history_lag_seconds": float(lag.total_seconds()),
    }


def _require_new_output_paths() -> None:
    existing = [p for p in (CSV_PATH, SIDECAR_PATH, MANIFEST_PATH, STRUCTURAL_PATH, DECISION_PATH) if p.exists()]
    if existing:
        raise FileExistsError(
            "Controlled re-export refuses to overwrite existing artifacts: "
            + ", ".join(str(p.relative_to(ROOT)) for p in existing)
        )


def _initialize_mt5(terminal_path: Optional[str]) -> None:
    if mt5 is None:
        raise RuntimeError("MetaTrader5 Python package is not installed")
    ok = mt5.initialize(terminal_path) if terminal_path else mt5.initialize()
    if not ok:
        raise RuntimeError(f"mt5.initialize failed: {mt5.last_error()}")


def source_identity(symbol: str) -> Dict[str, Any]:
    account = mt5.account_info()
    terminal = mt5.terminal_info()
    symbol_info = mt5.symbol_info(symbol)
    if account is None:
        raise RuntimeError("MT5 account_info unavailable; broker/server provenance cannot be verified")
    if terminal is None:
        raise RuntimeError("MT5 terminal_info unavailable")
    if symbol_info is None:
        raise RuntimeError(f"Explicit symbol not available in terminal: {symbol}")

    company = getattr(account, "company", None) or getattr(terminal, "company", None)
    server = getattr(account, "server", None)
    if not company or not server:
        raise RuntimeError("Broker company/server identity incomplete; fail closed")

    version = mt5.version()
    version_value = list(version) if version is not None else None

    return {
        "broker_company": str(company),
        "broker_server": str(server),
        "symbol": str(symbol),
        "terminal": _namedtuple_to_safe_dict(
            terminal,
            ["company", "name", "connected", "trade_allowed", "build", "maxbars"],
        ),
        "symbol_metadata": _namedtuple_to_safe_dict(
            symbol_info,
            ["name", "path", "currency_base", "currency_profit", "digits", "point", "trade_contract_size"],
        ),
        "mt5_terminal_version": version_value,
        "mt5_python_package_version": str(getattr(mt5, "__version__", "UNKNOWN")),
    }


def deterministic_csv_write(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    # 17 significant digits preserve float64 round-trip identity.
    df.to_csv(tmp, index=False, columns=CANONICAL_COLUMNS, float_format="%.17g", lineterminator="\n")
    os.replace(tmp, path)


def run_export(symbol: str, terminal_path: Optional[str] = None, now_utc: Optional[datetime] = None) -> Dict[str, Any]:
    _require_new_output_paths()

    requested_end = last_completed_m30_open(now_utc)
    generated_at = (now_utc or datetime.now(UTC)).astimezone(UTC)

    _initialize_mt5(terminal_path)
    try:
        identity = source_identity(symbol)
        rates = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_M30, REQUEST_START_UTC, requested_end)
        if rates is None:
            raise RuntimeError(f"copy_rates_range returned None: {mt5.last_error()}")
        df = normalize_rates(rates)
    finally:
        mt5.shutdown()

    structural = structural_audit(df, requested_end)
    if structural["status"] != "PASS":
        raise RuntimeError(f"Structural validation failed before canonical write: {structural['problems']}")

    coverage = coverage_audit(df, requested_end)

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    PROV_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    deterministic_csv_write(df, CSV_PATH)
    dataset_hash = sha256_file(CSV_PATH)

    transform_chain = [
        "MetaTrader5.initialize using the operator-selected terminal connection",
        f"MetaTrader5.copy_rates_range(symbol={symbol}, timeframe=TIMEFRAME_M30, UTC-aware start/end)",
        "Preserve raw MT5 rate fields without resampling/interpolation/gap filling",
        "Stable-sort ascending by raw epoch time and reject duplicate epochs",
        "Derive timestamp_utc directly from raw Unix epoch seconds with UTC timezone",
        "Serialize fixed canonical columns with LF line endings and 17-significant-digit float formatting",
        "Calculate SHA-256 over exact serialized CSV bytes",
    ]

    source_id = (
        f"MetaTrader5 broker feed|company={identity['broker_company']}|"
        f"server={identity['broker_server']}|symbol={identity['symbol']}"
    )

    sidecar: Dict[str, Any] = {
        "dataset_sha256": dataset_hash,
        "source_type": "METATRADER5_TERMINAL_BROKER_FEED",
        "source_identifier": source_id,
        "broker_company": identity["broker_company"],
        "broker_server": identity["broker_server"],
        "broker_symbol": identity["symbol"],
        "exporter_or_extraction_method": "MetaTrader5.copy_rates_range",
        "exporter_path": EXPORTER_REPO_PATH,
        "exporter_git_sha": git_sha(),
        "timestamp_semantic": TimestampSemantic.BAR_OPEN_TIME.value,
        "timestamp_timezone_status": TimezoneStatus.EXPLICIT_UTC.value,
        "timestamp_timezone": "UTC",
        "timeframe": "M30",
        "generated_at_utc": generated_at.isoformat(),
        "requested_start_utc": REQUEST_START_UTC.isoformat(),
        "requested_last_completed_bar_open_utc": requested_end.isoformat(),
        "returned_first_bar_open_utc": structural["first_bar_open_utc"],
        "returned_last_bar_open_utc": structural["last_bar_open_utc"],
        "row_count": int(len(df)),
        "size_bytes": int(CSV_PATH.stat().st_size),
        "transform_chain": transform_chain,
        "official_api_documentation": OFFICIAL_DOC_REFERENCES,
        "environment": {
            "python_version": sys.version.split()[0],
            "platform": platform.platform(),
            "pandas_version": pd.__version__,
            "mt5_python_package_version": identity["mt5_python_package_version"],
            "mt5_terminal_version": identity["mt5_terminal_version"],
        },
        "terminal_metadata_non_sensitive": identity["terminal"],
        "symbol_metadata": identity["symbol_metadata"],
        "sensitive_account_fields_committed": False,
    }

    prov_eval = validate_provenance_sidecar(sidecar, dataset_hash)
    eligibility = decide_research_eligibility(
        structural_validation_status=structural["status"],
        timestamp_semantic=prov_eval["timestamp_semantic"],
        timestamp_timezone_status=prov_eval["timestamp_timezone_status"],
        lineage_status=prov_eval["lineage_status"],
        source_type=prov_eval["source_type"],
        source_identifier=prov_eval["source_identifier"],
        exporter_or_extraction_method=prov_eval["exporter_or_extraction_method"],
        transform_chain=prov_eval["transform_chain"],
    )

    blockers = list(eligibility["blocking_reasons"])
    if coverage["status"] != "PASS":
        blockers.extend("COVERAGE:" + x for x in coverage["reasons"])

    final_eligibility = Eligibility.ELIGIBLE.value if not blockers else Eligibility.BLOCKED.value

    manifest = {
        "dataset_id": "GOLD_M30_CANONICAL",
        "relative_path": str(CSV_PATH.relative_to(ROOT)).replace("\\", "/"),
        "sha256": dataset_hash,
        "size_bytes": int(CSV_PATH.stat().st_size),
        "row_count": int(len(df)),
        "columns": CANONICAL_COLUMNS,
        "first_bar_open_utc": structural["first_bar_open_utc"],
        "last_bar_open_utc": structural["last_bar_open_utc"],
        "timestamp_semantic": prov_eval["timestamp_semantic"],
        "timestamp_timezone_status": prov_eval["timestamp_timezone_status"],
        "timestamp_timezone": prov_eval["timestamp_timezone"],
        "timeframe": "M30",
        "lineage_status": prov_eval["lineage_status"],
        "structural_validation_status": structural["status"],
        "coverage_status": coverage["status"],
        "canonical_lineage_verified": prov_eval["lineage_status"] == LineageStatus.VERIFIED.value,
        "research_eligibility": final_eligibility,
        "blocking_reasons": sorted(set(blockers)),
        "exporter_git_sha": git_sha(),
    }

    decision = {
        "dataset_id": "GOLD_M30_CANONICAL",
        "dataset_sha256": dataset_hash,
        "canonical_lineage_verified": manifest["canonical_lineage_verified"],
        "structural_validation_status": structural["status"],
        "coverage_status": coverage["status"],
        "timestamp_semantic": prov_eval["timestamp_semantic"],
        "timestamp_timezone_status": prov_eval["timestamp_timezone_status"],
        "lineage_status": prov_eval["lineage_status"],
        "research_eligibility": final_eligibility,
        "blocking_reasons": sorted(set(blockers)),
        "fail_closed": True,
    }

    SIDECAR_PATH.write_text(json.dumps(sidecar, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    STRUCTURAL_PATH.write_text(
        json.dumps({"dataset_sha256": dataset_hash, **structural, "coverage": coverage}, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    DECISION_PATH.write_text(json.dumps(decision, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    return {
        "csv": str(CSV_PATH),
        "sidecar": str(SIDECAR_PATH),
        "manifest": str(MANIFEST_PATH),
        "structural": str(STRUCTURAL_PATH),
        "decision": decision,
    }


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Controlled canonical MetaTrader5 GOLD M30 re-export")
    p.add_argument("--symbol", required=True, help="Exact broker symbol for Gold, e.g. GOLD or XAUUSD")
    p.add_argument("--terminal-path", default=None, help="Optional explicit MetaTrader 5 terminal executable path")
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    result = run_export(args.symbol, args.terminal_path)
    print(json.dumps(result["decision"], indent=2, ensure_ascii=False))
