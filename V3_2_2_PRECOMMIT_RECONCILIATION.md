# V3.2.2 PRECOMMIT-TO-CODE RECONCILIATION MATRIX

* **Authoritative Precommit Git Commit**: `f5be62deba702fd737149c64b5faca3599f0daca`
* **Authoritative Precommit File**: [`V3_2_PRECOMMIT_H204_PLUS.md`](file:///C:/Users/gugul/AppData/Roaming/MetaQuotes/Terminal/BB16F565FAAA6B23A20C26C49416FF05/V3_2_PRECOMMIT_H204_PLUS.md)

---

## 1. RECONCILIATION AUDIT MATRIX

| Hypothesis | Element | Original Precommit (`f5be62d`) | V3.2.1 Implementation | Status | V3.2.2 Action |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`H-204`** | Compression | BB(20, 2.0) inside Kelt(20, 1.2) $\ge 2$ bars | BB inside Kelt $\ge 2$ bars | **`EXACT MATCH`** | Retain |
| | Directional | `EMA(20) > EMA(50)` for Bull, `<` for Bear | `(ema20 > ema50) & (c > ema20)` / `(ema20 < ema50) & (c < ema20)` | **`DRIFT`** | **Remove `(c > ema20)` / `(c < ema20)`** |
| | Exit | $\text{SL} = 1.5\text{ ATR}, \text{TP} = 2.5\times\text{SL}$ ($3.75\text{ ATR}$) | $\text{sl\_dist} = 1.5\text{ ATR}, \text{tp\_dist} = 3.75\text{ ATR}$ | **`EXACT MATCH`** | Retain |
| **`H-205`** | Compression | $\text{ATR}(14) / \text{ATR}(50) \le 0.80 \ge 2$ bars | $\text{ATR}(14) / \text{ATR}(50) \le 0.80 \ge 2$ bars | **`EXACT MATCH`** | Retain |
| | Breakout | Close crosses 10-bar Donchian + EMA(50) | `c > donch10_h & (c > ema50)` | **`EXACT MATCH`** | Retain |
| | Exit | $\text{SL} = 1.5\text{ ATR}, \text{TP} = 2.5\times\text{SL}$ ($3.75\text{ ATR}$) | $\text{sl\_dist} = 1.5\text{ ATR}, \text{tp\_dist} = 3.75\text{ ATR}$ | **`EXACT MATCH`** | Retain |
| **`H-206`** | Compression | Bar Range $(H-L) \le 0.65\times\text{ATR}(14) \ge 2$ bars | Range $\le 0.65\times\text{ATR}(14) \ge 2$ bars | **`EXACT MATCH`** | Retain |
| | Breakout | Breakout 3-bar High/Low + EMA(50) | `c > h3 & (c > ema50) & (ema50 > shift(3))` | **`DRIFT`** | **Remove `(ema50 > shift(3))` slope filter** |
| | Exit | $\text{SL} = 1.5\text{ ATR}, \text{TP} = 2.5\times\text{SL}$ ($3.75\text{ ATR}$) | $\text{sl\_dist} = 1.5\text{ ATR}, \text{tp\_dist} = 3.75\text{ ATR}$ | **`EXACT MATCH`** | Retain |
| **`H-207`** | Compression | BB inside Kelt $\ge 2$ bars | BB inside Kelt $\ge 2$ bars | **`EXACT MATCH`** | Retain |
| | Session / Filter | Time of Day $\in [07:00, 17:00\text{ UTC}]$ + EMA(50) | Hour $\in [7, 17]$ & `(c > ema50)` / `(c < ema50)` | **`EXACT MATCH`** | Retain |
| | Exit | $\text{SL} = 1.5\text{ ATR}, \text{TP} = 2.5\times\text{SL}$ ($3.75\text{ ATR}$) | $\text{sl\_dist} = 1.5\text{ ATR}, \text{tp\_dist} = 3.75\text{ ATR}$ | **`EXACT MATCH`** | Retain |
| **`H-208A`**| Structure | Long-Only Squeeze | Inherited H-204 (Long+Short base) | **`DRIFT`** | Decouple |
| | Directional | Bullish EMA(50) slope (`ema50 > shift(1)`) | Inherited EMA20/EMA50 filter from H-204 | **`DRIFT`** | **Implement EMA50 slope** |
| | Exit | $\text{SL} = 1.5\text{ ATR}, \text{TP} = 2.0\times\text{SL}$ ($3.0\text{ ATR}$) | Inherited $\text{TP} = 2.5\times\text{SL}$ ($3.75\text{ ATR}$) from H-204 | **`DRIFT`** | **Change to $\text{TP} = 2.0\times\text{SL}$ ($3.0\text{ ATR}$)** |
| **`H-208B`**| Structure | Short-Only Squeeze | Inherited H-204 (Long+Short base) | **`DRIFT`** | Decouple |
| | Directional | Bearish EMA(50) slope (`ema50 < shift(1)`) | Inherited EMA20/EMA50 filter from H-204 | **`DRIFT`** | **Implement EMA50 slope** |
| | Exit | $\text{SL} = 1.5\text{ ATR}, \text{TP} = 3.0\times\text{SL}$ ($4.5\text{ ATR}$) | Inherited $\text{TP} = 2.5\times\text{SL}$ ($3.75\text{ ATR}$) from H-204 | **`DRIFT`** | **Change to $\text{TP} = 3.0\times\text{SL}$ ($4.5\text{ ATR}$)** |
| **`H-208C`**| Compression | BB inside Kelt $\ge 2$ bars | BB inside Kelt $\ge 2$ bars | **`EXACT MATCH`** | Retain |
| | Entries | Symmetrical entries | Added uncommitted EMA50 slope condition | **`DRIFT`** | **Remove uncommitted EMA50 slope filter; keep symmetrical breakout + EMA50** |
| | Exit | Asymmetric TP ($2.0\times\text{SL}$ Long, $3.0\times\text{SL}$ Short) | Long $\text{tp} = 3.0\text{ ATR}$, Short $\text{tp} = 4.5\text{ ATR}$ | **`EXACT MATCH`** | Retain |

---

## 2. RE-EXECUTION SUMMARY

- **Hypotheses with Exact Match in V3.2.1**: `H-205`, `H-207` (evaluation metrics recomputed under exact precommitted gates).
- **Hypotheses Requiring Code Correction & Rerun**: `H-204`, `H-206`, `H-208A`, `H-208B`, `H-208C`.
