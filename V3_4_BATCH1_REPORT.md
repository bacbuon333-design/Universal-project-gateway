# V3.4 BATCH-1 — H-215 TO H-217 DIRECTIONAL FOLLOW-UP REPORT

## 1. Governance

- Branch: `research/quant-v3.4-h215-directional-followup`
- Artifact-generation parent SHA: `a7479a4db066add480109efe93c12103e3b91302`
- Authoritative result source: `AlphaLab_Antigravity/reports/v3_4/batch1_directional_summary.csv`
- Evaluation window: entry-quarter `2018Q2` through `2026Q2` (33 complete quarters)
- Baseline costs: spread 25.0 pips, commission $7.00/lot, slippage 0.0 pips
- Research disclosure: Long-only direction was motivated by already-observed V3.3/V3.3.1 historical asymmetry. This is exploratory historical follow-up, not validation.

## 2. Authoritative Result Table

| Config | Family | Source symmetric | Trades | Min/Q | Median/Q | Max share | Gini | PF | Expectancy | R4 positive | R4 PF>=1.20 | Top3 +Q | Top5 +Q | Status |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `H-215-C1` | MRLM-L | `H-213-C1` | 3004 | 60 | 94.0 | 4.2% | 0.101 | 1.102 | $+4.69 | 46.7% | 16.7% | 60.9% | 78.7% | **REJECTED** |
| `H-215-C2` | MRLM-L | `H-213-C2` | 2600 | 49 | 81.0 | 3.8% | 0.095 | 1.157 | $+7.74 | 60.0% | 26.7% | 56.3% | 70.0% | **REJECTED** |
| `H-215-C3` | MRLM-L | `H-213-C3` | 2428 | 42 | 73.0 | 4.7% | 0.138 | 1.152 | $+6.93 | 63.3% | 16.7% | 61.3% | 78.6% | **REJECTED** |
| `H-215-C4` | MRLM-L | `H-213-C4` | 2071 | 34 | 62.0 | 4.1% | 0.126 | 1.179 | $+8.74 | 63.3% | 36.7% | 47.0% | 63.2% | **REJECTED** |
| `H-216-C1` | VRA-L | `H-214-C1` | 1966 | 37 | 61.0 | 3.8% | 0.079 | 1.013 | $+0.61 | 46.7% | 3.3% | 36.3% | 55.2% | **REJECTED** |
| `H-216-C2` | VRA-L | `H-214-C2` | 1820 | 36 | 57.0 | 3.6% | 0.078 | 1.025 | $+1.24 | 43.3% | 6.7% | 42.1% | 60.4% | **REJECTED** |
| `H-216-C3` | VRA-L | `H-214-C3` | 1509 | 26 | 46.0 | 4.0% | 0.113 | 1.047 | $+2.16 | 66.7% | 3.3% | 44.5% | 60.3% | **REJECTED** |
| `H-216-C4` | VRA-L | `H-214-C4` | 1409 | 25 | 44.0 | 4.2% | 0.114 | 1.103 | $+4.99 | 80.0% | 10.0% | 43.1% | 58.3% | **REJECTED** |
| `H-217-C1` | MHTP-L | `H-209-C1` | 2231 | 39 | 70.0 | 4.3% | 0.112 | 0.991 | $-0.40 | 40.0% | 6.7% | 44.6% | 62.3% | **REJECTED** |
| `H-217-C2` | MHTP-L | `H-209-C2` | 1993 | 37 | 61.0 | 4.3% | 0.104 | 1.033 | $+1.60 | 46.7% | 10.0% | 51.2% | 73.5% | **REJECTED** |
| `H-217-C3` | MHTP-L | `H-209-C3` | 1582 | 26 | 48.0 | 4.4% | 0.109 | 1.089 | $+5.26 | 50.0% | 20.0% | 50.7% | 71.8% | **REJECTED** |
| `H-217-C4` | MHTP-L | `H-209-C4` | 1422 | 24 | 44.0 | 4.5% | 0.104 | 1.090 | $+5.62 | 53.3% | 26.7% | 44.4% | 65.1% | **REJECTED** |

## 3. Frozen Hard-Gate Matrix

| Config | A1 min/Q | A2 max share | A3 max/median | A4 Gini | B1 Top3 | B2 Top5 | D1 R4+ | D2 R4 PF | E1 PF | E2 Exp | ALL |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `H-215-C1` | PASS | PASS | PASS | PASS | FAIL | FAIL | FAIL | FAIL | FAIL | PASS | FAIL |
| `H-215-C2` | PASS | PASS | PASS | PASS | FAIL | FAIL | FAIL | FAIL | FAIL | PASS | FAIL |
| `H-215-C3` | PASS | PASS | PASS | PASS | FAIL | FAIL | FAIL | FAIL | FAIL | PASS | FAIL |
| `H-215-C4` | PASS | PASS | PASS | PASS | FAIL | FAIL | FAIL | FAIL | FAIL | PASS | FAIL |
| `H-216-C1` | PASS | PASS | PASS | PASS | PASS | PASS | FAIL | FAIL | FAIL | PASS | FAIL |
| `H-216-C2` | PASS | PASS | PASS | PASS | FAIL | FAIL | FAIL | FAIL | FAIL | PASS | FAIL |
| `H-216-C3` | PASS | PASS | PASS | PASS | FAIL | FAIL | FAIL | FAIL | FAIL | PASS | FAIL |
| `H-216-C4` | PASS | PASS | PASS | PASS | FAIL | PASS | PASS | FAIL | FAIL | PASS | FAIL |
| `H-217-C1` | PASS | PASS | PASS | PASS | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL | FAIL |
| `H-217-C2` | PASS | PASS | PASS | PASS | FAIL | FAIL | FAIL | FAIL | FAIL | PASS | FAIL |
| `H-217-C3` | PASS | PASS | PASS | PASS | FAIL | FAIL | FAIL | FAIL | FAIL | PASS | FAIL |
| `H-217-C4` | PASS | PASS | PASS | PASS | FAIL | FAIL | FAIL | FAIL | FAIL | PASS | FAIL |

## 4. Primary Failure Reasons

- `H-215-C1`: Gate E1: PF = 1.102 < 1.25
- `H-215-C2`: Gate E1: PF = 1.157 < 1.25
- `H-215-C3`: Gate E1: PF = 1.152 < 1.25
- `H-215-C4`: Gate E1: PF = 1.179 < 1.25
- `H-216-C1`: Gate E1: PF = 1.013 < 1.25
- `H-216-C2`: Gate E1: PF = 1.025 < 1.25
- `H-216-C3`: Gate E1: PF = 1.047 < 1.25
- `H-216-C4`: Gate E1: PF = 1.103 < 1.25
- `H-217-C1`: Gate E1: PF = 0.991 < 1.25
- `H-217-C2`: Gate E1: PF = 1.033 < 1.25
- `H-217-C3`: Gate E1: PF = 1.089 < 1.25
- `H-217-C4`: Gate E1: PF = 1.090 < 1.25

## 5. Directional Follow-up vs Symmetric V3.3.1 Baseline

This comparison is diagnostic context only. It is not independent evidence because the directional follow-up was motivated by the earlier historical result.

| Config | Source | Long-only PF | Symmetric PF | Long-only Exp | Symmetric Exp | Long-only R4+ | Symmetric R4+ |
|---|---|---:|---:|---:|---:|---:|---:|
| `H-215-C1` | `H-213-C1` | 1.102 | 1.028 | $+4.69 | $+1.41 | 46.7% | 33.3% |
| `H-215-C2` | `H-213-C2` | 1.157 | 1.037 | $+7.74 | $+1.99 | 60.0% | 46.7% |
| `H-215-C3` | `H-213-C3` | 1.152 | 1.059 | $+6.93 | $+2.94 | 63.3% | 46.7% |
| `H-215-C4` | `H-213-C4` | 1.179 | 1.062 | $+8.74 | $+3.36 | 63.3% | 60.0% |
| `H-216-C1` | `H-214-C1` | 1.013 | 0.936 | $+0.61 | $-3.23 | 46.7% | 16.7% |
| `H-216-C2` | `H-214-C2` | 1.025 | 0.954 | $+1.24 | $-2.53 | 43.3% | 26.7% |
| `H-216-C3` | `H-214-C3` | 1.047 | 0.996 | $+2.16 | $-0.20 | 66.7% | 36.7% |
| `H-216-C4` | `H-214-C4` | 1.103 | 1.023 | $+4.99 | $+1.20 | 80.0% | 50.0% |
| `H-217-C1` | `H-209-C1` | 0.991 | 0.951 | $-0.40 | $-2.28 | 40.0% | 23.3% |
| `H-217-C2` | `H-209-C2` | 1.033 | 0.984 | $+1.60 | $-0.81 | 46.7% | 30.0% |
| `H-217-C3` | `H-209-C3` | 1.089 | 1.011 | $+5.26 | $+0.67 | 50.0% | 36.7% |
| `H-217-C4` | `H-209-C4` | 1.090 | 0.988 | $+5.62 | $-0.80 | 53.3% | 40.0% |

## 6. Scientific Decision

> **NO H-215→H-217 CONFIGURATION PASSED ALL FROZEN V3.4 DISTRIBUTED-EDGE GATES.**

No new configuration may be added or tuned automatically. Stop for independent audit.

## 7. Interpretation Limits

- Do not claim a universal Gold Long bias.
- Do not treat V3.3.1 and V3.4 as independent samples.
- Do not infer validation from a historical pass because Long-only direction was chosen after earlier historical diagnostics were observed.
- Do not launch H-218+, parameter optimization, cross-asset tests, or another timeframe before independent audit.
