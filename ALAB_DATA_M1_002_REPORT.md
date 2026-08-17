# ALAB-DATA-M1-002 — MT5 History Unlock & Canonical Extraction Report

## 1. Executive Summary & Data Verdict

- **Task ID**: `ALAB-DATA-M1-002`
- **Symbol**: `GOLD` (Timeframe: M1, Timezone: UTC)
- **Canonical Dataset Path**: `AlphaLab_Antigravity/data/canonical/GOLD_M1_PRE2026.csv`
- **Total Rows Extracted**: `2,827,419` valid M1 bars
- **Date Range**: `2018-01-02 09:05:00+00:00` to `2025-12-31 19:59:00+00:00`
- **Calendar Years**: `[2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025]` (8 full years)
- **Unique Trading Days**: `2,065` days
- **Dataset SHA-256**: `10d6df33c749315824bb9552b139439e6bbfcbac1bed54f272a62696c2f4965e`
- **File Size**: `208.34 MB`
- **Discovery 2026 Overlap**: `0` rows (Strictly quarantined)

### **FINAL DATA VERDICT: READY_FOR_REPLICATION**

## 2. Terminal State and MaxBars Unlock Audit

- **Terminal Path**: `C:\Program Files\XM Global MT5`
- **Server**: `XMGlobal-MT5 9` (Login: `333943735`, Build: `6090`)
- **Old MaxBars Ceiling**: `100,000` bars
- **New Effective MaxBars**: `100,000,000` bars (Unlimited chart memory)
- **Oldest Accessible Bar Before Unlock**: `2026-05-06 10:03:00+00:00`
- **Oldest Accessible Bar After Unlock**: `2018-01-02 09:05:00+00:00`
- **History Depth Expansion**: Expanded from 100k bars (~3 months) to **2,827,419 bars (8 full calendar years)**.

## 3. Annual Chunk Extraction Breakdown

| Year | Requested Range (UTC) | Returned Rows | Actual First Bar | Actual Last Bar | Status |
|---|---|---:|---|---|---|
| 2018 | 2018-01-01 to 2018-12-31 | 351,696 | 2018-01-02 09:05:00+00:00 | 2018-12-31 18:50:00+00:00 | `SUCCESS` |
| 2019 | 2019-01-01 to 2019-12-31 | 352,158 | 2019-01-02 09:05:00+00:00 | 2019-12-31 18:50:00+00:00 | `SUCCESS` |
| 2020 | 2020-01-01 to 2020-12-31 | 354,255 | 2020-01-02 09:05:00+00:00 | 2020-12-31 18:50:00+00:00 | `SUCCESS` |
| 2021 | 2021-01-01 to 2021-12-31 | 353,758 | 2021-01-04 01:00:00+00:00 | 2021-12-31 18:50:00+00:00 | `SUCCESS` |
| 2022 | 2022-01-01 to 2022-12-31 | 354,441 | 2022-01-03 01:00:00+00:00 | 2022-12-30 23:57:00+00:00 | `SUCCESS` |
| 2023 | 2023-01-01 to 2023-12-31 | 353,062 | 2023-01-03 01:00:00+00:00 | 2023-12-29 23:57:00+00:00 | `SUCCESS` |
| 2024 | 2024-01-01 to 2024-12-31 | 354,980 | 2024-01-02 01:00:00+00:00 | 2024-12-31 20:00:00+00:00 | `SUCCESS` |
| 2025 | 2025-01-01 to 2025-12-31 | 353,069 | 2025-01-02 08:00:00+00:00 | 2025-12-31 19:59:00+00:00 | `SUCCESS` |

## 4. Canonical Quality & Integrity Checks

| Quality Gate | Required Standard | Observed Metric | Gate Status |
|---|---|---|---|
| **Sample Size** | $\ge 1,000,000$ M1 bars | `2,827,419` bars | **PASS** |
| **Temporal Coverage** | $\ge 3$ calendar years | `8` years (2018-2025) | **PASS** |
| **Discovery Quarantine** | Exactly `0` rows $\ge 2026-01-01$ | `0` rows | **PASS** |
| **OHLC Violations** | `0` violations | `0` violations | **PASS** |
| **Missing Data** | `0` null values | `0` null values | **PASS** |
| **Deduplication** | Deterministic monotonic time | `0` duplicates removed | **PASS** |

## 5. Methodological Provenance

1. **Official Timeseries Path**: All data extracted via `MetaTrader5.copy_rates_range` with explicit UTC Unix timestamps. Zero binary `.hcc` reverse engineering.
2. **No Data Fabrication**: Zero synthetic bars, zero interpolation, zero forward-filling across market closes.
3. **Zero 2026 Leakage**: The 2026 discovery sample (`99,999` bars) remains isolated.

---
**END OF REPORT**