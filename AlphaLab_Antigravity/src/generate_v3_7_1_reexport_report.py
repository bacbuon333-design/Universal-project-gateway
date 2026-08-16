"""Generate V3.7.1 canonical re-export conclusion from machine artifacts only."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
PROV_DIR = ROOT / "AlphaLab_Antigravity" / "data" / "provenance"
REPORT_DIR = ROOT / "AlphaLab_Antigravity" / "reports" / "v3_7_1"
REPORT_PATH = ROOT / "V3_7_1_CANONICAL_REEXPORT_REPORT.md"
MANIFEST_PATH = PROV_DIR / "GOLD_M30_CANONICAL.manifest.json"
SIDECAR_PATH = PROV_DIR / "GOLD_M30_CANONICAL.source.json"
STRUCTURAL_PATH = REPORT_DIR / "GOLD_M30_CANONICAL.structural_audit.json"
DECISION_PATH = REPORT_DIR / "V3_7_1_REEXPORT_DECISION.json"


def git_sha(ref: str = "HEAD") -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", ref], cwd=ROOT, text=True).strip()
    except Exception:
        return "UNKNOWN_GIT_SHA"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def generate() -> Path:
    manifest = load(MANIFEST_PATH)
    sidecar = load(SIDECAR_PATH)
    structural = load(STRUCTURAL_PATH)
    decision = load(DECISION_PATH)
    parent_sha = git_sha("HEAD")

    blockers = decision.get("blocking_reasons") or []
    blockers_md = "\n".join(f"- `{x}`" for x in blockers) if blockers else "- None"

    lines = [
        "# V3.7.1 CONTROLLED CANONICAL RE-EXPORT REPORT",
        "",
        f"- Artifact-generation parent SHA: `{parent_sha}`",
        f"- Dataset: `{manifest['dataset_id']}`",
        f"- Path: `{manifest['relative_path']}`",
        f"- SHA-256: `{manifest['sha256']}`",
        f"- Rows: `{manifest['row_count']}`",
        f"- First bar open UTC: `{manifest['first_bar_open_utc']}`",
        f"- Last bar open UTC: `{manifest['last_bar_open_utc']}`",
        f"- Timestamp semantic: `{manifest['timestamp_semantic']}`",
        f"- Timezone: `{manifest['timestamp_timezone_status']} / {manifest['timestamp_timezone']}`",
        f"- Lineage: `{manifest['lineage_status']}`",
        f"- Structural validation: `{manifest['structural_validation_status']}`",
        f"- Coverage: `{manifest['coverage_status']}`",
        f"- Research eligibility: **`{decision['research_eligibility']}`**",
        "",
        "## Source identity",
        "",
        f"- Source type: `{sidecar['source_type']}`",
        f"- Broker/company: `{sidecar['broker_company']}`",
        f"- Broker server: `{sidecar['broker_server']}`",
        f"- Broker symbol: `{sidecar['broker_symbol']}`",
        f"- Extraction method: `{sidecar['exporter_or_extraction_method']}`",
        f"- Exporter Git SHA: `{sidecar['exporter_git_sha']}`",
        "",
        "No account login or account-holder name is part of the committed provenance.",
        "",
        "## Structural audit",
        "",
        f"- Median cadence minutes: `{structural['median_delta_minutes']}`",
        f"- Exact 30-minute deltas: `{structural['pct_exact_30m_deltas']:.4f}%`",
        f"- Duplicate timestamps: `{structural['duplicate_timestamp_count']}`",
        f"- Non-monotonic timestamps: `{structural['non_monotonic_timestamp_count']}`",
        f"- OHLC violations: `{structural['ohlc']['total_violation_count']}`",
        "",
        "## Blocking reasons",
        "",
        blockers_md,
        "",
        "## Scientific conclusion",
        "",
    ]

    if decision["research_eligibility"] == "ELIGIBLE":
        lines.extend([
            "> **GOLD_M30_CANONICAL IS CANONICALLY VERIFIED AND RESEARCH-ELIGIBLE UNDER THE FROZEN V3.7/V3.7.1 DATA CONTRACT.**",
            "",
            "This authorizes the dataset for a future independently precommitted research chapter. It does not validate any previous strategy or create a new strategy by itself.",
        ])
    else:
        lines.extend([
            "> **GOLD_M30_CANONICAL REMAINS RESEARCH-BLOCKED.**",
            "",
            "No strategy research is authorized until every listed blocker is resolved without changing the frozen evidence standard.",
        ])

    lines.extend([
        "",
        "## Stop rule",
        "",
        "V3.7.1 ends after data export, provenance validation and this report. No H-221 or strategy backtest is started automatically.",
        "",
    ])

    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
    return REPORT_PATH


if __name__ == "__main__":
    print(generate())
