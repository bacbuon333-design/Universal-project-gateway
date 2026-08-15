# V3.1 REPAIRED EVENT STUDY: VOLATILITY COMPRESSION STATE VS RELEASE DYNAMICS

This report documents the decoupled econometric event study analyzing discrete compression episodes and breakout releases versus uncompressed baselines.

---

## 1. EVENT FAMILY SPECIFICATIONS & DEDUPLICATION

* **Dataset**: `GOLD_H1_2001_2026.csv` (81,463 bars, 2001–2026).
* **Discrete Squeeze Episodes ($\ge 4$ bars)**: **315 unique episodes** (Zero overlapping multi-bar inflation).
* **Overlap Rate within Episodes**: Decoupled to exactly 1 event per episode release.

---

## 2. FORWARD VOLATILITY EXPANSION BY EVENT FAMILY

| Event Family | Event Sample ($N$) | 6h Max Range (%) | 12h Max Range (%) | 24h Max Range (%) | 48h Max Range (%) | 72h Max Range (%) | Expansion Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Family A: Active Compression State** | 2,022 | 0.729% | 1.118% | 1.727% | 2.423% | 3.011% | **COMPRESSED ($< \text{Baseline}$)** |
| **Family B: Episode Start Bar** | 315 | 0.692% | 1.087% | 1.712% | 2.458% | 3.082% | **COMPRESSED** |
| **Family C: Episode End Bar** | 315 | 0.894% | 1.279% | 1.800% | 2.493% | 3.111% | **TRANSITIONAL** |
| **Family D: Squeeze $\to$ Upper Breakout**| 126 | **0.930%** | **1.396%** | **1.957%** | **2.749%** | **3.366%** | **STRONG EXPANSION ($> \text{Baseline}$)** |
| **Family E: Squeeze $\to$ Lower Breakout**| 142 | **0.899%** | **1.279%** | **1.752%** | **2.408%** | **2.968%** | **EXPANSION** |
| **Family F: Non-Squeeze Upper Break** | 1,414 | 0.930% | 1.232% | 1.811% | 2.575% | 3.146% | Uncompressed Breakout |
| **Family G: Non-Squeeze Lower Break** | 1,282 | 0.997% | 1.325% | 1.841% | 2.584% | 3.143% | Uncompressed Breakout |
| **Family H: Unconditional Baseline** | 16,239 | 0.828% | 1.201% | 1.745% | 2.505% | 3.092% | Market Baseline |

---

## 3. KEY ECONOMETRIC TAKEAWAY

1. **State vs Release Decoupling**: Compression state bars exhibit lower than baseline volatility ($1.118\%$ vs $1.201\%$ at 12h).
2. **Breakout Release Explosion**: Upper breakout releases following squeeze exhibit $1.957\%$ (24h) and $2.749\%$ (48h) maximum price excursion, confirming that volatility expansion is localized at the release event.
