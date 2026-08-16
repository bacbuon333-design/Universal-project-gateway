from __future__ import annotations

import json
from pathlib import Path
import subprocess

import fresh_oos_v312_contract as v312

ROOT = v312.ROOT
DECISION = ROOT / "AlphaLab_Antigravity" / "reports" / "v3_13_1" / "V3_13_1_CHECKPOINT_HASH_REPAIR_DECISION.json"
REPORT = ROOT / "V3_13_1_CHECKPOINT_HASH_CANONICALIZATION_REPORT.md"


def git_sha(ref: str = "HEAD") -> str:
    return subprocess.check_output(["git", "rev-parse", ref], cwd=ROOT, text=True).strip()


def main() -> None:
    d = json.loads(DECISION.read_text(encoding="utf-8"))
    checks = d["checks"]
    lines = [
        "# V3.13.1 CHECKPOINT HASH CANONICALIZATION REPAIR REPORT",
        "",
        f"- Artifact-generation parent SHA: `{d['artifact_generation_parent_sha']}`",
        f"- Report-generation parent SHA: `{git_sha('HEAD')}`",
        f"- Scientific parent V3.13 final: `{d['scientific_parent_v313_final']}`",
        f"- Final status: **{d['final_status']}**",
        "",
        "## Defect and repair",
        "",
        f"- Frozen genesis: `{d['genesis_checkpoint_filename']}`",
        f"- Historical report-published local-worktree SHA: `{d['historical_reported_local_worktree_sha256']}`",
        f"- Historical SHA status: **{d['historical_reported_sha_status']}**",
        f"- Canonical hash scheme: `{d['checkpoint_hash_scheme']}`",
        f"- Authoritative genesis chain SHA: `{d['authoritative_genesis_chain_sha256']}`",
        f"- Raw worktree SHA observed during repair audit: `{d['genesis_raw_worktree_sha256_at_audit']}`",
        "",
        "The V3.13 genesis payload is not rewritten. The repair only canonicalizes how checkpoint identity is hashed so line-ending translation cannot change ledger identity.",
        "",
        "## Repair checks",
        "",
    ]
    for k, ok in checks.items():
        lines.append(f"- {'PASS' if ok else 'FAIL'} `{k}`")
    lines += [
        "",
        "## Scientific boundary",
        "",
        f"- Checkpoint #2 created: `{d['checkpoint2_created']}`",
        f"- Genesis payload rewritten: `{d['genesis_payload_rewritten']}`",
        f"- Historical V3.13 report rewritten: `{d['v313_historical_report_rewritten']}`",
        f"- OOS exporter called: `{d['oos_exporter_called']}`",
        f"- Outcome metrics computed: `{d['outcome_metrics_computed']}`",
        f"- Trading engine called: `{d['trading_engine_called']}`",
        f"- Strategy executed: `{d['strategy_executed']}`",
        f"- Future OOS outcome evaluator authorized: `{d['future_oos_outcome_evaluator_authorized']}`",
        f"- Strategy design authorized: `{d['strategy_design_authorized']}`",
        f"- Same-sample H226 research closed: `{d['same_sample_h226_research_closed']}`",
        f"- Historical H226 strategy status: `{d['historical_h226_strategy_status']}`",
        "",
        "## Ledger authority after repair",
        "",
        "Checkpoint #2 and all later checkpoints must use `SHA256_UTF8_LF_NORMALIZED_V1` and must point to the canonical hash of the prior checkpoint. For genesis, the authoritative parent pointer is the canonical LF hash recorded above, not the superseded Windows-local pre-Git hash.",
        "",
        "## Stop rule",
        "",
        "STOP after this repair report. Do not run the OOS exporter or create checkpoint #2 inside V3.13.1. Future blind accrual resumes only after independent review accepts this repair.",
    ]
    REPORT.write_bytes(("\n".join(lines) + "\n").encode("utf-8"))
    print(str(REPORT))


if __name__ == "__main__":
    main()
