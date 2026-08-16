# V3.5 BATCH-1 — H-218 TO H-220 NEW-MECHANISM REPORT

## Governance

- Branch: `research/quant-v3.5-h218-new-mechanisms`
- Artifact-generation parent SHA: `3eb5fd59575508b78b94be9146a2b82460a9b307`
- Authoritative source: `AlphaLab_Antigravity/reports/v3_5/batch1_summary.csv`
- Evaluation: entry-quarter `2018Q2` through `2026Q2`
- Full rolling diagnostics: 30 rolling-4Q windows and 26 rolling-8Q windows
- Full-year hard-gate window: 2019 through 2025
- Costs: spread 25 pips, commission $7/lot, slippage 0 pips baseline

## Results

| Config | Family | Trades | Min/Q | Gini | PF | Exp | R4+ | R4 PF | R8+ | R8 PF | Years+ | Top3 +Q | Top5 +Q | Status |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `H-218-C1` | PDBC | 2365 | 60 | 0.046 | 0.951 | $-2.49 | 26.7% | 0.0% | 19.2% | 0.0% | 28.6% | 54.1% | 73.3% | **REJECTED** |
| `H-218-C2` | PDBC | 2266 | 56 | 0.049 | 0.993 | $-0.37 | 30.0% | 6.7% | 23.1% | 0.0% | 28.6% | 67.0% | 78.4% | **REJECTED** |
| `H-218-C3` | PDBC | 1968 | 48 | 0.055 | 1.007 | $+0.43 | 40.0% | 6.7% | 30.8% | 0.0% | 28.6% | 53.3% | 70.9% | **REJECTED** |
| `H-218-C4` | PDBC | 1851 | 46 | 0.052 | 0.989 | $-0.77 | 50.0% | 3.3% | 38.5% | 0.0% | 28.6% | 52.4% | 68.0% | **REJECTED** |
| `H-219-C1` | NIC | 5216 | 131 | 0.046 | 1.025 | $+1.18 | 20.0% | 3.3% | 19.2% | 0.0% | 14.3% | 83.2% | 89.1% | **REJECTED** |
| `H-219-C2` | NIC | 4549 | 105 | 0.042 | 0.966 | $-1.64 | 6.7% | 0.0% | 7.7% | 0.0% | 0.0% | 74.5% | 88.5% | **REJECTED** |
| `H-219-C3` | NIC | 4591 | 101 | 0.045 | 0.951 | $-2.49 | 23.3% | 0.0% | 3.8% | 0.0% | 14.3% | 79.7% | 90.6% | **REJECTED** |
| `H-219-C4` | NIC | 4422 | 110 | 0.047 | 0.950 | $-2.58 | 13.3% | 0.0% | 0.0% | 0.0% | 14.3% | 57.0% | 79.6% | **REJECTED** |
| `H-220-C1` | LMDC | 1339 | 31 | 0.068 | 1.126 | $+4.81 | 16.7% | 16.7% | 19.2% | 15.4% | 14.3% | 79.5% | 96.4% | **REJECTED** |
| `H-220-C2` | LMDC | 1326 | 30 | 0.070 | 1.167 | $+6.78 | 16.7% | 16.7% | 19.2% | 11.5% | 14.3% | 76.7% | 92.2% | **REJECTED** |
| `H-220-C3` | LMDC | 1000 | 17 | 0.101 | 1.244 | $+9.17 | 36.7% | 16.7% | 34.6% | 15.4% | 28.6% | 74.4% | 89.6% | **REJECTED** |
| `H-220-C4` | LMDC | 992 | 17 | 0.102 | 1.285 | $+11.37 | 50.0% | 16.7% | 53.8% | 11.5% | 42.9% | 70.1% | 86.5% | **REJECTED** |

## Full 14-Gate Matrix

| Config | A1 | A2 | A3 | A4 | B1 | B2 | D4.1 | D4.2 | D8.1 | D8.2 | Y1 | Y2 | E1 | E2 | ALL |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `H-218-C1` | PASS | PASS | PASS | PASS | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL | PASS | FAIL | FAIL | FAIL | FAIL |
| `H-218-C2` | PASS | PASS | PASS | PASS | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL | PASS | FAIL | FAIL | FAIL | FAIL |
| `H-218-C3` | PASS | PASS | PASS | PASS | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL | PASS | FAIL | FAIL | PASS | FAIL |
| `H-218-C4` | PASS | PASS | PASS | PASS | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL | PASS | FAIL | FAIL | FAIL | FAIL |
| `H-219-C1` | PASS | PASS | PASS | PASS | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL | PASS | FAIL | FAIL | PASS | FAIL |
| `H-219-C2` | PASS | PASS | PASS | PASS | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL | PASS | FAIL | FAIL | FAIL | FAIL |
| `H-219-C3` | PASS | PASS | PASS | PASS | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL | PASS | FAIL | FAIL | FAIL | FAIL |
| `H-219-C4` | PASS | PASS | PASS | PASS | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL | PASS | FAIL | FAIL | FAIL | FAIL |
| `H-220-C1` | PASS | PASS | PASS | PASS | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL | PASS | FAIL | FAIL | PASS | FAIL |
| `H-220-C2` | PASS | PASS | PASS | PASS | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL | PASS | FAIL | FAIL | PASS | FAIL |
| `H-220-C3` | PASS | PASS | PASS | PASS | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL | PASS | FAIL | FAIL | PASS | FAIL |
| `H-220-C4` | PASS | PASS | PASS | PASS | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL | PASS | FAIL | PASS | PASS | FAIL |

## Primary Failure Reasons

- `H-218-C1`: Gate E1: PF 0.951 < 1.25
- `H-218-C2`: Gate E1: PF 0.993 < 1.25
- `H-218-C3`: Gate E1: PF 1.007 < 1.25
- `H-218-C4`: Gate E1: PF 0.989 < 1.25
- `H-219-C1`: Gate E1: PF 1.025 < 1.25
- `H-219-C2`: Gate E1: PF 0.966 < 1.25
- `H-219-C3`: Gate E1: PF 0.951 < 1.25
- `H-219-C4`: Gate E1: PF 0.950 < 1.25
- `H-220-C1`: Gate E1: PF 1.126 < 1.25
- `H-220-C2`: Gate E1: PF 1.167 < 1.25
- `H-220-C3`: Gate E1: PF 1.244 < 1.25
- `H-220-C4`: Gate D4_1: R4 positive 50.0% < 70%

## Scientific Decision

> **NO H-218→H-220 CONFIGURATION PASSED ALL FROZEN V3.5 DISTRIBUTED-EDGE GATES.**

## Interpretation Limits

- Do not optimize a near-miss after reading this report.
- Do not create a directional variant inside this batch after seeing results.
- Rolling windows overlap and are diagnostics, not independent samples.
- A historical survivor is not true OOS evidence.
