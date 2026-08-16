from __future__ import annotations

from pathlib import Path
import json
import subprocess

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
REPORT_DIR = ROOT / "AlphaLab_Antigravity" / "reports" / "v3_8"
OUT = ROOT / "V3_8_CANONICAL_NEW_MECHANISM_REPORT.md"


def git_head() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        return "UNAVAILABLE"


def fmt(x, nd=3):
    if pd.isna(x):
        return "NA"
    return f"{float(x):.{nd}f}"


def generate() -> str:
    configs_path = REPORT_DIR / "v3_8_all_configs.csv"
    gates_path = REPORT_DIR / "v3_8_gate_matrix.csv"
    meta_path = REPORT_DIR / "v3_8_metadata.json"
    for p in (configs_path, gates_path, meta_path):
        if not p.exists():
            raise RuntimeError(f"Missing V3.8 machine artifact: {p}")

    df = pd.read_csv(configs_path)
    gates = pd.read_csv(gates_path)
    meta = json.loads(meta_path.read_text(encoding="utf-8"))

    if len(df) != 24 or len(gates) != 24:
        raise RuntimeError("V3.8 report requires exactly 24 configs")
    if int(meta.get("gate_count", 0)) != 14:
        raise RuntimeError("V3.8 report requires frozen 14-gate contract")

    gate_names = list(meta["gate_names"])
    for g in gate_names:
        if g not in df.columns:
            raise RuntimeError(f"Missing gate column {g}")

    pass_counts = df[gate_names].astype(bool).sum(axis=1)
    df = df.copy()
    df["gate_pass_count"] = pass_counts

    survivors = df[df["all_gates_pass"].astype(bool)]["config_id"].tolist()
    if survivors != list(meta.get("survivors", [])):
        raise RuntimeError("Survivor list disagrees with metadata")

    lines = [
        "# V3.8 CANONICAL V2 NEW-MECHANISM REPORT",
        "",
        f"- Artifact-generation parent SHA: `{meta['artifact_generation_parent_sha']}`",
        f"- Report-generation parent SHA: `{git_head()}`",
        f"- Canonical dataset: `{meta['canonical_dataset_id']}`",
        f"- Canonical SHA-256: `{meta['canonical_dataset_sha256']}`",
        f"- Execution engine: `{meta['execution_engine']}`",
        f"- Execution contract: `{meta['execution_contract']}`",
        f"- Configurations: `{meta['configuration_count']}` across `{meta['family_count']}` families",
        f"- Frozen hard gates per config: `{meta['gate_count']}`",
        f"- Costs: spread `{meta['spread_pips']}` pips, commission `${meta['commission_per_lot_usd']}/lot`, slippage `{meta['slippage_pips']}` pips",
        "",
        "## Configuration results",
        "",
        "| Config | Family | Trades | MinQ | PF | Exp $ | R4+ | R4 PF>=1.2 | R8+ | R8 PF>=1.2 | Years+ | Top3 +Q | Gates | Final |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]

    for _, r in df.sort_values("config_id").iterrows():
        lines.append(
            "| {config} | {family} | {trades} | {minq} | {pf} | {exp} | {r4p}% | {r4pf}% | {r8p}% | {r8pf}% | {yp}% | {top3}% | {gc}/14 | {status} |".format(
                config=r["config_id"],
                family=r["family"],
                trades=int(r["total_trades"]),
                minq=int(r["min_trades_q"]),
                pf=fmt(r["pf"]),
                exp=fmt(r["expectancy_usd"], 2),
                r4p=fmt(r["rolling4_positive_pct"], 1),
                r4pf=fmt(r["rolling4_pf120_pct"], 1),
                r8p=fmt(r["rolling8_positive_pct"], 1),
                r8pf=fmt(r["rolling8_pf120_pct"], 1),
                yp=fmt(r["profitable_full_year_pct"], 1),
                top3=fmt(r["top3_positive_q_share_pct"], 1),
                gc=int(r["gate_pass_count"]),
                status=r["final_status"],
            )
        )

    lines += ["", "## Family-level descriptive summary", ""]
    for family, sub in df.groupby("family", sort=True):
        max_gates = int(sub["gate_pass_count"].max())
        family_survivors = sub[sub["all_gates_pass"].astype(bool)]["config_id"].tolist()
        lines += [
            f"### {family}",
            "",
            f"- Config count: `{len(sub)}`",
            f"- Maximum frozen gates passed by any family config: `{max_gates}/14`",
            f"- Historical distributed survivors: `{family_survivors if family_survivors else 'None'}`",
            "",
        ]

    lines += [
        "## Gate integrity",
        "",
        "All configuration verdicts use the simultaneous frozen A1-A4, B1-B2, D4_1-D4_2, D8_1-D8_2, Y1-Y2, E1-E2 gates. A positive PF or expectancy alone cannot create a survivor.",
        "",
        "## Scientific conclusion",
        "",
        f"> **{meta['batch_conclusion']}**",
        "",
    ]

    if survivors:
        lines += [
            "The survivor list is frozen above. V3.8 does not tune, simplify, direction-filter or otherwise modify any survivor. A separate independently precommitted stability batch is required.",
            "",
        ]
    else:
        lines += [
            "No V3.8 config passed all frozen gates. No near-miss is automatically promoted and no threshold is modified inside this chapter.",
            "",
        ]

    lines += [
        "## Stop rule",
        "",
        "V3.8 stops after this report. No H-227, parameter tuning, direction removal, new asset/timeframe or automatic second batch is authorized.",
        "",
    ]

    text = "\n".join(lines)
    OUT.write_text(text, encoding="utf-8")
    return text


if __name__ == "__main__":
    print(generate())
