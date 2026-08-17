# ALAB-M1 — FINAL HOLDOUT 2015–2017

## Scope
One-shot confirmation of the single surviving narrow development hypothesis. No further discovery, gradient rescue, placebo redesign, strategy creation, PnL backtest, paper/live trading, or broker execution.

## Frozen hypothesis
After a prior-20-closed-M1-bar extreme breach, greater in-candle snapback realization is associated with sub-one-for-one +5m future total-reversion persistence (`rho_5m < 1`) across ATR_T, ATR_PRE, PRICE_BPS, and EXCURSION_RATIO.

No strict monotonic-bin claim, fixed-budget claim, market-law claim, or causal microstructure claim is part of this holdout test.

## Dataset
- Holdout years: 2015–2017 only
- SHA256: `fae4d3ef815c38110bf8e9e19ea70467b6ec1d4d0b5de2f4c790516d7331cb00`
- Rows: `1,058,276`
- Range: `2015-01-02 08:06:00+00:00` to `2017-12-29 23:57:00+00:00`
- Development 2018–2025 read by this runner: NO
- 2026+ read by this runner: NO
- Scientific regressions executed: `True`

## Frozen confirmation rule
PASS requires data/coverage integrity, all four point `rho_5m < 1`, all four individual UTC-day bootstrap 95% upper bounds `<1`, and the shared-day bootstrap 97.5th percentile of `max(rho)` across the four representations `<1`.

Year-specific 2015/2016/2017 coefficients are descriptive only and cannot rescue or overturn the pooled rule.

## Final verdict
`FINAL_HOLDOUT_CONFIRMED`

## Research program status
`CLOSE_CONFIRMED_PHENOMENON`
