from __future__ import annotations

"""Runner for ALAB-M1-MECH-002 — Market State Transition Discovery.

DEVELOPMENT RESEARCH ONLY.
No strategy, PnL backtest, order API, paper trading, or sealed 2015-2017 holdout.
"""

import hashlib
import json
from pathlib import Path

import pandas as pd

from m1_fusion.failed_auction import detect_failed_auction_events
from m1_mech_002.state_engine import (
    DEVELOPMENT_START_UTC,
    DEVELOPMENT_END_UTC,
    EXPECTED_DATA_SHA256,
    add_gap_aware_state_labels,
    build_mechanism_event_frame,
    validate_development_frame,
)
from m1_mech_002.decomposition import (
    add_descriptive_factor_bins,
    build_factor_summary,
    build_location_energy_matrix,
    build_tail_risk_summary,
    build_transition_summary,
)

ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = ROOT / "AlphaLab_Antigravity" / "data" / "canonical" / "GOLD_M1_PRE2026.csv"
OUT = ROOT / "AlphaLab_Antigravity" / "reports" / "m1_mech_002"
LOCAL_EVENT_PATH = OUT / "local" / "M1_MECH_002_EVENTS.csv.gz"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    if not DATA_PATH.exists():
        raise RuntimeError(f"STOP_BLOCKED_DATASET_MISSING: {DATA_PATH}")
    actual_sha = sha256_file(DATA_PATH)
    if actual_sha != EXPECTED_DATA_SHA256:
        raise RuntimeError(
            f"STOP_BLOCKED_DATASET_HASH_MISMATCH: expected={EXPECTED_DATA_SHA256} actual={actual_sha}"
        )

    df = pd.read_csv(DATA_PATH)
    if "datetime" in df.columns:
        df["datetime"] = pd.to_datetime(df["datetime"], utc=True)
    elif "time" in df.columns:
        df["datetime"] = pd.to_datetime(df["time"], unit="s", utc=True)
    else:
        raise ValueError("Canonical dataset has no datetime/time column.")
    validate_development_frame(df)

    if df["datetime"].min() < DEVELOPMENT_START_UTC:
        raise RuntimeError("STOP_BLOCKED_SEALED_HOLDOUT_ACCESS")
    if df["datetime"].max() >= DEVELOPMENT_END_UTC:
        raise RuntimeError("STOP_BLOCKED_DISCOVERY_LEAKAGE")

    events = detect_failed_auction_events(df)
    frame = build_mechanism_event_frame(df, events)
    frame = add_gap_aware_state_labels(df, frame)
    frame, cutpoints = add_descriptive_factor_bins(frame)

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "local").mkdir(parents=True, exist_ok=True)

    factor_summary = build_factor_summary(frame, horizon=5)
    le_matrix = build_location_energy_matrix(frame, horizon=5)
    transitions = build_transition_summary(frame)
    tails = build_tail_risk_summary(frame)

    factor_summary.to_csv(OUT / "M1_MECH_002_FACTOR_SUMMARY.csv", index=False)
    le_matrix.to_csv(OUT / "M1_MECH_002_LOCATION_ENERGY_MATRIX.csv", index=False)
    transitions.to_csv(OUT / "M1_MECH_002_STATE_TRANSITIONS.csv", index=False)
    tails.to_csv(OUT / "M1_MECH_002_TAIL_RISK.csv", index=False)

    frame.to_csv(LOCAL_EVENT_PATH, index=False, compression="gzip")
    local_event_sha = sha256_file(LOCAL_EVENT_PATH)

    gap_audit = {
        "events": int(len(frame)),
        "exact_5m_available": int(frame["exact_5m_available"].sum()),
        "continuous_5m_paths": int(frame["continuous_5m_path"].sum()),
        "gap_contaminated_5m": int((~frame["continuous_5m_path"]).sum()),
        "gap_contaminated_5m_pct": float((~frame["continuous_5m_path"]).mean() * 100.0),
        "gap_any_within_30m": int(frame["gap_any_within_30m"].sum()),
        "gap_any_within_30m_pct": float(frame["gap_any_within_30m"].mean() * 100.0),
    }
    with (OUT / "M1_MECH_002_GAP_AUDIT.json").open("w", encoding="utf-8") as f:
        json.dump(gap_audit, f, indent=2)

    manifest = {
        "experiment_id": "ALAB-M1-MECH-002",
        "research_type": "MARKET_STATE_TRANSITION_DISCOVERY",
        "dataset_path": str(DATA_PATH),
        "dataset_sha256": actual_sha,
        "development_start": str(df["datetime"].min()),
        "development_end": str(df["datetime"].max()),
        "sealed_holdout": "2015-2017 — NOT ACCESSED",
        "events": int(len(frame)),
        "primary_state_basis": "CLOSE_ONLY",
        "intrabar_sequence_claimed": False,
        "gap_aware_exact_clock_labels": True,
        "economic_microstructure_claims": "NOT_AUTHORIZED_FROM_M1",
        "descriptive_bin_cutpoints": cutpoints,
        "local_event_table": str(LOCAL_EVENT_PATH),
        "local_event_table_sha256": local_event_sha,
        "strategy_backtest": "NOT_RUN",
        "paper_trading": "NO",
        "live_trading": "NO",
        "broker_execution": "NO",
        "research_only": True,
    }
    with (OUT / "M1_MECH_002_MANIFEST.json").open("w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    report = f"""# ALAB-M1-MECH-002 — Market State Transition Discovery

## Scope
Development-only mechanism decomposition on the frozen 2018-2025 GOLD M1 dataset.
No strategy, PnL backtest, trading, or 2015-2017 holdout access.

## Dataset
- SHA256: `{actual_sha}`
- Rows: `{len(df):,}`
- Range: `{df['datetime'].min()}` to `{df['datetime'].max()}`
- Sealed holdout: `2015-2017 NOT ACCESSED`

## Observable state model
- ENERGY: path efficiency, robust stretch, ATR percentile.
- LOCATION: previous observed trading-day H/L; completed-session H/L with 24 clock-hour retention; confirmed M15 swing zones with preserved 0.10*M15 ATR width.
- REJECTION: sweep depth, reclaim depth, event range, signed body, close location.
- TRANSITION: exact-clock close state relative to the failed-auction prior extreme.
- TAIL: quantiles, skew, adverse/favorable 5% expected shortfall, gap-aware MFE/MAE.

## Interpretation boundary
`SNAPBACK_SIDE` and `BREAKOUT_SIDE` are price-state labels only.
The study does not claim liquidity refill, institutional flow, or order-book causality from M1 OHLC.

## Gap policy
A +h minute label requires a bar exactly h clock minutes after the event.
No later bar substitutes for a missing minute. Excursions require a continuous bar path.

## Artifacts
- M1_MECH_002_FACTOR_SUMMARY.csv
- M1_MECH_002_LOCATION_ENERGY_MATRIX.csv
- M1_MECH_002_STATE_TRANSITIONS.csv
- M1_MECH_002_TAIL_RISK.csv
- M1_MECH_002_GAP_AUDIT.json
- M1_MECH_002_MANIFEST.json
- Local full event table (not for Git if large): `{LOCAL_EVENT_PATH}`
"""
    (OUT / "M1_MECH_002_REPORT.md").write_text(report, encoding="utf-8")


if __name__ == "__main__":
    main()
