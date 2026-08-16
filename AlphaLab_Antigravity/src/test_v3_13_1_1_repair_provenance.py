from __future__ import annotations

import inspect
import json
import subprocess

import audit_v3_13_1_1_repair_provenance as audit
import create_v3_13_blind_oos_checkpoint as ledger


def _git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=audit.ROOT, text=True).strip()


def test_scientific_parent_is_v3131_final():
    assert audit.V3131_FINAL == "af7ee188f46a658aa8134282721c4bbf3a3e0f32"


def test_prior_raw_commit_is_frozen():
    assert audit.V3131_RAW == "9d733fcfb93fcf434a07156493af318512d54806"


def test_prior_pre_repair_head_is_frozen():
    assert audit.V3131_FROZEN_PRE_REPAIR == "44ff23351bba5334d311d6d07ec383ac9581bcbb"


def test_prior_raw_parent_is_pre_repair_head():
    assert _git("rev-parse", f"{audit.V3131_RAW}^") == audit.V3131_FROZEN_PRE_REPAIR


def test_prior_raw_commit_combined_source_and_artifact():
    changed = set(_git("diff-tree", "--no-commit-id", "--name-only", "-r", audit.V3131_RAW).splitlines())
    assert "AlphaLab_Antigravity/src/audit_v3_13_1_checkpoint_hash_repair.py" in changed
    assert "AlphaLab_Antigravity/reports/v3_13_1/V3_13_1_CHECKPOINT_HASH_REPAIR_DECISION.json" in changed


def test_prior_machine_artifact_recorded_pre_repair_head():
    p = audit.ROOT / "AlphaLab_Antigravity/reports/v3_13_1/V3_13_1_CHECKPOINT_HASH_REPAIR_DECISION.json"
    obj = json.loads(p.read_text(encoding="utf-8"))
    assert obj["artifact_generation_parent_sha"] == audit.V3131_FROZEN_PRE_REPAIR
    assert obj["final_status"] == "V3_13_1_CHECKPOINT_HASH_CANONICALIZATION_PASS"


def test_hash_scheme_and_genesis_authority_unchanged():
    assert ledger.HASH_SCHEME == "SHA256_UTF8_LF_NORMALIZED_V1"
    assert audit.AUTHORITATIVE_GENESIS_SHA == "b45ac406bfa7da1436f23f0add600a6354485b5a4d5d25c064b3470e23300876"
    assert ledger.verify_frozen_genesis_checkpoint()["canonical_sha256"] == audit.AUTHORITATIVE_GENESIS_SHA


def test_superseded_local_sha_remains_historical_only():
    assert audit.SUPERSEDED_LOCAL_SHA == "f8f97c2a7aa47e79784f37dc83072896971d52a34fef8ba28248351447ac000b"
    assert ledger.GENESIS_SUPERSEDED_LOCAL_WORKTREE_SHA256 == audit.SUPERSEDED_LOCAL_SHA
    assert audit.SUPERSEDED_LOCAL_SHA != audit.AUTHORITATIVE_GENESIS_SHA


def test_exactly_one_checkpoint_before_closure_execution():
    files = ledger._checkpoint_files()
    assert len(files) == 1
    assert files[0].name == ledger.GENESIS_FILENAME


def test_auditor_captures_head_before_writing_artifact():
    src = inspect.getsource(audit.run_audit)
    assert 'execution_head = _git("rev-parse", "HEAD")' in src
    assert 'status_before = _git("status", "--porcelain")' in src
    assert src.index('execution_head = _git("rev-parse", "HEAD")') < src.index("DECISION_PATH.write_bytes")


def test_auditor_has_no_exporter_or_checkpoint_creation_call():
    src = inspect.getsource(audit.run_audit)
    assert "run_accrual(" not in src
    assert "create_checkpoint(" not in src


def test_auditor_hardcodes_no_research_authorization():
    src = inspect.getsource(audit.run_audit)
    assert '"oos_exporter_called": False' in src
    assert '"outcome_metrics_computed": False' in src
    assert '"trading_engine_called": False' in src
    assert '"strategy_executed": False' in src
    assert '"strategy_design_authorized": False' in src
    assert '"future_oos_outcome_evaluator_authorized": False' in src
    assert '"same_sample_h226_research_closed": True' in src


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for t in tests:
        t()
        print(f"PASS: {t.__name__}")
    print(f"All {len(tests)} V3.13.1.1 tests passed")
