# V5-A Independent Alpha RR1 Discovery — Frozen Result Report

## Provenance and frozen contracts

- Scientific parent commit: `5a1a2f8c28f857789943295f6a59df2f1037e72b`
- Frozen execution HEAD recorded by runner: `e94f03865114a34657ed744876d052b5859e1153`
- Canonical dataset SHA-256: `c48ca44dcecae9eb1c2590c586e27c4bc5f246215c549d0d0bc1201d95d5ea1d`
- Execution contract: `CANONICAL_V2_GAP_SAFE_V3_7_3`
- Evaluator contract: `V3_8_WRAPPER_OVER_V3_5_FULL_14_GATES`
- Families/configurations: 4 / 4
- Common SL/TP: 1.5 ATR / 1.5 ATR (1:1)
- Dynamic grid / automatic Batch 2 / post-result tuning: false / false / false

## Configuration outcomes

| ID | Family | Trades | PF | Expectancy USD | Net PnL USD | Min/Q | Min/Year | R4 +% | R4 PF120% | R8 +% | R8 PF120% | Prof Years % | Gates | Status |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| H401-C1 | H401_LSR | 6429 | 0.842 | -5.925 | -38090.939 | 165 | 724 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 5/14 | REJECTED |
| H402-C1 | H402_IBB | 3661 | 0.936 | -2.455 | -8989.048 | 93 | 412 | 16.7 | 0.0 | 19.2 | 0.0 | 14.3 | 5/14 | REJECTED |
| H403-C1 | H403_BER | 5700 | 0.874 | -4.602 | -26233.743 | 146 | 622 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 5/14 | REJECTED |
| H404-C1 | H404_CPB | 7196 | 0.899 | -3.745 | -26947.815 | 193 | 821 | 10.0 | 0.0 | 3.8 | 0.0 | 14.3 | 5/14 | REJECTED |

## Gate-level audit

### H401-C1 — REJECTED

Family: `H401_LSR`; params: `{'LOOKBACK': 24}`

Primary failure: `Gate E1: PF 0.842 < 1.25`

- gate_A1: PASS
- gate_A2: PASS
- gate_A3: PASS
- gate_A4: PASS
- gate_B1: FAIL
- gate_B2: FAIL
- gate_D4_1: FAIL
- gate_D4_2: FAIL
- gate_D8_1: FAIL
- gate_D8_2: FAIL
- gate_Y1: PASS
- gate_Y2: FAIL
- gate_E1: FAIL
- gate_E2: FAIL

### H402-C1 — REJECTED

Family: `H402_IBB`; params: `{}`

Primary failure: `Gate E1: PF 0.936 < 1.25`

- gate_A1: PASS
- gate_A2: PASS
- gate_A3: PASS
- gate_A4: PASS
- gate_B1: FAIL
- gate_B2: FAIL
- gate_D4_1: FAIL
- gate_D4_2: FAIL
- gate_D8_1: FAIL
- gate_D8_2: FAIL
- gate_Y1: PASS
- gate_Y2: FAIL
- gate_E1: FAIL
- gate_E2: FAIL

### H403-C1 — REJECTED

Family: `H403_BER`; params: `{'MIN_BODY_ATR': 0.5}`

Primary failure: `Gate E1: PF 0.874 < 1.25`

- gate_A1: PASS
- gate_A2: PASS
- gate_A3: PASS
- gate_A4: PASS
- gate_B1: FAIL
- gate_B2: FAIL
- gate_D4_1: FAIL
- gate_D4_2: FAIL
- gate_D8_1: FAIL
- gate_D8_2: FAIL
- gate_Y1: PASS
- gate_Y2: FAIL
- gate_E1: FAIL
- gate_E2: FAIL

### H404-C1 — REJECTED

Family: `H404_CPB`; params: `{'PIVOT_FLANK': 2}`

Primary failure: `Gate E1: PF 0.899 < 1.25`

- gate_A1: PASS
- gate_A2: PASS
- gate_A3: PASS
- gate_A4: PASS
- gate_B1: FAIL
- gate_B2: FAIL
- gate_D4_1: FAIL
- gate_D4_2: FAIL
- gate_D8_1: FAIL
- gate_D8_2: FAIL
- gate_Y1: PASS
- gate_Y2: FAIL
- gate_E1: FAIL
- gate_E2: FAIL

## Frozen conclusion

**NO V5-A CONFIGURATION PASSED ALL FROZEN DISTRIBUTED-EDGE GATES**

Survivors: `[]`

## Governance assertions

- FRESH OOS ACCESSED: false
- CLOSED RESEARCH MODIFIED: false
- CLOSED RESEARCH DESCENDANT CREATED: false
- H226 REUSED: false
- V4 H301-H304 REUSED: false
- STRATEGY DESIGN AUTHORIZED FOR DEPLOYMENT: false
- PAPER TRADING AUTHORIZED: false
- LIVE TRADING AUTHORIZED: false

A failed configuration is closed for this chapter and may not be tuned here. A historical survivor would require separately precommitted independent validation and remains unauthorized for deployment.
