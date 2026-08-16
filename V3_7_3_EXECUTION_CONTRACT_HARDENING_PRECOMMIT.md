# V3.7.3 CANONICAL EXECUTION CONTRACT HARDENING PRECOMMIT

## PURPOSE

V3.7.3 is an execution-engine infrastructure audit only.

It does not create a market hypothesis, H-221, a strategy candidate, an event study, or a performance claim.

Scientific parent:

`dab93ae7c918383038ee1a9a5fb7065788f09aee`

Canonical authority:

- dataset: `GOLD_M30_CANONICAL_V2`;
- SHA-256: `c48ca44dcecae9eb1c2590c586e27c4bc5f246215c549d0d0bc1201d95d5ea1d`;
- engine interface status: `CANONICAL_V2_ENGINE_COMPATIBILITY_PASS`.

## DISCOVERED EXECUTION DEFECT

The legacy `DeepQuantEngine.run_strategy()` manages an existing BUY stop with:

`low <= stop -> exit at stop`

and an existing SELL stop with:

`high + spread >= stop -> exit at stop`.

If a new bar opens beyond the stop in the adverse direction, this fills at the old stop price rather than the worse executable gap-open price.

That is optimistic gap-stop handling.

The defect is discovered before any new canonical strategy research.

## FROZEN HARDENED CONTRACT

New canonical research must use a separate execution adapter. The legacy engine remains unchanged for historical reproducibility.

Frozen rules:

1. Signal is observed at close of bar `i`.
2. Entry occurs at open of bar `i+1`.
3. Entry-bar management begins on bar `i+1` after entry.
4. One active position maximum.
5. BUY entry price = next Bid open + spread + slippage.
6. SELL entry price = next Bid open - slippage.
7. BUY normal stop hit fills at stop - slippage.
8. If BUY bar Bid open is already below the stop, fill at Bid open - slippage, not at the better stop price.
9. SELL normal stop hit uses Ask-side logic.
10. If SELL bar Ask open is already above the stop, fill at Ask open + slippage, not at the better stop price.
11. Favorable gaps beyond TP do not receive positive price improvement; TP fills remain capped at the frozen target price. This is deliberately conservative.
12. If SL and TP are both touched in one bar, SL wins under pessimistic ambiguous-bar handling.
13. Spread, commission, slippage, lot size, and instrument economics are otherwise unchanged.
14. No live or historical market strategy may be executed in V3.7.3. Synthetic unit fixtures only.

## END-OF-SAMPLE POLICY

V3.7.3 does not introduce discretionary forced liquidation at the final dataset bar.

Future research must instead prove that the canonical dataset extends beyond the frozen evaluation end by at least the strategy maximum holding horizon.

For the current program baseline:

- evaluation end remains `2026Q2` unless a future precommit changes it;
- canonical data extends into August 2026;
- future research runners must assert sufficient post-evaluation buffer before execution.

## REQUIRED TESTS

Synthetic tests must cover at minimum:

- close signal -> next-open entry;
- entry-bar SL handling;
- entry-bar TP handling;
- pessimistic ambiguous SL-first behavior;
- BUY adverse stop gap fills at worse open;
- SELL adverse stop gap fills at worse Ask open;
- normal non-gap stop behavior remains stop-price based;
- favorable TP gap does not receive price improvement;
- spread symmetry remains unchanged;
- commission remains unchanged;
- one-position rule remains unchanged;
- canonical V2 authorization remains required;
- no real canonical market strategy is executed by the audit;
- post-evaluation buffer check passes for 2026Q2 with max holding 120 M30 bars.

## ALLOWED FINAL STATUSES

`CANONICAL_EXECUTION_CONTRACT_PASS`

or

`CANONICAL_EXECUTION_CONTRACT_BLOCKED`

## STOP RULE

Even if PASS:

- do not create H-221;
- do not rerun LMDC;
- do not optimize parameters;
- do not start V3.8 automatically;
- return the execution-contract evidence for independent audit first.
