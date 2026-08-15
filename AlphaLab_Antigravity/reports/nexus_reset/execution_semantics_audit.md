# Execution Semantics Audit

Issues found:
- **Entry Issue:** Uses `h1c[i] + SPR*PIP` (market order at bar close + spread). This is unrealistic because the close price is already past. Real entry would be at open of next bar.
- **Exit Issue:** Uses `pos.sl` directly when `h1l[i] <= pos.sl`. This assumes perfect stop fill at exactly the SL price, ignoring slippage and gapping.
- **Future Leak:** Pivot detection uses `h1h[i] == max(h1h[i-5:i+6])` — this looks 5 bars FORWARD, which is a future leak in the pivot high/low calculation.
- **Spread Assumption:** Spread is fixed at 25 pips — Gold spread varies significantly during high-volatility events.
