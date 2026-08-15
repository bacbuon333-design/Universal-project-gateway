"""Machine-generated report for V3.4 H-215→H-217 Batch 1.

This script reads only the authoritative CSV produced by
experiment_v3_4_h215_to_h217_directional.py. It does not recompute or alter
strategy results and does not choose configurations.
"""

from __future__ import annotations

import json
import os
import subprocess

import pandas as pd


def git_sha(ref: str = "HEAD") -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", ref], text=True).strip()
    except Exception:
        return "UNKNOWN"


def bool_mark(value) -> str:
    return "PASS" if bool(value) else "FAIL"


def pct(value) -> str:
    if pd.isna(value):
        return "N/A"
    return f"{float(value):.1f}%"


def generate_report() -> str:
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    out_dir = os.path.join(root, "AlphaLab_Antigravity", "reports", "v3_4")
    summary_path = os.path.join(out_dir, "batch1_directional_summary.csv")
    if not os.path.exists(summary_path):
        raise FileNotFoundError(f"Run V3.4 Batch-1 runner first: {summary_path}")

    df = pd.read_csv(summary_path)
    expected_ids = [
        "H-215-C1", "H-215-C2", "H-215-C3", "H-215-C4",
        "H-216-C1", "H-216-C2", "H-216-C3", "H-216-C4",
        "H-217-C1", "H-217-C2", "H-217-C3", "H-217-C4",
    ]
    assert df["config_id"].tolist() == expected_ids, "Authoritative result matrix does not match frozen 12-config precommit"
    assert len(df) == 12
    assert df["config_id"].is_unique

    parent_sha = git_sha("HEAD")
    survivors = df[df["all_gates_pass"] == True].copy()  # noqa: E712

    lines = [
        "# V3.4 BATCH-1 — H-215 TO H-217 DIRECTIONAL FOLLOW-UP REPORT",
        "",
        "## 1. Governance",
        "",
        "- Branch: `research/quant-v3.4-h215-directional-followup`",
        f"- Artifact-generation parent SHA: `{parent_sha}`",
        "- Authoritative result source: `AlphaLab_Antigravity/reports/v3_4/batch1_directional_summary.csv`",
        "- Evaluation window: entry-quarter `2018Q2` through `2026Q2` (33 complete quarters)",
        "- Baseline costs: spread 25.0 pips, commission $7.00/lot, slippage 0.0 pips",
        "- Research disclosure: Long-only direction was motivated by already-observed V3.3/V3.3.1 historical asymmetry. This is exploratory historical follow-up, not validation.",
        "",
        "## 2. Authoritative Result Table",
        "",
        "| Config | Family | Source symmetric | Trades | Min/Q | Median/Q | Max share | Gini | PF | Expectancy | R4 positive | R4 PF>=1.20 | Top3 +Q | Top5 +Q | Status |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]

    for _, r in df.iterrows():
        lines.append(
            "| `{config}` | {family} | `{source}` | {trades} | {minq} | {med:.1f} | {share:.1f}% | {gini:.3f} | {pf:.3f} | ${exp:+.2f} | {r4p:.1f}% | {r4pf:.1f}% | {top3} | {top5} | **{status}** |".format(
                config=r["config_id"],
                family=r["family"],
                source=r["source_symmetric_config"],
                trades=int(r["total_trades"]),
                minq=int(r["min_trades_q"]),
                med=float(r["median_trades_q"]),
                share=float(r["max_q_share_pct"]),
                gini=float(r["trade_count_gini"]),
                pf=float(r["pf"]),
                exp=float(r["expectancy_usd"]),
                r4p=float(r["rolling4_positive_pct"]),
                r4pf=float(r["rolling4_pf120_pct"]),
                top3=pct(r["top3_positive_q_share_pct"]),
                top5=pct(r["top5_positive_q_share_pct"]),
                status=r["final_status"],
            )
        )

    lines += [
        "",
        "## 3. Frozen Hard-Gate Matrix",
        "",
        "| Config | A1 min/Q | A2 max share | A3 max/median | A4 Gini | B1 Top3 | B2 Top5 | D1 R4+ | D2 R4 PF | E1 PF | E2 Exp | ALL |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]

    gate_cols = ["gate_A1", "gate_A2", "gate_A3", "gate_A4", "gate_B1", "gate_B2", "gate_D1", "gate_D2", "gate_E1", "gate_E2"]
    for _, r in df.iterrows():
        marks = [bool_mark(r[c]) for c in gate_cols]
        lines.append(
            f"| `{r['config_id']}` | " + " | ".join(marks) + f" | {bool_mark(r['all_gates_pass'])} |"
        )

    lines += [
        "",
        "## 4. Primary Failure Reasons",
        "",
    ]
    for _, r in df.iterrows():
        lines.append(f"- `{r['config_id']}`: {r['primary_failure_reason']}")

    lines += [
        "",
        "## 5. Directional Follow-up vs Symmetric V3.3.1 Baseline",
        "",
        "This comparison is diagnostic context only. It is not independent evidence because the directional follow-up was motivated by the earlier historical result.",
        "",
        "| Config | Source | Long-only PF | Symmetric PF | Long-only Exp | Symmetric Exp | Long-only R4+ | Symmetric R4+ |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for _, r in df.iterrows():
        lines.append(
            f"| `{r['config_id']}` | `{r['source_symmetric_config']}` | {float(r['pf']):.3f} | {float(r['symmetric_v3_3_1_pf']):.3f} | "
            f"${float(r['expectancy_usd']):+.2f} | ${float(r['symmetric_v3_3_1_expectancy']):+.2f} | "
            f"{float(r['rolling4_positive_pct']):.1f}% | {float(r['symmetric_v3_3_1_r4_positive_pct']):.1f}% |"
        )

    lines += [
        "",
        "## 6. Scientific Decision",
        "",
    ]

    if len(survivors) == 0:
        lines.append("> **NO H-215→H-217 CONFIGURATION PASSED ALL FROZEN V3.4 DISTRIBUTED-EDGE GATES.**")
        lines.append("")
        lines.append("No new configuration may be added or tuned automatically. Stop for independent audit.")
    else:
        ids = ", ".join(f"`{x}`" for x in survivors["config_id"].tolist())
        lines.append(f"> **{len(survivors)} HISTORICAL DIRECTIONAL SURVIVOR(S): {ids}.**")
        lines.append("")
        lines.append("These are exploratory historical survivors only. They require a separately precommitted stability batch and later true future OOS. Do not optimize them in this batch.")

    lines += [
        "",
        "## 7. Interpretation Limits",
        "",
        "- Do not claim a universal Gold Long bias.",
        "- Do not treat V3.3.1 and V3.4 as independent samples.",
        "- Do not infer validation from a historical pass because Long-only direction was chosen after earlier historical diagnostics were observed.",
        "- Do not launch H-218+, parameter optimization, cross-asset tests, or another timeframe before independent audit.",
    ]

    report = "\n".join(lines) + "\n"
    report_path = os.path.join(root, "V3_4_BATCH1_REPORT.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)

    # Machine-readable report manifest. This makes no claim that Markdown is a
    # separate independent calculation; Markdown is a deterministic rendering
    # of the authoritative CSV.
    manifest = {
        "artifact_generation_parent_sha": parent_sha,
        "authoritative_csv": "AlphaLab_Antigravity/reports/v3_4/batch1_directional_summary.csv",
        "row_count": int(len(df)),
        "config_ids": df["config_id"].tolist(),
        "survivor_count": int(len(survivors)),
        "report_generated_directly_from_csv": True,
        "manual_numeric_table_copying": False,
        "hard_gate_columns_rendered": gate_cols,
    }
    manifest_path = os.path.join(out_dir, "report_manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print(f"Generated: {report_path}")
    print(f"Generated: {manifest_path}")
    print(f"Artifact-generation parent SHA: {parent_sha}")
    print(f"Survivors: {len(survivors)}")
    return report_path


if __name__ == "__main__":
    generate_report()
