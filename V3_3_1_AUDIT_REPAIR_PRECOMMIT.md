# V3.3.1 AUDIT REPAIR PRECOMMIT PROTOCOL
## REPAIR OF EVALUATION WINDOW, PROFIT CONCENTRATION, AND COST CONTRACT

* **Precommitment Timestamp**: `2026-08-16T00:57:30+07:00`
* **Parent Git Commit SHA**: `440171d8f4ca087af582248aa8713ef1a5ad3a8e`
* **Active Branch**: `research/quant-v3.3.1-batch1-audit-repair`

---

## 1. NATURE OF AUDIT DEFECTS & CORRECTIONS

1. **Defect #1 — Evaluation Window Contamination**:
   - In V3.3, quarterly frequency metrics were filtered to 2018Q2–2026Q2, but full-engine summary fields (`overall_pf`, `total_pnl_usd`, `avg_expectancy_usd`, Long/Short PFs) were computed from the full backtest trade list including 2018Q1 and 2026Q3.
   - *Correction*: Define an immutable authoritative population `evaluation_trades` where `2018Q2 <= entry_quarter <= 2026Q2`. All candidate metrics (PF, Net PnL, expectancy, win rate, quarterly statistics, rolling 4Q, Long/Short breakdown) are recomputed strictly from `evaluation_trades`.

2. **Defect #2 — Profit Concentration Estimator**:
   - In V3.3, Top 3 / Top 5 quarterly PnLs were divided by `total_net_pnl`, producing distorted percentages $> 100\%$ or meaningless negative values.
   - *Correction*: Implement the exact precommitted estimand dividing Top 3 / Top 5 positive quarter PnLs by total positive quarterly PnL: $\sum_{q} \max(\text{Q\_PnL}[q], 0)$. If total positive quarter PnL $\le 0$, Gate B1/B2 = FAIL and report `NaN`.

3. **Defect #3 — Cost Contract & Slippage Transparency**:
   - In V3.3, narrative text mentioned "slippage" while the runner executed with `slippage_pips = 0.0`.
   - *Correction*: Explicitly document baseline execution as: Spread = 25.0 pips, Commission = $7.0/lot, Slippage = 0.0 pips (because no numerical slippage value was precommitted in Batch 1).

---

## 2. ABSOLUTE NO-RESEARCH & SIGNAL FREEZE MANDATE
- All 24 configurations of H-209, H-210, H-211, H-212, H-213, H-214 are **100% IMMUTABLE AND FROZEN**.
- Zero parameter tuning, zero indicator changes, zero directional removals (no Long-only modifications).
- This is an audit-only evaluation repair phase.
