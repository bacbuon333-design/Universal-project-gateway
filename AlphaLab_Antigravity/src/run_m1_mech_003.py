from __future__ import annotations

"""Runner for ALAB-M1-MECH-003 — Matched Control / Counterfactual Study.

Research-only observational matched-control analysis. No strategy, PnL backtest,
broker call, paper trading, live trading, or sealed 2015-2017 holdout access.
"""

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from m1_mech_002.state_engine import EXPECTED_DATA_SHA256, validate_development_frame
from m1_mech_003.control_study import (
    BOOTSTRAP_ITERATIONS,
    BOOTSTRAP_SEED,
    EXPERIMENT_ID,
    add_frozen_cem_strata,
    build_balance_table,
    build_counterfactual_frame,
    compute_cem_weights,
    day_block_bootstrap_5m,
    detect_breach_events,
    estimate_matched_effects,
    estimate_yearly_5m_effect,
    evaluate_mechanism_gates,
)

ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = ROOT / "AlphaLab_Antigravity" / "data" / "canonical" / "GOLD_M1_PRE2026.csv"
OUT = ROOT / "AlphaLab_Antigravity" / "reports" / "m1_mech_003"
LOCAL_EVENT_PATH = OUT / "local" / "M1_MECH_003_MATCHED_EVENTS.csv.gz"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _json_safe(obj):
    if isinstance(obj, dict):
        return {k: _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_json_safe(v) for v in obj]
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return None if not np.isfinite(obj) else float(obj)
    return obj


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

    events = detect_breach_events(df)
    frame = build_counterfactual_frame(df, events)
    if frame.empty:
        raise RuntimeError("STOP_BLOCKED_NO_BREACH_EVENTS")
    frame = add_frozen_cem_strata(frame)
    frame, matching_audit = compute_cem_weights(frame)

    balance = build_balance_table(frame)
    effects = estimate_matched_effects(frame)
    yearly = estimate_yearly_5m_effect(frame)
    bootstrap = day_block_bootstrap_5m(
        frame, iterations=BOOTSTRAP_ITERATIONS, seed=BOOTSTRAP_SEED
    )
    gates = evaluate_mechanism_gates(matching_audit, balance, effects, yearly, bootstrap)

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "local").mkdir(parents=True, exist_ok=True)

    balance.to_csv(OUT / "M1_MECH_003_BALANCE.csv", index=False)
    effects.to_csv(OUT / "M1_MECH_003_MATCHED_EFFECTS.csv", index=False)
    yearly.to_csv(OUT / "M1_MECH_003_YEARLY_5M.csv", index=False)
    frame.to_csv(LOCAL_EVENT_PATH, index=False, compression="gzip")

    local_sha = sha256_file(LOCAL_EVENT_PATH)
    (OUT / "M1_MECH_003_MATCHING_AUDIT.json").write_text(
        json.dumps(_json_safe(matching_audit), indent=2), encoding="utf-8"
    )
    (OUT / "M1_MECH_003_BLOCK_BOOTSTRAP.json").write_text(
        json.dumps(_json_safe(bootstrap), indent=2), encoding="utf-8"
    )
    (OUT / "M1_MECH_003_GATES.json").write_text(
        json.dumps(_json_safe(gates), indent=2), encoding="utf-8"
    )

    class_counts = frame["event_class"].value_counts().to_dict()
    primary = effects.loc[effects["horizon_min"] == 5].iloc[0].to_dict()
    manifest = {
        "experiment_id": EXPERIMENT_ID,
        "research_type": "MATCHED_OBSERVATIONAL_CONTROL_STUDY",
        "dataset_path": str(DATA_PATH),
        "dataset_sha256": actual_sha,
        "dataset_rows": int(len(df)),
        "development_start": str(df["datetime"].min()),
        "development_end": str(df["datetime"].max()),
        "sealed_holdout": "2015-2017 — NOT ACCESSED",
        "discovery_2026": "NOT_ACCESSED",
        "breach_events": int(len(frame)),
        "event_class_counts": {str(k): int(v) for k, v in class_counts.items()},
        "matching_method": "FROZEN_COARSENED_EXACT_MATCHING_ATT_WEIGHTS",
        "primary_horizon_minutes": 5,
        "bootstrap": "UTC_DAY_BLOCK",
        "bootstrap_iterations": BOOTSTRAP_ITERATIONS,
        "bootstrap_seed": BOOTSTRAP_SEED,
        "primary_effect": _json_safe(primary),
        "gates": _json_safe(gates),
        "causal_identification_claimed": False,
        "economic_microstructure_claims": "NOT_AUTHORIZED_FROM_M1",
        "strategy_backtest": "NOT_RUN",
        "paper_trading": "NO",
        "live_trading": "NO",
        "broker_execution": "NO",
        "research_only": True,
        "local_event_table": str(LOCAL_EVENT_PATH),
        "local_event_table_sha256": local_sha,
    }
    (OUT / "M1_MECH_003_MANIFEST.json").write_text(
        json.dumps(_json_safe(manifest), indent=2), encoding="utf-8"
    )

    report = f"""# ALAB-M1-MECH-003 — Matched Control Study

## Question
Does a Failed Auction contain forward information beyond the fact that its trigger candle already closed back inside the breached prior extreme?

## Scope
- Frozen GOLD M1 development dataset: 2018-2025 only.
- Dataset SHA256: `{actual_sha}`.
- 2015-2017 sealed holdout: NOT ACCESSED.
- 2026 discovery sample: NOT ACCESSED.
- No strategy, PnL backtest, paper/live trading, or broker execution.

## Treatment and control
- FAILED_AUCTION: prior 20-bar extreme is breached and event close returns inside the old range.
- ACCEPTED_BREAKOUT: the same type of extreme is breached and event close remains beyond the breached level.
- Exact closes at the prior extreme and dual-side breach bars are excluded.

## Matching
Frozen coarsened exact matching on:
- breach side
- calendar year
- UTC hour
- structural location count
- ATR-percentile bin
- path-efficiency bin
- absolute-stretch bin
- sweep-depth/ATR bin

Treatment observations use weight 1. Controls are weighted within common-support strata to the treatment distribution.
No outcome is used to form matching strata.

## Primary inference
- Primary horizon: +5 exact clock minutes.
- Primary effect: weighted treatment-minus-control signed forward return.
- Dependence-aware uncertainty: UTC day-block bootstrap, B={BOOTSTRAP_ITERATIONS}, seed={BOOTSTRAP_SEED}.
- State-rate difference relative to the prior extreme is secondary evidence.

## Scientific boundary
This is a matched observational control study, not randomized causal identification.
`MECHANISM_SUPPORTED` means the frozen conditional association survived the precommitted common-support, balance, day-block and temporal-stability gates. It does NOT prove liquidity-provider behavior, institutional flow, or order-book causality.

## Result placeholder
Verdict after one run: `{gates.get('verdict')}`.
See `M1_MECH_003_GATES.json`, `M1_MECH_003_MATCHED_EFFECTS.csv`, and `M1_MECH_003_YEARLY_5M.csv`.
"""
    (OUT / "M1_MECH_003_REPORT.md").write_text(report, encoding="utf-8")


if __name__ == "__main__":
    main()
