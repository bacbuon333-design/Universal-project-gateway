from __future__ import annotations

"""One-run research runner for ALAB-M1-MECH-004."""

import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from m1_mech_002.state_engine import EXPECTED_DATA_SHA256, validate_development_frame
from m1_mech_003.control_study import detect_breach_events
from m1_mech_004.reversion_budget import (
    BOOTSTRAP_ITERATIONS,
    BOOTSTRAP_SEED,
    EXPERIMENT_ID,
    build_counterfactual_reversion_frame,
    build_energy_location_budget,
    build_event_class_summary,
    build_fixed_reclaim_bins,
    build_horizon_summary,
    build_regression_table,
    build_yearly_5m_slopes,
    evaluate_gates,
    fixed_residual_day_block_bootstrap,
    geometry_audit,
)

ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = ROOT / "AlphaLab_Antigravity" / "data" / "canonical" / "GOLD_M1_PRE2026.csv"
OUT = ROOT / "AlphaLab_Antigravity" / "reports" / "m1_mech_004"
LOCAL_EVENT_PATH = OUT / "local" / "M1_MECH_004_EVENTS.csv.gz"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _json_safe(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {str(k): _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_json_safe(x) for x in obj]
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        x = float(obj)
        return x if np.isfinite(x) else None
    if isinstance(obj, float):
        return obj if np.isfinite(obj) else None
    return obj


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(_json_safe(payload), indent=2), encoding="utf-8")


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
    if df["datetime"].min() < pd.Timestamp("2018-01-01T00:00:00Z"):
        raise RuntimeError("STOP_BLOCKED_SEALED_HOLDOUT_ACCESS")
    if df["datetime"].max() >= pd.Timestamp("2026-01-01T00:00:00Z"):
        raise RuntimeError("STOP_BLOCKED_DISCOVERY_LEAKAGE")

    events = detect_breach_events(df)
    frame = build_counterfactual_reversion_frame(df, events)

    OUT.mkdir(parents=True, exist_ok=True)
    LOCAL_EVENT_PATH.parent.mkdir(parents=True, exist_ok=True)

    audit = geometry_audit(frame)
    horizons = build_horizon_summary(frame)
    bins = build_fixed_reclaim_bins(frame)
    event_classes = build_event_class_summary(frame)
    energy_location = build_energy_location_budget(frame, horizon=5)
    regressions = build_regression_table(frame)
    yearly = build_yearly_5m_slopes(frame)
    bootstrap = fixed_residual_day_block_bootstrap(
        frame,
        iterations=BOOTSTRAP_ITERATIONS,
        seed=BOOTSTRAP_SEED,
    )
    gates = evaluate_gates(audit, regressions, yearly, bootstrap)

    write_json(OUT / "M1_MECH_004_GEOMETRY_AUDIT.json", audit)
    horizons.to_csv(OUT / "M1_MECH_004_HORIZON_SUMMARY.csv", index=False)
    bins.to_csv(OUT / "M1_MECH_004_FIXED_RECLAIM_BINS.csv", index=False)
    event_classes.to_csv(OUT / "M1_MECH_004_EVENT_CLASS_SUMMARY.csv", index=False)
    energy_location.to_csv(OUT / "M1_MECH_004_ENERGY_LOCATION_BUDGET.csv", index=False)
    regressions.to_csv(OUT / "M1_MECH_004_REGRESSION.csv", index=False)
    yearly.to_csv(OUT / "M1_MECH_004_YEARLY_5M.csv", index=False)
    write_json(OUT / "M1_MECH_004_BLOCK_BOOTSTRAP.json", bootstrap)
    write_json(OUT / "M1_MECH_004_GATES.json", gates)

    frame.to_csv(LOCAL_EVENT_PATH, index=False, compression="gzip")
    local_event_sha = sha256_file(LOCAL_EVENT_PATH)

    primary_row = regressions[regressions["horizon_min"] == 5]
    primary_rho = float(primary_row.iloc[0]["rho_total_on_in"]) if not primary_row.empty else np.nan

    manifest = {
        "experiment_id": EXPERIMENT_ID,
        "research_type": "REVERSION_TIMING_COMPENSATION_STUDY",
        "dataset_path": str(DATA_PATH),
        "dataset_sha256": actual_sha,
        "dataset_rows": int(len(df)),
        "development_start": str(df["datetime"].min()),
        "development_end": str(df["datetime"].max()),
        "sealed_holdout": "2015-2017 — NOT ACCESSED",
        "discovery_2026": "NOT_ACCESSED",
        "breach_events": int(len(frame)),
        "event_class_counts": {
            str(k): int(v) for k, v in frame["event_class"].value_counts().to_dict().items()
        },
        "primary_horizon_minutes": 5,
        "primary_rho_total_on_in": primary_rho,
        "primary_null_rho": 1.0,
        "bootstrap_method": bootstrap.get("method"),
        "bootstrap_iterations": BOOTSTRAP_ITERATIONS,
        "bootstrap_seed": BOOTSTRAP_SEED,
        "post_close_regression_prohibited": True,
        "pre_run_algebraic_coupling_repair": True,
        "gates": gates,
        "conservation_law_claimed": False,
        "causal_identification_claimed": False,
        "strategy_backtest": "NOT_RUN",
        "paper_trading": "NO",
        "live_trading": "NO",
        "broker_execution": "NO",
        "research_only": True,
        "local_event_table": str(LOCAL_EVENT_PATH),
        "local_event_table_sha256": local_event_sha,
    }
    write_json(OUT / "M1_MECH_004_MANIFEST.json", manifest)

    report = f"""# ALAB-M1-MECH-004 — Reversion Timing / Compensation Study

## Scope
Development-only continuous reversion timing study on frozen GOLD M1 2018–2025.
No strategy, PnL backtest, paper/live trading, broker execution, 2015–2017 holdout access, or 2026 access.

## Dataset
- SHA256: `{actual_sha}`
- Rows: `{len(df):,}`
- Range: `{df['datetime'].min()}` to `{df['datetime'].max()}`
- Breach events: `{len(frame):,}`
- Sealed holdout: `2015–2017 NOT ACCESSED`

## Mechanics
- `R_in`: snapback-direction movement from event extreme to event close, normalized by event ATR14.
- `R_post(h)`: additional exact-clock snapback-direction movement after event close; descriptive only.
- `R_total(h)`: snapback-direction displacement from event extreme to exact-clock future close.
- Consumption ratio is descriptive only and defined only when `R_total(h) > 0`.

## Pre-run scientific repair
A draft regression of `R_post` on `R_in` was rejected before any real outcome was run because those variables are algebraically coupled through event close. The frozen primary model instead uses future `R_total`.

## Primary model
`R_total(h) = rho_h * R_in + frozen controls + error`.

Null reference: `rho=1` (one-for-one persistence). Evidence for attenuation/compensation requires `rho<1`, with the +5m UTC day-block bootstrap upper 95% bound also below 1.

## Interpretation boundary
A rho below 1 is development-set attenuation relative to one-for-one persistence. It is not a physical conservation law, a fixed budget, or randomized causal identification.
No liquidity-provider, institutional-flow, or order-book causality is claimed.

## Verdict
`{gates['verdict']}`

See regression, yearly, bootstrap, fixed-bin, energy/location, and geometry artifacts for details.
"""
    (OUT / "M1_MECH_004_REPORT.md").write_text(report, encoding="utf-8")

    (ROOT / "M1_MECH_004_MANIFEST.json").write_text(
        (OUT / "M1_MECH_004_MANIFEST.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (ROOT / "M1_MECH_004_REPORT.md").write_text(report, encoding="utf-8")


if __name__ == "__main__":
    main()
