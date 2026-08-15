# HYPOTHESIS REGISTRY

This registry logs every scientific hypothesis evaluated in the research program, its lineage, mechanism, tested parameters, quarterly results, and validation status.

| ID | Family | Lineage | Core Mechanism | Timeframes | Research Period | OOS Period | Results (IS / OOS / Quarters) | Final Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `H-000` | Legacy / Benchmark | CP-01 to CP-16 | DaviddTech Scalping & Multi-timeframe trend following | H1, M15 | 2022 Q2–2026 Q2 | 2001–2021 | IS PF 2.06 -> OOS PF 1.17; FX PF 0.42–0.93 | **REJECTED (OOS COLLAPSE)** |
| `H-001` | Legacy / Portfolio | CP-101 to CP-400 | Session-specific multi-engine long-only breakout | H1 | 2022 Q2–2026 Q2 | 2001–2021, FX | In-sample mined; OOS Quarterly pass rate 50.0% | **REJECTED (OVERFIT / MINED)** |
| `H-010` | R2 Alpha / Breakout | Pure Donchian | 20-bar Donchian High/Low break + ATR expansion | H1, M30, M15 | 2001–2026 (100 Qs) | 2001–2021, FX | Gold OOS PF 1.087; USDJPY PF 0.571; Q-Pass 39.7% | **REJECTED (INSUFFICIENT EDGE)** |
| `H-020` | R2 Alpha / Mean Rev | BB + RSI Stretch | Fade 2.5σ BB excursion + RSI < 30 / > 70 | H1, M30, M15 | 2001–2026 (100 Qs) | 2001–2021, FX | Gold OOS PF 1.056, PnL -$455; USDJPY PF 0.360 | **REJECTED (NEGATIVE EXPECTANCY)** |
| `H-030` | R2 Alpha / MTF Trend | Macro Trend Pullback | Macro EMA200 slope + Fast EMA21 Pullback Reversal | H1, M30, M15 | 2001–2026 (100 Qs) | 2001–2021, FX | Gold OOS PF 1.119; USDJPY PF 0.440; Q-Pass 32.3% | **REJECTED (CHOP FRAGILITY)** |
| `H-040` | R2 Alpha / Volatility | Volatility Squeeze | Bollinger Bands inside Keltner Channels (5 bars) | H1, M30, M15 | 2001–2026 (100 Qs) | 2001–2021, FX | Gold OOS PF 1.491, PnL +$10,683; USDJPY PF 0.503 | **QUALIFIED (CORE ALPHA DRIVER)** |
| `H-050` | R2 Alpha / Session ORB | London & NY ORB | Opening Range Breakout at 07:00 & 13:00 UTC | M15, M30 | 2018–2026 (35 Qs) | FX (12 Yrs) | Gold PnL -$9.1k (London) / -$6.5k (NY); Q-Pass <18% | **REJECTED (FALSE BREAKOUT NOISE)** |
| `H-060` | R3/R4 Meta / Regime | Adaptive Squeeze | Squeeze + Macro EMA200 Trend + Kaufman ER Filter | H1, M30 | 2001–2026 (100 Qs) | 2001–2021, FX | Gold Total PF 2.078, OOS PF 1.639; Expectancy +0.351 R | **SURVIVOR (CAND-001 BASELINE)** |
| `H-070` | R7 Multi-Scale | Multi-Scale Squeeze | Squeeze + Macro + ER across M15, M30, H1 | M15, M30, H1 | 2001–2026 | Multi-Asset | Gold H1 PF 2.078, M30 PF 1.542, M15 PF 1.008 | **VALIDATED (SCALE PERSISTENCE)** |
