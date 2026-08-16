from __future__ import annotations

"""V3.13.1 checkpoint-hash canonicalization audit.

Provenance repair only. This module does not acquire OOS data, create a new
checkpoint, evaluate outcomes, or call a trading engine.
"""

import hashlib
import inspect
import json
from pathlib import Path
import platform
import subprocess

import create_v3_13_blind_oos_checkpoint as ledger
import fresh_oos_v312_contract as v312

ROOT = v312.ROOT
REPORT_DIR = ROOT / "AlphaLab_Antigravity" / "reports" / "v3_13_1"
DECISION_PATH = REPORT_DIR / "V3_13_1_CHECKPOINT_HASH_REPAIR_DECISION.json"
PRECOMMIT = ROOT / "V3_13_1_CHECKPOINT_HASH_CANONICALIZATION_PRECOMMIT.md"
GITATTR = ROOT / ".gitattributes"
SCIENTIFIC_PARENT = "e2c4d64d93545be12ddf6d40ad8fc4dc5644bd7c"
FROZEN_DESIGN_PARENT = "__EXECUTION_HEAD_TO_BE_RECORDED_BY_GIT__"


def git_sha(ref: str = "HEAD") -> str:
    return subprocess.check_output(["git", "rev-parse", ref], cwd=ROOT, text=True).strip()


def raw_file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_audit() -> dict:
    v312.verify_frozen_canonical_cutoff()
    files = ledger._checkpoint_files()
    if len(files) != 1:
        raise RuntimeError(f"V3.13.1 repair requires exactly genesis checkpoint before audit; found {len(files)}")
    genesis_path = files[0]
    if genesis_path.name != ledger.GENESIS_FILENAME:
        raise RuntimeError(f"Genesis filename drift: {genesis_path.name}")

    genesis = ledger.verify_frozen_genesis_checkpoint()
    chain = ledger.validate_checkpoint_chain()

    attr_text = GITATTR.read_text(encoding="utf-8") if GITATTR.exists() else ""
    writer_source = inspect.getsource(ledger)
    audit_source = inspect.getsource(run_audit)

    checks = {
        "exactly_one_checkpoint_and_no_checkpoint2": len(files) == 1,
        "genesis_filename_frozen": genesis_path.name == ledger.GENESIS_FILENAME,
        "canonical_hash_scheme_frozen": ledger.HASH_SCHEME == "SHA256_UTF8_LF_NORMALIZED_V1",
        "genesis_canonical_sha_matches_repair_contract": genesis["canonical_sha256"] == ledger.GENESIS_REPO_LF_SHA256,
        "genesis_authoritative_sha_is_repo_lf_sha": ledger.GENESIS_REPO_LF_SHA256 == "b45ac406bfa7da1436f23f0add600a6354485b5a4d5d25c064b3470e23300876",
        "old_local_worktree_sha_explicitly_superseded": ledger.GENESIS_SUPERSEDED_LOCAL_WORKTREE_SHA256 == "f8f97c2a7aa47e79784f37dc83072896971d52a34fef8ba28248351447ac000b",
        "chain_uses_canonical_genesis_sha": chain["latest_checkpoint_sha256"] == ledger.GENESIS_REPO_LF_SHA256,
        "writer_uses_binary_lf_serialization": "path.write_bytes(raw)" in writer_source and "_write_checkpoint_lf" in writer_source,
        "writer_uses_portable_checkpoint_hash": "checkpoint_sha256(path)" in writer_source,
        "new_payload_records_hash_scheme": '"checkpoint_hash_scheme": HASH_SCHEME' in writer_source,
        "gitattributes_checkpoint_lf": "AlphaLab_Antigravity/reports/v3_13/checkpoints/*.json text eol=lf" in attr_text,
        "gitattributes_report_lf": "V3_13_BLIND_OOS_CHECKPOINT_REPORT_*.md text eol=lf" in attr_text,
        "precommit_exists": PRECOMMIT.exists(),
        "no_outcome_or_engine_execution": ("run_" + "strategy(") not in audit_source and ("CanonicalV2" + "ExecutionEngine") not in audit_source,
    }

    failed = [k for k, ok in checks.items() if not ok]
    status = "V3_13_1_CHECKPOINT_HASH_CANONICALIZATION_PASS" if not failed else "V3_13_1_CHECKPOINT_HASH_CANONICALIZATION_BLOCKED"

    decision = {
        "chapter": "V3.13.1 CHECKPOINT HASH CANONICALIZATION REPAIR",
        "artifact_generation_parent_sha": git_sha("HEAD"),
        "scientific_parent_v313_final": SCIENTIFIC_PARENT,
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "checkpoint_count_before_repair_audit": len(files),
        "checkpoint2_created": False,
        "genesis_checkpoint_filename": genesis_path.name,
        "historical_reported_local_worktree_sha256": ledger.GENESIS_SUPERSEDED_LOCAL_WORKTREE_SHA256,
        "historical_reported_sha_status": "SUPERSEDED_FOR_LEDGER_CHAIN_AUTHORITY",
        "genesis_raw_worktree_sha256_at_audit": raw_file_sha256(genesis_path),
        "checkpoint_hash_scheme": ledger.HASH_SCHEME,
        "genesis_canonical_lf_sha256": genesis["canonical_sha256"],
        "authoritative_genesis_chain_sha256": ledger.GENESIS_REPO_LF_SHA256,
        "genesis_payload_rewritten": False,
        "v313_historical_report_rewritten": False,
        "oos_exporter_called": False,
        "outcome_metrics_computed": False,
        "trading_engine_called": False,
        "strategy_executed": False,
        "strategy_design_authorized": False,
        "future_oos_outcome_evaluator_authorized": False,
        "same_sample_h226_research_closed": True,
        "historical_h226_strategy_status": "REJECTED",
        "checks": checks,
        "failed_checks": failed,
        "final_status": status,
    }
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    DECISION_PATH.write_bytes((json.dumps(decision, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))
    return decision


if __name__ == "__main__":
    print(json.dumps(run_audit(), indent=2, ensure_ascii=False))
