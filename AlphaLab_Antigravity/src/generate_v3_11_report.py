from __future__ import annotations

from pathlib import Path
import json

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "AlphaLab_Antigravity" / "reports" / "v3_11"
REPORT = ROOT / "V3_11_H226_ECONOMIC_MATERIALITY_CLOSURE_REPORT.md"


def _fmt(x: float, n: int = 4) -> str:
    return "nan" if pd.isna(x) else f"{float(x):+.{n}f}"


def generate() -> str:
    views = pd.read_csv(OUT / "v3_11_8h_economic_views.csv")
    years = pd.read_csv(OUT / "v3_11_8h_economic_years.csv")
    loo = pd.read_csv(OUT / "v3_11_8h_economic_leave_one_year_out.csv")
    boot = pd.read_csv(OUT / "v3_11_8h_economic_cluster_bootstrap.csv")
    decision = json.loads((OUT / "v3_11_8h_economic_decision.json").read_text(encoding="utf-8"))
    meta = json.loads((OUT / "v3_11_metadata.json").read_text(encoding="utf-8"))

    lines = [
        "# V3.11 H226 ECONOMIC-MATERIALITY & ASYMMETRY CLOSURE REPORT",
        "",
        f"- Artifact-generation parent SHA: `{meta['artifact_generation_parent_sha']}`",
        f"- Scientific parent V3.10 final: `{meta['scientific_parent_v310_final']}`",
        f"- Frozen V3.9 event SHA-256: `{meta['source_v39_events_sha256']}`",
        f"- Canonical dataset: `{meta['canonical_dataset_id']}`",
        f"- Canonical SHA-256: `{meta['canonical_dataset_sha256']}`",
        f"- Horizon: `{meta['horizon']}` only",
        f"- Round-trip price-equivalent cost hurdle: `${meta['roundtrip_price_equiv_usd_per_oz']:.2f}/oz`",
        f"- Raw market data read: `{meta['raw_market_data_read']}`",
        f"- Events reconstructed: `{meta['events_reconstructed']}`",
        f"- Trading engine called: `{meta['trading_engine_called']}`",
        f"- Strategy executed: `{meta['strategy_executed']}`",
        "",
        "All H226 trading strategies remain **REJECTED**. V3.11 is a final same-sample economic-scale diagnostic only.",
        "",
        "## Frozen economic views",
        "",
        "| Cohort | View | N | Raw mean ATR | Excess mean ATR | Excess median ATR | Excess>0 | Median cost ATR | Worst5% excess |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for _, r in views.iterrows():
        lines.append(
            f"| {r['cohort']} | {r['view']} | {int(r['event_count'])} | {_fmt(r['mean_raw_reversion_atr'])} | "
            f"{_fmt(r['mean_excess_reversion_atr'])} | {_fmt(r['median_excess_reversion_atr'])} | "
            f"{float(r['positive_excess_pct']):.1f}% | {float(r['median_cost_hurdle_atr']):.4f} | {_fmt(r['worst5pct_mean_excess_atr'])} |"
        )

    lines += ["", "## Cluster bootstrap on mean excess-reversion ATR", "", "| Cohort | Block | Reps | 95% CI | P(mean excess>0) |", "|---|---|---:|---|---:|"]
    for _, r in boot.iterrows():
        lines.append(
            f"| {r['cohort']} | {r['block_type']} | {int(r['bootstrap_reps_valid'])} | "
            f"[{float(r['ci_2_5']):+.4f}, {float(r['ci_97_5']):+.4f}] | {float(r['p_mean_excess_gt_zero_pct']):.1f}% |"
        )

    lines += ["", "## Decision-cohort economic checks"]
    for cohort in ("H226-C1", "H226-C4"):
        d = decision["detail"][cohort]
        v = views[views["cohort"] == cohort].set_index("view")
        y = years[years["cohort"] == cohort]
        l = loo[loo["cohort"] == cohort]
        lines += [
            "",
            f"### {cohort}",
            "",
            f"- FULL N: `{d['full']['n']}`",
            f"- FULL raw mean: `{d['full']['mean_raw']:+.6f}` ATR",
            f"- FULL mean excess: `{d['full']['mean_excess']:+.6f}` ATR",
            f"- FULL median excess: `{d['full']['median_excess']:+.6f}` ATR",
            f"- PRE_2025 mean excess: `{float(v.loc['PRE_2025','mean_excess_reversion_atr']):+.6f}` ATR",
            f"- RECENT mean excess: `{float(v.loc['RECENT','mean_excess_reversion_atr']):+.6f}` ATR",
            f"- UP_GAP mean excess: `{float(v.loc['UP_GAP','mean_excess_reversion_atr']):+.6f}` ATR",
            f"- DOWN_GAP mean excess: `{float(v.loc['DOWN_GAP','mean_excess_reversion_atr']):+.6f}` ATR",
            f"- Positive complete years: `{int(y['positive_mean_excess'].sum())}/7`",
            f"- Minimum leave-one-year-out mean excess: `{float(l['mean_excess_reversion_atr'].min()):+.6f}` ATR",
            f"- Quarter-block CI: `[{d['quarter_block_ci'][0]:+.6f}, {d['quarter_block_ci'][1]:+.6f}]`",
            f"- Year-block CI: `[{d['year_block_ci'][0]:+.6f}, {d['year_block_ci'][1]:+.6f}]`",
            "",
        ]
        for name, ok in d["checks"].items():
            lines.append(f"- {'PASS' if ok else 'FAIL'} `{name}`")

    lines += [
        "",
        "## Frozen scientific conclusion",
        "",
        f"> **{decision['mechanism_label']}**",
        "",
        "Regardless of the label:",
        "",
        "- all H226 trading strategies remain **REJECTED**;",
        "- same-sample H226 research is now **CLOSED**;",
        "- strategy design is **not authorized**;",
        "- no UP/DOWN or PRE/RECENT split may be converted into a filter on this sample;",
        "- any future H226-inspired strategy requires fresh out-of-sample data or a separately justified independent dataset.",
        "",
        "## Stop rule",
        "",
        "STOP after this report. No H226 descendant, threshold tuning, direction filter, new horizon, SL/TP/RR change, asset/timeframe switch, or same-sample strategy design is authorized.",
    ]
    text = "\n".join(lines) + "\n"
    REPORT.write_text(text, encoding="utf-8")
    return text


if __name__ == "__main__":
    print(generate())
