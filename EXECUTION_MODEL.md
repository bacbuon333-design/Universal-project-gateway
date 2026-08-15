# EXECUTION MODEL & COST ACCOUNTING SPECIFICATION (AUDIT V2)

This document provides the exact mathematical and institutional specification of the execution engine, Bid/Ask pricing, spread deductions, commission accounting, and PnL conversions used in **DeepQuantEngine**.

---

## 1. INSTRUMENT & PRICING SPECIFICATIONS (XAUUSD / GOLD)

* **Base Currency**: USD
* **Contract Size**: $1.0\text{ Standard Lot} = 100\text{ Troy Ounces}$
* **Fixed Position Size**: $0.10\text{ Lot} = 10\text{ Troy Ounces}$
* **Price Precision**: $2\text{ Decimal Places}$ (e.g., $\$2,450.50$)
* **Pip Size (`pip_size`)**: $\$0.01$ (1 cent per ounce)
* **Point Value (`point_val`)**: $\$0.01$
* **Dollar Value per Pip**:
  $$\text{USD per Pip} = \text{pip\_size} \times \text{point\_val} \times \frac{\text{lots}}{0.01} = 0.01 \times 0.01 \times \frac{0.10}{0.01} = \$0.10\text{ USD / pip}$$
* **Dollar Value per \$1.00 Price Move**:
  $$\text{USD per \$1.00 Move} = \$1.00 \times 10\text{ oz} = \$10.00\text{ USD}$$

---

## 2. COST ACCOUNTING RULES

1. **Spread**:
   - Baseline Spread = $25.0\text{ pips} = \$0.25\text{ price width}$.
   - Cost per trade on $0.10\text{ lot} = 25\text{ pips} \times \$0.10/\text{pip} = \$2.50\text{ USD}$.
   - **Symmetry Rule**: Paid exactly ONCE per round-trip by both BUY and SELL positions.
2. **Commission**:
   - Institutional ECN Rate = $\$7.00\text{ USD per 1.0 standard lot round-turn}$.
   - Cost per trade on $0.10\text{ lot} = (0.10 / 1.0) \times \$7.00 = \$0.70\text{ USD}$.
3. **Slippage**:
   - Adverse slippage added to BUY entry / SELL exit (Ask) and subtracted from SELL entry / BUY exit (Bid).

---

## 3. BID / ASK ORDER EXECUTION FORMULAS

The historical OHLC series represents the **Bid** price.

### A. LONG (BUY) POSITIONS
* **Entry (Open Bar $i+1$)**:
  $$\text{Entry Price} = \text{Open}_{i+1} + \text{spread\_price} + \text{slippage\_price}\quad (\text{Executed at Ask})$$
* **Target Levels**:
  $$\text{SL Price} = \text{Entry Price} - \text{sl\_dist}$$
  $$\text{TP Price} = \text{Entry Price} + \text{tp\_dist}$$
* **Intrabar Trigger**:
  - SL Trigger: $\text{Low}_i \le \text{SL Price}$
  - TP Trigger: $\text{High}_i \ge \text{TP Price}$
* **Exit Price**:
  $$\text{Exit Price} = \text{Bid Price} - \text{slippage\_price}\quad (\text{Executed at Bid})$$
* **PnL Calculation**:
  $$\text{PnL (pts)} = \frac{\text{Exit Price} - \text{Entry Price}}{\text{pip\_size}}$$
  $$\text{PnL (USD)} = \left(\text{PnL (pts)} \times \text{point\_val} \times \frac{\text{lots}}{0.01}\right) - \text{commission\_usd}$$

---

### B. SHORT (SELL) POSITIONS
* **Entry (Open Bar $i+1$)**:
  $$\text{Entry Price} = \text{Open}_{i+1} - \text{slippage\_price}\quad (\text{Executed at Bid})$$
* **Target Levels (Target Ask Prices)**:
  $$\text{SL Price} = \text{Entry Price} + \text{sl\_dist}$$
  $$\text{TP Price} = \text{Entry Price} - \text{tp\_dist}$$
* **Intrabar Trigger (Ask Touches Target)**:
  - SL Trigger: $\text{High}_i + \text{spread\_price} \ge \text{SL Price}$
  - TP Trigger: $\text{Low}_i + \text{spread\_price} \le \text{TP Price}$
* **Exit Price (Buying Back at Ask)**:
  $$\text{Exit Price} = \text{Target Price} + \text{slippage\_price}\quad (\text{Executed at Ask})$$
* **PnL Calculation**:
  $$\text{PnL (pts)} = \frac{\text{Entry Price} - \text{Exit Price}}{\text{pip\_size}}$$
  $$\text{PnL (USD)} = \left(\text{PnL (pts)} \times \text{point\_val} \times \frac{\text{lots}}{0.01}\right) - \text{commission\_usd}$$

---

## 4. WORKED NUMERICAL EXAMPLES (0.10 LOT)

### Example 1: Long (BUY) Winning Trade
* **Assumptions**: Open = $\$100.00$, SL Dist = $\$5.00$ ($500\text{ pips}$), TP Dist = $\$5.00$ ($500\text{ pips}$), Spread = $25\text{ pips}$ ($\$0.25$), Slippage = $2\text{ pips}$ ($\$0.02$), Commission = $\$0.70$.
* **Execution**:
  - Entry Price: $100.00 + 0.25 + 0.02 = \$100.27$
  - TP Level: $100.27 + 5.00 = \$105.27$
  - Exit Price (Hit TP): $105.27 - 0.02 = \$105.25$
  - Points: $(105.25 - 100.27) / 0.01 = 498.0\text{ pips}$
  - Gross PnL: $498.0 \times \$0.10 = \$49.80\text{ USD}$
  - Net PnL: $\$49.80 - \$0.70\text{ (comm)} = \mathbf{+\$49.10\text{ USD}}$

### Example 2: Short (SELL) Winning Trade
* **Assumptions**: Open = $\$100.00$, SL Dist = $\$5.00$, TP Dist = $\$5.00$, Spread = $25\text{ pips}$ ($\$0.25$), Slippage = $2\text{ pips}$ ($\$0.02$), Commission = $\$0.70$.
* **Execution**:
  - Entry Price: $100.00 - 0.02 = \$99.98$
  - TP Level (Target Ask): $99.98 - 5.00 = \$94.98$
  - Exit Price (Hit TP): $94.98 + 0.02 = \$95.00$
  - Points: $(99.98 - 95.00) / 0.01 = 498.0\text{ pips}$
  - Gross PnL: $498.0 \times \$0.10 = \$49.80\text{ USD}$
  - Net PnL: $\$49.80 - \$0.70\text{ (comm)} = \mathbf{+\$49.10\text{ USD}}$

*(Both examples match unit test outputs in `test_engine_causality_and_integrity.py` to $< 0.0001$).*
