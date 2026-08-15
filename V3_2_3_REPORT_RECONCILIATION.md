# V3.2.3 DEEP FIELD-BY-FIELD MACHINE RECONCILIATION REPORT

This document records the automated verification asserting 100% numerical and boolean equality between the raw machine-readable dataset (`reports/v3_2_3/final_status.csv`) and the presentation report (`V3_2_3_EXACT_STATUS.md`).

## 1. RECONCILIATION AUDIT LOG (168 CHECKS: 24 FIELDS x 7 HYPOTHESES)

| Hypothesis | Field | CSV Raw Value | Markdown Report Value | Equality Check |
| :--- | :--- | :--- | :--- | :--- |
| **`H-204`** | `total_trades` | `311` | `311` | **`PASSED (100% MATCH)`** |
| **`H-204`** | `min_trades_per_q` | `4` | `4` | **`PASSED (100% MATCH)`** |
| **`H-204`** | `median_trades_per_q` | `9.0` | `9.0` | **`PASSED (100% MATCH)`** |
| **`H-204`** | `max_trades_per_q` | `19` | `19` | **`PASSED (100% MATCH)`** |
| **`H-204`** | `max_q_trade_share_pct` | `6.1%` | `6.1%` | **`PASSED (100% MATCH)`** |
| **`H-204`** | `max_to_median_ratio` | `2.11` | `2.11` | **`PASSED (100% MATCH)`** |
| **`H-204`** | `trade_count_gini` | `0.217` | `0.217` | **`PASSED (100% MATCH)`** |
| **`H-204`** | `top3_q_pnl_share_pct` | `102.1%` | `102.1%` | **`PASSED (100% MATCH)`** |
| **`H-204`** | `top5_q_pnl_share_pct` | `121.8%` | `121.8%` | **`PASSED (100% MATCH)`** |
| **`H-204`** | `rolling_4q_pos_pct` | `73.3%` | `73.3%` | **`PASSED (100% MATCH)`** |
| **`H-204`** | `rolling_4q_pf12_pct` | `53.3%` | `53.3%` | **`PASSED (100% MATCH)`** |
| **`H-204`** | `overall_pf` | `1.256` | `1.256` | **`PASSED (100% MATCH)`** |
| **`H-204`** | `avg_expectancy_usd` | `$+11.68` | `$+11.68` | **`PASSED (100% MATCH)`** |
| **`H-204`** | `gate_min_trades` | `FAIL` | `FAIL` | **`PASSED (100% MATCH)`** |
| **`H-204`** | `gate_max_share` | `FAIL` | `FAIL` | **`PASSED (100% MATCH)`** |
| **`H-204`** | `gate_max_median` | `PASS` | `PASS` | **`PASSED (100% MATCH)`** |
| **`H-204`** | `gate_gini` | `PASS` | `PASS` | **`PASSED (100% MATCH)`** |
| **`H-204`** | `gate_top3_pnl` | `FAIL` | `FAIL` | **`PASSED (100% MATCH)`** |
| **`H-204`** | `gate_top5_pnl` | `FAIL` | `FAIL` | **`PASSED (100% MATCH)`** |
| **`H-204`** | `gate_r4_pos` | `PASS` | `PASS` | **`PASSED (100% MATCH)`** |
| **`H-204`** | `gate_r4_pf` | `FAIL` | `FAIL` | **`PASSED (100% MATCH)`** |
| **`H-204`** | `gate_pf` | `PASS` | `PASS` | **`PASSED (100% MATCH)`** |
| **`H-204`** | `gate_expectancy` | `PASS` | `PASS` | **`PASSED (100% MATCH)`** |
| **`H-204`** | `final_status` | `VALIDLY REPRODUCED — REJECTED` | `VALIDLY REPRODUCED — REJECTED` | **`PASSED (100% MATCH)`** |
| **`H-205`** | `total_trades` | `2545` | `2545` | **`PASSED (100% MATCH)`** |
| **`H-205`** | `min_trades_per_q` | `50` | `50` | **`PASSED (100% MATCH)`** |
| **`H-205`** | `median_trades_per_q` | `79.0` | `79.0` | **`PASSED (100% MATCH)`** |
| **`H-205`** | `max_trades_per_q` | `98` | `98` | **`PASSED (100% MATCH)`** |
| **`H-205`** | `max_q_trade_share_pct` | `3.9%` | `3.9%` | **`PASSED (100% MATCH)`** |
| **`H-205`** | `max_to_median_ratio` | `1.24` | `1.24` | **`PASSED (100% MATCH)`** |
| **`H-205`** | `trade_count_gini` | `0.100` | `0.100` | **`PASSED (100% MATCH)`** |
| **`H-205`** | `top3_q_pnl_share_pct` | `N/A (Loss)` | `N/A (Loss)` | **`PASSED (100% MATCH)`** |
| **`H-205`** | `top5_q_pnl_share_pct` | `N/A (Loss)` | `N/A (Loss)` | **`PASSED (100% MATCH)`** |
| **`H-205`** | `rolling_4q_pos_pct` | `6.7%` | `6.7%` | **`PASSED (100% MATCH)`** |
| **`H-205`** | `rolling_4q_pf12_pct` | `3.3%` | `3.3%` | **`PASSED (100% MATCH)`** |
| **`H-205`** | `overall_pf` | `0.962` | `0.962` | **`PASSED (100% MATCH)`** |
| **`H-205`** | `avg_expectancy_usd` | `$-1.27` | `$-1.27` | **`PASSED (100% MATCH)`** |
| **`H-205`** | `gate_min_trades` | `PASS` | `PASS` | **`PASSED (100% MATCH)`** |
| **`H-205`** | `gate_max_share` | `PASS` | `PASS` | **`PASSED (100% MATCH)`** |
| **`H-205`** | `gate_max_median` | `PASS` | `PASS` | **`PASSED (100% MATCH)`** |
| **`H-205`** | `gate_gini` | `PASS` | `PASS` | **`PASSED (100% MATCH)`** |
| **`H-205`** | `gate_top3_pnl` | `FAIL` | `FAIL` | **`PASSED (100% MATCH)`** |
| **`H-205`** | `gate_top5_pnl` | `FAIL` | `FAIL` | **`PASSED (100% MATCH)`** |
| **`H-205`** | `gate_r4_pos` | `FAIL` | `FAIL` | **`PASSED (100% MATCH)`** |
| **`H-205`** | `gate_r4_pf` | `FAIL` | `FAIL` | **`PASSED (100% MATCH)`** |
| **`H-205`** | `gate_pf` | `FAIL` | `FAIL` | **`PASSED (100% MATCH)`** |
| **`H-205`** | `gate_expectancy` | `FAIL` | `FAIL` | **`PASSED (100% MATCH)`** |
| **`H-205`** | `final_status` | `SPECIFICATION AMBIGUOUS — DURATION SEMANTICS NOT HISTORICALLY PROVEN` | `SPECIFICATION AMBIGUOUS — DURATION SEMANTICS NOT HISTORICALLY PROVEN` | **`PASSED (100% MATCH)`** |
| **`H-206`** | `total_trades` | `1623` | `1623` | **`PASSED (100% MATCH)`** |
| **`H-206`** | `min_trades_per_q` | `32` | `32` | **`PASSED (100% MATCH)`** |
| **`H-206`** | `median_trades_per_q` | `49.0` | `49.0` | **`PASSED (100% MATCH)`** |
| **`H-206`** | `max_trades_per_q` | `63` | `63` | **`PASSED (100% MATCH)`** |
| **`H-206`** | `max_q_trade_share_pct` | `3.9%` | `3.9%` | **`PASSED (100% MATCH)`** |
| **`H-206`** | `max_to_median_ratio` | `1.29` | `1.29` | **`PASSED (100% MATCH)`** |
| **`H-206`** | `trade_count_gini` | `0.076` | `0.076` | **`PASSED (100% MATCH)`** |
| **`H-206`** | `top3_q_pnl_share_pct` | `178.7%` | `178.7%` | **`PASSED (100% MATCH)`** |
| **`H-206`** | `top5_q_pnl_share_pct` | `206.0%` | `206.0%` | **`PASSED (100% MATCH)`** |
| **`H-206`** | `rolling_4q_pos_pct` | `40.0%` | `40.0%` | **`PASSED (100% MATCH)`** |
| **`H-206`** | `rolling_4q_pf12_pct` | `10.0%` | `10.0%` | **`PASSED (100% MATCH)`** |
| **`H-206`** | `overall_pf` | `1.087` | `1.087` | **`PASSED (100% MATCH)`** |
| **`H-206`** | `avg_expectancy_usd` | `$+4.98` | `$+4.98` | **`PASSED (100% MATCH)`** |
| **`H-206`** | `gate_min_trades` | `PASS` | `PASS` | **`PASSED (100% MATCH)`** |
| **`H-206`** | `gate_max_share` | `PASS` | `PASS` | **`PASSED (100% MATCH)`** |
| **`H-206`** | `gate_max_median` | `PASS` | `PASS` | **`PASSED (100% MATCH)`** |
| **`H-206`** | `gate_gini` | `PASS` | `PASS` | **`PASSED (100% MATCH)`** |
| **`H-206`** | `gate_top3_pnl` | `FAIL` | `FAIL` | **`PASSED (100% MATCH)`** |
| **`H-206`** | `gate_top5_pnl` | `FAIL` | `FAIL` | **`PASSED (100% MATCH)`** |
| **`H-206`** | `gate_r4_pos` | `FAIL` | `FAIL` | **`PASSED (100% MATCH)`** |
| **`H-206`** | `gate_r4_pf` | `FAIL` | `FAIL` | **`PASSED (100% MATCH)`** |
| **`H-206`** | `gate_pf` | `FAIL` | `FAIL` | **`PASSED (100% MATCH)`** |
| **`H-206`** | `gate_expectancy` | `PASS` | `PASS` | **`PASSED (100% MATCH)`** |
| **`H-206`** | `final_status` | `VALIDLY REPRODUCED — REJECTED` | `VALIDLY REPRODUCED — REJECTED` | **`PASSED (100% MATCH)`** |
| **`H-207`** | `total_trades` | `277` | `277` | **`PASSED (100% MATCH)`** |
| **`H-207`** | `min_trades_per_q` | `2` | `2` | **`PASSED (100% MATCH)`** |
| **`H-207`** | `median_trades_per_q` | `8.0` | `8.0` | **`PASSED (100% MATCH)`** |
| **`H-207`** | `max_trades_per_q` | `20` | `20` | **`PASSED (100% MATCH)`** |
| **`H-207`** | `max_q_trade_share_pct` | `7.2%` | `7.2%` | **`PASSED (100% MATCH)`** |
| **`H-207`** | `max_to_median_ratio` | `2.50` | `2.50` | **`PASSED (100% MATCH)`** |
| **`H-207`** | `trade_count_gini` | `0.268` | `0.268` | **`PASSED (100% MATCH)`** |
| **`H-207`** | `top3_q_pnl_share_pct` | `148.1%` | `148.1%` | **`PASSED (100% MATCH)`** |
| **`H-207`** | `top5_q_pnl_share_pct` | `183.4%` | `183.4%` | **`PASSED (100% MATCH)`** |
| **`H-207`** | `rolling_4q_pos_pct` | `56.7%` | `56.7%` | **`PASSED (100% MATCH)`** |
| **`H-207`** | `rolling_4q_pf12_pct` | `43.3%` | `43.3%` | **`PASSED (100% MATCH)`** |
| **`H-207`** | `overall_pf` | `1.164` | `1.164` | **`PASSED (100% MATCH)`** |
| **`H-207`** | `avg_expectancy_usd` | `$+7.10` | `$+7.10` | **`PASSED (100% MATCH)`** |
| **`H-207`** | `gate_min_trades` | `FAIL` | `FAIL` | **`PASSED (100% MATCH)`** |
| **`H-207`** | `gate_max_share` | `FAIL` | `FAIL` | **`PASSED (100% MATCH)`** |
| **`H-207`** | `gate_max_median` | `PASS` | `PASS` | **`PASSED (100% MATCH)`** |
| **`H-207`** | `gate_gini` | `PASS` | `PASS` | **`PASSED (100% MATCH)`** |
| **`H-207`** | `gate_top3_pnl` | `FAIL` | `FAIL` | **`PASSED (100% MATCH)`** |
| **`H-207`** | `gate_top5_pnl` | `FAIL` | `FAIL` | **`PASSED (100% MATCH)`** |
| **`H-207`** | `gate_r4_pos` | `FAIL` | `FAIL` | **`PASSED (100% MATCH)`** |
| **`H-207`** | `gate_r4_pf` | `FAIL` | `FAIL` | **`PASSED (100% MATCH)`** |
| **`H-207`** | `gate_pf` | `FAIL` | `FAIL` | **`PASSED (100% MATCH)`** |
| **`H-207`** | `gate_expectancy` | `PASS` | `PASS` | **`PASSED (100% MATCH)`** |
| **`H-207`** | `final_status` | `VALIDLY REPRODUCED — REJECTED` | `VALIDLY REPRODUCED — REJECTED` | **`PASSED (100% MATCH)`** |
| **`H-208A`** | `total_trades` | `234` | `234` | **`PASSED (100% MATCH)`** |
| **`H-208A`** | `min_trades_per_q` | `2` | `2` | **`PASSED (100% MATCH)`** |
| **`H-208A`** | `median_trades_per_q` | `6.0` | `6.0` | **`PASSED (100% MATCH)`** |
| **`H-208A`** | `max_trades_per_q` | `19` | `19` | **`PASSED (100% MATCH)`** |
| **`H-208A`** | `max_q_trade_share_pct` | `8.1%` | `8.1%` | **`PASSED (100% MATCH)`** |
| **`H-208A`** | `max_to_median_ratio` | `3.17` | `3.17` | **`PASSED (100% MATCH)`** |
| **`H-208A`** | `trade_count_gini` | `0.247` | `0.247` | **`PASSED (100% MATCH)`** |
| **`H-208A`** | `top3_q_pnl_share_pct` | `72.5%` | `72.5%` | **`PASSED (100% MATCH)`** |
| **`H-208A`** | `top5_q_pnl_share_pct` | `87.0%` | `87.0%` | **`PASSED (100% MATCH)`** |
| **`H-208A`** | `rolling_4q_pos_pct` | `73.3%` | `73.3%` | **`PASSED (100% MATCH)`** |
| **`H-208A`** | `rolling_4q_pf12_pct` | `56.7%` | `56.7%` | **`PASSED (100% MATCH)`** |
| **`H-208A`** | `overall_pf` | `1.466` | `1.466` | **`PASSED (100% MATCH)`** |
| **`H-208A`** | `avg_expectancy_usd` | `$+17.09` | `$+17.09` | **`PASSED (100% MATCH)`** |
| **`H-208A`** | `gate_min_trades` | `FAIL` | `FAIL` | **`PASSED (100% MATCH)`** |
| **`H-208A`** | `gate_max_share` | `FAIL` | `FAIL` | **`PASSED (100% MATCH)`** |
| **`H-208A`** | `gate_max_median` | `FAIL` | `FAIL` | **`PASSED (100% MATCH)`** |
| **`H-208A`** | `gate_gini` | `PASS` | `PASS` | **`PASSED (100% MATCH)`** |
| **`H-208A`** | `gate_top3_pnl` | `FAIL` | `FAIL` | **`PASSED (100% MATCH)`** |
| **`H-208A`** | `gate_top5_pnl` | `FAIL` | `FAIL` | **`PASSED (100% MATCH)`** |
| **`H-208A`** | `gate_r4_pos` | `PASS` | `PASS` | **`PASSED (100% MATCH)`** |
| **`H-208A`** | `gate_r4_pf` | `FAIL` | `FAIL` | **`PASSED (100% MATCH)`** |
| **`H-208A`** | `gate_pf` | `PASS` | `PASS` | **`PASSED (100% MATCH)`** |
| **`H-208A`** | `gate_expectancy` | `PASS` | `PASS` | **`PASSED (100% MATCH)`** |
| **`H-208A`** | `final_status` | `SPECIFICATION AMBIGUOUS — EXACT REPRODUCTION IMPOSSIBLE` | `SPECIFICATION AMBIGUOUS — EXACT REPRODUCTION IMPOSSIBLE` | **`PASSED (100% MATCH)`** |
| **`H-208B`** | `total_trades` | `227` | `227` | **`PASSED (100% MATCH)`** |
| **`H-208B`** | `min_trades_per_q` | `1` | `1` | **`PASSED (100% MATCH)`** |
| **`H-208B`** | `median_trades_per_q` | `6.0` | `6.0` | **`PASSED (100% MATCH)`** |
| **`H-208B`** | `max_trades_per_q` | `15` | `15` | **`PASSED (100% MATCH)`** |
| **`H-208B`** | `max_q_trade_share_pct` | `6.6%` | `6.6%` | **`PASSED (100% MATCH)`** |
| **`H-208B`** | `max_to_median_ratio` | `2.50` | `2.50` | **`PASSED (100% MATCH)`** |
| **`H-208B`** | `trade_count_gini` | `0.255` | `0.255` | **`PASSED (100% MATCH)`** |
| **`H-208B`** | `top3_q_pnl_share_pct` | `N/A (Loss)` | `N/A (Loss)` | **`PASSED (100% MATCH)`** |
| **`H-208B`** | `top5_q_pnl_share_pct` | `N/A (Loss)` | `N/A (Loss)` | **`PASSED (100% MATCH)`** |
| **`H-208B`** | `rolling_4q_pos_pct` | `50.0%` | `50.0%` | **`PASSED (100% MATCH)`** |
| **`H-208B`** | `rolling_4q_pf12_pct` | `36.7%` | `36.7%` | **`PASSED (100% MATCH)`** |
| **`H-208B`** | `overall_pf` | `0.889` | `0.889` | **`PASSED (100% MATCH)`** |
| **`H-208B`** | `avg_expectancy_usd` | `$-6.07` | `$-6.07` | **`PASSED (100% MATCH)`** |
| **`H-208B`** | `gate_min_trades` | `FAIL` | `FAIL` | **`PASSED (100% MATCH)`** |
| **`H-208B`** | `gate_max_share` | `FAIL` | `FAIL` | **`PASSED (100% MATCH)`** |
| **`H-208B`** | `gate_max_median` | `PASS` | `PASS` | **`PASSED (100% MATCH)`** |
| **`H-208B`** | `gate_gini` | `PASS` | `PASS` | **`PASSED (100% MATCH)`** |
| **`H-208B`** | `gate_top3_pnl` | `FAIL` | `FAIL` | **`PASSED (100% MATCH)`** |
| **`H-208B`** | `gate_top5_pnl` | `FAIL` | `FAIL` | **`PASSED (100% MATCH)`** |
| **`H-208B`** | `gate_r4_pos` | `FAIL` | `FAIL` | **`PASSED (100% MATCH)`** |
| **`H-208B`** | `gate_r4_pf` | `FAIL` | `FAIL` | **`PASSED (100% MATCH)`** |
| **`H-208B`** | `gate_pf` | `FAIL` | `FAIL` | **`PASSED (100% MATCH)`** |
| **`H-208B`** | `gate_expectancy` | `FAIL` | `FAIL` | **`PASSED (100% MATCH)`** |
| **`H-208B`** | `final_status` | `SPECIFICATION AMBIGUOUS — EXACT REPRODUCTION IMPOSSIBLE` | `SPECIFICATION AMBIGUOUS — EXACT REPRODUCTION IMPOSSIBLE` | **`PASSED (100% MATCH)`** |
| **`H-208C`** | `total_trades` | `456` | `456` | **`PASSED (100% MATCH)`** |
| **`H-208C`** | `min_trades_per_q` | `5` | `5` | **`PASSED (100% MATCH)`** |
| **`H-208C`** | `median_trades_per_q` | `13.0` | `13.0` | **`PASSED (100% MATCH)`** |
| **`H-208C`** | `max_trades_per_q` | `28` | `28` | **`PASSED (100% MATCH)`** |
| **`H-208C`** | `max_q_trade_share_pct` | `6.1%` | `6.1%` | **`PASSED (100% MATCH)`** |
| **`H-208C`** | `max_to_median_ratio` | `2.15` | `2.15` | **`PASSED (100% MATCH)`** |
| **`H-208C`** | `trade_count_gini` | `0.202` | `0.202` | **`PASSED (100% MATCH)`** |
| **`H-208C`** | `top3_q_pnl_share_pct` | `75.5%` | `75.5%` | **`PASSED (100% MATCH)`** |
| **`H-208C`** | `top5_q_pnl_share_pct` | `112.6%` | `112.6%` | **`PASSED (100% MATCH)`** |
| **`H-208C`** | `rolling_4q_pos_pct` | `73.3%` | `73.3%` | **`PASSED (100% MATCH)`** |
| **`H-208C`** | `rolling_4q_pf12_pct` | `33.3%` | `33.3%` | **`PASSED (100% MATCH)`** |
| **`H-208C`** | `overall_pf` | `1.129` | `1.129` | **`PASSED (100% MATCH)`** |
| **`H-208C`** | `avg_expectancy_usd` | `$+5.89` | `$+5.89` | **`PASSED (100% MATCH)`** |
| **`H-208C`** | `gate_min_trades` | `PASS` | `PASS` | **`PASSED (100% MATCH)`** |
| **`H-208C`** | `gate_max_share` | `FAIL` | `FAIL` | **`PASSED (100% MATCH)`** |
| **`H-208C`** | `gate_max_median` | `PASS` | `PASS` | **`PASSED (100% MATCH)`** |
| **`H-208C`** | `gate_gini` | `PASS` | `PASS` | **`PASSED (100% MATCH)`** |
| **`H-208C`** | `gate_top3_pnl` | `FAIL` | `FAIL` | **`PASSED (100% MATCH)`** |
| **`H-208C`** | `gate_top5_pnl` | `FAIL` | `FAIL` | **`PASSED (100% MATCH)`** |
| **`H-208C`** | `gate_r4_pos` | `PASS` | `PASS` | **`PASSED (100% MATCH)`** |
| **`H-208C`** | `gate_r4_pf` | `FAIL` | `FAIL` | **`PASSED (100% MATCH)`** |
| **`H-208C`** | `gate_pf` | `FAIL` | `FAIL` | **`PASSED (100% MATCH)`** |
| **`H-208C`** | `gate_expectancy` | `PASS` | `PASS` | **`PASSED (100% MATCH)`** |
| **`H-208C`** | `final_status` | `SPECIFICATION AMBIGUOUS — EXACT REPRODUCTION IMPOSSIBLE` | `SPECIFICATION AMBIGUOUS — EXACT REPRODUCTION IMPOSSIBLE` | **`PASSED (100% MATCH)`** |

## 2. RECONCILIATION VERDICT (168 CHECKS)
✅ **100% FIELD-BY-FIELD MACHINE EQUALITY VERIFIED ACROSS ALL 168 CHECKS (24 METRIC & GATE FIELDS x 7 HYPOTHESES).**