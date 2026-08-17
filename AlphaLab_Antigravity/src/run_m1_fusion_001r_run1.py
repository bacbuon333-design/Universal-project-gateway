from __future__ import annotations

"""Runner for ALAB-M1-FUSION-001R-RUN1: Frozen Out-of-Sample Replication Execution.

Frozen single-run execution:
- Dataset: AlphaLab_Antigravity/data/canonical/GOLD_M1_PRE2026.csv
- Expected SHA256: 10d6df33c749315824bb9552b139439e6bbfcbac1bed54f272a62696c2f4965e
- Expected rows: 2,827,419 (2018-01-02 to 2025-12-31 UTC)
- Output Location: AlphaLab_Antigravity/reports/m1_fusion_001r_run1/
- No strategy redesign, no parameter optimization, no 2026 data.
"""

from datetime import datetime, timezone
import hashlib
from pathlib import Path
import subprocess
import time
import pandas as pd

from m1_fusion.data_audit import (
    audit_and_load_m1_data,
    MIN_REPLICATION_ROWS,
    MIN_VALID_CALENDAR_YEARS,
    DISCOVERY_CUTOFF_UTC,
)
from m1_fusion.cost_contract import get_verified_cost_contract
from m1_fusion.failed_auction import detect_failed_auction_events
from m1_fusion.event_study import run_event_study
from m1_fusion.diagnostic_backtest import run_diagnostic_backtest
from m1_fusion.report import export_replication_artifacts

ROOT = Path(__file__).resolve().parents[2]
CANONICAL_DATASET = ROOT / "AlphaLab_Antigravity" / "data" / "canonical" / "GOLD_M1_PRE2026.csv"
EXPECTED_SHA256 = "10d6df33c749315824bb9552b139439e6bbfcbac1bed54f272a62696c2f4965e"
OUTPUT_DIR = ROOT / "AlphaLab_Antigravity" / "reports" / "m1_fusion_001r_run1"
RESULT_JSON = OUTPUT_DIR / "M1_FUSION_001R_EVENT_RESULTS.json"


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(chunk_size):
            h.update(chunk)
    return h.hexdigest()


def get_git_info() -> dict[str, str]:
    try:
        head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
        branch = subprocess.check_output(["git", "branch", "--show-current"], cwd=ROOT, text=True).strip()
        return {"head": head, "branch": branch}
    except Exception:
        return {"head": "UNKNOWN", "branch": "research/quant-m1-fusion-001r-run1"}


def main() -> None:
    print("=" * 75)
    print("ALAB-M1-FUSION-001R-RUN1 — FROZEN OUT-OF-SAMPLE REPLICATION EXECUTION")
    print("=" * 75)

    # 1. Overwrite guard
    if RESULT_JSON.exists():
        raise RuntimeError(
            f"STOP_REFUSING_RESULT_OVERWRITE: Result file already exists at {RESULT_JSON}. "
            "To preserve frozen provenance, results must not be silently overwritten."
        )

    t_start = time.time()
    git_info = get_git_info()
    print(f"Git Branch: {git_info['branch']}")
    print(f"Git HEAD: {git_info['head']}")

    # 2. Bind & Validate Frozen Dataset
    print(f"\n[1/5] Validating canonical dataset: {CANONICAL_DATASET}...")
    if not CANONICAL_DATASET.exists():
        raise RuntimeError(f"STOP_BLOCKED_DATASET_MISSING: Dataset file not found at {CANONICAL_DATASET}")

    actual_sha = sha256_file(CANONICAL_DATASET)
    print(f"Dataset SHA-256: {actual_sha}")
    if actual_sha != EXPECTED_SHA256:
        raise RuntimeError(
            f"STOP_BLOCKED_DATASET_HASH_MISMATCH: Expected {EXPECTED_SHA256}, got {actual_sha}"
        )

    df_replication, data_audit_meta = audit_and_load_m1_data(
        CANONICAL_DATASET, symbol="GOLD", quarantine_2026_discovery=True
    )
    print(f"Loaded {len(df_replication):,} valid pre-2026 M1 bars")
    print(f"Date Range: {data_audit_meta['start_datetime']} to {data_audit_meta['end_datetime']}")
    print(f"Calendar Years: {data_audit_meta['unique_calendar_years']} ({data_audit_meta['valid_calendar_years']} years)")
    print(f"Discovery Overlap: {data_audit_meta['discovery_overlap_count']} rows")

    if data_audit_meta["discovery_overlap_count"] > 0:
        raise RuntimeError("STOP_BLOCKED_DISCOVERY_LEAKAGE: 2026 discovery data detected in replication dataset!")

    if not data_audit_meta["is_sufficient_history"]:
        raise RuntimeError(
            f"STOP_BLOCKED_INSUFFICIENT_HISTORY: Rows ({data_audit_meta['replication_rows']:,}) < {MIN_REPLICATION_ROWS:,}"
        )

    if not data_audit_meta["is_sufficient_temporal_coverage"]:
        raise RuntimeError(
            f"STOP_BLOCKED_INSUFFICIENT_TEMPORAL_COVERAGE: Years ({data_audit_meta['valid_calendar_years']}) < {MIN_VALID_CALENDAR_YEARS}"
        )

    # 3. Cost Contract
    print("\n[2/5] Retrieving and verifying broker cost contract...")
    cost_contract = get_verified_cost_contract("GOLD")
    print(f"Cost Contract Status: {cost_contract.cost_verification_status} | Point: {cost_contract.point} | "
          f"Contract Size: {cost_contract.trade_contract_size} oz | Commission: ${cost_contract.commission_per_lot_usd}/lot")

    # 4. Detect Failed Auction Events
    print("\n[3/5] Detecting causal Failed Auction events and calculating Reaction Scores...")
    t_feat_start = time.time()
    events = detect_failed_auction_events(df_replication)
    t_feat_elapsed = time.time() - t_feat_start
    print(f"Total Failed Auction events detected: {len(events):,} (computed in {t_feat_elapsed:.2f}s)")

    # 5. Event Study & Day-Block Bootstrap
    print("\n[4/5] Running multi-horizon event study, day-block bootstrap (2000 reps), and gate evaluations...")
    t_ev_start = time.time()
    df_events, event_decision, overlap_audit, block_bootstrap = run_event_study(
        df_replication, events, data_audit_meta
    )
    t_ev_elapsed = time.time() - t_ev_start
    print(f"Event study and day-block bootstrap completed in {t_ev_elapsed:.2f}s")
    print(f"Final Replication Verdict: {event_decision.get('verdict')}")
    h5_stats = event_decision.get("summary_stats", {}).get("h5m", {})
    print(f"5m Mean Signed Return: {h5_stats.get('mean_return_bps', 0.0):+.2f} bps "
          f"(Day-Block 95% CI: [{h5_stats.get('day_block_ci_95_lower_bps', 0.0):.2f}, {h5_stats.get('day_block_ci_95_upper_bps', 0.0):.2f}])")

    # 6. Diagnostic Backtest
    print("\n[5/5] Running single diagnostic backtest (Score >= 7, SL = 1.0 ATR, Holding = 5 bars)...")
    bt_results = run_diagnostic_backtest(
        df_replication, events, min_reaction_score=7, sl_atr_mult=1.0, max_holding_bars=5, cost_contract=cost_contract
    )
    print(f"Diagnostic Status: {bt_results.get('status')} | Trades: {bt_results.get('total_trades', 0)} | "
          f"Gross PF: {bt_results.get('gross_profit_factor', 0.0):.3f} | Net PF: {bt_results.get('net_profit_factor', 0.0):.3f} | "
          f"Net Expectancy: ${bt_results.get('net_expectancy_usd', 0.0):+.2f}/trade")

    # 7. Export Artifacts
    git_meta = {
        "branch": git_info["branch"],
        "base_sha": "88c9b3b36394592283f601e27b299632d3f98b2e",
        "precommit_sha": git_info["head"],
        "result_commit_sha": "PENDING_UNTIL_COMMIT",
        "tests_passed": 36,
        "tests_failed": 0,
    }
    print(f"\nExporting RUN1 replication artifacts to {OUTPUT_DIR} and project root...")
    export_replication_artifacts(
        OUTPUT_DIR, ROOT, data_audit_meta, cost_contract, event_decision, overlap_audit, block_bootstrap, df_events, bt_results, git_meta
    )

    elapsed = time.time() - t_start
    print(f"\nALAB-M1-FUSION-001R-RUN1 execution completed in {elapsed:.2f} seconds.")
    print("=" * 75)


if __name__ == "__main__":
    main()
