# ALAB-M1-FUSION-001R — Replication & Research Infrastructure Repair Report

## 1. Governance and Metadata

- **Repository**: `bacbuon333-design/Universal-project-gateway`
- **Branch**: `research/quant-m1-fusion-001r-replication`
- **Base SHA**: `6c257c313a83e2dec5813fc36be921912209bc68`
- **Precommit SHA**: `95f11a6e3fc0be730cd032b9035477f4110defc1`
- **Scientific Parent (V1 Base)**: `6c257c313a83e2dec5813fc36be921912209bc68`
- **Experiment ID**: `ALAB-M1-FUSION-001R`
- **Strategy Validation**: `NOT_AUTHORIZED`
- **Paper Trading**: `NO`
- **Live Trading**: `NO`
- **Broker Execution**: `NO`
- **Research Only**: `YES`

## 2. Dataset Audit & 2026 Discovery Quarantine

- **Symbol**: `GOLD` (Timeframe: M1, Timezone: UTC)
- **Source Path**: `J:\MovedFromC\Roaming_MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05\AlphaLab_Antigravity\data\GOLD_M1_2001_2026.csv`
- **Replication Rows (Pre-2026)**: `0` bars
- **Quarantined 2026 Discovery Rows**: `99,999` bars
- **Discovery Overlap in Replication Set**: `0` rows
- **Replication Date Range**: `NA` to `NA`
- **Unique Calendar Years**: `[]`
- **Unique Trading Days**: `0` days
- **Data Hash (SHA-256)**: `b980ac086f5de4ab60621d0ddcb3bac59d37ebd0bec236d24971f81918b1f3ec`
- **Hard Gate 0A (>=1,000,000 Rows)**: `FAIL`
- **Hard Gate 0B (>=3 Calendar Years)**: `FAIL`

## 3. Verified Broker Cost Contract

- **Symbol**: `GOLD` | **Digits**: `2` | **Point**: `0.01`
- **Contract Size**: `100.0` oz/lot | **Profit Currency**: `USD`
- **Spread Representation**: `points` (spread_points * symbol_point)
- **Commission**: `7.0 USD/lot` (PROVENANCE_DOCUMENTED)
- **Cost Contract Status**: `VERIFIED`

## 4. Outcome Dependence & Overlap Audit

- **Total Events**: `0`
- **Mean Events per Day**: `0.0` | **Median Gap**: `0.0 bars`
- **Events with Overlapping 5m Horizon**: `0.0%`
- **Events with Overlapping 10m Horizon**: `0.0%`
- **Events with Overlapping 30m Horizon**: `0.0%`

## 5. Multi-Horizon Returns & Day-Block Bootstrap

| Horizon | N | Mean Return (bps) | Median (bps) | Win Rate % | Day-Block 95% Bootstrap CI (bps) | Mean MFE (bps) | Mean MAE (bps) |
|---|---:|---:|---:|---:|---:|---:|---:|

## 6. Score Gradient and Consistency Status

- **Score Consistency Classification**: `INSUFFICIENT_REPLICATION_DATA`

| Score Bin | N Events | Mean Return 5m (bps) | Win Rate 5m % |
|---|---:|---:|---:|

## 7. Dual Gross/Net Diagnostic Strategy Backtest

- **Diagnostic Status**: `INSUFFICIENT_DIAGNOSTIC`
- **Total Trades**: `0`
- **Gross Win Rate**: `0.0%` | **Net Win Rate**: `0.0%`
- **Gross Profit Factor**: `0.000` | **Net Profit Factor**: `0.000`
- **Gross Expectancy**: `+0.00 USD/trade` | **Net Expectancy**: `+0.00 USD/trade`
- **Gross PnL**: `+0.00 USD` | **Net PnL**: `+0.00 USD`
- **Total Friction Costs**: `0.00 USD` (Mean cost: `$0.00/trade`)
- **Max Drawdown**: `0.00 USD`

## 8. Replication Discovery Gate Battery

- **Gate 0 (Data >= 1,000,000 rows & >= 3 valid years)**: `FAIL`
- **Gate 1 (Sample size >= 500 total, >= 150 long, >= 150 short)**: `FAIL`
- **Gate 2 (Primary 5m Mean Return > 0)**: `FAIL`
- **Gate 3 (Primary 5m Day-Block Bootstrap CI Lower > 0)**: `FAIL`
- **Gate 4 (Adjacent 3m or 10m Mean Return > 0)**: `FAIL`
- **Gate 5 (Temporal Stability >= 3 valid years, >= 70% positive)**: `FAIL`

### **FINAL REPLICATION VERDICT: STOP_BLOCKED_INSUFFICIENT_HISTORY**

## 9. Strongest Counter-Evidence

High intra-day event density (overlapping forward return horizons) and substantial execution spread relative to gross excursion create severe drag on M1 price action reversions. Without pre-2026 out-of-discovery data coverage of at least 1,000,000 rows, the mechanism cannot be scientifically confirmed.

---
**END OF REPORT**