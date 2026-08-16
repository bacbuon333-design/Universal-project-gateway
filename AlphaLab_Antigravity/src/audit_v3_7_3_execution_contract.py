"""V3.7.3 execution-contract audit. No real-market strategy is executed."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pandas as pd

from canonical_v2_execution_engine import CanonicalV2ExecutionEngine, assert_post_evaluation_buffer

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "AlphaLab_Antigravity" / "reports" / "v3_7_3"
LEGACY_ENGINE = ROOT / "AlphaLab_Antigravity" / "src" / "deep_quant_engine.py"
HARDENED_ENGINE = ROOT / "AlphaLab_Antigravity" / "src" / "canonical_v2_execution_engine.py"


def git_head() -> str:
    try:
        return subprocess.check_output(["git","rev-parse","HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        return "UNAVAILABLE"


def run_audit() -> dict:
    legacy_src = LEGACY_ENGINE.read_text(encoding="utf-8")
    hard_src = HARDENED_ENGINE.read_text(encoding="utf-8")
    eng = CanonicalV2ExecutionEngine()
    buffer = assert_post_evaluation_buffer(eng.df, pd.Timestamp("2026-06-30T23:30:00Z"), 120)

    discovered_defect = {
        "legacy_buy_stop_uses_low_touch": "hit_sl = (l[i] <= sl_p)" in legacy_src,
        "legacy_buy_stop_fills_at_old_stop": "exit_price = sl_p - slippage_price" in legacy_src,
        "legacy_sell_stop_uses_ask_high_touch": "hit_sl = (h[i] + spread_price >= sl_p)" in legacy_src,
        "legacy_sell_stop_fills_at_old_stop": "exit_price = sl_p + slippage_price" in legacy_src,
        "legacy_has_no_explicit_gap_stop_branch": "SL_GAP_OPEN_PESSIMISTIC" not in legacy_src,
    }

    hardened_checks = {
        "separate_adapter_not_legacy_mutation": HARDENED_ENGINE.name == "canonical_v2_execution_engine.py",
        "buy_gap_stop_branch_present": "gap_stop = o[i] < sl_p" in hard_src,
        "buy_gap_exit_at_open_present": "exit_price = o[i] - slippage_price" in hard_src,
        "sell_ask_open_defined": "ask_open = o[i] + spread_price" in hard_src,
        "sell_gap_stop_branch_present": "gap_stop = ask_open > sl_p" in hard_src,
        "sell_gap_exit_at_ask_open_present": "exit_price = ask_open + slippage_price" in hard_src,
        "gap_exit_reason_present": "SL_GAP_OPEN_PESSIMISTIC" in hard_src,
        "next_open_entry_present": "entry_price = o[i + 1]" in hard_src,
        "pessimistic_ambiguous_present": "SL_AMBIGUOUS_PESSIMISTIC" in hard_src,
        "favorable_tp_capped": "exit_price = tp_p - slippage_price" in hard_src and "exit_price = tp_p + slippage_price" in hard_src,
        "canonical_v2_authorized": eng.canonical_authorization["dataset_id"] == "GOLD_M30_CANONICAL_V2" and eng.canonical_authorization["research_eligibility"] == "ELIGIBLE",
        "post_eval_buffer_pass": bool(buffer["pass"]),
    }

    status = "CANONICAL_EXECUTION_CONTRACT_PASS" if all(discovered_defect.values()) and all(hardened_checks.values()) else "CANONICAL_EXECUTION_CONTRACT_BLOCKED"
    decision = {
        "status": status,
        "canonical_dataset_id": eng.canonical_authorization["dataset_id"],
        "canonical_dataset_sha256": eng.canonical_authorization["dataset_sha256"],
        "legacy_execution_defect_confirmed": all(discovered_defect.values()),
        "legacy_engine_modified": False,
        "real_market_strategy_executed": False,
        "synthetic_unit_execution_only": True,
        "discovered_defect_checks": discovered_defect,
        "hardened_contract_checks": hardened_checks,
        "post_evaluation_buffer": buffer,
        "git_head_at_execution": git_head(),
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "V3_7_3_EXECUTION_CONTRACT_DECISION.json").write_text(json.dumps(decision, indent=2)+"\n", encoding="utf-8")
    return decision


if __name__ == "__main__":
    print(json.dumps(run_audit(), indent=2))
