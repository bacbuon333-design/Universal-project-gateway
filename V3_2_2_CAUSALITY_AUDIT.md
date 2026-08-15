# V3.2.2 CAUSALITY AUDIT & POSITION CONCURRENCY RECORD

---

## 1. SIGNAL & EXECUTION CAUSALITY VERIFICATION

Every signal generation rule was audited for strict causal integrity:
1. **Indicator Availability**: All indicators (BB, Keltner, ATR, EMA, Donchian) are calculated strictly on bar $[0 \dots i]$.
2. **Breakout & Squeeze Checks**:
   - `was_sqz` is determined using `.shift(1)` from bar $i$, verifying that squeeze was active on or before bar $i$.
   - Donchian channels and multi-bar highs/lows use `.shift(1)` to ensure breakout threshold is computed strictly from completed past bars.
3. **Execution Timestamp**:
   - Signal generated at close of bar $i$.
   - Entry order executed at open of bar $i+1$ with entry price:
     * BUY: $P_{\text{open}}[i+1] + \text{spread} + \text{slippage}$
     * SELL: $P_{\text{open}}[i+1] - \text{slippage}$
4. **Intra-Bar Simulation**: Ambiguous bars where both SL and TP are touched are resolved with pessimistic execution (`pessimistic_ambiguous_bars=True`), preferring Stop Loss.

---

## 2. POSITION CONCURRENCY AUDIT

- **Concurrency Rule**: `DeepQuantEngine` maintains an explicit single-position constraint (`active_trade is not None`), meaning only one position can be open at any time.
- **Impact on Trade Frequency**: During strongly trending or long-holding bars, new signals occurring during an active trade are skipped. This accurately reflects a realistic non-hedging execution architecture.
