# V3.2 RESEARCH STATE & GOVERNANCE RECORD

## 1. REPOSITORY GOVERNANCE & BRANCH TOPOLOGY
- **Execution Mode**: Single continuous research agent.
- **Base Commit**: `ee40ec8f22d95700e1c880acbf9c3575a765a0c9` (`research/quant-v3.1-audit-distribution`).
- **Active Branch**: `research/quant-v3.2-distributed-edge`.
- **Benchmark Lane A**: `CAND-001` (Status: `REJECTED UNDER V3.1/V3.2 GATES`).
- **Benchmark Lane B**: `CAND-002` (Status: `REJECTED UNDER V3.1/V3.2 GATES`).
- **Benchmark Lane C**: `H-200` to `H-208` (Status: `ALL REJECTED`).

## 2. ENGINE REPAIR & CROSS-ASSET STATUS
- Native `InstrumentSpec` implemented and verified via 5/5 unit tests in `test_engine_asset_aware.py`.
- H-103 Retest: Verified that Volatility Squeeze + Macro Trend successfully transfers to **Gold ($PF = 1.837$)** and **USDJPY ($PF = 1.622$)**, but fails on EURUSD, GBPUSD, and BTCUSD.

## 3. FINAL V3.2 RESEARCH VERDICT
- `H-204` to `H-208`: All rejected due to failing either Gate 12A ($\text{Min trades/Q} \ge 5$), Gate 15 (Profit concentration $\le 40\%$), or Gate 16 (Rolling 4Q consistency $\ge 65\%$).
- **Overall Mandate Outcome**: `NO HISTORICAL CANDIDATE PASSED V3.2 DISTRIBUTED EDGE STANDARD`.
