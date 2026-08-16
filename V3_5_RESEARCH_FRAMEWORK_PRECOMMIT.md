# V3.5 RESEARCH FRAMEWORK PRECOMMIT

## Purpose
V3.5 restores the full temporal-distribution standard before any new H-218+ experiment is executed.

Base research state: V3.4 closed with no survivor. H-215 through H-217 remain rejected and are not to be tuned or reopened.

## Authoritative evaluation window
- Instrument/timeframe: GOLD M30
- Entry-quarter window: 2018Q2 through 2026Q2 inclusive
- 33 complete quarters
- 7 complete calendar years for yearly gates: 2019 through 2025

## Frozen execution contract
- fixed lot 0.10
- spread 25.0 pips
- commission $7.00/lot
- slippage 0.0 pips baseline
- pessimistic ambiguous-bar handling
- one active position at a time
- signal at bar i close, entry at bar i+1 open

## FULL DISTRIBUTED EDGE STANDARD
All hard gates must pass simultaneously.

### A — Opportunity distribution
- A1: minimum trades in every complete quarter >= 5
- A2: max single-quarter trade share <= 5.0%
- A3: max quarterly trades / median quarterly trades <= 3.0
- A4: quarterly trade-count Gini < 0.30

### B — Profit distribution
Denominator is total positive-quarter PnL only.
- B1: Top-3 positive-quarter PnL share <= 40.0%
- B2: Top-5 positive-quarter PnL share <= 60.0%

### D4 — Rolling 4-quarter robustness
- D4_1: >= 70.0% rolling-4Q windows have positive net PnL
- D4_2: >= 65.0% rolling-4Q windows have PF >= 1.20
- Exactly 30 rolling-4Q windows must exist

### D8 — Rolling 8-quarter robustness
- D8_1: >= 75.0% rolling-8Q windows have positive net PnL
- D8_2: >= 70.0% rolling-8Q windows have PF >= 1.20
- Exactly 26 rolling-8Q windows must exist

### Y — Full-calendar-year robustness
Complete calendar years are 2019 through 2025 only.
- Y1: every complete calendar year has >= 20 trades
- Y2: >= 70.0% of complete calendar years have positive net PnL

### E — Economics
- E1: PF >= 1.25
- E2: mean net expectancy > $0

## Anti-gaming rules
- Do not fill sparse quarters deliberately.
- Do not optimize a failed quarter/year.
- Do not add calendar-specific overrides.
- Do not remove a direction after viewing the new batch unless it is precommitted as a later hypothesis.
- Do not change hard gates after execution.
- No random/genetic/Bayesian search.

## Research-budget rule
The first H-218+ batch will be separately precommitted before execution. The evaluator is frozen by this document and must be used unchanged for all configurations in that batch.

## Interpretation
A historical pass is only a HISTORICAL DISTRIBUTED SURVIVOR. It is not validated alpha. True OOS begins only after a later immutable candidate freeze.
