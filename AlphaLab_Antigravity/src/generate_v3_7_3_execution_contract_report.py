from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DECISION = ROOT / "AlphaLab_Antigravity" / "reports" / "v3_7_3" / "V3_7_3_EXECUTION_CONTRACT_DECISION.json"
OUT = ROOT / "V3_7_3_EXECUTION_CONTRACT_REPORT.md"


def git_head() -> str:
    try:
        return subprocess.check_output(["git","rev-parse","HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        return "UNAVAILABLE"


def main() -> None:
    d = json.loads(DECISION.read_text(encoding="utf-8"))
    lines = [
        "# V3.7.3 CANONICAL EXECUTION CONTRACT REPORT",
        "",
        f"- Artifact-generation parent SHA: `{git_head()}`",
        f"- Canonical dataset: `{d['canonical_dataset_id']}`",
        f"- SHA-256: `{d['canonical_dataset_sha256']}`",
        f"- Legacy gap-stop defect confirmed: `{d['legacy_execution_defect_confirmed']}`",
        f"- Legacy engine modified: `{d['legacy_engine_modified']}`",
        f"- Real-market strategy executed: `{d['real_market_strategy_executed']}`",
        f"- Synthetic unit execution only: `{d['synthetic_unit_execution_only']}`",
        f"- Final status: **`{d['status']}`**",
        "",
        "## Confirmed legacy defect",
        "",
    ]
    for k,v in d["discovered_defect_checks"].items():
        lines.append(f"- {k}: `{'PASS' if v else 'FAIL'}`")
    lines += ["", "## Hardened contract checks", ""]
    for k,v in d["hardened_contract_checks"].items():
        lines.append(f"- {k}: `{'PASS' if v else 'FAIL'}`")
    b = d["post_evaluation_buffer"]
    lines += [
        "",
        "## Post-evaluation buffer",
        "",
        f"- Evaluation end: `{b['evaluation_end']}`",
        f"- Dataset last datetime: `{b['dataset_last_datetime']}`",
        f"- Required buffer minutes: `{b['required_buffer_minutes']}`",
        f"- Available buffer minutes: `{b['available_buffer_minutes']}`",
        f"- Buffer check: `{'PASS' if b['pass'] else 'FAIL'}`",
        "",
        "## Scientific conclusion",
        "",
        f"> **{d['status']}**",
        "",
        "A PASS authorizes the hardened canonical execution adapter for a future independently precommitted research chapter. It does not validate any legacy backtest and does not start a strategy.",
        "",
        "## Stop rule",
        "",
        "No H-221, LMDC rerun, parameter tuning, or new mechanism batch is executed by V3.7.3.",
    ]
    OUT.write_text("\n".join(lines)+"\n", encoding="utf-8")


if __name__ == "__main__":
    main()
