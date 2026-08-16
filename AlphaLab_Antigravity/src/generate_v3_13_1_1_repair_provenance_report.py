from __future__ import annotations

import json
from pathlib import Path
import subprocess

import fresh_oos_v312_contract as v312

ROOT = v312.ROOT
DECISION = ROOT / "AlphaLab_Antigravity/reports/v3_13_1_1/V3_13_1_1_REPAIR_PROVENANCE_DECISION.json"
REPORT = ROOT / "V3_13_1_1_REPAIR_PROVENANCE_CLOSURE_REPORT.md"


def git_sha() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def main() -> None:
    d = json.loads(DECISION.read_text(encoding="utf-8"))
    checks = d.get("checks", {})
    lines = [
        "# V3.13.1.1 REPAIR PROVENANCE CLOSURE REPORT",
        "",
        f"- Execution code HEAD before artifact write: `{d['execution_head_before_artifact_write']}`",
        f"- Report-generation parent SHA: `{git_sha()}`",
        f"- Scientific parent V3.13.1 final: `{d['scientific_parent_v3131_final']}`",
        f"- Prior V3.13.1 raw commit: `{d['v3131_raw_commit']}`",
        f"- Prior raw parent: `{d['v3131_raw_parent']}`",
        f"- Prior artifact-recorded parent: `{d['prior_v3131_artifact_generation_parent_sha']}`",
        f"- Prior provenance issue: **{d['prior_provenance_issue']}**",
        f"- Final status: **{d['final_status']}**",
        "",
        "## Frozen hash authority",
        "",
        f"- Hash scheme: `{d['checkpoint_hash_scheme']}`",
        f"- Authoritative genesis chain SHA: `{d['authoritative_genesis_chain_sha256']}`",
        f"- Checkpoint count: `{d['checkpoint_count']}`",
        "",
        "## Closure checks",
        "",
    ]
    lines += [f"- {'PASS' if ok else 'FAIL'} `{name}`" for name, ok in checks.items()]
    lines += [
        "",
        "## Scientific boundary",
        "",
        f"- Checkpoint #2 created: `{d['checkpoint2_created']}`",
        f"- OOS exporter called: `{d['oos_exporter_called']}`",
        f"- Outcome metrics computed: `{d['outcome_metrics_computed']}`",
        f"- Trading engine called: `{d['trading_engine_called']}`",
        f"- Strategy executed: `{d['strategy_executed']}`",
        f"- Strategy design authorized: `{d['strategy_design_authorized']}`",
        f"- Future OOS outcome evaluator authorized: `{d['future_oos_outcome_evaluator_authorized']}`",
        f"- Same-sample H226 research closed: `{d['same_sample_h226_research_closed']}`",
        f"- Historical H226 strategy status: `{d['historical_h226_strategy_status']}`",
        "",
        "The V3.13.1 scientific hash repair is unchanged. V3.13.1.1 only closes the execution-code provenance ambiguity caused by combining a technical source repair and raw machine artifact in one commit.",
        "",
        "## Stop rule",
        "",
        "Do not acquire OOS data or create checkpoint #2 in this closure chapter. After independent acceptance, blind accrual may resume under the repaired V3.13 ledger protocol.",
    ]
    REPORT.write_bytes(("\n".join(lines) + "\n").encode("utf-8"))


if __name__ == "__main__":
    main()
