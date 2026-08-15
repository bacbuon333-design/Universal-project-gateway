# V3.2 AUDIT FINDINGS: ENGINE REPAIR & DISTRIBUTED EDGE ROADMAP

This document outlines the scope of defects addressed in V3.2 and the precommitted roadmap for M30 distributed mechanism research.

---

## 1. REPAIRS SPECIFICATION (COMMIT 1 SCOPE)

1. **Engine Level Asset-Aware PnL**:
   - Eliminates post-hoc aggregate PnL rescaling.
   - Embeds `InstrumentSpec` registry directly into `DeepQuantEngine`.
   - Every individual trade calculates its true account-currency (USD) gross profit, spread loss, commission, and win/loss label using contemporaneous price-based conversions (e.g. dynamic USDJPY conversion).
2. **Engine-Level Unit Tests**:
   - Tests execute through the backtester's native simulation loop and assert numerical correctness for LONG/SHORT wins, losses, spread, and commission across XAUUSD, EURUSD, GBPUSD, USDJPY, and BTCUSD.
3. **Cross-Asset Re-Evaluation**:
   - Re-runs H-103 under the native engine without post-hoc scaling.

---

## 2. DISTRIBUTED M30 MECHANISM RESEARCH ROADMAP (H-204+)

- Primary Focus: Gold M30 (33 complete quarters, 2018Q2–2026Q2).
- Hard Standard: Every complete quarter must contain $\ge 5$ trades ($N \ge 165$), Rolling 4Q positive $\ge 70\%$, Rolling 4Q $PF \ge 1.20 \ge 65\%$, Top 3 quarters PnL $\le 40\%$.
- Precommitted Hypotheses:
  - `H-204`: M30 Squeeze Breakout with Light Trend (EMA 20/50)
  - `H-205`: M30 Volatility-Percentile Contraction/Expansion
  - `H-206`: M30 Normalized Range Compression $(H-L)/\text{ATR} \le 0.65$
  - `H-207`: M30 Session-Aware Squeeze Breakout (London/NY)
  - `H-208`: M30 Asymmetric Directional Decomposition (Long vs Short)
