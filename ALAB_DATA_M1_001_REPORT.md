# ALAB-DATA-M1-001 — Canonical GOLD M1 Historical Dataset Discovery and Audit Report

## 1. Executive Summary and Final Data Verdict

- **Task ID**: `ALAB-DATA-M1-001`
- **Repository**: `bacbuon333-design/Universal-project-gateway`
- **Branch**: `research/alab-data-m1-001`
- **Base Commit**: `9d29c67da02b7031f29d1c32894580e074951dbd`
- **Objective**: Discover, audit, and canonicalize pre-2026 historical GOLD M1 data ($\ge 1,000,000$ bars, $\ge 3$ calendar years) for AlphaLab.
- **Safety Boundary**: Zero trading, zero strategy modification, zero backtesting, zero event studies.

### **DATA VERDICT: STOP_BLOCKED_DATA_INSUFFICIENT**

---

## 2. Multi-Source Discovery Findings

A exhaustive scan was conducted across four distinct data modalities:

### A. Local Flat File (`AlphaLab_Antigravity/data/GOLD_M1_2001_2026.csv`)
- **Total Rows**: `99,999` M1 bars.
- **Actual Date Range**: `2026-04-15 01:12:00 UTC` to `2026-07-24 23:57:00 UTC` (~3.3 months).
- **Pre-2026 Rows**: `0` rows.
- **2026 Discovery Quarantine**: `99,999` rows quarantined as `DISCOVERY_SAMPLE_SEEN`.
- **SHA-256**: `b980ac086f5de4ab60621d0ddcb3bac59d37ebd0bec236d24971f81918b1f3ec`.
- **File Size**: `7,219,308 bytes`.
- **Finding**: Despite the filename `GOLD_M1_2001_2026.csv`, the file contains strictly 2026 data.

### B. Local SQLite Database (`AlphaLab_Antigravity/data/gold_history.db:gold_m1`)
- **Total Rows**: `99,999` M1 bars.
- **Actual Date Range**: `2026-04-15 01:12:00 UTC` to `2026-07-24 23:57:00 UTC`.
- **Pre-2026 Rows**: `0` rows.
- **Finding**: Identical content to the CSV dataset.

### C. Read-Only MetaTrader 5 Python API Buffer
- **Connected Server**: `XMGlobal-MT5 9` (Login: `333943735`, Build: `6090`).
- **Symbol Inspected**: `GOLD` (Point: `0.01`, Digits: `2`, Contract Size: `100.0` oz).
- **Terminal Configuration**: `Terminal maxbars = 100,000` (`Charts.MaxBars=100000` in `config/common.ini`).
- **API Extraction Depth Probed**:
  - `pos = 0`: `2026-08-17 09:36:00 UTC` (10 bars returned, OK).
  - `pos = 50,000`: `2026-06-25 22:28:00 UTC` (10 bars returned, OK).
  - `pos = 99,990`: `2026-05-06 09:57:00 UTC` (10 bars returned, OK).
  - `pos = 100,000`: `None, error=(-1, 'Terminal: Call failed')`.
  - `pos = 150,000`: `None, error=(-1, 'Terminal: Call failed')`.
- **Pre-2026 Rows Accessible via Python API**: `0` rows.
- **Root Cause**: The terminal process memory manager strictly clamps the in-memory M1 chart buffer to 100,000 bars.

### D. MT5 Offline History Cache (`bases\XMGlobal-MT5 9\history\GOLD\*.hcc`)
- **Files Detected on Disk**:
  - `2015.hcc` (21.2 MB)
  - `2016.hcc` (21.3 MB)
  - `2017.hcc` (21.2 MB)
  - `2018.hcc` (21.2 MB)
  - `2019.hcc` (21.2 MB)
  - `2020.hcc` (21.3 MB)
  - `2021.hcc` (21.3 MB)
  - `2022.hcc` (21.3 MB)
  - `2023.hcc` (21.2 MB)
  - `2024.hcc` (21.4 MB)
  - `2025.hcc` (21.2 MB)
  - `2026.hcc` (21.8 MB)
- **Total Compressed Size**: `256,847,844 bytes` (~256 MB LZ4 compressed binary archive).
- **Status**: Binary compressed `.hcc` archive files physically exist locally, but are inaccessible to the MT5 Python API while the active terminal instance is bounded by the 100k chart buffer limit.

---

## 3. Data Audit and Hard Requirements Evaluation

| Metric / Gate | Required Threshold | Discovered Pre-2026 Value | Gate Status |
|---|---|---|---|
| **Replication Row Count** | $\ge 1,000,000$ valid M1 bars | `0` valid bars | **FAIL** |
| **Valid Calendar Years** | $\ge 3$ independent years | `0` years | **FAIL** |
| **2026 Discovery Overlap** | Exactly `0` rows | `0` rows (100% quarantined) | **PASS** |
| **OHLC Validity** | `high >= max(open, close)` | `0` violations | **PASS** |
| **Monotonicity & Uniqueness** | `0` duplicate timestamps | `0` violations | **PASS** |

---

## 4. Methodological Safeguards

1. **No Data Fabrication**: Zero synthetic candles were substituted.
2. **No Lookahead / Forward Filling**: No missing minutes were forward-filled or interpolated.
3. **Strict Discovery Quarantine**: The 99,999-bar 2026 dataset was isolated completely and excluded from replication eligibility.
4. **Honest Reporting**: In accordance with Rule 6 and Rule 11 of the task charter, the insufficiency is reported truthfully as `STOP_BLOCKED_DATA_INSUFFICIENT`.

---

## 5. Technical Path to Unlocking Pre-2026 M1 Data

To extract the ~4,000,000 historical M1 bars residing in the local `bases\XMGlobal-MT5 9\history\GOLD\*.hcc` archive:
1. In MT5 Terminal: Navigate to `Tools` -> `Options` -> `Charts` -> Set `Max bars in chart` to `Unlimited`.
2. Restart MT5 Terminal so the chart memory manager loads the complete historical archive.
3. Once `maxbars` is set to `Unlimited`, MT5 Python API `copy_rates_range` can extract the 2018–2025 M1 bars directly into a canonical CSV.

---

**END OF DATA AUDIT REPORT**
