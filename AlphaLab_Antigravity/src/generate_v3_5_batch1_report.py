from __future__ import annotations

import json
import os
import subprocess
import pandas as pd


def _git_head(root: str) -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    except Exception:
        return "UNAVAILABLE"


def generate_report():
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    report_dir = os.path.join(root, "AlphaLab_Antigravity", "reports", "v3_5")
    summary_path = os.path.join(report_dir, "batch1_summary.csv")
    if not os.path.exists(summary_path):
        raise FileNotFoundError(summary_path)

    df = pd.read_csv(summary_path)
    if len(df) != 12:
        raise RuntimeError(f"Expected 12 configurations, got {len(df)}")

    parent_sha = _git_head(root)
    gate_cols = [
        "gate_A1", "gate_A2", "gate_A3", "gate_A4",
        "gate_B1", "gate_B2",
        "gate_D4_1", "gate_D4_2",
        "gate_D8_1", "gate_D8_2",
        "gate_Y1", "gate_Y2",
        "gate_E1", "gate_E2",
    ]
    missing = [c for c in gate_cols if c not in df.columns]
    if missing:
        raise RuntimeError(f"Missing hard-gate columns: {missing}")

    lines = [
        "# V3.5 BATCH-1 — H-218 TO H-220 NEW-MECHANISM REPORT",
        "",
        "## Governance",
        "",
        "- Branch: `research/quant-v3.5-h218-new-mechanisms`",
        f"- Artifact-generation parent SHA: `{parent_sha}`",
        "- Authoritative source: `AlphaLab_Antigravity/reports/v3_5/batch1_summary.csv`",
        "- Evaluation: entry-quarter `2018Q2` through `2026Q2`",
        "- Full rolling diagnostics: 30 rolling-4Q windows and 26 rolling-8Q windows",
        "- Full-year hard-gate window: 2019 through 2025",
        "- Costs: spread 25 pips, commission $7/lot, slippage 0 pips baseline",
        "",
        "## Results",
        "",
        "| Config | Family | Trades | Min/Q | Gini | PF | Exp | R4+ | R4 PF | R8+ | R8 PF | Years+ | Top3 +Q | Top5 +Q | Status |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]

    for _, r in df.iterrows():
        lines.append(
            f"| `{r['config_id']}` | {r['family']} | {int(r['total_trades'])} | {int(r['min_trades_q'])} | "
            f"{r['trade_count_gini']:.3f} | {r['pf']:.3f} | ${r['expectancy_usd']:+.2f} | "
            f"{r['rolling4_positive_pct']:.1f}% | {r['rolling4_pf120_pct']:.1f}% | "
            f"{r['rolling8_positive_pct']:.1f}% | {r['rolling8_pf120_pct']:.1f}% | "
            f"{r['profitable_full_year_pct']:.1f}% | {r['top3_positive_q_share_pct']:.1f}% | "
            f"{r['top5_positive_q_share_pct']:.1f}% | **{r['final_status']}** |"
        )

    lines += [
        "",
        "## Full 14-Gate Matrix",
        "",
        "| Config | A1 | A2 | A3 | A4 | B1 | B2 | D4.1 | D4.2 | D8.1 | D8.2 | Y1 | Y2 | E1 | E2 | ALL |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for _, r in df.iterrows():
        vals = ["PASS" if bool(r[c]) else "FAIL" for c in gate_cols]
        allv = "PASS" if bool(r["all_gates_pass"]) else "FAIL"
        lines.append(f"| `{r['config_id']}` | " + " | ".join(vals) + f" | {allv} |")

    lines += ["", "## Primary Failure Reasons", ""]
    for _, r in df.iterrows():
        lines.append(f"- `{r['config_id']}`: {r['primary_failure_reason']}")

    survivors = df[df["all_gates_pass"] == True]
    lines += ["", "## Scientific Decision", ""]
    if len(survivors) == 0:
        lines.append("> **NO H-218→H-220 CONFIGURATION PASSED ALL FROZEN V3.5 DISTRIBUTED-EDGE GATES.**")
    else:
        lines.append(f"> **{len(survivors)} HISTORICAL DISTRIBUTED SURVIVOR(S) PASSED ALL FROZEN V3.5 GATES.**")
        for cfg in survivors["config_id"]:
            lines.append(f"> - `{cfg}`")
        lines.append("> Requires a separate precommitted stability batch; this is not validation.")

    lines += [
        "",
        "## Interpretation Limits",
        "",
        "- Do not optimize a near-miss after reading this report.",
        "- Do not create a directional variant inside this batch after seeing results.",
        "- Rolling windows overlap and are diagnostics, not independent samples.",
        "- A historical survivor is not true OOS evidence.",
    ]

    report_path = os.path.join(root, "V3_5_BATCH1_REPORT.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    manifest = {
        "artifact_generation_parent_sha": parent_sha,
        "authoritative_csv": "AlphaLab_Antigravity/reports/v3_5/batch1_summary.csv",
        "row_count": int(len(df)),
        "config_ids": df["config_id"].tolist(),
        "hard_gate_count": len(gate_cols),
        "hard_gate_columns": gate_cols,
        "survivor_count": int(len(survivors)),
        "report_generated_directly_from_csv": True,
    }
    with open(os.path.join(report_dir, "report_manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    return report_path


if __name__ == "__main__":
    print(generate_report())
