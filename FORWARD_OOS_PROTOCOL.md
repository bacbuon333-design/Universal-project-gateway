# FORWARD OUT-OF-SAMPLE (OOS) VALIDATION PROTOCOL & CUTOFF BOUNDARIES

This protocol establishes the permanent, immutable scientific boundary between all **Historical Development / Research Data** and **True Future Out-of-Sample Data** for the V3 research program.

---

## 1. PROTOCOL METADATA & REPOSITORY STATE

* **Protocol Version**: `V3.0-FORWARD-CORE`
* **Creation / Freeze Timestamp**: `2026-08-15T23:30:00+07:00`
* **Base Git Commit SHA**: `b9ab22065e5e404289a654217ffdc68e40820ba9` (Audit V2 clean revalidation)
* **Active V3 Research Branch**: `research/quant-v3-mechanism-forward`
* **Cryptographic Protocol SHA256**: `f688e1548a31e847c13dcbc06c27389a9f2420a1cf64560b431713e5ae80d196`

---

## 2. IMMUTABLE HISTORICAL DATA CUTOFF BOUNDARIES

All data currently stored in the repository through the latest recorded timestamp is strictly classified as **Historical Development / Research Data**. No historical sub-period may be claimed as pristine OOS.

| Dataset Filename | Asset | Timeframe | Start Timestamp | Exact Historical Cutoff Timestamp | Total Rows | Total Calendar Quarters | Complete Quarters |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `GOLD_H1_2001_2026.csv` | GOLD (XAUUSD) | H1 | `2001-06-04 01:00:00` | **`2026-07-24 23:00:00`** | 81,463 | 102 | **100** (2001Q3–2026Q2) |
| `GOLD_H4.csv` | GOLD (XAUUSD) | H4 | `2001-06-04 00:00:00` | **`2026-07-24 20:00:00`** | 23,493 | 102 | **100** (2001Q3–2026Q2) |
| `GOLD_D1_2001_2026.csv` | GOLD (XAUUSD) | D1 | `2001-06-04 00:00:00` | **`2026-07-24 00:00:00`** | 6,538 | 102 | **100** (2001Q3–2026Q2) |
| `GOLD_M30.csv` | GOLD (XAUUSD) | M30 | `2018-02-01 15:00:00` | **`2026-07-24 23:30:00`** | 99,999 | 35 | **33** (2018Q2–2026Q2) |
| `GOLD_M15.csv` | GOLD (XAUUSD) | M15 | `2022-05-02 03:45:00` | **`2026-07-24 23:45:00`** | 99,999 | 18 | **16** (2022Q3–2026Q2) |
| `GOLD_M5.csv` | GOLD (XAUUSD) | M5 | `2025-02-25 08:15:00` | **`2026-07-24 23:55:00`** | 99,999 | 7 | **5** (2025Q2–2026Q2) |
| `GOLD_M1_2001_2026.csv` | GOLD (XAUUSD) | M1 | `2026-04-15 01:12:00` | **`2026-07-24 23:57:00`** | 99,999 | 2 | **1** (2026Q2) |
| `EURUSD_H1.csv` | EURUSD | H1 | `2014-07-01 10:00:00` | **`2026-07-31 00:00:00`** | 75,000 | 49 | **48** (2014Q3–2026Q2) |
| `GBPUSD_H1.csv` | GBPUSD | H1 | `2014-07-01 10:00:00` | **`2026-07-31 00:00:00`** | 75,000 | 49 | **48** (2014Q3–2026Q2) |
| `USDJPY_H1.csv` | USDJPY | H1 | `2014-07-01 10:00:00` | **`2026-07-31 00:00:00`** | 75,000 | 49 | **48** (2014Q3–2026Q2) |
| `BTCUSD_H1.csv` | BTCUSD | H1 | `2013-01-02 00:00:00` | **`2026-07-31 00:00:00`** | 70,823 | 55 | **53** (2013Q2–2026Q2) |

---

## 3. RULES GOVERNING TRUE FUTURE OOS VALIDATION

To qualify as **True Future Out-of-Sample (OOS)**:
1. **Temporal Precedence**: The market data must have a timestamp strictly greater than the cutoff timestamp (e.g., `> 2026-07-24 23:00:00` for Gold H1).
2. **Pre-Commitment**: The candidate strategy logic, parameter set, risk rules, and pass/fail criteria must be registered in [`FORWARD_CANDIDATE_REGISTRY.md`](file:///C:/Users/gugul/AppData/Roaming/MetaQuotes/Terminal/BB16F565FAAA6B23A20C26C49416FF05/FORWARD_CANDIDATE_REGISTRY.md) with an immutable cryptographic SHA256 hash BEFORE observing future bars.
3. **Zero Post-Hoc Tuning**: No parameter tuning, filter adjustment, or threshold modification is permitted after observing future data. Any change creates a new hypothesis that restarts the future observation clock.
4. **Dual Gate Requirement**: Future validation requires satisfying BOTH:
   - **Sample Size Gate**: Minimum $N \ge 30$ independent trades executed under future data.
   - **Calendar Duration Gate**: Minimum 4 complete forward calendar quarters (1 full calendar year).
5. **Acceptance Threshold**:
   - Cost-adjusted Profit Factor $PF \ge 1.30$ (with 25 pips spread + \$7/lot commission).
   - Positive average expectancy $\text{Exp} > +0.10\text{ R / trade}$.
   - Max Realized Drawdown $< 20\%$.
