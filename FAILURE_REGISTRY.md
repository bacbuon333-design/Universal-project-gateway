# FAILURE REGISTRY

This registry documents all rejected strategies, mechanisms, and ideas, detailing the exact empirical failure category and root-cause evidence to prevent rediscovery loops.

| ID | Failure Category | Strategy / Family | Root Cause Evidence | Impact / Action |
| :--- | :--- | :--- | :--- | :--- |
| `FAIL-001` | `OOS COLLAPSE` | CP-01 / CP-04 (DaviddTech) | 90% adverse excursion on Bar 1; win rate < 42% across multi-year cycles. | Strategy family permanently archived. |
| `FAIL-002` | `MULTIPLE-TESTING BIAS` | CP-17 to CP-400 (Checkpoints Bloat) | Optimization of 10+ conjunction rules against fixed 2022–2026 dataset; collapsed on pre-2022 history. | Prohibit complex conjunction filtering. Enforce strict quarterly OOS. |
| `FAIL-003` | `OPTIMISTIC FILLS` | Unbounded Intra-bar Simulators | Assuming TP triggered first on candles that touch both TP and SL. | Enforce pessimistic intra-bar execution: SL always triggers first on ambiguous bars. |
| `FAIL-004` | `TIMEFRAME FRAGILITY` | CP-101 Long-only session filters | Edge vanished when evaluated on EURUSD, GBPUSD, USDJPY, and 2001–2021 Gold. | Mandate cross-asset and multi-decade validation. |
| `FAIL-005` | `NO STANDALONE EDGE` | H-010 (Pure Donchian Breakout) | OOS PF 1.087 on Gold; collapses to PF 0.571 on FX. Whipsaws during ranging quarters. | Breakout requires prior volatility compression filter. |
| `FAIL-006` | `NEGATIVE EXPECTANCY` | H-020 (BB + RSI Mean Reversion) | Negative total PnL (-$455 to -$14k) on Gold; PF 0.360 on USDJPY. Counter-trend tail risk. | Counter-trend fading rejected as standalone model. |
| `FAIL-007` | `CHOP FRAGILITY` | H-030 (Macro Trend + Fast EMA Pullback) | Low quarterly pass rate (32.3%) on Gold; PF 0.440 on USDJPY. High churn during consolidation. | Pullback triggers without compression filters are prone to false resumes. |
| `FAIL-008` | `NOISE OVERWHELM` | H-050 (Session ORB London/NY) | Net loss -$9.1k (London) / -$6.5k (NY) on Gold M30; quarterly pass rate < 18%. | Fixed-time opening breakouts suffer from frequent intraday liquidity stop-runs. |
