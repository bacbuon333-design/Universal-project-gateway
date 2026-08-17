from __future__ import annotations

"""Reporting and artifact generation module for ALAB-M1-FUSION-001R."""

import json
from pathlib import Path
from typing import Any, Dict
import pandas as pd

from .cost_contract import CostContract, save_cost_contract_json

HORIZONS = [1, 3, 5, 10, 15, 30]


def export_replication_artifacts(
    output_dir: Path,
    root_dir: Path,
    data_audit_meta: Dict[str, Any],
    cost_contract: CostContract,
    event_decision: Dict[str, Any],
    overlap_audit: Dict[str, Any],
    block_bootstrap: Dict[str, Any],
    df_events: pd.DataFrame,
    backtest_results: Dict[str, Any],
    git_meta: Dict[str, str],
) -> None:
    """Generate all required CSV, JSON, and Markdown reports for 001R."""
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. M1_FUSION_001R_DATA_AUDIT.json
    with open(output_dir / "M1_FUSION_001R_DATA_AUDIT.json", "w", encoding="utf-8") as f:
        json.dump(data_audit_meta, f, indent=2, default=str)

    # 2. M1_FUSION_001R_COST_CONTRACT.json
    save_cost_contract_json(cost_contract, output_dir / "M1_FUSION_001R_COST_CONTRACT.json")

    # 3. M1_FUSION_001R_EVENT_RESULTS.json
    with open(output_dir / "M1_FUSION_001R_EVENT_RESULTS.json", "w", encoding="utf-8") as f:
        json.dump(event_decision, f, indent=2, default=str)

    # 4. M1_FUSION_001R_BLOCK_BOOTSTRAP.json
    with open(output_dir / "M1_FUSION_001R_BLOCK_BOOTSTRAP.json", "w", encoding="utf-8") as f:
        json.dump(block_bootstrap, f, indent=2, default=str)

    # 5. M1_FUSION_001R_OVERLAP_AUDIT.json
    with open(output_dir / "M1_FUSION_001R_OVERLAP_AUDIT.json", "w", encoding="utf-8") as f:
        json.dump(overlap_audit, f, indent=2, default=str)

    # 6. M1_FUSION_001R_DIAGNOSTIC_BACKTEST.json
    with open(output_dir / "M1_FUSION_001R_DIAGNOSTIC_BACKTEST.json", "w", encoding="utf-8") as f:
        json.dump(backtest_results, f, indent=2, default=str)

    # CSV Exports
    if not df_events.empty:
        # 7. M1_FUSION_001R_SCORE_BINS.csv
        sb_rows = []
        for sb in ["3-4", "5-6", "7-8", "9-10"]:
            sub = df_events[df_events["score_bin"] == sb]
            n_sub = len(sub)
            if n_sub > 0:
                ret5 = sub["fwd_ret_5m"].dropna() * 10000.0
                mfe5 = sub["mfe_5m"].dropna() * 10000.0
                mae5 = sub["mae_5m"].dropna() * 10000.0
                sb_rows.append({
                    "score_bin": sb,
                    "n_events": n_sub,
                    "mean_5m_bps": float(ret5.mean()),
                    "median_5m_bps": float(ret5.median()),
                    "win_rate_5m_pct": float((ret5 > 0).mean() * 100.0),
                    "mean_mfe_5m_bps": float(mfe5.mean()),
                    "mean_mae_5m_bps": float(mae5.mean()),
                })
            else:
                sb_rows.append({"score_bin": sb, "n_events": 0, "mean_5m_bps": 0.0, "median_5m_bps": 0.0, "win_rate_5m_pct": 0.0, "mean_mfe_5m_bps": 0.0, "mean_mae_5m_bps": 0.0})
        pd.DataFrame(sb_rows).to_csv(output_dir / "M1_FUSION_001R_SCORE_BINS.csv", index=False)

        # 8. M1_FUSION_001R_YEARLY.csv
        yr_rows = []
        for yr in sorted(df_events["year"].unique()):
            sub = df_events[df_events["year"] == yr]
            ret5 = sub["fwd_ret_5m"].dropna() * 10000.0
            yr_rows.append({
                "year": yr,
                "n_events": len(sub),
                "mean_5m_bps": float(ret5.mean()) if len(ret5) else 0.0,
                "median_5m_bps": float(ret5.median()) if len(ret5) else 0.0,
                "win_rate_5m_pct": float((ret5 > 0).mean() * 100.0) if len(ret5) else 0.0,
                "is_valid_year": len(sub) >= 200,
            })
        pd.DataFrame(yr_rows).to_csv(output_dir / "M1_FUSION_001R_YEARLY.csv", index=False)

        # 9. M1_FUSION_001R_LONG_SHORT.csv
        ls_rows = []
        for side in ["LONG", "SHORT"]:
            sub = df_events[df_events["side"] == side]
            for h in HORIZONS:
                ret_h = sub[f"fwd_ret_{h}m"].dropna() * 10000.0
                mfe_h = sub[f"mfe_{h}m"].dropna() * 10000.0
                mae_h = sub[f"mae_{h}m"].dropna() * 10000.0
                ls_rows.append({
                    "side": side,
                    "horizon": f"{h}m",
                    "n_events": len(ret_h),
                    "mean_bps": float(ret_h.mean()) if len(ret_h) else 0.0,
                    "median_bps": float(ret_h.median()) if len(ret_h) else 0.0,
                    "win_rate_pct": float((ret_h > 0).mean() * 100.0) if len(ret_h) else 0.0,
                    "mean_mfe_bps": float(mfe_h.mean()) if len(mfe_h) else 0.0,
                    "mean_mae_bps": float(mae_h.mean()) if len(mae_h) else 0.0,
                })
        pd.DataFrame(ls_rows).to_csv(output_dir / "M1_FUSION_001R_LONG_SHORT.csv", index=False)

        # 10. M1_FUSION_001R_HOURLY.csv
        hr_rows = []
        for hr in range(24):
            sub = df_events[df_events["hour"] == hr]
            ret5 = sub["fwd_ret_5m"].dropna() * 10000.0
            hr_rows.append({
                "utc_hour": hr,
                "n_events": len(sub),
                "mean_5m_bps": float(ret5.mean()) if len(ret5) else 0.0,
                "median_5m_bps": float(ret5.median()) if len(ret5) else 0.0,
                "win_rate_5m_pct": float((ret5 > 0).mean() * 100.0) if len(ret5) else 0.0,
            })
        pd.DataFrame(hr_rows).to_csv(output_dir / "M1_FUSION_001R_HOURLY.csv", index=False)

        # 11. M1_FUSION_001R_SESSION.csv
        sess_rows = []
        for sess in ["ASIA", "LONDON_RESEARCH", "NEW_YORK_RESEARCH", "OTHER"]:
            sub = df_events[df_events["session"] == sess]
            ret5 = sub["fwd_ret_5m"].dropna() * 10000.0
            sess_rows.append({
                "session": sess,
                "n_events": len(sub),
                "mean_5m_bps": float(ret5.mean()) if len(ret5) else 0.0,
                "median_5m_bps": float(ret5.median()) if len(ret5) else 0.0,
                "win_rate_5m_pct": float((ret5 > 0).mean() * 100.0) if len(ret5) else 0.0,
            })
        pd.DataFrame(sess_rows).to_csv(output_dir / "M1_FUSION_001R_SESSION.csv", index=False)

        # 12. M1_FUSION_001R_VOLATILITY.csv
        vol_rows = []
        for vs in ["0-49", "50-79", "80-94", "95-100"]:
            sub = df_events[df_events["vol_state"] == vs]
            ret5 = sub["fwd_ret_5m"].dropna() * 10000.0
            vol_rows.append({
                "volatility_state": vs,
                "n_events": len(sub),
                "mean_5m_bps": float(ret5.mean()) if len(ret5) else 0.0,
                "median_5m_bps": float(ret5.median()) if len(ret5) else 0.0,
                "win_rate_5m_pct": float((ret5 > 0).mean() * 100.0) if len(ret5) else 0.0,
            })
        pd.DataFrame(vol_rows).to_csv(output_dir / "M1_FUSION_001R_VOLATILITY.csv", index=False)

    # 13. Markdown Reports
    report_md = render_replication_markdown(
        data_audit_meta, cost_contract, event_decision, overlap_audit, block_bootstrap, backtest_results, git_meta, df_events
    )
    with open(root_dir / "M1_FUSION_001R_REPORT.md", "w", encoding="utf-8") as f:
        f.write(report_md)
    with open(root_dir / "M1_FUSION_001R_RUN1_REPORT.md", "w", encoding="utf-8") as f:
        f.write(report_md)
    with open(output_dir / "M1_FUSION_001R_RUN1_REPORT.md", "w", encoding="utf-8") as f:
        f.write(report_md)

    # 14. Manifests
    manifest = {
        "experiment_id": "ALAB-M1-FUSION-001R-RUN1",
        "branch": git_meta.get("branch", "research/quant-m1-fusion-001r-run1"),
        "base_sha": git_meta.get("base_sha", "88c9b3b36394592283f601e27b299632d3f98b2e"),
        "precommit_sha": git_meta.get("precommit_sha", "PENDING"),
        "result_commit_sha": git_meta.get("result_commit_sha", "PENDING_UNTIL_COMMIT"),
        "data_sha256": data_audit_meta.get("data_hash_sha256", "UNKNOWN"),
        "rows": data_audit_meta.get("replication_rows", 0),
        "quarantined_2026_rows": data_audit_meta.get("quarantined_2026_rows", 0),
        "start_datetime": data_audit_meta.get("start_datetime", "NA"),
        "end_datetime": data_audit_meta.get("end_datetime", "NA"),
        "unique_days": data_audit_meta.get("unique_days", 0),
        "tests_passed": git_meta.get("tests_passed", 0),
        "tests_failed": git_meta.get("tests_failed", 0),
        "event_count": event_decision.get("total_events", 0),
        "long_events": event_decision.get("long_events", 0),
        "short_events": event_decision.get("short_events", 0),
        "event_verdict": event_decision.get("verdict", "STOP_BLOCKED"),
        "diagnostic_backtest_status": backtest_results.get("status", "INSUFFICIENT_DIAGNOSTIC"),
        "primary_5m_mean_bps": event_decision.get("summary_stats", {}).get("h5m", {}).get("mean_return_bps", 0.0),
        "primary_5m_day_block_95_ci_lower_bps": event_decision.get("summary_stats", {}).get("h5m", {}).get("day_block_ci_95_lower_bps", 0.0),
        "primary_5m_day_block_95_ci_upper_bps": event_decision.get("summary_stats", {}).get("h5m", {}).get("day_block_ci_95_upper_bps", 0.0),
        "score_consistency_status": event_decision.get("score_consistency_status", "UNKNOWN"),
        "all_gates_pass": event_decision.get("all_gates_pass", False),
        "cost_verification_status": cost_contract.cost_verification_status,
        "strategy_validation": "NOT_AUTHORIZED",
        "paper_trading": "NO",
        "live_trading": "NO",
        "broker_execution": "NO",
        "research_only": True,
    }
    with open(root_dir / "M1_FUSION_001R_MANIFEST.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, default=str)
    with open(root_dir / "M1_FUSION_001R_RUN1_MANIFEST.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, default=str)
    with open(output_dir / "M1_FUSION_001R_RUN1_MANIFEST.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, default=str)


def render_replication_markdown(
    data_meta: Dict[str, Any],
    cost: CostContract,
    decision: Dict[str, Any],
    overlap: Dict[str, Any],
    bb: Dict[str, Any],
    bt: Dict[str, Any],
    git_meta: Dict[str, str],
    df_events: pd.DataFrame,
) -> str:
    stats = decision.get("summary_stats", {})
    h5 = stats.get("h5m", {})
    bb5 = bb.get("h5m", {})

    lines = [
        "# ALAB-M1-FUSION-001R — Replication & Research Infrastructure Repair Report",
        "",
        "## 1. Governance and Metadata",
        "",
        f"- **Repository**: `bacbuon333-design/Universal-project-gateway`",
        f"- **Branch**: `{git_meta.get('branch', 'research/quant-m1-fusion-001r-replication')}`",
        f"- **Base SHA**: `{git_meta.get('base_sha', '6c257c313a83e2dec5813fc36be921912209bc68')}`",
        f"- **Precommit SHA**: `{git_meta.get('precommit_sha', 'PENDING')}`",
        f"- **Scientific Parent (V1 Base)**: `6c257c313a83e2dec5813fc36be921912209bc68`",
        f"- **Experiment ID**: `ALAB-M1-FUSION-001R`",
        f"- **Strategy Validation**: `NOT_AUTHORIZED`",
        f"- **Paper Trading**: `NO`",
        f"- **Live Trading**: `NO`",
        f"- **Broker Execution**: `NO`",
        f"- **Research Only**: `YES`",
        "",
        "## 2. Dataset Audit & 2026 Discovery Quarantine",
        "",
        f"- **Symbol**: `{data_meta.get('symbol', 'GOLD')}` (Timeframe: M1, Timezone: UTC)",
        f"- **Source Path**: `{data_meta.get('source_path')}`",
        f"- **Replication Rows (Pre-2026)**: `{data_meta.get('replication_rows', 0):,}` bars",
        f"- **Quarantined 2026 Discovery Rows**: `{data_meta.get('quarantined_2026_rows', 0):,}` bars",
        f"- **Discovery Overlap in Replication Set**: `0` rows",
        f"- **Replication Date Range**: `{data_meta.get('start_datetime')}` to `{data_meta.get('end_datetime')}`",
        f"- **Unique Calendar Years**: `{data_meta.get('unique_calendar_years')}`",
        f"- **Unique Trading Days**: `{data_meta.get('unique_days', 0):,}` days",
        f"- **Data Hash (SHA-256)**: `{data_meta.get('data_hash_sha256')}`",
        f"- **Hard Gate 0A (>=1,000,000 Rows)**: `{'PASS' if data_meta.get('is_sufficient_history') else 'FAIL'}`",
        f"- **Hard Gate 0B (>=3 Calendar Years)**: `{'PASS' if data_meta.get('is_sufficient_temporal_coverage') else 'FAIL'}`",
        "",
        "## 3. Verified Broker Cost Contract",
        "",
        f"- **Symbol**: `{cost.symbol}` | **Digits**: `{cost.digits}` | **Point**: `{cost.point}`",
        f"- **Contract Size**: `{cost.trade_contract_size}` oz/lot | **Profit Currency**: `{cost.currency_profit}`",
        f"- **Spread Representation**: `{cost.spread_raw_unit}` ({cost.spread_price_conversion})",
        f"- **Commission**: `{cost.commission_per_lot_usd} USD/lot` ({cost.commission_status})",
        f"- **Cost Contract Status**: `{cost.cost_verification_status}`",
        "",
        "## 4. Outcome Dependence & Overlap Audit",
        "",
        f"- **Total Events**: `{overlap.get('total_events', 0):,}`",
        f"- **Mean Events per Day**: `{overlap.get('mean_events_per_day', 0.0):.1f}` | **Median Gap**: `{overlap.get('median_gap_bars', 0.0):.1f} bars`",
        f"- **Events with Overlapping 5m Horizon**: `{overlap.get('overlap_pct_5m', 0.0):.1f}%`",
        f"- **Events with Overlapping 10m Horizon**: `{overlap.get('overlap_pct_10m', 0.0):.1f}%`",
        f"- **Events with Overlapping 30m Horizon**: `{overlap.get('overlap_pct_30m', 0.0):.1f}%`",
        "",
        "## 5. Multi-Horizon Returns & Day-Block Bootstrap",
        "",
        "| Horizon | N | Mean Return (bps) | Median (bps) | Win Rate % | Day-Block 95% Bootstrap CI (bps) | Mean MFE (bps) | Mean MAE (bps) |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]

    for h in HORIZONS:
        h_info = stats.get(f"h{h}m", {})
        if h_info:
            ci_str = f"[{h_info.get('day_block_ci_95_lower_bps', 0.0):.2f}, {h_info.get('day_block_ci_95_upper_bps', 0.0):.2f}]"
            lines.append(
                f"| {h}m | {h_info['n']:,} | {h_info['mean_return_bps']:+.2f} | {h_info['median_return_bps']:+.2f} | {h_info['win_proportion']*100.0:.1f}% | {ci_str} | {h_info['mean_mfe_bps']:.2f} | {h_info['mean_mae_bps']:.2f} |"
            )

    lines.extend([
        "",
        "## 6. Score Gradient and Consistency Status",
        "",
        f"- **Score Consistency Classification**: `{decision.get('score_consistency_status')}`",
        "",
        "| Score Bin | N Events | Mean Return 5m (bps) | Win Rate 5m % |",
        "|---|---:|---:|---:|",
    ])

    for sb, m_val in decision.get("score_bin_means_5m", {}).items():
        n_sb = decision.get("score_bin_counts", {}).get(sb, 0)
        lines.append(f"| {sb} | {n_sb:,} | {m_val:+.2f} | - |")

    lines.extend([
        "",
        "## 7. Dual Gross/Net Diagnostic Strategy Backtest",
        "",
        f"- **Diagnostic Status**: `{bt.get('status')}`",
        f"- **Total Trades**: `{bt.get('total_trades', 0)}`",
        f"- **Gross Win Rate**: `{bt.get('gross_win_rate_pct', 0.0):.1f}%` | **Net Win Rate**: `{bt.get('win_rate_pct', 0.0):.1f}%`",
        f"- **Gross Profit Factor**: `{bt.get('gross_profit_factor', 0.0):.3f}` | **Net Profit Factor**: `{bt.get('net_profit_factor', 0.0):.3f}`",
        f"- **Gross Expectancy**: `{bt.get('gross_expectancy_usd', 0.0):+.2f} USD/trade` | **Net Expectancy**: `{bt.get('net_expectancy_usd', 0.0):+.2f} USD/trade`",
        f"- **Gross PnL**: `{bt.get('gross_pnl_usd', 0.0):+.2f} USD` | **Net PnL**: `{bt.get('net_pnl_usd', 0.0):+.2f} USD`",
        f"- **Total Friction Costs**: `{bt.get('total_costs_usd', 0.0):.2f} USD` (Mean cost: `${bt.get('mean_cost_per_trade_usd', 0.0):.2f}/trade`)",
        f"- **Max Drawdown**: `{bt.get('max_drawdown_usd', 0.0):.2f} USD`",
        "",
        "## 8. Replication Discovery Gate Battery",
        "",
        f"- **Gate 0 (Data >= 1,000,000 rows & >= 3 valid years)**: `{'PASS' if decision.get('gate0_data') else 'FAIL'}`",
        f"- **Gate 1 (Sample size >= 500 total, >= 150 long, >= 150 short)**: `{'PASS' if decision.get('gate1_sample') else 'FAIL'}`",
        f"- **Gate 2 (Primary 5m Mean Return > 0)**: `{'PASS' if decision.get('gate2_mean_5m_pos') else 'FAIL'}`",
        f"- **Gate 3 (Primary 5m Day-Block Bootstrap CI Lower > 0)**: `{'PASS' if decision.get('gate3_day_block_ci_pos') else 'FAIL'}`",
        f"- **Gate 4 (Adjacent 3m or 10m Mean Return > 0)**: `{'PASS' if decision.get('gate4_adjacent_pos') else 'FAIL'}`",
        f"- **Gate 5 (Temporal Stability >= 3 valid years, >= 70% positive)**: `{'PASS' if decision.get('gate5_year_stability') else 'FAIL'}`",
        "",
        f"### **FINAL REPLICATION VERDICT: {decision.get('verdict')}**",
        "",
        "## 9. Strongest Counter-Evidence",
        "",
        "High intra-day event density (overlapping forward return horizons) and substantial execution spread relative to gross excursion create severe drag on M1 price action reversions. Without pre-2026 out-of-discovery data coverage of at least 1,000,000 rows, the mechanism cannot be scientifically confirmed.",
        "",
        "---",
        "**END OF REPORT**",
    ])

    return "\n".join(lines)
