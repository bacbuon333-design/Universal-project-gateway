# ALAB NEXUS v32 - Backtest Results

## Baseline Configuration

**TRAIN (2022-05-02 to 2024-04-30)**
- PnL: 16.74%
- Max DD: 16.36%
- Trades: 13
- Win Rate: 46.15%
- Profit Factor: 1.48
- Breakdown: {'STRUCTURE_LONG': 13}

**OOS (2024-05-01 to 2025-04-30)**
- PnL: -5.93%
- Max DD: 15.36%
- Trades: 13
- Win Rate: 38.46%
- Profit Factor: 0.83
- Breakdown: {'STRUCTURE_LONG': 13}

**SEALED (2025-05-01 to 2026-07-24)**
- PnL: 8.16%
- Max DD: 22.05%
- Trades: 42
- Win Rate: 38.10%
- Profit Factor: 1.12
- Breakdown: {'STRUCTURE_LONG': 42}

**2022-2023 (2022-01-01 to 2023-12-31)**
- PnL: 23.98%
- Max DD: 11.35%
- Trades: 10
- Win Rate: 60.00%
- Profit Factor: 1.86
- Breakdown: {'STRUCTURE_LONG': 10}

**2023-2024 (2023-01-01 to 2024-12-31)**
- PnL: 30.67%
- Max DD: 18.95%
- Trades: 17
- Win Rate: 35.29%
- Profit Factor: 1.83
- Breakdown: {'STRUCTURE_LONG': 17}

**2024-2025 (2024-01-01 to 2025-12-31)**
- PnL: -20.70%
- Max DD: 20.70%
- Trades: 32
- Win Rate: 28.12%
- Profit Factor: 0.59
- Breakdown: {'STRUCTURE_LONG': 32}

**2025-2026 (2025-01-01 to 2026-12-31)**
- PnL: 1.47%
- Max DD: 22.05%
- Trades: 48
- Win Rate: 39.58%
- Profit Factor: 1.02
- Breakdown: {'STRUCTURE_LONG': 48}

## Sensitivity Analysis (OOS Period 2024-05-01 to 2025-04-30)

**Threshold 0.5** -> PnL: -5.93%, MaxDD: 15.36%, Trades: 13, WR: 38.46%, PF: 0.83

**Threshold 1.0** -> PnL: -5.93%, MaxDD: 15.36%, Trades: 13, WR: 38.46%, PF: 0.83

**Threshold 1.5** -> PnL: -5.93%, MaxDD: 15.36%, Trades: 13, WR: 38.46%, PF: 0.83

**Threshold 2.0** -> PnL: -5.93%, MaxDD: 15.36%, Trades: 13, WR: 38.46%, PF: 0.83

## Honest Assessment & Recommendations

**Does it meet the 20% annual PnL and MaxDD < 20% target?**
**No.** While the training period (2022-2024) and some individual historical slices showed promising results, the Out-Of-Sample (OOS) period (2024-2025) generated a loss (-5.93%) with a 15.36% MaxDD. The SEALED period also fell short, yielding only 8.16% and exceeding the MaxDD limit (22.05%). The current HMM causal engine setup is too rigid, and the relaxed signal parameters resulted in many false setups underperforming the baseline. 

**Modifications Needed to Reach Target:**
1. **Dynamic HMM State Emission:** Instead of a static HMM fitted once on the 2022-2024 period, we should consider a slow-rolling recalibration of the HMM emission matrices. 
2. **Signal Parameter Tuning:** The engine only triggered STRUCTURE_LONG trades, meaning the thresholds for IMPULSE_LONG and SHORT setups are disconnected from current market regimes. We need an adaptive filter for Donchian breakouts.
3. **Shorter Cooldown:** Changing the cooldown to 48 hours instead of 72 hours could increase the frequency of high-quality setups without overtrading.
4. **Distance Filtering:** The strict dist_to_low48 check conflicts heavily with the 
etracement logic on lower timeframes like H1. This interaction requires further backtesting via an independent grid search to find the correct structural entry band.
