# V3.2.2 EXACT PRECOMMITTED GATES SPECIFICATION

This document establishes the exact evaluation gates precommitted in `V3_2_PRECOMMIT_H204_PLUS.md` at Git commit `f5be62deba702fd737149c64b5faca3599f0daca`.

---

## 1. PRECOMMITTED HARD EVALUATION GATES

| Gate ID | Category | Metric | Exact Condition | Precommitted Threshold |
| :--- | :--- | :--- | :--- | :--- |
| **`Gate A`** | Hard Temporal | Quarterly Minimum Trades | Minimum executed trades in EVERY complete quarter | **$\ge 5$ trades** in 100% of quarters (33/33) |
| **`Gate B1`**| Trade Concentration | Max Quarter Share | Percentage of total trades in single most active quarter | **$\le 5.0\%$** |
| **`Gate B2`**| Trade Concentration | Max / Median Ratio | Maximum quarterly trades divided by median quarterly trades | **$\le 3.0$** |
| **`Gate B3`**| Trade Concentration | Trade Count Gini | Gini coefficient of quarterly trade counts | **$< 0.30$** |
| **`Gate C1`**| Profit Distribution | Top 3 Quarters PnL Share | Net PnL of top 3 quarters divided by total net PnL | **$\le 40.0\%$** |
| **`Gate C2`**| Profit Distribution | Top 5 Quarters PnL Share | Net PnL of top 5 quarters divided by total net PnL | **$\le 60.0\%$** |
| **`Gate D1`**| Rolling Consistency | Rolling 4Q Positive Windows | Percentage of rolling 4-quarter windows with positive net PnL | **$\ge 70.0\%$** |
| **`Gate D2`**| Rolling Consistency | Rolling 4Q $PF \ge 1.20$ | Percentage of rolling 4-quarter windows with $PF \ge 1.20$ | **$\ge 65.0\%$** |
| **`Gate E1`**| Economic Edge | Baseline Profit Factor | Full-sample Profit Factor with 25 pips spread + $7/lot comm | **$\ge 1.25$** |
| **`Gate E2`**| Economic Edge | Net Expectancy | Average net PnL per trade | **$> \$0.00$** |

---

## 2. NON-PRECOMMITTED INFORMATIVE DIAGNOSTICS (NOT HARD GATES)

The following metrics are tracked and reported strictly as non-precommitted diagnostic information and DO NOT influence the hard pass/fail classification:
- **Rolling 8Q Positive Windows** ($\ge 75\%$)
- **Rolling 8Q $PF \ge 1.20$** ($\ge 70\%$)
- **Profitable Full Calendar Years** ($\ge 70\%$)
- **100-Pip Spread Stress Test Profit Factor**

---

## 3. UNAMBIGUOUS BOOLEAN EVALUATION SCHEMA

```python
gate_min_trades = bool(min_trades_per_q >= 5)
gate_max_share  = bool(max_q_trade_share_pct <= 5.0)
gate_max_median = bool(max_to_median_ratio <= 3.0)
gate_gini       = bool(trade_count_gini < 0.30)
gate_top3_pnl   = bool(top3_q_pnl_share_pct <= 40.0) if total_pnl > 0 else False
gate_top5_pnl   = bool(top5_q_pnl_share_pct <= 60.0) if total_pnl > 0 else False
gate_r4_pos     = bool(rolling_4q_pos_pct >= 70.0)
gate_r4_pf      = bool(rolling_4q_pf12_pct >= 65.0)
gate_pf         = bool(overall_profit_factor >= 1.25)
gate_expectancy = bool(avg_expectancy_usd > 0.0)

all_precommitted_gates_pass = (
    gate_min_trades and gate_max_share and gate_max_median and gate_gini and
    gate_top3_pnl and gate_top5_pnl and gate_r4_pos and gate_r4_pf and
    gate_pf and gate_expectancy
)
```
