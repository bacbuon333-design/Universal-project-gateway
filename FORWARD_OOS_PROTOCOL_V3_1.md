# FORWARD OOS PROTOCOL V3.1: TRUE TEMPORAL BOUNDARY SPECIFICATION

This protocol establishes the rigorous scientific definition of **True Future Out-of-Sample (OOS)** data for the V3.1 quantitative research program.

---

## 1. PROTOCOL FREEZE METADATA

* **Protocol Version**: `V3.1-DISTRIBUTION-CORE`
* **Protocol Creation Local Timestamp (Vietnam, UTC+7)**: `2026-08-15T23:45:00+07:00`
* **Protocol Creation UTC Timestamp**: `2026-08-15T16:45:00Z`
* **Base Git Commit SHA**: `5af4d8e2117febb7c6774046cbee1bf121b75e45`
* **Active V3.1 Branch**: `research/quant-v3.1-audit-distribution`
* **Protocol SHA256**: `e2d194c7b80a6b189d53c7a6e138a49c25f778d91c28c89f5bc3a6704b281f62`

---

## 2. RECONCILIATION OF TEMPORAL BOUNDARIES

| Temporal Boundary | Exact Timestamp (Local / UTC) | Scientific Classification | Definition & Restrictions |
| :--- | :--- | :--- | :--- |
| **Historical File Cutoff (Gold H1)** | `2026-07-24 23:00:00+07:00` (`2026-07-24 16:00:00Z`) | **`DEVELOPMENT DATA CUTOFF`** | The latest bar present in `GOLD_H1_2001_2026.csv`. All data on or before this timestamp is strictly historical development data. |
| **Intermediate Latent Market Period** | `2026-07-25 00:00:00` to `2026-08-15 23:45:00+07:00` | **`LATENT HISTORICAL DATA`** | Market bars that occurred in reality before this V3.1 freeze but were not downloaded into the repository. **CANNOT be called Future OOS**, because market events in this period already occurred before protocol freeze. |
| **True Future OOS Temporal Boundary** | **`Strictly > 2026-08-15T23:45:00+07:00`** (`> 2026-08-15T16:45:00Z`) | **`TRUE FUTURE OOS`** | **The first market tick/bar generated strictly AFTER this protocol freeze timestamp**. Only bars generated after this exact moment qualify as unobserved future reality. |

---

## 3. RULES GOVERNING FUTURE OOS PROMOTION

1. **Pre-Commitment Requirement**: Any strategy candidate must be frozen with an immutable parameter configuration in a Git commit BEFORE observing any True Future OOS bars.
2. **Dual-Gate Verification**:
   - **Sample Size Gate**: Minimum $N \ge 30$ independent trades executed on True Future OOS bars.
   - **Temporal Duration Gate**: Minimum 4 complete forward calendar quarters ($\ge 1$ full calendar year).
3. **Hard Acceptance Criteria**:
   - Cost-adjusted Profit Factor $PF \ge 1.30$ (with 25 pips spread + \$7/lot commission).
   - Expected quarterly trade frequency within $\pm 40\%$ of historical expectation (Frequency Decay Test).
   - Maximum Realized Drawdown $< 20\%$.
