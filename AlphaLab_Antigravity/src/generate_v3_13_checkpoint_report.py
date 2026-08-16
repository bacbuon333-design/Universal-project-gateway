from __future__ import annotations

import json
from pathlib import Path

import create_v3_13_blind_oos_checkpoint as ledger
import fresh_oos_v312_contract as v312

ROOT = v312.ROOT


def generate_report() -> Path:
    chain = ledger.validate_checkpoint_chain()
    latest = chain.get("latest_checkpoint_filename")
    if not latest:
        raise RuntimeError("No V3.13 checkpoint exists")
    checkpoint_path = ledger.CHECKPOINT_DIR / latest
    obj = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    checkpoint_sha = v312.sha256_file(checkpoint_path)
    seq = int(obj["sequence"])
    out = ROOT / f"V3_13_BLIND_OOS_CHECKPOINT_REPORT_{seq:06d}.md"
    if out.exists():
        raise FileExistsError(f"Immutable checkpoint report already exists: {out}")

    r = obj["readiness"]
    checks = r.get("checks", {})
    lines = [
        f"# V3.13 BLIND OOS ACCRUAL CHECKPOINT {seq:06d}",
        "",
        f"- Checkpoint file: `{latest}`",
        f"- Checkpoint SHA-256: `{checkpoint_sha}`",
        f"- Created at UTC: `{obj['created_at_utc']}`",
        f"- Scientific parent V3.12 final: `{obj['scientific_parent_v312_final']}`",
        f"- Previous checkpoint: `{obj.get('previous_checkpoint_filename')}`",
        f"- Previous checkpoint SHA-256: `{obj.get('previous_checkpoint_sha256')}`",
        f"- Canonical freeze cutoff: `{obj['canonical_freeze_cutoff_utc']}`",
        f"- Bridge quarter quarantined: `{obj['bridge_quarter_quarantined']}`",
        f"- First complete OOS decision quarter: `{obj['first_complete_fresh_oos_decision_quarter']}`",
        "",
        "## Fresh-OOS storage state",
        "",
        f"- Fresh-OOS file present: `{obj['fresh_oos_file_present']}`",
        f"- Fresh-OOS dataset SHA-256: `{obj.get('fresh_oos_dataset_sha256')}`",
        f"- Fresh-OOS provenance SHA-256: `{obj.get('fresh_oos_provenance_sha256')}`",
        f"- Previous OOS dataset SHA-256 in source sidecar: `{obj.get('fresh_oos_previous_dataset_sha256')}`",
        f"- Rows: `{obj['fresh_oos_row_count']}`",
        f"- First bar UTC: `{obj.get('fresh_oos_first_bar_open_utc')}`",
        f"- Last bar UTC: `{obj.get('fresh_oos_last_bar_open_utc')}`",
        f"- Bridge/quarantine rows: `{obj['bridge_quarantine_rows']}`",
        "",
        "## Blind readiness",
        "",
        f"- Status: **{r['status']}**",
        f"- Complete decision quarters: `{len(r['complete_decision_quarters'])}`",
        f"- C1 total: `{r['c1_total']}`",
        f"- C4 total: `{r['c4_total']}`",
        f"- Minimum C1 per complete quarter: `{r['c1_min_per_complete_quarter']}`",
        f"- Minimum C4 per complete quarter: `{r['c4_min_per_complete_quarter']}`",
        "",
        "### Maturity checks",
        "",
    ]
    for key in (
        "eight_complete_quarters",
        "c1_total_min",
        "c4_total_min",
        "c1_each_quarter_min",
        "c4_each_quarter_min",
    ):
        lines.append(f"- {'PASS' if checks.get(key) else 'FAIL'} `{key}`")

    lines += [
        "",
        "## Scientific boundary",
        "",
        f"- Outcome metrics computed: `{obj['outcome_metrics_computed']}`",
        f"- Trading engine called: `{obj['trading_engine_called']}`",
        f"- Strategy executed: `{obj['strategy_executed']}`",
        f"- Strategy design authorized: `{obj['strategy_design_authorized']}`",
        f"- Future OOS outcome evaluator authorized: `{obj['future_oos_outcome_evaluator_authorized']}`",
        f"- Same-sample H226 research closed: `{obj['same_sample_h226_research_closed']}`",
        f"- Historical H226 strategy status: `{obj['historical_h226_strategy_status']}`",
        "",
        "This checkpoint is accrual/readiness evidence only. It contains no post-signal return, economic-excess, MFE/MAE, PF, expectancy, fill, or PnL result.",
        "",
        "## Stop rule",
        "",
        "Do not create an OOS outcome evaluator, H226 descendant, direction/regime filter, or strategy until a separately precommitted chapter is authorized after the frozen maturity contract passes.",
    ]
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


if __name__ == "__main__":
    print(generate_report())
