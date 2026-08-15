# V3.1 DIRECTIONALITY STUDY: IDENTICAL HORIZON PREDICTABILITY ANALYSIS

This report compares Long and Short directional predictability following compression release across strictly identical forward horizons ($6\text{h}, 12\text{h}, 24\text{h}, 48\text{h}, 72\text{h}$).

---

## 1. IDENTICAL HORIZON PERFORMANCE COMPARISON

| Architecture | Events | Horizon | Mean Return (%) | Median Return (%) | Win Rate (%) | Mean MFE (%) | Mean MAE (%) | MFE/MAE Ratio | 95% Confidence Interval |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **LONG: Baseline Non-Squeeze Break** | 1,414 | **24h** | +0.098% | +0.021% | 52.8% | 0.814% | 0.704% | 1.156 | `[+0.01%, +0.18%]` |
| **LONG: Squeeze Upper Breakout** | 126 | **24h** | +0.155% | -0.010% | 47.6% | 0.887% | 0.738% | 1.202 | `[-0.12%, +0.43%]` |
| **LONG: Squeeze + Bullish Macro Trend**| 80 | **24h** | **+0.174%** | +0.005% | 50.0% | **0.998%** | 0.765% | **1.305** | `[-0.18%, +0.53%]` |
| **SHORT: Baseline Non-Squeeze Break**| 1,282 | **24h** | **-0.129%** | -0.071% | 45.6% | 0.712% | 0.755% | 0.943 | `[-0.21%, -0.05%]` |
| **SHORT: Squeeze Lower Breakout** | 142 | **24h** | +0.087% | +0.065% | 55.6% | 0.803% | 0.693% | 1.158 | `[-0.14%, +0.31%]` |
| **SHORT: Squeeze + Bearish Macro Trend**| 80 | **24h** | **+0.219%** | +0.156% | **60.0%** | **0.902%** | 0.687% | **1.313** | `[-0.08%, +0.52%]` |
| | | | | | | | | | |
| **LONG: Baseline Non-Squeeze Break** | 1,414 | **48h** | +0.147% | +0.085% | 51.8% | 1.258% | 1.074% | 1.172 | `[+0.04%, +0.25%]` |
| **LONG: Squeeze Upper Breakout** | 126 | **48h** | +0.150% | -0.024% | 46.8% | 1.341% | 1.097% | 1.222 | `[-0.23%, +0.53%]` |
| **LONG: Squeeze + Bullish Macro Trend**| 80 | **48h** | -0.005% | -0.058% | 45.0% | 1.458% | 1.198% | 1.217 | `[-0.43%, +0.42%]` |
| **SHORT: Baseline Non-Squeeze Break**| 1,282 | **48h** | **-0.271%** | -0.198% | 45.2% | 1.042% | 1.218% | 0.856 | `[-0.39%, -0.15%]` |
| **SHORT: Squeeze Lower Breakout** | 142 | **48h** | +0.218% | +0.165% | 54.9% | 1.228% | 0.978% | 1.255 | `[-0.04%, +0.48%]` |
| **SHORT: Squeeze + Bearish Macro Trend**| 80 | **48h** | **+0.517%** | **+0.342%** | **57.5%** | **1.456%** | **0.922%** | **1.580** | **`[+0.17%, +0.87%]`** |

---

## 2. SEPARATE MECHANISM EVALUATION

* **SHORT Mechanism Strength**: **VERY STRONG & STATISTICALLY SIGNIFICANT**.
  - Squeeze + Bearish Macro Trend generates $+0.517\%$ mean return at 48h with a 95% Confidence Interval `[+0.17%, +0.87%]` strictly above zero, $57.5\%$ win rate, and MFE/MAE ratio of **$1.580$**.
  - Uncompressed downward breakouts lose $-0.271\%$. The squeeze filter prevents catastrophic false breakdown churn.
* **LONG Mechanism Strength**: **MODERATE AT 24H, DECAYS AT 48H**.
  - Squeeze + Bullish Macro Trend shows positive asymmetry at 24h (MFE/MAE $1.305$), but mean return flattens by 48h ($-0.005\%$).
