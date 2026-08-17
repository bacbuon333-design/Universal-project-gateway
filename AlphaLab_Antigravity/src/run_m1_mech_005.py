from __future__ import annotations

"""One-run runner for ALAB-M1-MECH-005 invariance/falsification study."""

import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from m1_mech_002.state_engine import EXPECTED_DATA_SHA256, validate_development_frame
from m1_mech_005.invariance_falsification import (
    BOOTSTRAP_ITERATIONS,
    BOOTSTRAP_SEED,
    EXPERIMENT_ID,
    PLACEBO_LOCAL_SEED,
    PLACEBO_SIGN_SEED,
    build_coordinate_audit,
    build_falsification_frame,
    build_gradient_table,
    build_invariance_regression_table,
    build_placebo_table,
    build_yearly_invariance_table,
    evaluate_falsification_gates,
)

ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = ROOT / "AlphaLab_Antigravity" / "data" / "canonical" / "GOLD_M1_PRE2026.csv"
OUT = ROOT / "AlphaLab_Antigravity" / "reports" / "m1_mech_005"
LOCAL_EVENT_PATH = OUT / "local" / "M1_MECH_005_EVENTS.csv.gz"


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
        x = float(obj); return x if np.isfinite(x) else None
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
        raise RuntimeError(f"STOP_BLOCKED_DATASET_HASH_MISMATCH: expected={EXPECTED_DATA_SHA256} actual={actual_sha}")

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

    frame = build_falsification_frame(df)
    OUT.mkdir(parents=True, exist_ok=True); LOCAL_EVENT_PATH.parent.mkdir(parents=True, exist_ok=True)

    audit = build_coordinate_audit(frame)
    invariance, coordinate_bootstrap = build_invariance_regression_table(frame)
    gradient, gradient_audit = build_gradient_table(frame)
    placebo = build_placebo_table(frame)
    yearly = build_yearly_invariance_table(frame)
    gates = evaluate_falsification_gates(audit, invariance, gradient_audit, placebo)

    write_json(OUT / "M1_MECH_005_COORDINATE_AUDIT.json", audit)
    invariance.to_csv(OUT / "M1_MECH_005_INVARIANCE_REGRESSION.csv", index=False)
    write_json(OUT / "M1_MECH_005_COORDINATE_BOOTSTRAP.json", coordinate_bootstrap)
    gradient.to_csv(OUT / "M1_MECH_005_GRADIENT.csv", index=False)
    write_json(OUT / "M1_MECH_005_GRADIENT_AUDIT.json", gradient_audit)
    placebo.to_csv(OUT / "M1_MECH_005_PLACEBO.csv", index=False)
    yearly.to_csv(OUT / "M1_MECH_005_YEARLY_INVARIANCE.csv", index=False)
    write_json(OUT / "M1_MECH_005_GATES.json", gates)

    frame.to_csv(LOCAL_EVENT_PATH, index=False, compression="gzip")
    local_event_sha = sha256_file(LOCAL_EVENT_PATH)

    manifest = {
        "experiment_id": EXPERIMENT_ID,
        "research_type": "COMPENSATION_INVARIANCE_FALSIFICATION",
        "dataset_path": str(DATA_PATH), "dataset_sha256": actual_sha, "dataset_rows": int(len(df)),
        "development_start": str(df["datetime"].min()), "development_end": str(df["datetime"].max()),
        "sealed_holdout": "2015-2017 — NOT ACCESSED", "discovery_2026": "NOT_ACCESSED",
        "events": int(len(frame)), "bootstrap_iterations": BOOTSTRAP_ITERATIONS,
        "bootstrap_seed": BOOTSTRAP_SEED, "placebo_local_seed": PLACEBO_LOCAL_SEED,
        "placebo_sign_seed": PLACEBO_SIGN_SEED, "gates": gates,
        "market_law_claimed": False, "causal_identification_claimed": False,
        "strategy_backtest": "NOT_RUN", "paper_trading": "NO", "live_trading": "NO",
        "broker_execution": "NO", "research_only": True,
        "local_event_table": str(LOCAL_EVENT_PATH), "local_event_table_sha256": local_event_sha,
    }
    write_json(OUT / "M1_MECH_005_MANIFEST.json", manifest)

    report = f"""# ALAB-M1-MECH-005 — Compensation Invariance & Falsification Audit

## Scope
Development-only attempt to falsify MECH-004 on frozen GOLD M1 2018–2025.
No strategy, PnL backtest, paper/live trading, broker execution, 2015–2017 access, or 2026 access.

## Dataset
- SHA256: `{actual_sha}`
- Rows: `{len(df):,}`
- Range: `{df['datetime'].min()}` to `{df['datetime'].max()}`
- Sealed holdout: `2015–2017 NOT ACCESSED`

## Invariance battery
Four pre-registered coordinates: ATR_t, ATR_(t-1), prior-price bps, and excursion-normalized ratios.
EXCURSION_RATIO uses only breaches with excursion >=0.10 ATR_t to prevent near-zero denominator blow-up.
The MECH-004 ATR_t rho_5m must reproduce within 1e-10 before any invariance claim is allowed.

## Placebo battery
1. Within UTC-date x side cyclic reassignment of R_post, rebuilding placebo total as R_in + shuffled R_post.
2. Within UTC-date x side balanced sign randomization of R_post, rebuilding placebo total as R_in + signed-placebo R_post.
Both have a pre-registered null rho=1 because the event's R_in is retained while the event-specific future increment linkage is destroyed.

## Interpretation boundary
Survival means the attenuation relationship is coordinate-robust and does not survive the two frozen placebo destructions.
It still does not prove a physical law, fixed budget, economic microstructure cause, or tradable edge.

## Verdict
`{gates['verdict']}`
"""
    (OUT / "M1_MECH_005_REPORT.md").write_text(report, encoding="utf-8")
    (ROOT / "M1_MECH_005_MANIFEST.json").write_text((OUT / "M1_MECH_005_MANIFEST.json").read_text(encoding="utf-8"), encoding="utf-8")
    (ROOT / "M1_MECH_005_REPORT.md").write_text(report, encoding="utf-8")


if __name__ == "__main__":
    main()
