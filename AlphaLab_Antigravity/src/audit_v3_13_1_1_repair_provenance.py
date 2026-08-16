from __future__ import annotations

"""V3.13.1.1 execution-code provenance closure.

Audit-only. No OOS acquisition, checkpoint creation, outcome evaluation,
trading-engine execution, or strategy design is present.
"""

import json
from pathlib import Path
import platform
import subprocess
from typing import Any, Dict, List

import create_v3_13_blind_oos_checkpoint as ledger
import fresh_oos_v312_contract as v312

ROOT = v312.ROOT
REPORT_DIR = ROOT / "AlphaLab_Antigravity" / "reports" / "v3_13_1_1"
DECISION_PATH = REPORT_DIR / "V3_13_1_1_REPAIR_PROVENANCE_DECISION.json"
PRECOMMIT = ROOT / "V3_13_1_1_REPAIR_PROVENANCE_CLOSURE_PRECOMMIT.md"
V3131_FINAL = "af7ee188f46a658aa8134282721c4bbf3a3e0f32"
V3131_RAW = "9d733fcfb93fcf434a07156493af318512d54806"
V3131_FROZEN_PRE_REPAIR = "44ff23351bba5334d311d6d07ec383ac9581bcbb"
HASH_SCHEME = "SHA256_UTF8_LF_NORMALIZED_V1"
AUTHORITATIVE_GENESIS_SHA = "b45ac406bfa7da1436f23f0add600a6354485b5a4d5d25c064b3470e23300876"
SUPERSEDED_LOCAL_SHA = "f8f97c2a7aa47e79784f37dc83072896971d52a34fef8ba28248351447ac000b"


def _git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def _git_lines(*args: str) -> List[str]:
    out = _git(*args)
    return [x for x in out.splitlines() if x.strip()]


def _load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        obj = json.load(f)
    if not isinstance(obj, dict):
        raise RuntimeError(f"Expected JSON object: {path}")
    return obj


def run_audit() -> Dict[str, Any]:
    # Capture execution provenance before this function writes any artifact.
    execution_head = _git("rev-parse", "HEAD")
    branch = _git("branch", "--show-current")
    status_before = _git("status", "--porcelain")
    clean_before = status_before == ""

    v312.verify_frozen_canonical_cutoff()
    files = ledger._checkpoint_files()
    genesis = ledger.verify_frozen_genesis_checkpoint()
    chain = ledger.validate_checkpoint_chain()

    prior_decision = _load_json(
        ROOT / "AlphaLab_Antigravity" / "reports" / "v3_13_1" / "V3_13_1_CHECKPOINT_HASH_REPAIR_DECISION.json"
    )

    raw_parent = _git("rev-parse", f"{V3131_RAW}^")
    raw_changed = _git_lines("diff-tree", "--no-commit-id", "--name-only", "-r", V3131_RAW)
    audit_path = "AlphaLab_Antigravity/src/audit_v3_13_1_checkpoint_hash_repair.py"
    decision_path = "AlphaLab_Antigravity/reports/v3_13_1/V3_13_1_CHECKPOINT_HASH_REPAIR_DECISION.json"

    checks = {
        "clean_worktree_before_audit": clean_before,
        "v3131_final_is_ancestor_of_execution_head": subprocess.run(
            ["git", "merge-base", "--is-ancestor", V3131_FINAL, execution_head], cwd=ROOT
        ).returncode == 0,
        "prior_v3131_machine_status_pass": prior_decision.get("final_status") == "V3_13_1_CHECKPOINT_HASH_CANONICALIZATION_PASS",
        "prior_artifact_parent_was_pre_repair_head": prior_decision.get("artifact_generation_parent_sha") == V3131_FROZEN_PRE_REPAIR,
        "v3131_raw_parent_is_pre_repair_head": raw_parent == V3131_FROZEN_PRE_REPAIR,
        "v3131_raw_commit_combined_audit_source_and_machine_artifact": audit_path in raw_changed and decision_path in raw_changed,
        "exactly_one_checkpoint": len(files) == 1,
        "genesis_canonical_hash_unchanged": genesis.get("canonical_sha256") == AUTHORITATIVE_GENESIS_SHA,
        "chain_authority_uses_canonical_genesis_sha": chain.get("latest_checkpoint_sha256") == AUTHORITATIVE_GENESIS_SHA,
        "hash_scheme_unchanged": ledger.HASH_SCHEME == HASH_SCHEME,
        "superseded_local_sha_unchanged": ledger.GENESIS_SUPERSEDED_LOCAL_WORKTREE_SHA256 == SUPERSEDED_LOCAL_SHA,
        "checkpoint2_absent": len(files) == 1,
        "precommit_exists": PRECOMMIT.exists(),
    }

    failed = [k for k, ok in checks.items() if not ok]
    final_status = (
        "V3_13_1_1_REPAIR_PROVENANCE_CLOSURE_PASS"
        if not failed
        else "V3_13_1_1_REPAIR_PROVENANCE_CLOSURE_BLOCKED"
    )

    decision: Dict[str, Any] = {
        "chapter": "V3.13.1.1 REPAIR PROVENANCE CLOSURE",
        "execution_head_before_artifact_write": execution_head,
        "execution_branch": branch,
        "working_tree_clean_before_audit": clean_before,
        "scientific_parent_v3131_final": V3131_FINAL,
        "v3131_raw_commit": V3131_RAW,
        "v3131_raw_parent": raw_parent,
        "prior_v3131_artifact_generation_parent_sha": prior_decision.get("artifact_generation_parent_sha"),
        "prior_provenance_issue": "TECHNICAL_REPAIR_AND_RAW_ARTIFACT_COMMITTED_TOGETHER",
        "checkpoint_hash_scheme": ledger.HASH_SCHEME,
        "authoritative_genesis_chain_sha256": AUTHORITATIVE_GENESIS_SHA,
        "checkpoint_count": len(files),
        "checkpoint2_created": False,
        "oos_exporter_called": False,
        "outcome_metrics_computed": False,
        "trading_engine_called": False,
        "strategy_executed": False,
        "strategy_design_authorized": False,
        "future_oos_outcome_evaluator_authorized": False,
        "same_sample_h226_research_closed": True,
        "historical_h226_strategy_status": "REJECTED",
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "checks": checks,
        "failed_checks": failed,
        "final_status": final_status,
    }

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    DECISION_PATH.write_bytes((json.dumps(decision, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))
    return decision


if __name__ == "__main__":
    print(json.dumps(run_audit(), indent=2, ensure_ascii=False))
