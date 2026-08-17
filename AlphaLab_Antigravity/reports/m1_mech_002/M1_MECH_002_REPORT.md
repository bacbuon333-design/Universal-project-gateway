# ALAB-M1-MECH-002 — Market State Transition Discovery

## Scope
Development-only mechanism decomposition on the frozen 2018-2025 GOLD M1 dataset.
No strategy, PnL backtest, trading, or 2015-2017 holdout access.

## Dataset
- SHA256: `10d6df33c749315824bb9552b139439e6bbfcbac1bed54f272a62696c2f4965e`
- Rows: `2,827,419`
- Range: `2018-01-02 09:05:00+00:00` to `2025-12-31 19:59:00+00:00`
- Sealed holdout: `2015-2017 NOT ACCESSED`

## Observable state model
- ENERGY: path efficiency, robust stretch, ATR percentile.
- LOCATION: previous observed trading-day H/L; completed-session H/L with 24 clock-hour retention; confirmed M15 swing zones with preserved 0.10*M15 ATR width.
- REJECTION: sweep depth, reclaim depth, event range, signed body, close location.
- TRANSITION: exact-clock close state relative to the failed-auction prior extreme.
- TAIL: quantiles, skew, adverse/favorable 5% expected shortfall, gap-aware MFE/MAE.

## Interpretation boundary
`SNAPBACK_SIDE` and `BREAKOUT_SIDE` are price-state labels only.
The study does not claim liquidity refill, institutional flow, or order-book causality from M1 OHLC.

## Gap policy
A +h minute label requires a bar exactly h clock minutes after the event.
No later bar substitutes for a missing minute. Excursions require a continuous bar path.

## Artifacts
- M1_MECH_002_FACTOR_SUMMARY.csv
- M1_MECH_002_LOCATION_ENERGY_MATRIX.csv
- M1_MECH_002_STATE_TRANSITIONS.csv
- M1_MECH_002_TAIL_RISK.csv
- M1_MECH_002_GAP_AUDIT.json
- M1_MECH_002_MANIFEST.json
- Local full event table (not for Git if large): `J:\MovedFromC\Roaming_MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05\AlphaLab_Antigravity\reports\m1_mech_002\local\M1_MECH_002_EVENTS.csv.gz`
