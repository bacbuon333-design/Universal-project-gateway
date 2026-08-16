# V3.10 H226 DELAYED 8H REVERSION STABILITY REPORT

- Artifact-generation parent SHA: `4c0bdb6914dc26516203fb8aa0ebbe47149d395f`
- Scientific parent V3.9 final: `ae3e4a0d0116b07867ead4e09a6466e54faef8d5`
- Frozen V3.9 event SHA-256: `aecdb78d22598a962c29adbd7448755eaf31399d351d5efcbeeddc0c823d920f`
- Canonical dataset: `GOLD_M30_CANONICAL_V2`
- Canonical SHA-256: `c48ca44dcecae9eb1c2590c586e27c4bc5f246215c549d0d0bc1201d95d5ea1d`
- Horizon: `8h` only
- Raw market data read: `False`
- Events reconstructed: `False`
- Trading engine called: `False`
- Strategy executed: `False`

All H226 trading configurations remain **REJECTED**. This chapter audits only the frozen V3.9 8h event-study clue.

## Frozen 8h views

| Cohort | View | N | Mean ATR | Median ATR | Positive % | Gap closed % | Worst5% mean | Median cost ATR | Mean/cost |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| H226-C1 | FULL | 913 | 0.1347 | 0.1264 | 52.4% | 77.7% | -4.9631 | 0.0961 | 1.40 |
| H226-C1 | PRE_2025 | 720 | 0.0832 | 0.1150 | 52.1% | 79.3% | -4.4525 | 0.1091 | 0.76 |
| H226-C1 | RECENT | 193 | 0.3266 | 0.2519 | 53.4% | 71.5% | -5.9961 | 0.0330 | 9.90 |
| H226-C1 | UP_GAP | 521 | 0.0034 | 0.0597 | 51.2% | 74.1% | -5.5429 | 0.0981 | 0.03 |
| H226-C1 | DOWN_GAP | 392 | 0.3091 | 0.2027 | 53.8% | 82.4% | -3.9773 | 0.0949 | 3.26 |
| H226-C1 | LEAVE_2025_2026_OUT | 720 | 0.0832 | 0.1150 | 52.1% | 79.3% | -4.4525 | 0.1091 | 0.76 |
| H226-C2 | FULL | 696 | 0.1551 | 0.1487 | 53.0% | 75.4% | -4.8550 | 0.0990 | 1.57 |
| H226-C2 | PRE_2025 | 557 | 0.1031 | 0.1039 | 52.1% | 76.7% | -4.3051 | 0.1124 | 0.92 |
| H226-C2 | RECENT | 139 | 0.3635 | 0.5289 | 56.8% | 70.5% | -5.8647 | 0.0329 | 11.05 |
| H226-C2 | UP_GAP | 396 | 0.0666 | 0.1311 | 52.3% | 72.0% | -5.3539 | 0.1007 | 0.66 |
| H226-C2 | DOWN_GAP | 300 | 0.2719 | 0.1986 | 54.0% | 80.0% | -4.0077 | 0.0971 | 2.80 |
| H226-C2 | LEAVE_2025_2026_OUT | 557 | 0.1031 | 0.1039 | 52.1% | 76.7% | -4.3051 | 0.1124 | 0.92 |
| H226-C3 | FULL | 851 | 0.1095 | 0.1179 | 51.7% | 76.5% | -5.0465 | 0.0961 | 1.14 |
| H226-C3 | PRE_2025 | 667 | 0.0598 | 0.1121 | 51.6% | 78.3% | -4.4848 | 0.1105 | 0.54 |
| H226-C3 | RECENT | 184 | 0.2896 | 0.1503 | 52.2% | 70.1% | -5.9961 | 0.0332 | 8.73 |
| H226-C3 | UP_GAP | 502 | -0.0153 | 0.0464 | 50.8% | 73.3% | -5.6088 | 0.0982 | -0.16 |
| H226-C3 | DOWN_GAP | 349 | 0.2890 | 0.1945 | 53.0% | 81.1% | -3.9952 | 0.0948 | 3.05 |
| H226-C3 | LEAVE_2025_2026_OUT | 667 | 0.0598 | 0.1121 | 51.6% | 78.3% | -4.4848 | 0.1105 | 0.54 |
| H226-C4 | FULL | 639 | 0.1293 | 0.1264 | 52.1% | 73.9% | -4.9506 | 0.0992 | 1.30 |
| H226-C4 | PRE_2025 | 508 | 0.0860 | 0.0982 | 51.4% | 75.2% | -4.3360 | 0.1154 | 0.75 |
| H226-C4 | RECENT | 131 | 0.2970 | 0.3554 | 55.0% | 68.7% | -5.8647 | 0.0330 | 9.01 |
| H226-C4 | UP_GAP | 378 | 0.0399 | 0.0818 | 51.6% | 70.9% | -5.4213 | 0.1010 | 0.39 |
| H226-C4 | DOWN_GAP | 261 | 0.2587 | 0.1819 | 52.9% | 78.2% | -3.9727 | 0.0964 | 2.68 |
| H226-C4 | LEAVE_2025_2026_OUT | 508 | 0.0860 | 0.0982 | 51.4% | 75.2% | -4.3360 | 0.1154 | 0.75 |

## Clustered bootstrap

| Cohort | Block | Reps | 95% CI | P(mean>0) |
|---|---|---:|---|---:|
| H226-C1 | QUARTER | 5000 | [0.0190, 0.2505] | 99.0% |
| H226-C2 | QUARTER | 5000 | [0.0222, 0.2907] | 99.0% |
| H226-C3 | QUARTER | 5000 | [-0.0111, 0.2313] | 96.4% |
| H226-C4 | QUARTER | 5000 | [-0.0225, 0.2902] | 95.3% |
| H226-C1 | YEAR | 5000 | [0.0503, 0.2028] | 99.9% |
| H226-C2 | YEAR | 5000 | [0.0577, 0.2373] | 99.8% |
| H226-C3 | YEAR | 5000 | [0.0041, 0.1849] | 98.0% |
| H226-C4 | YEAR | 5000 | [0.0046, 0.2391] | 97.9% |

## Complete-year stability

| Cohort | Positive years / 7 | Worst year mean | Best year mean |
|---|---:|---:|---:|
| H226-C1 | 6/7 | -0.1252 | 0.2318 |
| H226-C2 | 6/7 | -0.1102 | 0.3212 |
| H226-C3 | 6/7 | -0.1941 | 0.2471 |
| H226-C4 | 5/7 | -0.1564 | 0.3993 |

## Leave-one-year-out stability

| Cohort | Positive LOO / 7 | Min LOO mean | Max LOO mean |
|---|---:|---:|---:|
| H226-C1 | 7/7 | 0.1190 | 0.1627 |
| H226-C2 | 7/7 | 0.1317 | 0.1833 |
| H226-C3 | 7/7 | 0.0945 | 0.1415 |
| H226-C4 | 7/7 | 0.0955 | 0.1589 |

## Frozen decision-cohort checks

### H226-C1

- Full N: `913`
- Full mean: `+0.134656` ATR
- Full median: `+0.126439` ATR
- Positive complete years: `6/7`
- Quarter-block CI: `[0.018977058443157693, 0.2505150909206563]`
- Year-block CI: `[0.05029737655267601, 0.2028164503094823]`

- PASS `full_mean_positive`
- PASS `full_median_positive`
- PASS `quarter_block_ci_lower_positive`
- PASS `year_block_ci_lower_positive`
- PASS `pre2025_mean_positive`
- PASS `recent_mean_positive`
- PASS `up_gap_mean_positive`
- PASS `down_gap_mean_positive`
- PASS `at_least_5_of_7_positive_years`
- PASS `all_leave_one_year_out_means_positive`
- PASS `leave_2025_2026_out_mean_positive`

### H226-C4

- Full N: `639`
- Full mean: `+0.129266` ATR
- Full median: `+0.126439` ATR
- Positive complete years: `5/7`
- Quarter-block CI: `[-0.022529033526435628, 0.29016919557102716]`
- Year-block CI: `[0.00464084359278935, 0.23910733566678072]`

- PASS `full_mean_positive`
- PASS `full_median_positive`
- FAIL `quarter_block_ci_lower_positive`
- PASS `year_block_ci_lower_positive`
- PASS `pre2025_mean_positive`
- PASS `recent_mean_positive`
- PASS `up_gap_mean_positive`
- PASS `down_gap_mean_positive`
- PASS `at_least_5_of_7_positive_years`
- PASS `all_leave_one_year_out_means_positive`
- PASS `leave_2025_2026_out_mean_positive`

## Frozen scientific conclusion

> **H226 DELAYED 8H REVERSION REGIME / DIRECTION DEPENDENT — STRATEGY DESIGN NOT AUTHORIZED**

Regardless of the mechanism label:

- all H226 trading strategies remain **REJECTED**;
- no strategy design is authorized by V3.10;
- no direction/subperiod split may be converted into a filter inside this chapter;
- no new horizon or threshold is introduced.

## Artifact dimensions

- View summary rows: `24`
- Year rows: `28`
- Quarter rows: `132`
- Leave-one-year-out rows: `28`
- Bootstrap rows: `8`

## Stop rule

STOP after this report. No H227, no delayed-reversion strategy, no H226 tuning, no new asset/timeframe and no horizon extension are authorized.
