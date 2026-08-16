from __future__ import annotations

from pathlib import Path
import json
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "AlphaLab_Antigravity" / "reports" / "v3_10"
REPORT = ROOT / "V3_10_H226_DELAYED_REVERSION_STABILITY_REPORT.md"


def fmt(x, nd=4):
    if pd.isna(x):
        return "NA"
    return f"{float(x):.{nd}f}"


def main() -> None:
    views = pd.read_csv(OUT / "v3_10_8h_view_summary.csv")
    years = pd.read_csv(OUT / "v3_10_8h_year_stability.csv")
    quarters = pd.read_csv(OUT / "v3_10_8h_quarter_stability.csv")
    loo = pd.read_csv(OUT / "v3_10_8h_leave_one_year_out.csv")
    boots = pd.read_csv(OUT / "v3_10_8h_cluster_bootstrap.csv")
    decision = json.loads((OUT / "v3_10_8h_decision.json").read_text(encoding="utf-8"))
    meta = json.loads((OUT / "v3_10_metadata.json").read_text(encoding="utf-8"))

    lines = [
        "# V3.10 H226 DELAYED 8H REVERSION STABILITY REPORT",
        "",
        f"- Artifact-generation parent SHA: `{meta['artifact_generation_parent_sha']}`",
        f"- Scientific parent V3.9 final: `{meta['scientific_parent_v39_final']}`",
        f"- Frozen V3.9 event SHA-256: `{meta['source_v39_event_sha256']}`",
        f"- Canonical dataset: `{meta['canonical_dataset_id']}`",
        f"- Canonical SHA-256: `{meta['canonical_dataset_sha256']}`",
        f"- Horizon: `{meta['horizon']}` only",
        f"- Raw market data read: `{meta['raw_market_data_read']}`",
        f"- Events reconstructed: `{meta['events_reconstructed']}`",
        f"- Trading engine called: `{meta['trading_engine_called']}`",
        f"- Strategy executed: `{meta['strategy_executed']}`",
        "",
        "All H226 trading configurations remain **REJECTED**. This chapter audits only the frozen V3.9 8h event-study clue.",
        "",
        "## Frozen 8h views",
        "",
        "| Cohort | View | N | Mean ATR | Median ATR | Positive % | Gap closed % | Worst5% mean | Median cost ATR | Mean/cost |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for _, r in views.iterrows():
        lines.append(
            f"| {r['cohort']} | {r['view']} | {int(r['event_count'])} | {fmt(r['mean_signed_reversion_atr'])} | "
            f"{fmt(r['median_signed_reversion_atr'])} | {fmt(r['positive_return_pct'],1)}% | {fmt(r['gap_closure_pct'],1)}% | "
            f"{fmt(r['worst5pct_mean_signed_reversion_atr'])} | {fmt(r['median_cost_hurdle_atr'])} | "
            f"{fmt(r['mean_to_median_cost_hurdle_ratio'],2)} |"
        )

    lines += ["", "## Clustered bootstrap", "", "| Cohort | Block | Reps | 95% CI | P(mean>0) |", "|---|---|---:|---|---:|"]
    for _, r in boots.iterrows():
        lines.append(
            f"| {r['cohort']} | {r['block_type']} | {int(r['bootstrap_reps_valid'])} | "
            f"[{fmt(r['ci_2_5'])}, {fmt(r['ci_97_5'])}] | {fmt(r['p_mean_gt_zero_pct'],1)}% |"
        )

    lines += ["", "## Complete-year stability", "", "| Cohort | Positive years / 7 | Worst year mean | Best year mean |", "|---|---:|---:|---:|"]
    for cohort, sub in years.groupby("cohort"):
        vals = sub["mean_signed_reversion_atr"].dropna()
        lines.append(
            f"| {cohort} | {int(sub['positive_mean'].sum())}/7 | {fmt(vals.min() if len(vals) else float('nan'))} | "
            f"{fmt(vals.max() if len(vals) else float('nan'))} |"
        )

    lines += ["", "## Leave-one-year-out stability", "", "| Cohort | Positive LOO / 7 | Min LOO mean | Max LOO mean |", "|---|---:|---:|---:|"]
    for cohort, sub in loo.groupby("cohort"):
        vals = sub["mean_signed_reversion_atr"].dropna()
        lines.append(
            f"| {cohort} | {int(sub['positive_mean'].sum())}/7 | {fmt(vals.min() if len(vals) else float('nan'))} | "
            f"{fmt(vals.max() if len(vals) else float('nan'))} |"
        )

    lines += ["", "## Frozen decision-cohort checks", ""]
    for cohort in decision["decision_cohorts_frozen"]:
        d = decision["detail"][cohort]
        lines += [f"### {cohort}", "", f"- Full N: `{d['full']['n']}`", f"- Full mean: `{d['full']['mean']:+.6f}` ATR", f"- Full median: `{d['full']['median']:+.6f}` ATR", f"- Positive complete years: `{d['positive_complete_years']}/7`", f"- Quarter-block CI: `{d['quarter_block_ci']}`", f"- Year-block CI: `{d['year_block_ci']}`", ""]
        for name, passed in d["checks"].items():
            lines.append(f"- {'PASS' if passed else 'FAIL'} `{name}`")
        lines.append("")

    lines += [
        "## Frozen scientific conclusion",
        "",
        f"> **{decision['mechanism_label']}**",
        "",
        "Regardless of the mechanism label:",
        "",
        "- all H226 trading strategies remain **REJECTED**;",
        "- no strategy design is authorized by V3.10;",
        "- no direction/subperiod split may be converted into a filter inside this chapter;",
        "- no new horizon or threshold is introduced.",
        "",
        "## Artifact dimensions",
        "",
        f"- View summary rows: `{len(views)}`",
        f"- Year rows: `{len(years)}`",
        f"- Quarter rows: `{len(quarters)}`",
        f"- Leave-one-year-out rows: `{len(loo)}`",
        f"- Bootstrap rows: `{len(boots)}`",
        "",
        "## Stop rule",
        "",
        "STOP after this report. No H227, no delayed-reversion strategy, no H226 tuning, no new asset/timeframe and no horizon extension are authorized.",
    ]
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(REPORT)


if __name__ == "__main__":
    main()
