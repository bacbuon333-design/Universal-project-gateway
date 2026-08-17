# V4 Independent Alpha Discovery — Frozen Result Report

## Provenance and frozen contracts

- Frozen execution HEAD recorded by runner: `4576c3477385a6f04acf7c99bc7034cadade235d`
- Canonical dataset SHA-256: `c48ca44dcecae9eb1c2590c586e27c4bc5f246215c549d0d0bc1201d95d5ea1d`
- Execution contract: `CANONICAL_V2_GAP_SAFE_V3_7_3`
- Evaluator contract: `V3_8_WRAPPER_OVER_V3_5_FULL_14_GATES`
- Families/configurations: 4 / 12
- Automatic Batch 2 authorized: false

## Configuration outcomes

| ID | Family | Trades | PF | Expectancy USD | Net PnL USD | Min/Q | Min/Year | R4 +% | R4 PF120% | R8 +% | R8 PF120% | Prof Years % | Gates | Status |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| H301-C1 | H301_VCB | 1803 | 1.042 | 1.791 | 3229.116 | 40 | 191 | 16.7 | 10.0 | 15.4 | 3.8 | 14.3 | 6/14 | REJECTED |
| H301-C2 | H301_VCB | 920 | 0.920 | -4.069 | -3743.053 | 20 | 104 | 40.0 | 13.3 | 38.5 | 7.7 | 42.9 | 5/14 | REJECTED |
| H301-C3 | H301_VCB | 583 | 1.084 | 4.495 | 2620.836 | 12 | 63 | 73.3 | 43.3 | 88.5 | 11.5 | 85.7 | 9/14 | REJECTED |
| H302-C1 | H302_USRB | 123 | 1.425 | 19.635 | 2415.149 | 0 | 12 | 40.0 | 16.7 | 23.1 | 7.7 | 57.1 | 2/14 | REJECTED |
| H302-C2 | H302_USRB | 122 | 1.441 | 20.356 | 2483.386 | 0 | 11 | 40.0 | 16.7 | 26.9 | 7.7 | 57.1 | 2/14 | REJECTED |
| H302-C3 | H302_USRB | 120 | 1.428 | 19.656 | 2358.679 | 0 | 11 | 40.0 | 23.3 | 34.6 | 11.5 | 57.1 | 2/14 | REJECTED |
| H303-C1 | H303_TPER | 2509 | 0.899 | -4.818 | -12087.190 | 63 | 292 | 13.3 | 0.0 | 11.5 | 0.0 | 14.3 | 5/14 | REJECTED |
| H303-C2 | H303_TPER | 2221 | 0.913 | -4.128 | -9168.616 | 54 | 258 | 20.0 | 0.0 | 15.4 | 0.0 | 14.3 | 5/14 | REJECTED |
| H303-C3 | H303_TPER | 1971 | 0.940 | -2.808 | -5534.649 | 46 | 230 | 20.0 | 0.0 | 19.2 | 0.0 | 14.3 | 5/14 | REJECTED |
| H304-C1 | H304_EMR | 3963 | 0.970 | -1.524 | -6040.600 | 105 | 450 | 16.7 | 0.0 | 11.5 | 0.0 | 14.3 | 5/14 | REJECTED |
| H304-C2 | H304_EMR | 3127 | 0.895 | -5.713 | -17865.240 | 81 | 361 | 20.0 | 0.0 | 7.7 | 0.0 | 0.0 | 5/14 | REJECTED |
| H304-C3 | H304_EMR | 1975 | 0.936 | -3.468 | -6850.087 | 50 | 233 | 36.7 | 10.0 | 46.2 | 3.8 | 42.9 | 5/14 | REJECTED |

## Gate-level audit

### H301-C1 — REJECTED

Primary failure: `Gate E1: PF 1.042 < 1.25`

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
- gate_E2: PASS

### H301-C2 — REJECTED

Primary failure: `Gate E1: PF 0.920 < 1.25`

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

### H301-C3 — REJECTED

Primary failure: `Gate E1: PF 1.084 < 1.25`

- gate_A1: PASS
- gate_A2: PASS
- gate_A3: PASS
- gate_A4: PASS
- gate_B1: FAIL
- gate_B2: FAIL
- gate_D4_1: PASS
- gate_D4_2: FAIL
- gate_D8_1: PASS
- gate_D8_2: FAIL
- gate_Y1: PASS
- gate_Y2: PASS
- gate_E1: FAIL
- gate_E2: PASS

### H302-C1 — REJECTED

Primary failure: `Gate A1: min trades/Q 0 < 5`

- gate_A1: FAIL
- gate_A2: FAIL
- gate_A3: FAIL
- gate_A4: FAIL
- gate_B1: FAIL
- gate_B2: FAIL
- gate_D4_1: FAIL
- gate_D4_2: FAIL
- gate_D8_1: FAIL
- gate_D8_2: FAIL
- gate_Y1: FAIL
- gate_Y2: FAIL
- gate_E1: PASS
- gate_E2: PASS

### H302-C2 — REJECTED

Primary failure: `Gate A1: min trades/Q 0 < 5`

- gate_A1: FAIL
- gate_A2: FAIL
- gate_A3: FAIL
- gate_A4: FAIL
- gate_B1: FAIL
- gate_B2: FAIL
- gate_D4_1: FAIL
- gate_D4_2: FAIL
- gate_D8_1: FAIL
- gate_D8_2: FAIL
- gate_Y1: FAIL
- gate_Y2: FAIL
- gate_E1: PASS
- gate_E2: PASS

### H302-C3 — REJECTED

Primary failure: `Gate A1: min trades/Q 0 < 5`

- gate_A1: FAIL
- gate_A2: FAIL
- gate_A3: FAIL
- gate_A4: FAIL
- gate_B1: FAIL
- gate_B2: FAIL
- gate_D4_1: FAIL
- gate_D4_2: FAIL
- gate_D8_1: FAIL
- gate_D8_2: FAIL
- gate_Y1: FAIL
- gate_Y2: FAIL
- gate_E1: PASS
- gate_E2: PASS

### H303-C1 — REJECTED

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

### H303-C2 — REJECTED

Primary failure: `Gate E1: PF 0.913 < 1.25`

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

### H303-C3 — REJECTED

Primary failure: `Gate E1: PF 0.940 < 1.25`

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

### H304-C1 — REJECTED

Primary failure: `Gate E1: PF 0.970 < 1.25`

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

### H304-C2 — REJECTED

Primary failure: `Gate E1: PF 0.895 < 1.25`

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

### H304-C3 — REJECTED

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

## Frozen conclusion

**NO V4 CONFIGURATION PASSED ALL FROZEN DISTRIBUTED-EDGE GATES**

Survivors: `[]`

## Governance assertions

- FRESH OOS ACCESSED: false
- CLOSED RESEARCH MODIFIED: false
- CLOSED RESEARCH DESCENDANT CREATED: false
- STRATEGY DESIGN AUTHORIZED FOR DEPLOYMENT: false
- LIVE TRADING AUTHORIZED: false

No failed configuration is authorized for tuning in this chapter. Any historical candidate requires a separately precommitted independent validation chapter.
