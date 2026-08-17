# ALAB-M1-MECH-005 — Compensation Invariance & Falsification Audit

## Scope
Development-only attempt to falsify MECH-004 on frozen GOLD M1 2018–2025.
No strategy, PnL backtest, paper/live trading, broker execution, 2015–2017 access, or 2026 access.

## Dataset
- SHA256: `10d6df33c749315824bb9552b139439e6bbfcbac1bed54f272a62696c2f4965e`
- Rows: `2,827,419`
- Range: `2018-01-02 09:05:00+00:00` to `2025-12-31 19:59:00+00:00`
- Sealed holdout: `2015–2017 NOT ACCESSED`

## Invariance battery
Four pre-registered coordinates: ATR_t, ATR_(t-1), prior-price bps, and excursion-normalized ratios.
EXCURSION_RATIO uses only breaches with excursion >=0.10 ATR_t to prevent near-zero denominator blow-up.
The MECH-004 ATR_t rho_5m must reproduce within 1e-10 before any invariance claim is allowed.

## Placebo battery
1. Within UTC-date x side cyclic reassignment of R_post, rebuilding placebo total as R_in + shuffled R_post.
2. Within UTC-date x side balanced sign randomization of R_post, rebuilding placebo total as R_in + signed-placebo R_post.
Both have a pre-registered null rho=1 because the event's R_in is retained while the event-specific future increment linkage is destroyed.

## Interpretation boundary
Survival means the attenuation relationship is coordinate-robust and does not survive the two frozen placebo destructions.
It still does not prove a physical law, fixed budget, economic microstructure cause, or tradable edge.

## Verdict
`COMPENSATION_FALSIFIED_OR_NOT_INVARIANT`
