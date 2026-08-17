# ALAB-M1-FUSION-001R — Replication & Research Infrastructure Repair Report

## 1. Governance and Metadata

- **Repository**: `bacbuon333-design/Universal-project-gateway`
- **Branch**: `research/quant-m1-fusion-001r-run1`
- **Base SHA**: `88c9b3b36394592283f601e27b299632d3f98b2e`
- **Precommit SHA**: `631c2d1e7e2678f853f52f9a2e3cc7fa052a39e1`
- **Scientific Parent (V1 Base)**: `6c257c313a83e2dec5813fc36be921912209bc68`
- **Experiment ID**: `ALAB-M1-FUSION-001R`
- **Strategy Validation**: `NOT_AUTHORIZED`
- **Paper Trading**: `NO`
- **Live Trading**: `NO`
- **Broker Execution**: `NO`
- **Research Only**: `YES`

## 2. Dataset Audit & 2026 Discovery Quarantine

- **Symbol**: `GOLD` (Timeframe: M1, Timezone: UTC)
- **Source Path**: `J:\MovedFromC\Roaming_MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05\AlphaLab_Antigravity\data\canonical\GOLD_M1_PRE2026.csv`
- **Replication Rows (Pre-2026)**: `2,827,419` bars
- **Quarantined 2026 Discovery Rows**: `0` bars
- **Discovery Overlap in Replication Set**: `0` rows
- **Replication Date Range**: `2018-01-02 09:05:00+00:00` to `2025-12-31 19:59:00+00:00`
- **Unique Calendar Years**: `[2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025]`
- **Unique Trading Days**: `2,065` days
- **Data Hash (SHA-256)**: `10d6df33c749315824bb9552b139439e6bbfcbac1bed54f272a62696c2f4965e`
- **Hard Gate 0A (>=1,000,000 Rows)**: `PASS`
- **Hard Gate 0B (>=3 Calendar Years)**: `PASS`

## 3. Verified Broker Cost Contract

- **Symbol**: `GOLD` | **Digits**: `2` | **Point**: `0.01`
- **Contract Size**: `100.0` oz/lot | **Profit Currency**: `USD`
- **Spread Representation**: `points` (spread_points * symbol_point)
- **Commission**: `7.0 USD/lot` (PROVENANCE_DOCUMENTED)
- **Cost Contract Status**: `VERIFIED`

## 4. Outcome Dependence & Overlap Audit

- **Total Events**: `271,631`
- **Mean Events per Day**: `131.5` | **Median Gap**: `6.0 bars`
- **Events with Overlapping 5m Horizon**: `46.3%`
- **Events with Overlapping 10m Horizon**: `64.6%`
- **Events with Overlapping 30m Horizon**: `93.9%`

## 5. Multi-Horizon Returns & Day-Block Bootstrap

| Horizon | N | Mean Return (bps) | Median (bps) | Win Rate % | Day-Block 95% Bootstrap CI (bps) | Mean MFE (bps) | Mean MAE (bps) |
|---|---:|---:|---:|---:|---:|---:|---:|
| 1m | 271,631 | +0.00 | +0.00 | 48.9% | [-0.01, 0.01] | 1.59 | 1.64 |
| 3m | 271,631 | +0.01 | +0.05 | 50.3% | [-0.01, 0.03] | 2.85 | 2.96 |
| 5m | 271,631 | +0.03 | +0.11 | 51.0% | [0.00, 0.06] | 3.71 | 3.87 |
| 10m | 271,631 | +0.04 | +0.17 | 51.3% | [-0.01, 0.08] | 5.30 | 5.52 |
| 15m | 271,631 | +0.03 | +0.26 | 51.6% | [-0.02, 0.09] | 6.51 | 6.77 |
| 30m | 271,631 | +0.03 | +0.33 | 51.5% | [-0.05, 0.12] | 9.29 | 9.61 |

## 6. Score Gradient and Consistency Status

- **Score Consistency Classification**: `INVERTED`

| Score Bin | N Events | Mean Return 5m (bps) | Win Rate 5m % |
|---|---:|---:|---:|
| 3-4 | 181,063 | +0.06 | - |
| 5-6 | 81,503 | -0.02 | - |
| 7-8 | 8,550 | -0.09 | - |
| 9-10 | 515 | -0.31 | - |

## 7. Dual Gross/Net Diagnostic Strategy Backtest

- **Diagnostic Status**: `NEGATIVE_DIAGNOSTIC`
- **Total Trades**: `8166`
- **Gross Win Rate**: `41.1%` | **Net Win Rate**: `29.2%`
- **Gross Profit Factor**: `1.006` | **Net Profit Factor**: `0.464`
- **Gross Expectancy**: `+0.03 USD/trade` | **Net Expectancy**: `-3.89 USD/trade`
- **Gross PnL**: `+224.26 USD` | **Net PnL**: `-31756.04 USD`
- **Total Friction Costs**: `31980.30 USD` (Mean cost: `$3.92/trade`)
- **Max Drawdown**: `31858.04 USD`

## 8. Replication Discovery Gate Battery

- **Gate 0 (Data >= 1,000,000 rows & >= 3 valid years)**: `PASS`
- **Gate 1 (Sample size >= 500 total, >= 150 long, >= 150 short)**: `PASS`
- **Gate 2 (Primary 5m Mean Return > 0)**: `PASS`
- **Gate 3 (Primary 5m Day-Block Bootstrap CI Lower > 0)**: `PASS`
- **Gate 4 (Adjacent 3m or 10m Mean Return > 0)**: `PASS`
- **Gate 5 (Temporal Stability >= 3 valid years, >= 70% positive)**: `PASS`

### **FINAL REPLICATION VERDICT: REPLICATION_CONFIRMED**

## 9. Strongest Counter-Evidence

High intra-day event density (overlapping forward return horizons) and substantial execution spread relative to gross excursion create severe drag on M1 price action reversions. Without pre-2026 out-of-discovery data coverage of at least 1,000,000 rows, the mechanism cannot be scientifically confirmed.

---
**END OF REPORT**