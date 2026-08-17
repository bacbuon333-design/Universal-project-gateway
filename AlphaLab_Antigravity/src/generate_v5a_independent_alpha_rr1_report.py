from __future__ import annotations

"""Generate the human-readable V5-A report from committed raw JSON only."""

from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[2]
RAW_PATH = ROOT / "AlphaLab_Antigravity" / "reports" / "v5a" / "V5A_INDEPENDENT_ALPHA_RR1_RESULTS.json"
REPORT_PATH = ROOT / "V5A_INDEPENDENT_ALPHA_RR1_REPORT.md"

EXPECTED_CONFIG_IDS = ["H401-C1", "H402-C1", "H403-C1", "H404-C1"]
EXPECTED_CANONICAL_SHA = "c48ca44dcecae9eb1c2590c586e27c4bc5f246215c549d0d0bc1201d95d5ea1d"
EXPECTED_PARENT = "5a1a2f8c28f857789943295f6a59df2f1037e72b"


def fmt(value, digits: int = 3) -> str:
    if value is None:
        return "NA"
    if isinstance(value, bool):
        return "PASS" if value else "FAIL"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def validate_payload(payload: dict) -> None:
    if payload.get("chapter") != "V5A_INDEPENDENT_ALPHA_RR1_DISCOVERY":
        raise RuntimeError("wrong V5-A raw-result chapter")
    if payload.get("scientific_parent_commit") != EXPECTED_PARENT:
        raise RuntimeError("V5-A scientific parent drift")
    if payload.get("canonical_dataset_sha256") != EXPECTED_CANONICAL_SHA:
        raise RuntimeError("V5-A canonical SHA drift")
    if payload.get("execution_contract") != "CANONICAL_V2_GAP_SAFE_V3_7_3":
        raise RuntimeError("V5-A execution contract drift")
    if payload.get("evaluator_contract") != "V3_8_WRAPPER_OVER_V3_5_FULL_14_GATES":
        raise RuntimeError("V5-A evaluator contract drift")
    if len(payload.get("gate_names", [])) != 14:
        raise RuntimeError("V5-A raw result must contain exactly 14 frozen gates")

    configs = payload.get("configs", [])
    if [c.get("config_id") for c in configs] != EXPECTED_CONFIG_IDS:
        raise RuntimeError("V5-A raw result configuration order/budget drift")
    if len(configs) != 4 or len({c.get("family") for c in configs}) != 4:
        raise RuntimeError("V5-A raw result must contain exactly four independent families")

    budget = payload.get("multiple_testing_budget", {})
    if budget != {
        "automatic_batch_2_authorized": False,
        "configs_per_family": 1,
        "dynamic_grid_authorized": False,
        "families": 4,
        "post_result_tuning_authorized": False,
        "total_configs": 4,
    }:
        raise RuntimeError("V5-A multiple-testing budget drift")

    risk = payload.get("common_risk_contract", {})
    if risk.get("sl_atr") != 1.5 or risk.get("tp_atr") != 1.5 or risk.get("risk_reward") != "1:1":
        raise RuntimeError("V5-A RR1 contract drift")

    forbidden_true = [
        "fresh_oos_accessed",
        "closed_research_modified",
        "closed_research_descendant_created",
        "h226_reused",
        "v4_h301_h304_reused",
        "strategy_design_authorized_for_deployment",
        "paper_trading_authorized",
        "live_trading_authorized",
    ]
    for key in forbidden_true:
        if payload.get(key) is not False:
            raise RuntimeError(f"V5-A governance flag must remain false: {key}")

    gates = payload["gate_names"]
    for cfg in configs:
        expected_all = all(bool(cfg.get(g)) for g in gates)
        if bool(cfg.get("all_gates_pass")) != expected_all:
            raise RuntimeError(f"{cfg.get('config_id')}: all_gates_pass is not 14-gate conjunction")
        expected_status = "HISTORICAL_CANDIDATE_ONLY" if expected_all else "REJECTED"
        if cfg.get("final_status") != expected_status:
            raise RuntimeError(f"{cfg.get('config_id')}: classification drift")


def render(payload: dict) -> str:
    configs = payload["configs"]
    gates = payload["gate_names"]
    lines = [
        "# V5-A Independent Alpha RR1 Discovery — Frozen Result Report",
        "",
        "## Provenance and frozen contracts",
        "",
        f"- Scientific parent commit: `{payload['scientific_parent_commit']}`",
        f"- Frozen execution HEAD recorded by runner: `{payload.get('frozen_code_head')}`",
        f"- Canonical dataset SHA-256: `{payload['canonical_dataset_sha256']}`",
        f"- Execution contract: `{payload['execution_contract']}`",
        f"- Evaluator contract: `{payload['evaluator_contract']}`",
        "- Families/configurations: 4 / 4",
        "- Common SL/TP: 1.5 ATR / 1.5 ATR (1:1)",
        "- Dynamic grid / automatic Batch 2 / post-result tuning: false / false / false",
        "",
        "## Configuration outcomes",
        "",
        "| ID | Family | Trades | PF | Expectancy USD | Net PnL USD | Min/Q | Min/Year | R4 +% | R4 PF120% | R8 +% | R8 PF120% | Prof Years % | Gates | Status |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]

    for c in configs:
        lines.append(
            "| " + " | ".join([
                str(c["config_id"]),
                str(c["family"]),
                fmt(c.get("total_trades"), 0),
                fmt(c.get("pf")),
                fmt(c.get("expectancy_usd")),
                fmt(c.get("net_pnl_usd")),
                fmt(c.get("min_trades_q"), 0),
                fmt(c.get("min_full_year_trades"), 0),
                fmt(c.get("rolling4_positive_pct"), 1),
                fmt(c.get("rolling4_pf120_pct"), 1),
                fmt(c.get("rolling8_positive_pct"), 1),
                fmt(c.get("rolling8_pf120_pct"), 1),
                fmt(c.get("profitable_full_year_pct"), 1),
                f"{sum(bool(c.get(g)) for g in gates)}/14",
                str(c.get("final_status")),
            ]) + " |"
        )

    lines.extend(["", "## Gate-level audit", ""])
    for c in configs:
        lines.append(f"### {c['config_id']} — {c['final_status']}")
        lines.append("")
        lines.append(f"Family: `{c['family']}`; params: `{c.get('params', {})}`")
        lines.append("")
        lines.append(f"Primary failure: `{c.get('primary_failure_reason')}`")
        lines.append("")
        for g in gates:
            lines.append(f"- {g}: {'PASS' if bool(c.get(g)) else 'FAIL'}")
        lines.append("")

    lines.extend([
        "## Frozen conclusion",
        "",
        f"**{payload['batch_conclusion']}**",
        "",
        f"Survivors: `{payload.get('survivors', [])}`",
        "",
        "## Governance assertions",
        "",
        f"- FRESH OOS ACCESSED: {str(payload['fresh_oos_accessed']).lower()}",
        f"- CLOSED RESEARCH MODIFIED: {str(payload['closed_research_modified']).lower()}",
        f"- CLOSED RESEARCH DESCENDANT CREATED: {str(payload['closed_research_descendant_created']).lower()}",
        f"- H226 REUSED: {str(payload['h226_reused']).lower()}",
        f"- V4 H301-H304 REUSED: {str(payload['v4_h301_h304_reused']).lower()}",
        f"- STRATEGY DESIGN AUTHORIZED FOR DEPLOYMENT: {str(payload['strategy_design_authorized_for_deployment']).lower()}",
        f"- PAPER TRADING AUTHORIZED: {str(payload['paper_trading_authorized']).lower()}",
        f"- LIVE TRADING AUTHORIZED: {str(payload['live_trading_authorized']).lower()}",
        "",
        "A failed configuration is closed for this chapter and may not be tuned here. A historical survivor would require separately precommitted independent validation and remains unauthorized for deployment.",
        "",
    ])
    return "\n".join(lines)


def main() -> None:
    if not RAW_PATH.exists():
        raise RuntimeError(f"raw V5-A result not found: {RAW_PATH}")
    if REPORT_PATH.exists():
        raise RuntimeError(f"V5-A report already exists; refusing overwrite: {REPORT_PATH}")
    payload = json.loads(RAW_PATH.read_text(encoding="utf-8"))
    validate_payload(payload)
    REPORT_PATH.write_text(render(payload), encoding="utf-8")
    print(f"report={REPORT_PATH}")


if __name__ == "__main__":
    main()
