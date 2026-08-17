# ALAB-M1-MECH-003 — Matched Control Study

## Question
Does a Failed Auction contain forward information beyond the fact that its trigger candle already closed back inside the breached prior extreme?

## Scope
- Frozen GOLD M1 development dataset: 2018-2025 only.
- Dataset SHA256: `10d6df33c749315824bb9552b139439e6bbfcbac1bed54f272a62696c2f4965e`.
- 2015-2017 sealed holdout: NOT ACCESSED.
- 2026 discovery sample: NOT ACCESSED.
- No strategy, PnL backtest, paper/live trading, or broker execution.

## Treatment and control
- FAILED_AUCTION: prior 20-bar extreme is breached and event close returns inside the old range.
- ACCEPTED_BREAKOUT: the same type of extreme is breached and event close remains beyond the breached level.
- Exact closes at the prior extreme and dual-side breach bars are excluded.

## Matching
Frozen coarsened exact matching on:
- breach side
- calendar year
- UTC hour
- structural location count
- ATR-percentile bin
- path-efficiency bin
- absolute-stretch bin
- sweep-depth/ATR bin

Treatment observations use weight 1. Controls are weighted within common-support strata to the treatment distribution.
No outcome is used to form matching strata.

## Primary inference
- Primary horizon: +5 exact clock minutes.
- Primary effect: weighted treatment-minus-control signed forward return.
- Dependence-aware uncertainty: UTC day-block bootstrap, B=2000, seed=20260817.
- State-rate difference relative to the prior extreme is secondary evidence.

## Scientific boundary
This is a matched observational control study, not randomized causal identification.
`MECHANISM_SUPPORTED` means the frozen conditional association survived the precommitted common-support, balance, day-block and temporal-stability gates. It does NOT prove liquidity-provider behavior, institutional flow, or order-book causality.

## Result placeholder
Verdict after one run: `MECHANISM_NOT_CONFIRMED`.
See `M1_MECH_003_GATES.json`, `M1_MECH_003_MATCHED_EFFECTS.csv`, and `M1_MECH_003_YEARLY_5M.csv`.
