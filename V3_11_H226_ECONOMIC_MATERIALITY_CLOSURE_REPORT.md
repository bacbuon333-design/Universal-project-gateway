# V3.11 H226 ECONOMIC-MATERIALITY & ASYMMETRY CLOSURE REPORT

- Artifact-generation parent SHA: `3962a9a7db035e02389eb14a2fdf4987298fce33`
- Scientific parent V3.10 final: `b387e25bdf6fd814c3034f3688af50e976f5cc59`
- Frozen V3.9 event SHA-256: `aecdb78d22598a962c29adbd7448755eaf31399d351d5efcbeeddc0c823d920f`
- Canonical dataset: `GOLD_M30_CANONICAL_V2`
- Canonical SHA-256: `c48ca44dcecae9eb1c2590c586e27c4bc5f246215c549d0d0bc1201d95d5ea1d`
- Horizon: `8h` only
- Round-trip price-equivalent cost hurdle: `$0.32/oz`
- Raw market data read: `False`
- Events reconstructed: `False`
- Trading engine called: `False`
- Strategy executed: `False`

All H226 trading strategies remain **REJECTED**. V3.11 is a final same-sample economic-scale diagnostic only.

## Frozen economic views

| Cohort | View | N | Raw mean ATR | Excess mean ATR | Excess median ATR | Excess>0 | Median cost ATR | Worst5% excess |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| H226-C1 | FULL | 913 | +0.1347 | +0.0274 | +0.0274 | 50.6% | 0.0961 | -5.0658 |
| H226-C1 | PRE_2025 | 720 | +0.0832 | -0.0423 | -0.0042 | 49.9% | 0.1091 | -4.5980 |
| H226-C1 | RECENT | 193 | +0.3266 | +0.2876 | +0.1894 | 53.4% | 0.0330 | -6.0486 |
| H226-C1 | UP_GAP | 521 | +0.0034 | -0.1076 | -0.0063 | 49.5% | 0.0981 | -5.6463 |
| H226-C1 | DOWN_GAP | 392 | +0.3091 | +0.2070 | +0.0969 | 52.0% | 0.0949 | -4.0956 |
| H226-C2 | FULL | 696 | +0.1551 | +0.0443 | +0.0534 | 51.0% | 0.0990 | -4.9579 |
| H226-C2 | PRE_2025 | 557 | +0.1031 | -0.0257 | -0.0063 | 49.6% | 0.1124 | -4.4557 |
| H226-C2 | RECENT | 139 | +0.3635 | +0.3248 | +0.5063 | 56.8% | 0.0329 | -5.9190 |
| H226-C2 | UP_GAP | 396 | +0.0666 | -0.0492 | +0.0143 | 50.3% | 0.1007 | -5.4642 |
| H226-C2 | DOWN_GAP | 300 | +0.2719 | +0.1677 | +0.0961 | 52.0% | 0.0971 | -4.1300 |
| H226-C3 | FULL | 851 | +0.1095 | +0.0018 | +0.0031 | 50.1% | 0.0961 | -5.1467 |
| H226-C3 | PRE_2025 | 667 | +0.0598 | -0.0667 | -0.0079 | 49.5% | 0.1105 | -4.6325 |
| H226-C3 | RECENT | 184 | +0.2896 | +0.2503 | +0.0816 | 52.2% | 0.0332 | -6.0486 |
| H226-C3 | UP_GAP | 502 | -0.0153 | -0.1268 | -0.0670 | 49.0% | 0.0982 | -5.7126 |
| H226-C3 | DOWN_GAP | 349 | +0.2890 | +0.1869 | +0.0965 | 51.6% | 0.0948 | -4.1130 |
| H226-C4 | FULL | 639 | +0.1293 | +0.0178 | +0.0055 | 50.2% | 0.0992 | -5.0513 |
| H226-C4 | PRE_2025 | 508 | +0.0860 | -0.0442 | -0.0172 | 49.0% | 0.1154 | -4.4899 |
| H226-C4 | RECENT | 131 | +0.2970 | +0.2580 | +0.3114 | 55.0% | 0.0330 | -5.9190 |
| H226-C4 | UP_GAP | 378 | +0.0399 | -0.0766 | -0.0054 | 49.5% | 0.1010 | -5.5276 |
| H226-C4 | DOWN_GAP | 261 | +0.2587 | +0.1544 | +0.0957 | 51.3% | 0.0964 | -4.0963 |

## Cluster bootstrap on mean excess-reversion ATR

| Cohort | Block | Reps | 95% CI | P(mean excess>0) |
|---|---|---:|---|---:|
| H226-C1 | QUARTER | 5000 | [-0.0942, +0.1537] | 66.6% |
| H226-C2 | QUARTER | 5000 | [-0.0872, +0.1943] | 72.5% |
| H226-C3 | QUARTER | 5000 | [-0.1242, +0.1288] | 52.1% |
| H226-C4 | QUARTER | 5000 | [-0.1317, +0.1832] | 59.1% |
| H226-C1 | YEAR | 5000 | [-0.0486, +0.1111] | 81.5% |
| H226-C2 | YEAR | 5000 | [-0.0475, +0.1461] | 84.9% |
| H226-C3 | YEAR | 5000 | [-0.0926, +0.0861] | 56.0% |
| H226-C4 | YEAR | 5000 | [-0.0973, +0.1385] | 60.3% |

## Decision-cohort economic checks

### H226-C1

- FULL N: `913`
- FULL raw mean: `+0.134656` ATR
- FULL mean excess: `+0.027443` ATR
- FULL median excess: `+0.027361` ATR
- PRE_2025 mean excess: `-0.042295` ATR
- RECENT mean excess: `+0.287604` ATR
- UP_GAP mean excess: `-0.107641` ATR
- DOWN_GAP mean excess: `+0.206980` ATR
- Positive complete years: `6/7`
- Minimum leave-one-year-out mean excess: `+0.002222` ATR
- Quarter-block CI: `[-0.094224, +0.153746]`
- Year-block CI: `[-0.048625, +0.111079]`

- PASS `full_mean_excess_positive`
- PASS `full_median_excess_positive`
- FAIL `quarter_block_ci_lower_positive`
- FAIL `year_block_ci_lower_positive`
- FAIL `pre2025_mean_excess_positive`
- PASS `recent_mean_excess_positive`
- FAIL `up_gap_mean_excess_positive`
- PASS `down_gap_mean_excess_positive`
- PASS `at_least_5_of_7_positive_years`
- PASS `all_leave_one_year_out_means_positive`

### H226-C4

- FULL N: `639`
- FULL raw mean: `+0.129266` ATR
- FULL mean excess: `+0.017760` ATR
- FULL median excess: `+0.005512` ATR
- PRE_2025 mean excess: `-0.044195` ATR
- RECENT mean excess: `+0.258012` ATR
- UP_GAP mean excess: `-0.076573` ATR
- DOWN_GAP mean excess: `+0.154380` ATR
- Positive complete years: `4/7`
- Minimum leave-one-year-out mean excess: `-0.017194` ATR
- Quarter-block CI: `[-0.131729, +0.183164]`
- Year-block CI: `[-0.097255, +0.138522]`

- PASS `full_mean_excess_positive`
- PASS `full_median_excess_positive`
- FAIL `quarter_block_ci_lower_positive`
- FAIL `year_block_ci_lower_positive`
- FAIL `pre2025_mean_excess_positive`
- PASS `recent_mean_excess_positive`
- FAIL `up_gap_mean_excess_positive`
- PASS `down_gap_mean_excess_positive`
- FAIL `at_least_5_of_7_positive_years`
- FAIL `all_leave_one_year_out_means_positive`

## Frozen scientific conclusion

> **H226 DELAYED 8H REVERSION ECONOMICALLY ASYMMETRIC / REGIME-CONCENTRATED — H226 STRATEGY CHAPTER CLOSED; FRESH OOS REQUIRED**

Regardless of the label:

- all H226 trading strategies remain **REJECTED**;
- same-sample H226 research is now **CLOSED**;
- strategy design is **not authorized**;
- no UP/DOWN or PRE/RECENT split may be converted into a filter on this sample;
- any future H226-inspired strategy requires fresh out-of-sample data or a separately justified independent dataset.

## Stop rule

STOP after this report. No H226 descendant, threshold tuning, direction filter, new horizon, SL/TP/RR change, asset/timeframe switch, or same-sample strategy design is authorized.
