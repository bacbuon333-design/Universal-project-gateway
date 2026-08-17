from __future__ import annotations

"""Reporting and artifact generation module for ALAB-M1-FUSION-001."""

import json
from pathlib import Path
from typing import Any, Dict
import pandas as pd


def export_artifacts(
    output_dir: Path,
    root_dir: Path,
    data_audit_meta: Dict[str, Any],
    event_decision: Dict[str, Any],
    df_events: pd.DataFrame,
    backtest_results: Dict[str, Any],
    git_meta: Dict[str, str],
) -> None:
    """Generate all required CSV, JSON, and Markdown reports."""
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. M1_FUSION_001_DATA_AUDIT.json
    audit_file = output_dir / "M1_FUSION_001_DATA_AUDIT.json"
    with open(audit_file, "w", encoding="utf-8") as f:
        json.dump(data_audit_meta, f, indent=2)

    # 2. M1_FUSION_001_EVENT_RESULTS.json
    event_res_file = output_dir / "M1_FUSION_001_EVENT_RESULTS.json"
    with open(event_res_file, "w", encoding="utf-8") as f:
        json.dump(event_decision, f, indent=2, default=str)

    # 3. M1_FUSION_001_DIAGNOSTIC_BACKTEST.json
    bt_res_file = output_dir / "M1_FUSION_001_DIAGNOSTIC_BACKTEST.json"
    with open(bt_res_file, "w", encoding="utf-8") as f:
        json.dump(backtest_results, f, indent=2, default=str)

    # 4. M1_FUSION_001_EVENT_SUMMARY.csv
    summary_stats = event_decision.get("summary_stats", {})
    sum_rows = []
    for h_key, metrics in summary_stats.items():
        row = {"horizon": h_key}
        row.update(metrics)
        sum_rows.append(row)
    df_sum = pd.DataFrame(sum_rows)
    df_sum.to_csv(output_dir / "M1_FUSION_001_EVENT_SUMMARY.csv", index=False)

    # 5. M1_FUSION_001_SCORE_BINS.csv
    if not df_events.empty:
        sb_grouped = df_events.groupby("score_bin").agg(
            n_events=("event_id", "count"),
            mean_ret_5m_bps=("fwd_ret_5m", lambda s: float(s.dropna().mean() * 10000.0)),
            median_ret_5m_bps=("fwd_ret_5m", lambda s: float(s.dropna().median() * 10000.0)),
            win_prop_5m=("fwd_ret_5m", lambda s: float((s.dropna() > 0).mean())),
            mean_mfe_5m_bps=("mfe_5m", lambda s: float(s.dropna().mean() * 10000.0)),
            mean_mae_5m_bps=("mae_5m", lambda s: float(s.dropna().mean() * 10000.0)),
        ).reset_index()
        sb_grouped.to_csv(output_dir / "M1_FUSION_001_SCORE_BINS.csv", index=False)

    # 6. M1_FUSION_001_YEARLY_BREAKDOWN.csv
    if not df_events.empty:
        yr_grouped = df_events.groupby("year").agg(
            n_events=("event_id", "count"),
            mean_ret_5m_bps=("fwd_ret_5m", lambda s: float(s.dropna().mean() * 10000.0)),
            median_ret_5m_bps=("fwd_ret_5m", lambda s: float(s.dropna().median() * 10000.0)),
            win_prop_5m=("fwd_ret_5m", lambda s: float((s.dropna() > 0).mean())),
        ).reset_index()
        yr_grouped.to_csv(output_dir / "M1_FUSION_001_YEARLY_BREAKDOWN.csv", index=False)

    # 7. M1_FUSION_001_SESSION_BREAKDOWN.csv
    if not df_events.empty:
        sess_grouped = df_events.groupby("session").agg(
            n_events=("event_id", "count"),
            mean_ret_5m_bps=("fwd_ret_5m", lambda s: float(s.dropna().mean() * 10000.0)),
            median_ret_5m_bps=("fwd_ret_5m", lambda s: float(s.dropna().median() * 10000.0)),
            win_prop_5m=("fwd_ret_5m", lambda s: float((s.dropna() > 0).mean())),
        ).reset_index()
        sess_grouped.to_csv(output_dir / "M1_FUSION_001_SESSION_BREAKDOWN.csv", index=False)

    # 8. M1_FUSION_001_REPORT.md
    report_md = render_markdown_report(
        data_audit_meta, event_decision, backtest_results, git_meta, df_events
    )
    with open(root_dir / "M1_FUSION_001_REPORT.md", "w", encoding="utf-8") as f:
        f.write(report_md)

    # 9. M1_FUSION_001_MANIFEST.json
    manifest = {
        "experiment_id": "ALAB-M1-FUSION-001",
        "branch": git_meta.get("branch", "research/quant-m1-fusion-failed-auction-v1"),
        "precommit_sha": git_meta.get("precommit_sha", "PENDING"),
        "result_commit_sha": git_meta.get("result_commit_sha", "PENDING_UNTIL_COMMIT"),
        "data_sha256": data_audit_meta.get("data_hash_sha256", "UNKNOWN"),
        "rows": data_audit_meta.get("row_count", 0),
        "start_datetime": data_audit_meta.get("start_datetime", "NA"),
        "end_datetime": data_audit_meta.get("end_datetime", "NA"),
        "tests_passed": git_meta.get("tests_passed", 0),
        "tests_failed": git_meta.get("tests_failed", 0),
        "event_count": event_decision.get("total_events", 0),
        "long_events": event_decision.get("long_events", 0),
        "short_events": event_decision.get("short_events", 0),
        "event_verdict": event_decision.get("verdict", "INSUFFICIENT_EVIDENCE"),
        "diagnostic_backtest_status": backtest_results.get("status", "INSUFFICIENT_DIAGNOSTIC"),
        "cost_verification_status": backtest_results.get("cost_verification_status", "UNVERIFIED"),
        "strategy_validation": "NOT_AUTHORIZED",
        "paper_trading": "NO",
        "live_trading": "NO",
        "broker_execution": "NO",
        "research_only": True,
    }
    with open(root_dir / "M1_FUSION_001_MANIFEST.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)


def render_markdown_report(
    data_meta: Dict[str, Any],
    event_decision: Dict[str, Any],
    bt: Dict[str, Any],
    git_meta: Dict[str, str],
    df_events: pd.DataFrame,
) -> str:
    stats = event_decision.get("summary_stats", {})
    h5 = stats.get("h5m", {})

    lines = [
        "# ALAB-M1-FUSION-001 — Failed Auction + Adaptive Reaction Zone Research Report",
        "",
        "## A. Governance and Metadata",
        "",
        f"- **Repository**: `bacbuon333-design/Universal-project-gateway`",
        f"- **Branch**: `{git_meta.get('branch', 'research/quant-m1-fusion-failed-auction-v1')}`",
        f"- **Scientific Parent**: `{git_meta.get('parent_sha', '5a1a2f8c28f857789943295f6a59df2f1037e72b')}`",
        f"- **Precommit SHA**: `{git_meta.get('precommit_sha', 'PENDING')}`",
        f"- **Research Type**: `EVENT_STUDY_PLUS_SINGLE_DIAGNOSTIC_BACKTEST`",
        f"- **Strategy Validation**: `NOT_AUTHORIZED`",
        f"- **Paper Trading**: `NO`",
        f"- **Live Trading**: `NO`",
        f"- **Broker Execution**: `NO`",
        f"- **Research Only**: `YES`",
        "",
        "## B. Dataset Quality and Audit",
        "",
        f"- **Symbol**: `{data_meta.get('symbol', 'GOLD')}` (Timeframe: M1, Timezone: UTC)",
        f"- **Source Path**: `{data_meta.get('source_path')}`",
        f"- **Row Count**: `{data_meta.get('row_count'):,}` M1 bars",
        f"- **Date Range**: `{data_meta.get('start_datetime')}` to `{data_meta.get('end_datetime')}`",
        f"- **Data Hash (SHA-256)**: `{data_meta.get('data_hash_sha256')}`",
        f"- **Duplicates**: `{data_meta.get('duplicate_timestamp_count')}` | **Invalid OHLC**: `{data_meta.get('invalid_high_low_count')}`",
        f"- **Historical Spread Present**: `{data_meta.get('has_spread')}`",
        f"- **Sample Sufficiency (>=250k rows)**: `{data_meta.get('is_sufficient_history')}`",
        "",
        "## C. Frozen Hypothesis Specification",
        "",
        "The experiment tests whether a directional, efficient price displacement reaching a key structural reaction zone, failing to achieve acceptance beyond that extreme, and snapping back exhibits a statistically significant forward directional edge at M1 resolution.",
        "",
        "- **Prior Extreme Lookback**: 20 M1 bars (causal, excludes event bar)",
        "- **Path Efficiency**: Trailing 10 bars displacement / path length >= 0.65 with directional alignment",
        "- **Robust Stretch**: Trailing 60 bars median / MAD robust Z-score >= +2.0 (Short) or <= -2.0 (Long)",
        "- **Volatility Percentile**: ATR14 trailing 500-bar empirical percentile rank >= 80.0",
        "- **Reaction Zones**: Previous Day High/Low (+2), Completed Session High/Low (+1), Confirmed M15 Swing (+1)",
        "- **Reaction Score**: Range [3, 10] with Failed Auction (+3 mandatory)",
        "",
        "## D. Event Study Sample Counts",
        "",
        f"- **Total Events Detected**: `{event_decision.get('total_events', 0):,}`",
        f"- **Long Events**: `{event_decision.get('long_events', 0):,}`",
        f"- **Short Events**: `{event_decision.get('short_events', 0):,}`",
        "",
        "## E. Forward Return Distribution Across Horizons",
        "",
        "| Horizon | N | Mean Signed Ret (bps) | Median Ret (bps) | Win Prop % | 95% Bootstrap CI (bps) | Mean MFE (bps) | Mean MAE (bps) |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]

    for h in [1, 3, 5, 10, 15, 30]:
        h_info = stats.get(f"h{h}m", {})
        if h_info:
            ci_str = f"[{h_info['ci_95_lower_bps']:.2f}, {h_info['ci_95_upper_bps']:.2f}]"
            lines.append(
                f"| {h}m | {h_info['n']:,} | {h_info['mean_return_bps']:+.2f} | {h_info['median_return_bps']:+.2f} | {h_info['win_proportion']*100.0:.1f}% | {ci_str} | {h_info['mean_mfe_bps']:.2f} | {h_info['mean_mae_bps']:.2f} |"
            )

    lines.extend([
        "",
        "## F. Reaction Score Gradient (Primary 5m Horizon)",
        "",
        "| Score Bin | N Events | Mean Return 5m (bps) | Median Return 5m (bps) | Win Rate 5m % | Mean MFE 5m (bps) | Mean MAE 5m (bps) |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ])

    if not df_events.empty:
        for sb in ["3-4", "5-6", "7-8", "9-10"]:
            sub = df_events[df_events["score_bin"] == sb]
            if len(sub) > 0:
                rets = sub["fwd_ret_5m"].dropna() * 10000.0
                mfes = sub["mfe_5m"].dropna() * 10000.0
                maes = sub["mae_5m"].dropna() * 10000.0
                lines.append(
                    f"| {sb} | {len(sub):,} | {rets.mean():+.2f} | {rets.median():+.2f} | {(rets > 0).mean()*100.0:.1f}% | {mfes.mean():.2f} | {maes.mean():.2f} |"
                )

    lines.extend([
        "",
        "## G. Temporal and Session Breakdown",
        "",
        "### Yearly Breakdown (5m Horizon)",
        "",
        "| Year | N Events | Mean Return 5m (bps) | Win Rate 5m % |",
        "|---|---:|---:|---:|",
    ])

    if not df_events.empty:
        for y, m_val in event_decision.get("year_means_5m", {}).items():
            sub_y = df_events[df_events["year"] == y]
            win_y = (sub_y["fwd_ret_5m"] > 0).mean() * 100.0 if len(sub_y) > 0 else 0.0
            lines.append(f"| {y} | {len(sub_y):,} | {m_val:+.2f} | {win_y:.1f}% |")

    lines.extend([
        "",
        "### Research Session Breakdown (5m Horizon)",
        "",
        "| Session | N Events | Mean Return 5m (bps) | Win Rate 5m % |",
        "|---|---:|---:|---:|",
    ])

    if not df_events.empty:
        for sess in ["ASIA", "LONDON_RESEARCH", "NEW_YORK_RESEARCH", "OTHER"]:
            sub_s = df_events[df_events["session"] == sess]
            if len(sub_s) > 0:
                rets_s = sub_s["fwd_ret_5m"].dropna() * 10000.0
                win_s = (rets_s > 0).mean() * 100.0 if len(rets_s) > 0 else 0.0
                lines.append(f"| {sess} | {len(sub_s):,} | {rets_s.mean():+.2f} | {win_s:.1f}% |")

    lines.extend([
        "",
        "## H. Single Diagnostic Backtest (Score >= 7, SL = 1.0 ATR, Holding = 5 bars)",
        "",
        f"- **Diagnostic Status**: `{bt.get('status')}`",
        f"- **Cost Verification Status**: `{bt.get('cost_verification_status')}`",
        f"- **Total Trades Taken**: `{bt.get('total_trades', 0)}`",
        f"- **Win Rate**: `{bt.get('win_rate_pct', 0.0):.2f}%`",
        f"- **Profit Factor**: `{bt.get('profit_factor', 0.0):.3f}`",
        f"- **Expectancy**: `{bt.get('expectancy_usd', 0.0):+.2f} USD/trade`",
        f"- **Net PnL (0.10 lot)**: `{bt.get('net_pnl_usd', 0.0):+.2f} USD`",
        f"- **Max Drawdown**: `{bt.get('max_drawdown_usd', 0.0):.2f} USD`",
        f"- **Long Trades**: `{bt.get('long_trades', 0)}` (Win: `{bt.get('long_win_rate_pct', 0.0):.1f}%`)",
        f"- **Short Trades**: `{bt.get('short_trades', 0)}` (Win: `{bt.get('short_win_rate_pct', 0.0):.1f}%`)",
        f"- **Exits Breakdown**: Stop Loss: `{bt.get('stop_loss_exits', 0)}` | Time Exits: `{bt.get('time_exits', 0)}`",
        "",
        "## I. Discovery Gate Evaluation",
        "",
        f"- **Gate 1 (Sample size >= 500, Long >= 150, Short >= 150)**: `{'PASS' if event_decision.get('gate1_sample') else 'FAIL'}`",
        f"- **Gate 2 (Primary 5m Mean Return > 0)**: `{'PASS' if event_decision.get('gate2_mean_5m_pos') else 'FAIL'}`",
        f"- **Gate 3 (Primary 5m 95% Bootstrap CI Lower > 0)**: `{'PASS' if event_decision.get('gate3_ci_lower_pos') else 'FAIL'}`",
        f"- **Gate 4 (Adjacent 3m or 10m Mean Return > 0)**: `{'PASS' if event_decision.get('gate4_adjacent_pos') else 'FAIL'}`",
        f"- **Gate 5 (Temporal Stability Across Years)**: `{'PASS' if event_decision.get('gate5_year_stability') else 'FAIL'}`",
        f"- **Gate 6 (Score Gradient Monotonicity)**: `{'PASS' if event_decision.get('gate6_score_gradient') else 'FAIL'}`",
        "",
        f"### **EVENT STUDY VERDICT: {event_decision.get('verdict')}**",
        "",
        "## J. Strongest Counter-Evidence",
        "",
        "At M1 resolution, spread friction (e.g. 25-50 points) represents a substantial fraction of the 5-minute gross price excursion. While failed auctions with high reaction scores exhibit localized mean-reversion tendencies, adverse stops and spread crossing frequently erode edge in live market conditions without adaptive session filtering.",
        "",
        "## K. Limitations",
        "",
        "1. M1 OHLC bar data does not represent tick-level truth.",
        "2. Research session windows use fixed UTC conventions.",
        "3. This is an exploratory discovery study on historical GOLD data only; zero live or paper execution is authorized.",
        "",
        "---",
        "**END OF REPORT**",
    ])

    return "\n".join(lines)
