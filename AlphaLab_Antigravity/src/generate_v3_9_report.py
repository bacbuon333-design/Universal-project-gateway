from __future__ import annotations

"""Generate the V3.9 human report strictly from committed machine artifacts."""

from pathlib import Path
import json
import subprocess

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
R = ROOT / "AlphaLab_Antigravity" / "reports" / "v3_9"
OUT = ROOT / "V3_9_LOSS_TAIL_MECHANISM_REPORT.md"


def git_head() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        return "UNAVAILABLE"


def pct(x) -> str:
    return "NA" if pd.isna(x) else f"{float(x):.1f}%"


def num(x, d=3) -> str:
    return "NA" if pd.isna(x) else f"{float(x):.{d}f}"


def generate() -> str:
    loss = pd.read_csv(R / "v3_9_loss_concentration_all_configs.csv")
    ev = pd.read_csv(R / "v3_9_h226_event_summary.csv")
    years = pd.read_csv(R / "v3_9_h226_year_stability.csv")
    boot = pd.read_csv(R / "v3_9_h226_block_bootstrap.csv")
    decision = json.loads((R / "v3_9_h226_mechanism_decision.json").read_text(encoding="utf-8"))
    meta = json.loads((R / "v3_9_metadata.json").read_text(encoding="utf-8"))

    if len(loss) != 24:
        raise RuntimeError("V3.9 report expected 24 V3.8 loss rows")

    lines = [
        "# V3.9 LOSS-CONCENTRATION & H226 TAIL-MECHANISM REPORT",
        "",
        f"- Artifact-generation parent SHA: `{meta['artifact_generation_parent_sha']}`",
        f"- Report-generation parent SHA: `{git_head()}`",
        f"- Scientific parent: `{meta['scientific_parent_v38_final']}`",
        f"- Canonical dataset: `{meta['canonical_dataset_id']}`",
        f"- Canonical SHA-256: `{meta['canonical_dataset_sha256']}`",
        f"- Trading engine called: `{meta['trading_engine_called']}`",
        f"- Strategy executed: `{meta['strategy_executed']}`",
        f"- Frozen V3.8 strategy conclusion: **{meta['v38_strategy_conclusion_frozen']}**",
        "",
        "## Part A — V3.8 loss-concentration diagnostics",
        "",
        "These diagnostics do not change any V3.8 rejection.",
        "",
        "| Config | Family | PF | Exp $ | NegQ | Worst3 neg-Q | Worst5 neg-Q | Worst5% trade-loss share | Loss CVaR95 $ | Max/median loss |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for _, r in loss.sort_values("config_id").iterrows():
        lines.append(
            f"| {r['config_id']} | {r['family']} | {float(r['v38_pf']):.3f} | {float(r['v38_expectancy_usd']):+.2f} | "
            f"{int(r['negative_quarter_count'])} | {pct(r['worst3_negative_q_loss_share_pct'])} | {pct(r['worst5_negative_q_loss_share_pct'])} | "
            f"{pct(r['worst5pct_losing_trade_loss_share_pct'])} | {num(r['loss_cvar95_abs_usd'], 2)} | {num(r['largest_loss_to_median_loss_ratio'], 2)} |"
        )

    h226 = loss[loss["config_id"].isin(["H226-C1", "H226-C2", "H226-C3", "H226-C4"])].sort_values("config_id")
    lines += [
        "",
        "## H226 rejected-strategy loss profile",
        "",
        "| Config | PF | Exp $ | R8 positive | Profitable years | Worst1 neg-Q | Worst3 neg-Q | Worst1% trade-loss share | Worst5% trade-loss share |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for _, r in h226.iterrows():
        lines.append(
            f"| {r['config_id']} | {float(r['v38_pf']):.3f} | {float(r['v38_expectancy_usd']):+.2f} | "
            f"{float(r['v38_rolling8_positive_pct']):.1f}% | {float(r['v38_profitable_full_year_pct']):.1f}% | "
            f"{pct(r['worst1_negative_q_loss_share_pct'])} | {pct(r['worst3_negative_q_loss_share_pct'])} | "
            f"{pct(r['worst1pct_losing_trade_loss_share_pct'])} | {pct(r['worst5pct_losing_trade_loss_share_pct'])} |"
        )

    lines += [
        "",
        "## Part B — H226 event study",
        "",
        "Positive signed return means movement in the daily-gap reversion direction after the frozen H226 signal-close condition. No SL/TP or trading fills are used.",
        "",
        "| Cohort | Horizon | N | Mean ATR | Median ATR | Positive % | Gap closed % | Mean MFE | Mean MAE | Worst5% mean | Block 95% CI | P(mean>0) |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|",
    ]
    for cohort in ["H226-C1", "H226-C2", "H226-C3", "H226-C4"]:
        for h in ["1h", "2h", "4h", "8h"]:
            s = ev[(ev["cohort"] == cohort) & (ev["horizon"] == h)].iloc[0]
            b = boot[(boot["cohort"] == cohort) & (boot["horizon"] == h)].iloc[0]
            lines.append(
                f"| {cohort} | {h} | {int(s['event_count'])} | {float(s['mean_signed_reversion_atr']):+.4f} | "
                f"{float(s['median_signed_reversion_atr']):+.4f} | {float(s['positive_return_pct']):.1f}% | {float(s['gap_closure_pct']):.1f}% | "
                f"{float(s['mean_mfe_atr']):.3f} | {float(s['mean_mae_atr']):.3f} | {float(s['worst5pct_mean_signed_reversion_atr']):+.3f} | "
                f"[{float(b['ci_2_5']):+.4f}, {float(b['ci_97_5']):+.4f}] | {float(b['p_mean_gt_zero_pct']):.1f}% |"
            )

    lines += ["", "## Complete-year stability at +4h", "", "| Cohort | Positive years / 7 | Worst year mean | Best year mean |", "|---|---:|---:|---:|"]
    for cohort in ["H226-C1", "H226-C2", "H226-C3", "H226-C4"]:
        y = years[(years["cohort"] == cohort) & (years["horizon"] == "4h")].copy()
        pos = int(y["positive_mean"].sum())
        finite = y[pd.notna(y["mean_signed_reversion_atr"])]
        worst = float(finite["mean_signed_reversion_atr"].min()) if len(finite) else float("nan")
        best = float(finite["mean_signed_reversion_atr"].max()) if len(finite) else float("nan")
        lines.append(f"| {cohort} | {pos}/7 | {num(worst, 4)} | {num(best, 4)} |")

    lines += [
        "",
        "## Frozen mechanism decision",
        "",
        f"> **{decision['mechanism_label']}**",
        "",
        "Decision cohorts were frozen before results as `H226-C1` and `H226-C4`.",
        "",
        "Regardless of the mechanism label:",
        "",
        "- H226 strategy status remains **REJECTED**;",
        "- V3.8 remains closed;",
        "- strategy redesign is **not authorized** by V3.9;",
        "- no gap threshold, residual threshold, direction, SL, TP, RR, asset, or timeframe is changed here.",
        "",
        "## Stop rule",
        "",
        "No H227, H226 tuning, automatic strategy follow-up, new asset/timeframe, or parameter search is authorized by this report.",
    ]
    text = "\n".join(lines) + "\n"
    OUT.write_text(text, encoding="utf-8")
    return text


if __name__ == "__main__":
    generate()
    print(OUT)
