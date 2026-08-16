from __future__ import annotations

"""Generate the V3.12 human readiness report from machine artifacts only."""

from pathlib import Path
import json
import subprocess

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
REPORT_DIR = ROOT / "AlphaLab_Antigravity" / "reports" / "v3_12"
READINESS_JSON = REPORT_DIR / "V3_12_FRESH_OOS_READINESS.json"
COUNTS_CSV = REPORT_DIR / "v3_12_fresh_oos_event_counts.csv"
OUT = ROOT / "V3_12_FRESH_OOS_FORWARD_LOCK_REPORT.md"


def git_head() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        return "UNAVAILABLE"


def generate() -> str:
    if not READINESS_JSON.exists() or not COUNTS_CSV.exists():
        raise RuntimeError("V3.12 readiness machine artifacts missing")
    r = json.loads(READINESS_JSON.read_text(encoding="utf-8"))
    counts = pd.read_csv(COUNTS_CSV)
    if bool(r.get("outcome_metrics_computed")):
        raise RuntimeError("V3.12 report refuses readiness artifact containing outcome metrics")
    if bool(r.get("strategy_executed")) or bool(r.get("trading_engine_called")):
        raise RuntimeError("V3.12 report refuses strategy/trading execution")

    readiness = r["readiness"]
    checks = readiness.get("checks", {})
    lines = [
        "# V3.12 FRESH-OOS FORWARD LOCK REPORT",
        "",
        f"- Artifact-generation parent SHA: `{r['artifact_generation_parent_sha']}`",
        f"- Report-generation parent SHA: `{git_head()}`",
        f"- Scientific parent V3.11 final: `{r['scientific_parent_v311_final']}`",
        f"- Canonical dataset: `{r['canonical_dataset_id']}`",
        f"- Canonical SHA-256: `{r['canonical_dataset_sha256']}`",
        f"- Canonical freeze cutoff: `{r['canonical_freeze_cutoff_utc']}`",
        f"- Bridge quarter quarantined: `{r['bridge_quarter_quarantined']}`",
        f"- First complete fresh-OOS decision quarter: `{r['first_complete_fresh_oos_decision_quarter']}`",
        f"- Fresh-OOS file present: `{r['fresh_oos_file_present']}`",
        f"- Fresh-OOS provenance present: `{r['fresh_oos_provenance_present']}`",
        f"- Outcome metrics computed: `{r['outcome_metrics_computed']}`",
        f"- Trading engine called: `{r['trading_engine_called']}`",
        f"- Strategy executed: `{r['strategy_executed']}`",
        f"- Strategy design authorized: `{r['strategy_design_authorized']}`",
        f"- Same-sample H226 research closed: `{r['same_sample_h226_research_closed']}`",
        "",
        "## Fresh-OOS maturity contract",
        "",
        f"- Minimum complete quarters: `{r['maturity_contract']['minimum_complete_quarters']}`",
        f"- Minimum C1 events total: `{r['maturity_contract']['minimum_c1_events']}`",
        f"- Minimum C4 events total: `{r['maturity_contract']['minimum_c4_events']}`",
        f"- Minimum C1 events per complete quarter: `{r['maturity_contract']['minimum_c1_events_each_complete_quarter']}`",
        f"- Minimum C4 events per complete quarter: `{r['maturity_contract']['minimum_c4_events_each_complete_quarter']}`",
        "",
        "## Current readiness",
        "",
        f"- Status: **{r['final_status']}**",
        f"- Complete decision quarters: `{len(readiness.get('complete_decision_quarters', []))}`",
        f"- C1 events in complete decision quarters: `{readiness.get('c1_total', 0)}`",
        f"- C4 events in complete decision quarters: `{readiness.get('c4_total', 0)}`",
        f"- Minimum C1 / complete quarter: `{readiness.get('c1_min_per_complete_quarter', 0)}`",
        f"- Minimum C4 / complete quarter: `{readiness.get('c4_min_per_complete_quarter', 0)}`",
        "",
        "### Maturity checks",
        "",
    ]
    for name, ok in checks.items():
        lines.append(f"- {'PASS' if ok else 'FAIL'} `{name}`")

    lines.extend(["", "## Readiness event counts", ""])
    if counts.empty:
        lines.append("No complete-quarter fresh-OOS C1/C4 eligibility counts exist yet.")
    else:
        lines.append("| Quarter | C1 eligibility events | C4 eligibility events |")
        lines.append("|---|---:|---:|")
        for _, row in counts.iterrows():
            lines.append(f"| {row['quarter']} | {int(row['c1_events'])} | {int(row['c4_events'])} |")

    if r.get("fresh_oos_temporal_partition"):
        t = r["fresh_oos_temporal_partition"]
        lines.extend([
            "",
            "## Fresh-OOS temporal partition",
            "",
            f"- Rows: `{t['row_count']}`",
            f"- First bar open UTC: `{t['first_bar_open_utc']}`",
            f"- Last bar open UTC: `{t['last_bar_open_utc']}`",
            f"- Bridge/quarantine rows: `{t['bridge_quarantine_rows']}`",
            f"- Dataset SHA-256: `{r['fresh_oos_dataset_sha256']}`",
        ])

    lines.extend([
        "",
        "## Scientific boundary",
        "",
        "V3.12 is an accrual/readiness chapter only. It contains no forward-return, MFE/MAE, gap-closure, PF, expectancy, or trading-strategy result.",
        "",
        "All historical H226 strategies remain **REJECTED** and same-sample H226 research remains **CLOSED**.",
        "",
        "A future OOS outcome evaluator requires a new, separately frozen precommit and may not be created until the maturity contract passes.",
        "",
        "## Stop rule",
        "",
        "STOP after this report. Do not calculate OOS effect statistics, design an H226 descendant, or treat bridge/quarantined 2026Q3 bars as fresh-OOS decision evidence.",
    ])
    text = "\n".join(lines) + "\n"
    OUT.write_text(text, encoding="utf-8")
    return text


if __name__ == "__main__":
    generate()
    print(str(OUT))
